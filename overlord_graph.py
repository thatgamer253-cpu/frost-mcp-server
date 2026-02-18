#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  OVERLORD — LangGraph Orchestration Graph
  
  Replaces the linear pipeline with a stateful graph that
  supports conditional routing: e.g. Security Guardian can
  reject code back to the Engineer for rework.

  Graph topology:
    prompt_engineer → architect → assembler → engineer
        → guardian ──┬─→ binary_architect → handoff → END
                     └─→ engineer (rejection loop, max 3)

══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import shutil
import asyncio
import datetime
from typing import TypedDict, Optional, Any, List, Dict

# ── LangGraph import (with graceful fallback) ───────────────
try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except ImportError:
    _HAS_LANGGRAPH = False
    print("⚠ langgraph not installed. Run: pip install langgraph")
    print("  Falling back to linear pipeline.")

# ── Local imports ────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from agent_brain import (
    log, divider, ask_llm,
    GlobalWisdom, WisdomGuard, ReviewerAgent, CodebaseState,
    ProjectState, CodebaseRAG, DependencyVerifier,
    CostTracker, KnowledgeBase, GoogleResearchAgent,
    DevKnowledgeAgent, SelfCorrectionModule,
    preflight_search, project_assembler,
    finalize_package, setup_agent, update_gallery,
    voice_briefing, get_cached_client,
    PLATFORM_PROFILES, resolve_mission_parameters,
)

# Import compilation node from the orchestrator
from overlord_orchestrator import (
    compilation_specialist_node,
    inject_resource_bridge,
    detect_project_type,
    PACKAGING_STRATEGY,
)

# Import build signer
try:
    from code_signer import sign_build
    _HAS_SIGNER = True
except ImportError:
    _HAS_SIGNER = False


# ── Assets & Music ───────────────────────────────────────────
try:
    from creation_engine.media_director import MediaDirectorAgent
    from creation_engine.music_alchemist import MusicAlchemistAgent
    from creation_engine.narrator import NarratorAgent
    from creation_engine.post_processor import MediaPostProcessor
    _HAS_ASSETS = True
except ImportError:
    _HAS_ASSETS = False

from creation_engine.architect import resolve_design

# ═══════════════════════════════════════════════════════════════
#  CONSTRAINT MEMORY — Persistent Learning from Past Failures
# ═══════════════════════════════════════════════════════════════

class ConstraintMemory:
    """
    Manages memory/permanent_constraints.json — the pipeline's
    persistent memory of past failures and learned rules.
    
    Loaded before every Guardian audit so the same mistakes are
    never repeated. Auto-learns from rejections.
    """

    def __init__(self, memory_dir: str = ""):
        if not memory_dir:
            memory_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "memory"
            )
        os.makedirs(memory_dir, exist_ok=True)
        self.path = os.path.join(memory_dir, "permanent_constraints.json")
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "project_heritage": [],
            "permanent_rules": [],
            "prohibited_patterns": [],
        }

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def get_rules_directive(self) -> str:
        """Format all rules into a string for LLM prompt injection."""
        rules = self.data.get("permanent_rules", [])
        patterns = self.data.get("prohibited_patterns", [])
        if not rules and not patterns:
            return ""

        lines = ["PERMANENT CONSTRAINTS (learned from past build failures):"]
        for r in rules:
            lines.append(f"  - [{r.get('id', '?')}] {r.get('issue', '?')}: {r.get('lesson', '')}")
        if patterns:
            lines.append("PROHIBITED PATTERNS:")
            for p in patterns:
                lines.append(f"  - {p}")
        return "\n".join(lines)

    def learn_from_rejection(self, audit_report: dict):
        """
        Extract failure patterns from a Guardian rejection and
        persist them as new permanent rules.
        """
        issues = audit_report.get("issues", [])
        if not issues:
            return

        existing_ids = {r.get("id") for r in self.data.get("permanent_rules", [])}
        new_count = 0

        for issue in issues:
            severity = issue.get("severity", "MEDIUM")
            if severity not in ("HIGH", "MEDIUM"):
                continue  # Only learn from significant failures

            # Generate a unique rule ID
            desc = issue.get("description", "Unknown")
            rule_id = f"AUTO-{len(existing_ids) + new_count + 1:03d}"

            # Dedup: skip if we already have a rule with the same description
            if any(r.get("issue", "").lower() == desc.lower() for r in self.data["permanent_rules"]):
                continue

            new_rule = {
                "id": rule_id,
                "issue": desc[:120],
                "lesson": issue.get("fix", "Avoid this pattern in future builds."),
                "enforcement": "Auto-learned from Guardian rejection",
                "learned_on": datetime.datetime.now().isoformat(),
                "source_file": issue.get("file", "unknown"),
            }
            self.data["permanent_rules"].append(new_rule)
            existing_ids.add(rule_id)
            new_count += 1

        if new_count > 0:
            self._save()
            log("MEMORY", f"  🧠 Learned {new_count} new constraint(s) from rejection")

    @property
    def rule_count(self) -> int:
        return len(self.data.get("permanent_rules", []))


# ═══════════════════════════════════════════════════════════════
#  AGENT STATE — The shared state dict flowing through the graph
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict, total=False):
    """Typed state dictionary passed between all graph nodes."""
    # ── Input ──
    args: Any                         # CLI args namespace
    prompt: str                       # Original user prompt
    enhanced_prompt: str              # AI-expanded prompt
    project_path: str                 # Output directory
    project_name: str                 # Slug name

    # ── Model Routing ──
    client: Any                       # OpenAI/Anthropic client
    arch_model: str
    eng_model: str
    local_model: str
    review_model: str

    # ── Architecture ──
    plan: dict                        # Architect JSON blueprint
    file_tree: list                   # List of file paths
    files: list                       # List of {path, task} dicts
    dependencies: list
    run_command: str
    stack: dict
    research_report: str

    # ── Engineering ──
    written_files: dict               # {filepath: code}
    tracker: Any                      # CostTracker instance
    wisdom: Any                       # GlobalWisdom instance

    # ── Security Guardian ──
    audit_report: dict                # {"status": "APPROVED"|"REJECTED", "issues": [...]}
    rejection_count: int              # How many times Guardian has rejected
    constraint_memory: Any            # ConstraintMemory instance

    # ── Performance Reviewer ──
    perf_report: dict                 # {"status": "OPTIMIZED"|"NEEDS_WORK", "suggestions": [...]}

    # ── Compilation ──
    compile_requested: bool
    final_binary_path: Optional[str]

    # ── Pulse-Sync ──
    pulse_context: str                # Developer's current vibe/focus

    # ── Handoff ──
    manifest: dict

    # ── Assets ──
    assets: List[str]                 # Generated media asset paths
    music_report: dict                # {"status": "COMPOSED", "track_path": "..."}
    narration_path: Optional[str]     # Path to synthesized voiceover
    production_path: Optional[str]    # Path to final mixed video
    signature_report: dict            # HMAC-SHA256 signature from code_signer


# ═══════════════════════════════════════════════════════════════
#  NODE: Prompt Engineer (Phase 0)
# ═══════════════════════════════════════════════════════════════

def prompt_engineer_node(state: AgentState) -> AgentState:
    """Phase 0: Enhance the user's raw prompt into a detailed spec."""
    log("GRAPH", "🧠 Node: Prompt Engineer")
    args = state["args"]
    client = state["client"]
    arch_model = state["arch_model"]

    platform = getattr(args, 'platform', 'python')
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["python"])
    platform_directive = profile["arch_directive"]

    # Pulse-Sync: inject developer context into the prompt
    pulse_directive = ""
    pulse_ctx = state.get("pulse_context", "")
    if pulse_ctx:
        pulse_directive = f"\n\nDEVELOPER CONTEXT (Pulse-Sync):\n{pulse_ctx}"
        log("GRAPH", "  💓 Pulse-Sync context injected into enhancement")

    enhance_system = (
        "You are 'Overlord Prompt Engineer,' an elite AI that transforms vague user ideas "
        "into detailed, comprehensive software engineering specifications. "
        "The user will give you a brief idea — maybe just a few words. "
        "Your job is to expand it into a DETAILED prompt that a code-generating AI can use to build "
        "a complete, production-quality application. "
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        f"{pulse_directive}"
        "\n\nYour enhanced prompt MUST include:"
        "\n1. A clear project description and purpose"
        "\n2. Specific features (at least 5-8 concrete features with details)"
        "\n3. Technical architecture (what modules/files should exist)"
        "\n4. UI/UX details if applicable"
        "\n5. Error handling and edge cases"
        "\n6. Data flow — how the pieces connect"
        "\n7. External libraries or APIs to use"
        "\n\nRules:"
        "\n- Output ONLY the enhanced prompt text. No markdown, no headers."
        "\n- Be specific with function names, UI elements, data structures."
        "\n- Keep it under 500 words but make every word count."
    )

    try:
        enhanced = ask_llm(client, arch_model, enhance_system, args.prompt)
        log("GRAPH", "  ✓ Prompt enhanced successfully")
        state["enhanced_prompt"] = enhanced
    except Exception as e:
        log("WARN", f"  Prompt enhancement failed: {e}. Using original.")
        state["enhanced_prompt"] = args.prompt

    # Pre-flight search
    search_results = preflight_search(args.prompt, state["enhanced_prompt"])
    search_context = search_results.get("search_context", "")

    # Deep Research + Memory
    kb = KnowledgeBase(os.path.join(os.path.dirname(state["project_path"]), "memory"))
    memory_ctx = kb.recall(state["enhanced_prompt"])

    dk_agent = DevKnowledgeAgent()
    dk_docs = dk_agent.lookup(state["enhanced_prompt"])
    if dk_docs:
        memory_ctx = dk_docs + "\n\n" + memory_ctx if memory_ctx else dk_docs

    research_agent = GoogleResearchAgent(client, arch_model)
    report = research_agent.run_research(state["enhanced_prompt"], kb_context=memory_ctx)
    if report and search_context:
        report += "\n\n" + search_context
    elif not report:
        report = search_context

    state["research_report"] = report or ""
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Architect (Phase 1)
# ═══════════════════════════════════════════════════════════════

def architect_node(state: AgentState) -> AgentState:
    """Phase 1: Generate the JSON blueprint (file tree, deps, stack)."""
    log("GRAPH", "📐 Node: Architect")
    client = state["client"]
    arch_model = state["arch_model"]
    args = state["args"]

    platform = getattr(args, 'platform', 'python')
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["python"])

    version_advisory = ""
    research = state.get("research_report", "")

    # Resolve Design System (Styles & Layouts)
    design_directive, layout_directive = resolve_design(state["enhanced_prompt"])
    design_context = ""
    if design_directive or layout_directive:
        design_context = (
            f"\n\nDESIGN SYSTEM DIRECTIVE:\n{design_directive}"
            f"{layout_directive}"
        )

    arch_system = (
        "You are 'Overlord,' an autonomous Senior Full-Stack Engineer. "
        "Mission: Decompose user intent into a logical file structure. "
        f"\n\nPLATFORM CONSTRAINT: {profile['arch_directive']} "
        f"{design_context}"
        f"\n\n{research if research else ''}"
        "\n\nOutput ONLY valid JSON with this schema: "
        '{"project_name": "<slug>", '
        '"project_type": "VIDEO | GAME | WEBSITE | TOOL | SCRIPT", '
        '"mission_summary": "<1-sentence goal>", '
        '"stack": {"frontend": "<fw>", "backend": "<fw>", "database": "<provider>"}, '
        '"file_tree": ["path/file.ext", ...], '
        '"files": [{"path": "filename.ext", "task": "description"}], '
        '"visuals": [{"prompt": "scene prompt", "filename": "asset.mp4"}], '
        '"audio": [{"prompt": "music/audio prompt", "filename": "track.mp3"}], '
        '"dependencies": ["package1"], '
        f'"run_command": "{profile["run_command"]}"}} '
        "\n\nRules:"
        "\n- Every project MUST include a main entry point and a README.md. "
        "\n- 'visuals' are cinematic prompts for video generation."
        "\n- 'audio' are atmospheric prompts for music synthesis."
        "\n- Output ONLY raw JSON. No markdown."
    )

    import re as _re
    plan = {}
    for attempt in range(3):
        try:
            raw = ask_llm(client, arch_model, arch_system, state["enhanced_prompt"])
            try:
                plan = json.loads(raw)
            except json.JSONDecodeError:
                # Recovery: extract files from conversational response
                files = []
                matches = _re.findall(r"(?:-|\d+\.)\s*([\w\-\./]+\.\w+)\s*[:\-]?\s*(.*)", raw)
                for fp, ft in matches:
                    if fp and "." in fp:
                        files.append({"path": fp.strip(), "task": ft.strip() or "Synthesis"})
                if files:
                    plan = {
                        "project_name": state["project_name"],
                        "files": files,
                        "file_tree": [f["path"] for f in files],
                        "dependencies": [],
                        "run_command": profile["run_command"],
                    }
                else:
                    raise
            break
        except Exception as e:
            log("ERROR", f"  Architect attempt {attempt+1} failed: {e}")
            if attempt == 2:
                log("CRITICAL", "  Architect failed after 3 attempts.")
                sys.exit(1)

    state["plan"] = plan
    state["files"] = plan.get("files", [])
    state["file_tree"] = plan.get("file_tree", [])
    state["dependencies"] = plan.get("dependencies", [])
    state["run_command"] = plan.get("run_command", "python main.py")
    state["stack"] = plan.get("stack", {})
    state["assets"] = [] # Initialize asset list

    # Log blueprint
    log("ARCHITECT", f"Blueprint ready — {len(state['files'])} file(s), {len(state['dependencies'])} dep(s)")
    for f in state["files"]:
        log("ARCHITECT", f"  ├─ {f['path']}  →  {f.get('task', '')[:60]}")

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Assembler (Phase 1.5)
# ═══════════════════════════════════════════════════════════════

def assembler_node(state: AgentState) -> AgentState:
    """Phase 1.5: Scaffold directories and empty files."""
    log("GRAPH", "🏗️  Node: Project Assembler")
    project_assembler(state["plan"], state["project_path"])
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Engineer (Phase 2 — Code Generation)
# ═══════════════════════════════════════════════════════════════

def engineer_node(state: AgentState) -> AgentState:
    """Phase 2: Generate code for each file in the blueprint."""
    rejection_count = state.get("rejection_count", 0)
    is_rework = rejection_count > 0

    if is_rework:
        log("GRAPH", f"⚙️  Node: Engineer (REWORK #{rejection_count})")
        log("ENGINEER", f"  Guardian rejected code. Fixing {len(state.get('audit_report', {}).get('issues', []))} issue(s)...")
    else:
        log("GRAPH", "⚙️  Node: Engineer")

    client = state["client"]
    eng_model = state["eng_model"]
    project_path = state["project_path"]
    files = state["files"]

    # Initialize wisdom system
    wisdom = GlobalWisdom(project_path)
    wisdom_guard = WisdomGuard()
    state["wisdom"] = wisdom

    written = state.get("written_files", {})

    # Build file context for cross-file awareness
    file_context = "\n".join([f"- {f['path']}: {f.get('task', '')}" for f in files])

    for f in files:
        filepath = f["path"]
        task = f.get("task", "Implement this file")

        # If rework, only regenerate files flagged by Guardian
        if is_rework:
            issues = state.get("audit_report", {}).get("issues", [])
            flagged_files = [i.get("file", "") for i in issues]
            if filepath not in flagged_files and written.get(filepath):
                continue  # Skip files not flagged

        # Build the system prompt
        eng_system = (
            f"You are 'Overlord Engineer.' Write COMPLETE, PRODUCTION-READY code for: {filepath}\n"
            f"Task: {task}\n"
            f"\nProject context (other files in this project):\n{file_context}\n"
            f"\nDependencies: {json.dumps(state['dependencies'])}\n"
        )

        # Add rework context if rejected
        if is_rework and state.get("audit_report"):
            relevant_issues = [i for i in state["audit_report"].get("issues", []) if i.get("file") == filepath]
            if relevant_issues:
                eng_system += "\n\n⚠️ SECURITY AUDIT FINDINGS (fix these):\n"
                for issue in relevant_issues:
                    eng_system += f"  - [{issue.get('severity', 'HIGH')}] {issue.get('description', '')}\n"
                    if issue.get("fix"):
                        eng_system += f"    Fix: {issue['fix']}\n"

        # Add existing code context
        if written.get(filepath) and is_rework:
            eng_system += f"\n\nCurrent code to fix:\n```\n{written[filepath]}\n```\n"
            eng_system += "\nOutput ONLY the complete fixed code. No explanations."
        else:
            eng_system += "\nOutput ONLY raw code. No markdown fences, no explanations."

        # Add wisdom rules
        rules_directive = wisdom.get_generation_rules_directive()
        if rules_directive:
            eng_system += f"\n\n{rules_directive}"

        try:
            code = ask_llm(client, eng_model, eng_system, state["enhanced_prompt"])

            # Strip markdown fences if present
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            # Wisdom guard auto-fix
            code, fixes = wisdom_guard.auto_fix(code, filepath)
            if fixes:
                log("WISDOM", f"  🛡️  Auto-fixed {len(fixes)} pattern(s) in {filepath}")

            # Self-correction (lint loop)
            corrector = SelfCorrectionModule(code, filepath)
            def _fixer(broken_code, error_report):
                fix_sys = (
                    f"Fix this code. Error: {error_report}\n"
                    "Output ONLY the corrected code."
                )
                return ask_llm(client, eng_model, fix_sys, broken_code)
            code = corrector.repair_loop(_fixer)

            # Write file
            full_path = os.path.join(project_path, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as fp:
                fp.write(code)

            written[filepath] = code
            log("ENGINEER", f"  ✓ {filepath} ({len(code)} chars)")

        except Exception as e:
            log("ERROR", f"  ✗ {filepath} failed: {e}")

    state["written_files"] = written
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Security Guardian (Phase 2.5 — Audit)
# ═══════════════════════════════════════════════════════════════

def guardian_node(state: AgentState) -> AgentState:
    """Phase 2.5: Security audit. Can reject code back to Engineer."""
    log("GRAPH", "🔒 Node: Security Guardian")
    client = state["client"]
    review_model = state.get("review_model", state["eng_model"])
    written = state.get("written_files", {})

    if not written:
        log("GUARDIAN", "  ⚠ No files to audit.")
        state["audit_report"] = {"status": "APPROVED", "issues": []}
        return state

    # Build files summary for the LLM
    code_summary = ""
    for filepath, code in written.items():
        if filepath.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            code_summary += f"\n--- {filepath} ---\n{code[:3000]}\n"

    if not code_summary:
        state["audit_report"] = {"status": "APPROVED", "issues": []}
        return state

    # ── Constraint Memory: inject past lessons into the audit prompt ──
    constraint_directive = ""
    cm = state.get("constraint_memory")
    if cm:
        constraint_directive = cm.get_rules_directive()
        if constraint_directive:
            log("GUARDIAN", f"  🧠 Loaded {cm.rule_count} permanent constraint(s)")

    guardian_system = (
        "You are 'Security Guardian,' a senior security engineer performing a code audit. "
        "Review the following codebase for:\n"
        "1. Hardcoded secrets or API keys\n"
        "2. SQL injection vulnerabilities\n"
        "3. Command injection (os.system, subprocess with shell=True)\n"
        "4. Path traversal attacks\n"
        "5. Insecure deserialization (pickle.loads, eval)\n"
        "6. Missing input validation\n"
        "7. Cross-site scripting (XSS) in web apps\n"
        "8. Insecure file permissions\n"
    )

    # Inject constraint memory into the audit prompt
    if constraint_directive:
        guardian_system += f"\n{constraint_directive}\n"

    guardian_system += (
        "\nOutput ONLY valid JSON:\n"
        '{"status": "APPROVED" or "REJECTED", '
        '"issues": [{"file": "path", "severity": "HIGH|MEDIUM|LOW", '
        '"description": "what is wrong", "fix": "how to fix it"}]}\n'
        "\nRules:\n"
        "- If ALL issues are LOW severity, status is APPROVED.\n"
        "- If ANY issue is HIGH or MEDIUM, status is REJECTED.\n"
        "- Be specific about file names and line patterns."
    )

    try:
        raw_result = ask_llm(client, review_model, guardian_system, code_summary[:15000])
        report = json.loads(raw_result)
        state["audit_report"] = report

        status = report.get("status", "APPROVED")
        issues = report.get("issues", [])

        if status == "REJECTED":
            log("GUARDIAN", f"  ❌ REJECTED — {len(issues)} issue(s) found:")
            for issue in issues[:5]:
                log("GUARDIAN", f"    [{issue.get('severity', '?')}] {issue.get('file', '?')}: {issue.get('description', '')[:80]}")
            state["rejection_count"] = state.get("rejection_count", 0) + 1

            # ── Constraint Learning: persist the failure so it's never repeated ──
            if cm:
                cm.learn_from_rejection(report)
        else:
            log("GUARDIAN", f"  ✅ APPROVED ({len(issues)} low-severity note(s))")

    except Exception as e:
        log("WARN", f"  Guardian audit failed: {e}. Auto-approving.")
        state["audit_report"] = {"status": "APPROVED", "issues": []}

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Performance Reviewer (Phase 3 — Advisory)
# ═══════════════════════════════════════════════════════════════

def performance_reviewer_node(state: AgentState) -> AgentState:
    """Phase 3: Advisory performance review. Logs suggestions but never blocks."""
    log("GRAPH", "⚡ Node: Performance Reviewer")
    client = state["client"]
    review_model = state.get("review_model", state["eng_model"])
    written = state.get("written_files", {})

    if not written:
        log("PERF", "  ⚠ No files to review.")
        state["perf_report"] = {"status": "OPTIMIZED", "suggestions": []}
        return state

    # Build code summary (same pattern as Guardian)
    code_summary = ""
    for filepath, code in written.items():
        if filepath.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            code_summary += f"\n--- {filepath} ---\n{code[:3000]}\n"

    if not code_summary:
        state["perf_report"] = {"status": "OPTIMIZED", "suggestions": []}
        return state

    perf_system = (
        "You are 'Performance Reviewer,' a senior performance engineer. "
        "Review the following codebase for performance anti-patterns:\n"
        "1. Blocking/synchronous I/O in async or web server contexts\n"
        "2. N+1 query patterns (loading related data inside loops)\n"
        "3. Unbounded loops or recursive calls without limits\n"
        "4. Missing connection pooling for databases or HTTP clients\n"
        "5. Heavy computation on the main thread (should be offloaded)\n"
        "6. Unnecessary re-reads of files or repeated API calls\n"
        "7. Missing caching for expensive operations\n"
        "8. Large in-memory collections that could cause OOM\n"
        "\nOutput ONLY valid JSON:\n"
        '{"status": "OPTIMIZED" or "NEEDS_WORK", '
        '"suggestions": [{"file": "path", "category": "blocking_io|n_plus_1|unbounded_loop|'
        'missing_pooling|main_thread_compute|redundant_io|missing_cache|memory_risk", '
        '"description": "what is suboptimal", "recommendation": "how to improve it"}]}\n'
        "\nRules:\n"
        "- Be specific about file names and code patterns.\n"
        "- Only flag real performance concerns, not style issues.\n"
        "- If the code is reasonably performant, status is OPTIMIZED."
    )

    try:
        raw_result = ask_llm(client, review_model, perf_system, code_summary[:15000])
        report = json.loads(raw_result)
        state["perf_report"] = report

        status = report.get("status", "OPTIMIZED")
        suggestions = report.get("suggestions", [])

        if status == "NEEDS_WORK":
            log("PERF", f"  📊 {len(suggestions)} performance suggestion(s):")
            for s in suggestions[:5]:
                log("PERF", f"    [{s.get('category', '?')}] {s.get('file', '?')}: {s.get('description', '')[:80]}")
        else:
            log("PERF", f"  ✅ Code looks performant ({len(suggestions)} minor note(s))")

    except Exception as e:
        log("WARN", f"  Performance review failed: {e}. Skipping.")
        state["perf_report"] = {"status": "OPTIMIZED", "suggestions": []}

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Media Director (Phase 3.5 — Assets)
# ═══════════════════════════════════════════════════════════════

def media_director_node(state: AgentState) -> AgentState:
    """Phase 3.5: Asset generation (Videos)."""
    log("GRAPH", "🎨 Node: Media Director")
    plan = state.get("plan", {})
    visuals = plan.get("visuals", [])
    project_path = state.get("project_path", "")
    assets_dir = os.path.join(project_path, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    if not visuals:
        log("MEDIA", "  ⚠ No visuals in blueprint.")
        return state

    if not _HAS_ASSETS:
        log("WARN", "  Asset generation modules not found.")
        return state

    assets = state.get("assets", [])
    director = MediaDirectorAgent()
    
    # Run async-in-sync
    async def process_visuals():
        for i, visual in enumerate(visuals, 1):
            prompt = visual.get("prompt", "")
            filename = visual.get("filename", f"asset_{i}.mp4")
            if not prompt: continue

            log("MEDIA", f"  [{i}/{len(visuals)}] Generating: {filename}")
            try:
                # Try Luma cinematic video
                video_path = await director.create_cinematic_video(
                    prompt, assets_dir, filename
                )
                if video_path:
                    assets.append(f"./assets/{filename}")
            except Exception as e:
                log("MEDIA", f"    ✗ Failed: {e}")

    asyncio.run(process_visuals())
    state["assets"] = assets
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Music Alchemist (Phase 3.6 — Audio)
# ═══════════════════════════════════════════════════════════════

def music_alchemist_node(state: AgentState) -> AgentState:
    """Phase 3.6: Asset generation (Audio/Music)."""
    log("GRAPH", "🎵 Node: Music Alchemist")
    plan = state.get("plan", {})
    audio_specs = plan.get("audio", [])
    project_path = state.get("project_path", "")
    assets_dir = os.path.join(project_path, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    if not audio_specs:
        log("ALCHEMIST", "  ⚠ No audio specs in blueprint.")
        return state

    if not _HAS_ASSETS:
        log("WARN", "  MusicAlchemistAgent not found.")
        return state

    assets = state.get("assets", [])
    alchemist = MusicAlchemistAgent()

    async def process_audio():
        for i, spec in enumerate(audio_specs, 1):
            prompt = spec.get("prompt", "")
            filename = spec.get("filename", f"track_{i}.mp3")
            if not prompt: continue

            log("ALCHEMIST", f"  [{i}/{len(audio_specs)}] Synthesizing: {filename}")
            try:
                track_path = await alchemist.generate_ambient_track(
                    prompt, duration=30, save_dir=assets_dir, filename=filename
                )
                if track_path:
                    assets.append(f"./assets/{filename}")
                    state["music_report"] = {"status": "COMPOSED", "track_path": track_path}
            except Exception as e:
                log("ALCHEMIST", f"    ✗ Failed: {e}")

    asyncio.run(process_audio())
    state["assets"] = assets
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Narrator (Phase 3.7 — Voiceover)
# ═══════════════════════════════════════════════════════════════

def narrator_node(state: AgentState) -> AgentState:
    """Phase 3.7: Generate narration script and audio."""
    log("GRAPH", "🎤 Node: Narrator")
    if not _HAS_ASSETS:
        return state

    project_path = state["project_path"]
    assets_dir = os.path.join(project_path, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    narrator = NarratorAgent(model=state["eng_model"])
    
    # Use mission and blueprint for script context
    context = (
        f"Project: {state['project_name']}\n"
        f"Mission: {state['enhanced_prompt']}\n"
        f"Files: {', '.join(state['file_tree'][:10])}"
    )

    async def run_narration():
        script = await narrator.generate_script(state["client"], context)
        audio_path = await narrator.synthesize_speech(script, assets_dir, "narration.mp3")
        if audio_path:
            state["narration_path"] = audio_path
            # Add to manifest assets
            state["assets"].append("./assets/narration.mp3")

    asyncio.run(run_narration())
    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Post-Production (Phase 3.8 — Mixing)
# ═══════════════════════════════════════════════════════════════

def post_production_node(state: AgentState) -> AgentState:
    """Phase 3.8: Final media mixing (Video + Audio + Subs)."""
    log("GRAPH", "🎬 Node: Post-Production")
    if not _HAS_ASSETS:
        return state

    project_path = state["project_path"]
    assets_dir = os.path.join(project_path, "assets")
    
    # Identify primary video
    video_path = None
    for asset in state.get("assets", []):
        if asset.endswith(".mp4"):
            video_path = os.path.join(project_path, asset.replace("./", ""))
            break

    if not video_path:
        log("PRODUCER", "  ⚠ No source video found for mixing.")
        return state

    producer = MediaPostProcessor(output_dir=project_path)
    
    # Get music if available
    music_path = state.get("music_report", {}).get("track_path")
    narration_path = state.get("narration_path")

    # Simple subtitle from mission summary
    subtitles = [
        {"text": state["project_name"], "start": 0, "end": 3, "position": ("center", "top"), "font_size": 48},
        {"text": "Generated by Overlord", "start": 3, "end": 6, "position": ("center", "bottom")},
    ]

    final_path = producer.process_video(
        video_path=video_path,
        narration_path=narration_path,
        music_path=music_path,
        subtitles=subtitles,
        output_filename="final_production.mp4"
    )

    if final_path:
        state["production_path"] = final_path
        state["assets"].append("./final_production.mp4")

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Binary Architect (Phase 6 — Compilation)
# ═══════════════════════════════════════════════════════════════

def binary_architect_node(state: AgentState) -> AgentState:
    """Phase 6: Compile to standalone EXE using Nuitka/PyInstaller."""
    if not state.get("compile_requested", False):
        log("GRAPH", "💎 Node: Binary Architect (skipped — not requested)")
        return state

    log("GRAPH", "💎 Node: Binary Architect")
    project_dir = state["project_path"]
    project_name = state["project_name"]

    # Inject Resource Bridge
    inject_resource_bridge(project_dir)

    # Run async compilation
    binary_path = asyncio.run(
        compilation_specialist_node(project_dir, project_name)
    )

    if binary_path:
        state["final_binary_path"] = binary_path
        log("COMPILE", f"  ✅ EXE delivered: {binary_path}")
    else:
        log("COMPILE", "  ⚠ Compilation failed. Project source still available.")

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Handoff (Final Phase)
# ═══════════════════════════════════════════════════════════════

def handoff_node(state: AgentState) -> AgentState:
    """Final phase: Generate FULL_PACKAGE.md and gallery entry."""
    log("GRAPH", "🤝 Node: Handoff")
    args = state["args"]
    project_path = state["project_path"]
    written = state.get("written_files", {})

    # Setup Agent (scripts + docker-compose)
    if getattr(args, 'setup', False):
        setup_agent(project_path, written, state.get("dependencies", []), state.get("run_command", "python main.py"))

    # Finalize Package
    try:
        client = state["client"]
        model = state.get("local_model", state["eng_model"])
        finalize_package(
            project_path, written,
            arch_stack=state.get("stack"),
            arch_file_tree=state.get("file_tree"),
            deps=state.get("dependencies"),
            run_cmd=state.get("run_command", "python main.py"),
            prompt=state.get("enhanced_prompt", ""),
            client=client, model=model,
        )
    except Exception as e:
        log("WARN", f"  Handoff packaging failed: {e}")

    # Summary
    log("GRAPH", f"  ✓ Handoff complete — {len(written)} file(s)")
    if state.get("final_binary_path"):
        log("GRAPH", f"  💎 Binary: {state['final_binary_path']}")

    return state


# ═══════════════════════════════════════════════════════════════
#  NODE: Build Signing (Final — Cryptographic Provenance)
# ═══════════════════════════════════════════════════════════════

def signing_node(state: AgentState) -> AgentState:
    """Sign the build output with HMAC-SHA256 for tamper-evident provenance."""
    if not _HAS_SIGNER:
        log("GRAPH", "✍️  Node: Build Signing (skipped — code_signer not available)")
        state["signature_report"] = {}
        return state

    log("GRAPH", "✍️  Node: Build Signing")
    project_dir = state["project_path"]

    extra_meta = {
        "project_name": state.get("project_name", "unknown"),
        "prompt": state.get("prompt", "")[:200],
        "guardian_verdict": state.get("audit_report", {}).get("status", "UNKNOWN"),
        "perf_status": state.get("perf_report", {}).get("status", "UNKNOWN"),
        "rejection_count": state.get("rejection_count", 0),
    }

    if state.get("final_binary_path"):
        extra_meta["binary"] = state["final_binary_path"]

    try:
        report = sign_build(
            project_dir=project_dir,
            signer_id="Donovan",
            extra_metadata=extra_meta,
        )
        state["signature_report"] = report
        log("SIGNER", f"  ✅ BUILD_SIGNATURE.json written ({report.get('files_signed', 0)} files)")
    except Exception as e:
        log("WARN", f"  Build signing failed: {e}")
        state["signature_report"] = {}

    return state


# ═══════════════════════════════════════════════════════════════
#  CONDITIONAL EDGE: Guardian Decision Router
# ═══════════════════════════════════════════════════════════════

MAX_REJECTION_LOOPS = 3

def guardian_router(state: AgentState) -> str:
    """Route based on Guardian's audit verdict."""
    report = state.get("audit_report", {})
    status = report.get("status", "APPROVED")
    rejection_count = state.get("rejection_count", 0)

    if status == "REJECTED" and rejection_count < MAX_REJECTION_LOOPS:
        log("GRAPH", f"  🔄 Routing back to Engineer (rejection {rejection_count}/{MAX_REJECTION_LOOPS})")
        return "engineer"
    elif status == "REJECTED":
        log("GRAPH", f"  ⚠ Max rejections reached ({MAX_REJECTION_LOOPS}). Proceeding anyway.")
        return "performance_reviewer"
    else:
        return "performance_reviewer"


# ═══════════════════════════════════════════════════════════════
#  GRAPH BUILDER — Assemble the StateGraph
# ═══════════════════════════════════════════════════════════════

def build_factory():
    """
    Build the LangGraph orchestration graph.

    Topology:
        prompt_engineer → architect → assembler → engineer
            → guardian ──┬─→ performance_reviewer → binary_architect
                         │     → handoff → signing → END
                         └─→ engineer (rejection loop)
    """
    if not _HAS_LANGGRAPH:
        raise ImportError("langgraph is required. Install with: pip install langgraph")

    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("prompt_engineer", prompt_engineer_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("assembler", assembler_node)
    workflow.add_node("engineer", engineer_node)
    workflow.add_node("media_director", media_director_node)
    workflow.add_node("music_alchemist", music_alchemist_node)
    workflow.add_node("guardian", guardian_node)
    workflow.add_node("performance_reviewer", performance_reviewer_node)
    workflow.add_node("binary_architect", binary_architect_node)
    workflow.add_node("signing", signing_node)
    workflow.add_node("handoff", handoff_node)
    workflow.add_node("narrator", narrator_node)
    workflow.add_node("post_production", post_production_node)

    # 2. Define Linear Edges
    workflow.set_entry_point("prompt_engineer")
    workflow.add_edge("prompt_engineer", "architect")
    workflow.add_edge("architect", "assembler")
    workflow.add_edge("assembler", "engineer")
    workflow.add_edge("engineer", "media_director")
    workflow.add_edge("media_director", "music_alchemist")
    workflow.add_edge("music_alchemist", "narrator")
    workflow.add_edge("narrator", "post_production")
    workflow.add_edge("post_production", "guardian")

    # 3. Conditional Edge: Guardian → Engineer (rejection) or Performance Reviewer (approved)
    workflow.add_conditional_edges(
        "guardian",
        guardian_router,
        {
            "engineer": "engineer",
            "performance_reviewer": "performance_reviewer",
        }
    )

    # 4. Post-approval pipeline
    workflow.add_edge("performance_reviewer", "binary_architect")
    workflow.add_edge("binary_architect", "handoff")
    workflow.add_edge("handoff", "signing")
    workflow.add_edge("signing", END)

    return workflow.compile()


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT — Run the graph from CLI args
# ═══════════════════════════════════════════════════════════════

def run_graph(args) -> AgentState:
    """
    Execute the LangGraph pipeline with the given CLI args.
    Returns the final AgentState.
    """
    log("GRAPH", "═" * 52)
    log("GRAPH", "  LANGGRAPH ORCHESTRATION ENGINE")
    log("GRAPH", "═" * 52)

    # Resolve mission parameters (platform, scale, phase)
    resolve_mission_parameters(args)

    # Resolve models
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    model = args.model if args.model != "auto" else "gpt-4o"
    arch_model = getattr(args, 'arch_model', None) or model
    eng_model = getattr(args, 'eng_model', None) or model
    local_model = getattr(args, 'local_model', None) or eng_model
    review_model = getattr(args, 'review_model', None) or local_model

    # Create client
    client = get_cached_client(arch_model, api_key)

    # Initialize cost tracker
    budget = getattr(args, 'budget', 5.0) or 5.0
    tracker = CostTracker(budget=float(budget))

    # Set up project path
    project_path = os.path.join(args.output, args.project)
    os.makedirs(project_path, exist_ok=True)

    # Pulse-Sync: load developer context
    pulse_context = ""
    try:
        from pulse_sync_logger import PulseSyncLogger
        pulse = PulseSyncLogger(project_root=os.path.dirname(os.path.abspath(__file__)))
        pulse.capture_heartbeat()
        pulse_context = pulse.get_context_for_orchestrator()
        if pulse_context:
            log("GRAPH", "💓 Pulse-Sync: Developer context loaded")
    except Exception:
        pass

    # Load Constraint Memory
    constraint_mem = ConstraintMemory()
    log("GRAPH", f"🧠 Constraint Memory: {constraint_mem.rule_count} permanent rule(s) loaded")

    # Build initial state
    initial_state: AgentState = {
        "args": args,
        "prompt": args.prompt,
        "enhanced_prompt": args.prompt,
        "project_path": project_path,
        "project_name": args.project,
        "client": client,
        "arch_model": arch_model,
        "eng_model": eng_model,
        "local_model": local_model,
        "review_model": review_model,
        "plan": {},
        "file_tree": [],
        "files": [],
        "dependencies": [],
        "run_command": "python main.py",
        "stack": {},
        "research_report": "",
        "written_files": {},
        "tracker": tracker,
        "wisdom": None,
        "audit_report": {"status": "PENDING", "issues": []},
        "rejection_count": 0,
        "constraint_memory": constraint_mem,
        "perf_report": {"status": "PENDING", "suggestions": []},
        "compile_requested": getattr(args, 'compile', False),
        "final_binary_path": None,
        "pulse_context": pulse_context,
        "manifest": {},
        "signature_report": {},
    }

    # Build and run the graph
    graph = build_factory()

    log("GRAPH", "")
    log("GRAPH", "  📊 Graph topology:")
    log("GRAPH", "    prompt_engineer → architect → assembler → engineer")
    log("GRAPH", "        → guardian ──┬─→ perf_reviewer → binary_architect")
    log("GRAPH", "                     │     → handoff → signing → END")
    log("GRAPH", "                     └─→ engineer (rejection loop, max 3)")
    log("GRAPH", "")
    divider()

    # Execute
    final_state = graph.invoke(initial_state)
    return final_state


# ═══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not _HAS_LANGGRAPH:
        print("❌ Cannot run graph mode without langgraph. Install: pip install langgraph")
        sys.exit(1)

    print("✓ LangGraph orchestration module loaded successfully.")
    print("  Use: from overlord_graph import run_graph, build_factory")
    print("  Or run via overlord_orchestrator.py --graph")
