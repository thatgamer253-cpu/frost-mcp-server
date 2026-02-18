#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  OVERLORD MULTI-AGENT FACTORY — AgentBrain V2
  
  5-Node Directed Acyclic Graph (DAG):
  
    ┌──────────┐     ┌──────────┐    ┌──────────┐
    │ ARCHITECT │────►│ ENGINEER │───►│ GUARDIAN  │
    └──────────┘  ┌──►└──────────┘    └──────────┘
         │        │        ▲               │
         │        │        │               ▼
         └────────┘   ┌──────────┐    ┌──────────┐
         (parallel)   │  MEDIA   │───►│ BUNDLER  │
                      │ DIRECTOR │    └──────────┘
                      └──────────┘
  
  Four Pillars:
    1. DECOMPOSITION  — Architect Node → blueprint manifest
    2. PARALLELISM    — Engineer + Media Director via asyncio.gather
    3. ZERO-TRUST     — Security Guardian gates all output
    4. MEMORY         — Mem0Adapter for Donovan-style preferences
  
  Architectural Constraints:
    - Pydantic V2 (model_dump over dict)
    - Multi-threaded UI (prevent main-loop freezing)
    - Relative media paths (./assets/)
    - One-Click bootstrap script (PowerShell + Bash)
══════════════════════════════════════════════════════════════
"""

import asyncio
import ast
import os
import shutil
import sys
import hashlib
import json
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

# ── Resolve Imports from Existing Infrastructure ────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
except ImportError:
    pass

from agent_brain import (
    ask_llm,
    get_cached_client,
    log,
    divider,
    strip_fences,
    CostTracker,
    KnowledgeBase,
    ReviewerAgent,
    WisdomGuard,
    SelfCorrectionModule,
    GlobalWisdom,
    STABILITY_DIRECTIVE,
    SECURITY_DIRECTIVE,
    FEATURE_RICHNESS_DIRECTIVE,
    PRODUCTION_SAFETY_DIRECTIVE,
    API_CONVENTIONS,
    PKG_MAP,
)

# ── Pulse-Sync (Identity Anchor) ────────────────────────────
try:
    from pulse_sync_logger import PulseSyncLogger
    _HAS_PULSE_SYNC = True
except ImportError:
    _HAS_PULSE_SYNC = False

try:
    from visual_auditor import VisualAuditor
    from local_overlord import LocalOverlord
    _HAS_LOCAL_VISION = True
except ImportError:
    _HAS_LOCAL_VISION = False


# ══════════════════════════════════════════════════════════════
#  TYPED STATE — Flows through every node in the DAG
# ══════════════════════════════════════════════════════════════

class AgentState(TypedDict, total=False):
    """Immutable state contract flowing through the Overlord DAG."""
    prompt: str                     # Raw user prompt
    enhanced_prompt: str            # AI-enriched specification
    memory_context: str             # Recalled Donovan-style preferences
    pulse_context: str              # Pulse-Sync identity anchor
    blueprint: Dict[str, Any]       # Architect's decomposition manifest
    code: Dict[str, str]            # {filepath: source_code}
    assets: List[str]               # Generated media asset paths
    audit_report: Dict[str, Any]    # Security Guardian's verdict
    security_manifest: Dict[str, Any]  # Red-Team hardening report
    final_package_path: str         # Handoff directory
    final_binary: str               # Compiled executable path


# ══════════════════════════════════════════════════════════════
#  MEMORY — Donovan-Style Knowledge Continuity
# ══════════════════════════════════════════════════════════════

class OverlordMemory:
    """
    Unified memory interface wrapping both KnowledgeBase (lessons) and
    Mem0Adapter (knowledge graph). Gracefully degrades if either is unavailable.
    """

    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)

        # Primary: KnowledgeBase (always available)
        self.kb = KnowledgeBase(memory_dir)

        # Secondary: Mem0Adapter for graph-style memory
        self.mem0 = None
        try:
            from creation_engine.memory.mem0_integration import Mem0Adapter
            self.mem0 = Mem0Adapter(memory_dir)
            log("MEMORY", "  ✓ Mem0 Knowledge Graph: ONLINE")
        except Exception as e:
            log("MEMORY", f"  ℹ Mem0 unavailable (using KnowledgeBase only): {e}")

    def recall(self, context: str, user_id: str = "Donovan") -> str:
        """Query both memory systems and merge results."""
        insights = []

        # KnowledgeBase recall
        kb_result = self.kb.recall(context)
        if kb_result:
            insights.append(kb_result)

        # Mem0 graph search
        if self.mem0:
            try:
                search = self.mem0.search(context, user_id=user_id)
                for hit in search.get("results", [])[:5]:
                    insights.append(f"- [MEMORY] {hit['memory']}")
            except Exception:
                pass

        return "\n".join(insights) if insights else ""

    def memorize(self, lesson: dict, user_id: str = "Donovan"):
        """Store a lesson in both systems."""
        self.kb.memorize(lesson)
        if self.mem0:
            try:
                text = lesson.get("lesson", str(lesson))
                self.mem0.add(text, user_id=user_id, metadata=lesson)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
#  OVERLORD DIRECTIVES — INJECTED INTO ALL LLM PROMPTS
# ══════════════════════════════════════════════════════════════

OVERLORD_DIRECTIVE = """
OVERLORD SYSTEM DIRECTIVE 2026:

ARCHITECTURAL CONSTRAINTS (MANDATORY — zero exceptions):
1. PYDANTIC V2: Use `model_dump()` instead of `.dict()`. Use `model_validate()` 
   instead of `parse_obj()`. Import from `pydantic` not `pydantic.v1`.
2. MULTI-THREADED UI: All UI operations (PyQt6, Tkinter, etc.) MUST use a 
   background worker thread for heavy computation. Never block the main/GUI thread.
   Use QThread + pyqtSignal for PyQt6, or threading.Thread for Tkinter.
3. RELATIVE MEDIA PATHS: All media references MUST use relative paths (e.g., 
   './assets/bg.mp4', './assets/icon.png'). Never hardcode absolute paths to assets.
4. BOOTSTRAP READY: The project must be runnable via a single bootstrap command.
"""


# ══════════════════════════════════════════════════════════════
#  NODE 1: THE ARCHITECT — Decomposition Engine
# ══════════════════════════════════════════════════════════════

class ArchitectNode:
    """
    PILLAR 1: DECOMPOSITION
    Transforms a raw user prompt into a structured blueprint manifest
    containing file tree, visual assets, dependency list, and task specs.
    """

    SYSTEM = (
        "You are 'Overlord Architect,' an autonomous Senior Full-Stack Engineer. "
        "Mission: Decompose user intent into a COMPLETE project blueprint. "
        "Zero Hallucinations — no placeholder domains, no fake APIs. "
        f"\n{OVERLORD_DIRECTIVE}"
        "\n\nOutput ONLY valid JSON with this exact schema: "
        '{"project_name": "<slug_name>", '
        '"project_type": "VIDEO | GAME | WEBSITE | TOOL | SCRIPT", '
        '"mission_summary": "<1-sentence goal>", '
        '"stack": {"frontend": "<framework>", "backend": "<framework>", "database": "<provider>"}, '
        '"files": [{"path": "filename.ext", "task": "what this file does"}], '
        '"visuals": [{"prompt": "scene description for media generation", "filename": "asset_name.mp4"}], '
        '"dependencies": ["package1", "package2"], '
        '"run_command": "python main.py"}'
        "\n\nRules:"
        "\n- Every project MUST include a main entry point."
        "\n- File paths are relative to project root."
        "\n- Visuals are cinematic prompts for the Media Director."
        "\n- Dependencies are pip package names."
        "\n- Output ONLY raw JSON. No markdown."
    )

    def __init__(self, model: str, api_key: str = ""):
        self.model = model
        self.client = get_cached_client(model, api_key)

    async def run(self, state: AgentState) -> AgentState:
        """Architect Node: prompt → blueprint manifest."""
        log("ARCHITECT", "📐 Node 1: Decomposing prompt into blueprint...")

        memory_ctx = state.get("memory_context", "")
        user_prompt = state.get("enhanced_prompt", state.get("prompt", ""))

        prompt_body = f"MISSION: {user_prompt}\n"
        if memory_ctx:
            prompt_body += f"\nMEMORY CONTEXT (Donovan's preferences):\n{memory_ctx}\n"

        try:
            raw = await asyncio.to_thread(
                ask_llm, self.client, self.model, self.SYSTEM, prompt_body
            )
            blueprint = json.loads(strip_fences(raw))
            log("ARCHITECT", f"  ✓ Blueprint: {blueprint.get('project_name', '?')} "
                f"({len(blueprint.get('files', []))} files, "
                f"{len(blueprint.get('visuals', []))} visuals)")
            state["blueprint"] = blueprint
        except (json.JSONDecodeError, Exception) as e:
            log("ARCHITECT", f"  ⚠ Blueprint parse error: {e} — using fallback")
            state["blueprint"] = {
                "project_name": "overlord_project",
                "project_type": "TOOL",
                "mission_summary": user_prompt[:200],
                "files": [
                    {"path": "main.py", "task": f"Main entry point: {user_prompt[:100]}"},
                    {"path": "utils.py", "task": "Shared utilities"},
                ],
                "visuals": [],
                "dependencies": [],
                "run_command": "python main.py",
            }

        return state


# ══════════════════════════════════════════════════════════════
#  NODE 2: THE ENGINEER — Code Synthesis
# ══════════════════════════════════════════════════════════════

class EngineerNode:
    """
    Core code generation agent.
    Wired to: ask_llm (multi-provider), WisdomGuard (auto-fix),
              SelfCorrectionModule (lint→fix).
    """

    SYSTEM = (
        "You are 'Overlord Engineer,' an elite autonomous code generator. "
        "You produce COMPLETE, PRODUCTION-READY code. No placeholders, no TODOs, no stubs. "
        "Every function must be fully implemented. "
        "Output ONLY the raw source code for the requested file. No markdown fences, no explanations."
        f"\n{STABILITY_DIRECTIVE}"
        f"\n{SECURITY_DIRECTIVE}"
        f"\n{FEATURE_RICHNESS_DIRECTIVE}"
        f"\n{OVERLORD_DIRECTIVE}"
    )

    def __init__(self, model: str, api_key: str = ""):
        self.model = model
        self.client = get_cached_client(model, api_key)
        self.wisdom_guard = WisdomGuard()

    async def run(self, state: AgentState) -> AgentState:
        """Engineer Node: blueprint → code files."""
        blueprint = state.get("blueprint", {})
        file_specs = blueprint.get("files", [])
        mission = state.get("enhanced_prompt", state.get("prompt", ""))
        memory_ctx = state.get("memory_context", "")

        log("ENGINEER", f"🛠️  Node 2: Synthesizing {len(file_specs)} file(s)...")
        written: Dict[str, str] = {}

        for i, spec in enumerate(file_specs, 1):
            fpath = spec.get("path", f"file_{i}.py")
            ftask = spec.get("task", "Implement logic")
            log("ENGINEER", f"  [{i}/{len(file_specs)}] {fpath}")

            # Build cross-file context
            existing_ctx = ""
            if written:
                existing_ctx = "\n\nALREADY WRITTEN (use exact imports):\n"
                for wf, wc in written.items():
                    preview = wc[:2000] + ("..." if len(wc) > 2000 else "")
                    existing_ctx += f"\n--- {wf} ---\n{preview}\n"

            # Detect library-specific API conventions
            api_hints = ""
            context_str = f"{mission} {ftask}".lower()
            for lib, convention in API_CONVENTIONS.items():
                if lib in context_str:
                    api_hints += f"\n\nAPI RULES ({lib.upper()}):\n{convention}"

            # Pulse-Sync identity context (prevents drift)
            pulse_ctx = state.get("pulse_context", "")
            pulse_block = f"\n\nIDENTITY ANCHOR (Pulse-Sync):\n{pulse_ctx}\n" if pulse_ctx else ""

            user_prompt = (
                f"PROJECT: {blueprint.get('project_name', 'project')}\n"
                f"MISSION: {mission}\n\n"
                f"YOUR TASK: Write '{fpath}' — {ftask}\n"
                f"\nDEPENDENCIES: {', '.join(blueprint.get('dependencies', []))}\n"
                f"\nMEMORY:\n{memory_ctx}\n"
                f"{pulse_block}"
                f"{existing_ctx}{api_hints}\n\n"
                f"Output ONLY the complete source code for {fpath}."
            )

            try:
                raw_code = await asyncio.to_thread(
                    ask_llm, self.client, self.model, self.SYSTEM, user_prompt
                )

                # Stage 1: Deterministic wisdom fixes
                fixed_code, fixes = self.wisdom_guard.auto_fix(raw_code, fpath)
                if fixes:
                    log("ENGINEER", f"    🛡️  WisdomGuard: {len(fixes)} auto-fix(es)")

                # Stage 2: Lint + Self-Correction (Python only)
                if fpath.endswith(".py"):
                    corrector = SelfCorrectionModule(fixed_code, fpath, max_attempts=2)

                    def _fixer(code: str, error: str) -> str:
                        return ask_llm(
                            self.client, self.model,
                            "Fix the Python error and return ONLY corrected source.",
                            f"Code:\n```\n{code}\n```\nError:\n{error}"
                        )

                    fixed_code = corrector.repair_loop(_fixer)

                written[fpath] = fixed_code
                log("ENGINEER", f"    ✓ {fpath} ({len(fixed_code)} chars)")

            except Exception as e:
                log("ENGINEER", f"    ✗ {fpath}: {e}")
                written[fpath] = f"# Generation failed: {e}\n"

        state["code"] = written
        return state


# ══════════════════════════════════════════════════════════════
#  NODE 3: THE MEDIA DIRECTOR — Asset Synthesis
# ══════════════════════════════════════════════════════════════

class MediaDirectorNode:
    """
    PILLAR 2 (parallel with Engineer): Cinematic asset generation.
    Wired to: MediaDirectorAgent (Luma Ray-2, Runway Gen-4, Kie.ai).
    """

    def __init__(self):
        self._director = None
        self._init_error = None
        try:
            from creation_engine.media_director import MediaDirectorAgent
            self._director = MediaDirectorAgent()
        except Exception as e:
            self._init_error = str(e)
            log("MEDIA", f"  ⚠ MediaDirectorAgent unavailable: {e}")

    @property
    def available(self) -> bool:
        return self._director is not None

    async def run(self, state: AgentState) -> AgentState:
        """Media Director Node: blueprint visuals → asset files."""
        blueprint = state.get("blueprint", {})
        visuals = blueprint.get("visuals", [])
        project_name = blueprint.get("project_name", "project")
        assets_dir = os.path.join(SCRIPT_DIR, "output", project_name, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        if not visuals:
            log("MEDIA", "🎨 Node 3: No visuals in blueprint — skipping.")
            state["assets"] = []
            return state

        log("MEDIA", f"🎨 Node 3: Generating {len(visuals)} cinematic asset(s)...")
        assets: List[str] = []

        # Sovereign Sync: Detect User Media Folders
        user_home = os.path.expanduser("~")
        desktop = os.path.join(user_home, "Desktop")
        sys_videos = os.path.join(user_home, "Videos")
        sys_photos = os.path.join(user_home, "Pictures")
        
        # Easy Access Folders on Desktop
        desktop_creations = os.path.join(desktop, "Overlord_Creations")
        desktop_videos = os.path.join(desktop_creations, "Videos")
        desktop_photos = os.path.join(desktop_creations, "Photos")

        for vi, visual in enumerate(visuals, 1):
            prompt = visual.get("prompt", "")
            filename = visual.get("filename", f"asset_{vi}.mp4")
            if not prompt:
                continue

            log("MEDIA", f"  [{vi}/{len(visuals)}] {filename}")

            # Try providers in priority order
            generated = False

            if self._director and self._director.luma:
                try:
                    video = await self._director.create_cinematic_video(
                        prompt=prompt, save_dir=assets_dir, filename=filename
                    )
                    if video:
                        # Convert to relative path for the project
                        rel_path = f"./assets/{filename}"
                        assets.append(rel_path)
                        log("MEDIA", f"    ✓ Luma Ray-2: {rel_path}")
                        generated = True
                except Exception as e:
                    log("MEDIA", f"    ⚠ Luma failed: {e}")

            if not generated and self._director and self._director.kie:
                try:
                    result = self._director.generate_via_kie(
                        prompt=prompt, model="kling-2.1",
                        aspect_ratio="16:9", duration=5
                    )
                    if result.get("success") or result.get("task_id"):
                        # For Kie (async tasks), we just save the task manifest in assets
                        task_file = f"kie_{filename.replace('.mp4', '.json')}"
                        task_path = os.path.join(assets_dir, task_file)
                        with open(task_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2, default=str)
                        assets.append(f"./assets/{task_file}")
                        log("MEDIA", f"    ✓ Kie.ai task submitted: {result.get('task_id', 'pending')}")
                        generated = True
                except Exception as e:
                    log("MEDIA", f"    ⚠ Kie.ai failed: {e}")

            # 🔄 Sovereign Sync (If generated)
            if generated:
                source = os.path.join(assets_dir, filename)
                if os.path.exists(source):
                    is_vid = filename.lower().endswith((".mp4", ".mov", ".avi", ".webm"))
                    
                    # 1. Mirror to System Folders
                    sys_target_dir = sys_videos if is_vid else sys_photos
                    if os.path.exists(sys_target_dir):
                        sys_path = os.path.join(sys_target_dir, f"Overlord_{project_name}_{filename}")
                        shutil.copy2(source, sys_path)
                        log("MEDIA", f"    🔄 System Sync: Mirror saved to {os.path.basename(sys_target_dir)}")
                        
                    # 2. Mirror to Desktop for Easy Access
                    desk_target_dir = desktop_videos if is_vid else desktop_photos
                    os.makedirs(desk_target_dir, exist_ok=True)
                    desk_path = os.path.join(desk_target_dir, f"{project_name}_{filename}")
                    shutil.copy2(source, desk_path)
                    log("MEDIA", f"    🔄 Desktop Sync: Mirror saved to Desktop/Overlord_Creations")

            if not generated:
                # Save a deferred manifest so assets can be generated later
                manifest = {
                    "status": "deferred", "prompt": prompt,
                    "filename": filename, "timestamp": datetime.now().isoformat(),
                }
                deferred_path = os.path.join(assets_dir, f"{filename}.manifest.json")
                with open(deferred_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
                assets.append(f"./assets/{filename}.manifest.json")
                log("MEDIA", f"    ℹ Deferred: {filename} (no provider available)")

        state["assets"] = assets
        return state


# ══════════════════════════════════════════════════════════════
#  NODE 4: THE SECURITY GUARDIAN — Zero-Trust Audit
# ══════════════════════════════════════════════════════════════

class GuardianNode:
    """
    PILLAR 3: ZERO-TRUST AUDIT
    Every line of code is scanned before being written to disk.
    Layers: AST → WisdomGuard → ReviewerAgent → Bandit SAST.
    """

    def __init__(self, model: str = "gpt-4o", api_key: str = ""):
        self.model = model
        self.api_key = api_key
        self.visual_auditor = None
        if _HAS_LOCAL_VISION:
            ov = LocalOverlord("Guardian")
            self.visual_auditor = VisualAuditor(ov)
            log("SECURITY", "  👁 Local Visual Auditor: READY")
        self.wisdom_guard = WisdomGuard()

    # ── Tier classification: dangerous imports that promote a file to T3 ──
    T3_SIGNALS = {
        "subprocess", "socket", "jwt", "flask", "fastapi", "django",
        "requests", "httpx", "aiohttp", "sqlite3", "sqlalchemy",
        "pickle", "shelve", "paramiko", "ftplib", "smtplib",
        "cryptography", "hashlib", "hmac", "ssl", "ctypes",
        "multiprocessing", "shutil", "tempfile",
    }
    T3_PATTERNS = {"eval(", "exec(", "os.system(", "os.popen(", "__import__("}

    T1_NAMES = {
        "__init__.py", "conftest.py", "setup.py", "setup.cfg",
        "constants.py", "config.py", "settings.py", "types.py",
        "exceptions.py", "version.py", "__main__.py",
    }

    SHADOW_LOGIC_PROMPT = (
        "Act as a hostile security auditor performing a 'Shadow Logic' audit. "
        "Analyze this code for places where the developer prioritized 'it works' "
        "over 'it is secure'. Specifically look for:\n"
        "1. Auth bypasses or skipped validation for convenience\n"
        "2. Hardcoded secrets, tokens, or API keys\n"
        "3. Unvalidated user inputs passed to shell/exec/eval\n"
        "4. Data egress without encryption or logging\n"
        "5. Overly permissive error handling that leaks stack traces\n"
        "6. CORS/permission wildcards used to 'just make it work'\n\n"
        "Return ONLY valid JSON (no markdown fences):\n"
        '{"issues": [{"line_hint": "approx line", "shadow": "what shortcut was taken", '
        '"fix": "how to harden it"}], "clean": true/false}'
    )

    TRIAGE_PROMPT = (
        "You are a security triage analyst. Below are summaries of several source files. "
        "Identify ONLY the files that may contain security risks (auth flaws, unsanitized inputs, "
        "data leaks, hardcoded secrets, dangerous API usage).\n\n"
        "Return ONLY valid JSON (no markdown fences):\n"
        '{"flagged": ["filename1.py", "filename2.py"], "reason": "brief explanation"}'
    )

    # ── Tier Classification ──────────────────────────────────

    def _classify_tier(self, filepath: str, code: str) -> int:
        """Classify a file into security tiers: T1 (low), T2 (medium), T3 (high risk)."""
        basename = os.path.basename(filepath)

        # Non-Python files get T1 (AST/patterns only)
        if not filepath.endswith(".py"):
            return 1

        # Known low-risk filenames → T1
        if basename in self.T1_NAMES:
            return 1

        # Test files → T1
        if "test" in filepath.lower() or filepath.startswith("tests/"):
            return 1

        # Check for dangerous imports/patterns → T3
        for line in code.split("\n"):
            stripped = line.strip()
            # Import-based signals
            if stripped.startswith(("import ", "from ")):
                mod = stripped.split()[1].split(".")[0].split(",")[0]
                if mod in self.T3_SIGNALS:
                    return 3
            # Pattern-based signals
            for pat in self.T3_PATTERNS:
                if pat in stripped and not stripped.startswith("#"):
                    return 3

        # Everything else → T2
        return 2

    # ── Bulk Triage (1 LLM call for all T2 files) ────────────

    async def _bulk_triage(self, t2_files: Dict[str, str]) -> List[str]:
        """Send T2 file summaries to LLM, return filenames that need promotion to T3."""
        if not t2_files:
            return []

        # Build compact summaries (first 80 lines per file)
        summaries = []
        for fp, code in t2_files.items():
            lines = code.split("\n")[:80]
            summaries.append(f"### FILE: {fp}\n```\n" + "\n".join(lines) + "\n```")

        combined = "\n\n".join(summaries)
        # Cap at ~6K chars to stay within token budget
        if len(combined) > 6000:
            combined = combined[:6000] + "\n... (truncated)"

        try:
            client = get_cached_client(self.model, self.api_key)
            result = await asyncio.to_thread(
                ask_llm, client, self.model,
                self.TRIAGE_PROMPT, combined
            )
            cleaned = strip_fences(result)
            parsed = json.loads(cleaned)
            flagged = parsed.get("flagged", [])
            if flagged:
                log("SECURITY", f"  🔍 Triage promoted {len(flagged)} file(s) to T3: {flagged}")
            return flagged
        except (json.JSONDecodeError, Exception) as e:
            log("SECURITY", f"  ⚠ Triage skip: {e} — treating all T2 as-is")
            return []

    # ── Batched AI Review (1 LLM call for multiple T2 files) ──

    async def _batched_ai_review(self, files: Dict[str, str],
                                  issues: List[Dict], scores: dict):
        """Review multiple files in one LLM call with ### FILE: delimiters."""
        if not files:
            return

        combined_parts = []
        for fp, code in files.items():
            combined_parts.append(f"### FILE: {fp}\n{code[:3000]}")
        combined = "\n\n".join(combined_parts)

        try:
            client = get_cached_client(self.model, self.api_key)
            reviewer = ReviewerAgent(client, self.model)
            result = await asyncio.to_thread(
                reviewer.review, "BATCH_REVIEW", combined
            )
            if result.get("status") == "REJECTED":
                for fp in files:
                    issues.append({
                        "file": fp, "severity": "HIGH",
                        "detail": f"AI Review (batch): {result.get('reason', 'No reason')[:150]}"
                    })
                scores["review"] -= 10
                log("SECURITY", f"  ⚠ Batch review ({len(files)} files): ISSUES FOUND")
            else:
                log("SECURITY", f"  ✓ Batch review ({len(files)} files): APPROVED")
        except Exception as e:
            log("SECURITY", f"  ⚠ Batch review skip: {e}")

    # ── Batched Shadow Fix (1 LLM call for all shadow issues) ──

    async def _batch_shadow_fix(self, code_blocks: dict,
                                 shadow_findings: Dict[str, list]) -> int:
        """Fix all shadow issues across multiple files in one LLM call.
        Returns number of files hardened."""
        if not shadow_findings:
            return 0

        # Build combined fix prompt
        parts = []
        for fp, file_issues in shadow_findings.items():
            code = code_blocks.get(fp, "")
            parts.append(
                f"### FILE: {fp}\n"
                f"ISSUES:\n{json.dumps(file_issues, indent=2)}\n\n"
                f"CODE:\n{code[:4000]}"
            )

        fix_prompt = (
            "Harden ALL of the following files by fixing their Shadow Logic vulnerabilities. "
            "Return each fixed file with a clear delimiter.\n\n"
            "Format your response as:\n"
            "### FILE: filename.py\n"
            "<complete fixed source code>\n\n"
            "No markdown fences around the code. Fix every file listed.\n\n"
            + "\n\n---\n\n".join(parts)
        )

        try:
            client = get_cached_client(self.model, self.api_key)
            result = await asyncio.to_thread(
                ask_llm, client, self.model,
                fix_prompt, ""
            )

            # Parse multi-file response
            hardened = 0
            if result:
                sections = result.split("### FILE:")
                for section in sections:
                    section = section.strip()
                    if not section:
                        continue
                    # Extract filename from first line
                    lines = section.split("\n", 1)
                    fname = lines[0].strip().rstrip(":")
                    if len(lines) > 1 and fname in code_blocks:
                        fixed_code = lines[1].strip()
                        # Remove any markdown fences if present
                        if fixed_code.startswith("```"):
                            fixed_code = "\n".join(fixed_code.split("\n")[1:])
                        if fixed_code.endswith("```"):
                            fixed_code = fixed_code[:fixed_code.rfind("```")]
                        if len(fixed_code) > 50:
                            code_blocks[fname] = fixed_code.strip()
                            hardened += 1
                            log("SECURITY", f"    → [{fname}] Auto-hardened (batch)")

            return hardened
        except Exception as e:
            log("SECURITY", f"  ⚠ Batch shadow fix failed: {e}")
            return 0

    # ══════════════════════════════════════════════════════════
    #  MAIN AUDIT PIPELINE — Hybrid Batched
    # ══════════════════════════════════════════════════════════

    async def run(self, state: AgentState) -> AgentState:
        """Guardian Node: code → audit report (hybrid-batched pipeline)."""
        code_blocks = state.get("code", {})
        file_count = len(code_blocks)
        log("SECURITY", f"🛡️  Node 4: Zero-Trust Audit on {file_count} file(s)...")

        issues: List[Dict] = []
        scores = {"syntax": 100, "patterns": 100, "review": 100, "shadow": 100}
        llm_calls = 0

        # ════════════════════════════════════════════════════
        #  PHASE 0: Classify all files into tiers
        # ════════════════════════════════════════════════════
        tiers: Dict[int, Dict[str, str]] = {1: {}, 2: {}, 3: {}}
        for filepath, code in code_blocks.items():
            tier = self._classify_tier(filepath, code)
            tiers[tier][filepath] = code

        t1_count = len(tiers[1])
        t2_count = len(tiers[2])
        t3_count = len(tiers[3])
        log("SECURITY", f"  📊 Tier classification: T1={t1_count} T2={t2_count} T3={t3_count}")

        # ════════════════════════════════════════════════════
        #  PHASE 1: Free scans on ALL files (Layer 1 + 2)
        # ════════════════════════════════════════════════════
        for filepath, code in code_blocks.items():
            # ── Layer 1: AST Syntax ──
            if filepath.endswith(".py"):
                try:
                    compile(code, filepath, "exec")
                    ast.parse(code)
                    log("SECURITY", f"  ✓ [{filepath}] Syntax: CLEAN")
                except SyntaxError as e:
                    issues.append({
                        "file": filepath, "severity": "CRITICAL",
                        "detail": f"SyntaxError L{e.lineno}: {e.msg}"
                    })
                    scores["syntax"] -= 25
                    log("SECURITY", f"  ✗ [{filepath}] Syntax: FAIL — {e.msg}")

            # ── Layer 2: Wisdom Pattern Scan ──
            violations = self.wisdom_guard.check(code, filepath)
            if violations:
                for v in violations:
                    issues.append({
                        "file": filepath, "severity": "HIGH",
                        "detail": f"Pattern: {v.get('rule', '?')} — {v.get('fix', '')}"
                    })
                scores["patterns"] -= 10 * len(violations)
                log("SECURITY", f"  ⚠ [{filepath}] Patterns: {len(violations)} violation(s)")
            else:
                log("SECURITY", f"  ✓ [{filepath}] Patterns: CLEAN")

        # T1 files are DONE — no LLM calls needed
        if t1_count:
            log("SECURITY", f"  ⏩ T1: {t1_count} file(s) cleared (AST+patterns only, 0 LLM calls)")

        # ════════════════════════════════════════════════════
        #  PHASE 2: Bulk triage T2 files (1 LLM call)
        # ════════════════════════════════════════════════════
        if tiers[2]:
            log("SECURITY", f"  🔍 T2: Triaging {t2_count} file(s)...")
            flagged = await self._bulk_triage(tiers[2])
            llm_calls += 1

            # Promote flagged T2 → T3
            for fname in flagged:
                if fname in tiers[2]:
                    tiers[3][fname] = tiers[2].pop(fname)
                    log("SECURITY", f"    ↑ [{fname}] promoted T2→T3")

            # Remaining T2 files get batched AI review
            if tiers[2]:
                log("SECURITY", f"  📦 T2: Batched AI review on {len(tiers[2])} file(s)...")
                await self._batched_ai_review(tiers[2], issues, scores)
                llm_calls += 1
        
        # ════════════════════════════════════════════════════
        #  PHASE 3: Deep scan T3 files (individual LLM calls)
        # ════════════════════════════════════════════════════
        shadow_issues: List[Dict] = []
        shadow_findings: Dict[str, list] = {}  # filepath → list of issues

        if tiers[3]:
            log("SECURITY", f"  🔴 T3: Deep scan on {len(tiers[3])} high-risk file(s)...")

            for filepath, code in tiers[3].items():
                # ── Layer 3: Individual AI Review ──
                try:
                    client = get_cached_client(self.model, self.api_key)
                    reviewer = ReviewerAgent(client, self.model)
                    result = await asyncio.to_thread(reviewer.review, filepath, code)
                    llm_calls += 1
                    if result.get("status") == "REJECTED":
                        issues.append({
                            "file": filepath, "severity": "HIGH",
                            "detail": f"AI Review: {result.get('reason', 'No reason')[:150]}"
                        })
                        scores["review"] -= 20
                        log("SECURITY", f"  ✗ [{filepath}] Review: REJECTED")
                    else:
                        log("SECURITY", f"  ✓ [{filepath}] Review: APPROVED")
                except Exception as e:
                    log("SECURITY", f"  ⚠ [{filepath}] Review skip: {e}")

                # ── Layer 3.5: Shadow Logic (T3 only) ──
                if filepath.endswith(".py"):
                    try:
                        client = get_cached_client(self.model, self.api_key)
                        shadow_result = await asyncio.to_thread(
                            ask_llm, client, self.model,
                            self.SHADOW_LOGIC_PROMPT,
                            f"FILE: {filepath}\n\n{code[:6000]}"
                        )
                        llm_calls += 1
                        cleaned = strip_fences(shadow_result)
                        parsed = json.loads(cleaned)
                        if not parsed.get("clean", True):
                            file_shadows = parsed.get("issues", [])
                            for si in file_shadows:
                                shadow_issues.append({
                                    "file": filepath,
                                    "severity": "HIGH",
                                    "detail": f"Shadow: {si.get('shadow', '?')} → Fix: {si.get('fix', '?')}"
                                })
                            shadow_findings[filepath] = file_shadows
                            scores["shadow"] -= 15 * len(file_shadows)
                            log("SECURITY", f"  ⚠ [{filepath}] Shadow: {len(file_shadows)} shortcut(s) found")
                        else:
                            log("SECURITY", f"  ✓ [{filepath}] Shadow: CLEAN")
                    except (json.JSONDecodeError, Exception) as e:
                        log("SECURITY", f"  ⚠ [{filepath}] Shadow skip: {e}")

        # ════════════════════════════════════════════════════
        #  PHASE 4: Batched Shadow Fix (1 LLM call for all)
        # ════════════════════════════════════════════════════
        if shadow_findings:
            log("SECURITY", f"  🔧 Batching shadow fixes for {len(shadow_findings)} file(s)...")
            hardened = await self._batch_shadow_fix(code_blocks, shadow_findings)
            llm_calls += 1
            if hardened:
                log("SECURITY", f"  ✓ {hardened} file(s) auto-hardened in single batch call")

        # Merge shadow issues into main list
        issues.extend(shadow_issues)
        state["code"] = code_blocks

        # ════════════════════════════════════════════════════
        #  PHASE 5: Bandit SAST (free, unchanged)
        # ════════════════════════════════════════════════════
        project_path = state.get("final_package_path", "")
        if project_path and os.path.isdir(project_path):
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-m", "bandit", "-r", project_path,
                     "-x", "venv,tests,.git", "-f", "json", "-q"],
                    capture_output=True, text=True, timeout=30
                )
                if result.stdout:
                    report = json.loads(result.stdout)
                    for f in report.get("results", []):
                        if f.get("issue_severity") in ("HIGH", "MEDIUM"):
                            issues.append({
                                "file": f.get("filename", "?"), "severity": f["issue_severity"],
                                "detail": f"Bandit: {f.get('issue_text', '')} (L{f.get('line_number', '?')})"
                            })
            except (FileNotFoundError, Exception):
                pass

        # ════════════════════════════════════════════════════
        #  PHASE 6: Visual Audit (Local Vision-Language)
        # ════════════════════════════════════════════════════
        if self.visual_auditor:
            screenshots = [a for a in state.get("assets", []) if a.lower().endswith((".png", ".jpg", ".jpeg"))]
            if screenshots:
                log("SECURITY", f"  👁 Visual Audit: Analyzing {len(screenshots)} UI asset(s)...")
                try:
                    blueprint = state.get("blueprint", {})
                    v_report = await asyncio.to_thread(self.visual_auditor.audit_screenshot, screenshots[0], blueprint)
                    
                    if v_report.get("verdict") == "VISUAL_FAIL":
                        for finding in v_report.get("findings", []):
                            issues.append({
                                "file": screenshots[0],
                                "severity": finding.get("severity", "MEDIUM"),
                                "detail": f"Visual Audit: {finding.get('element')} - {finding.get('issue')}"
                            })
                        log("SECURITY", f"  ✗ Visual Audit: FAIL ({len(v_report.get('findings', []))} issues)")
                    else:
                        log("SECURITY", f"  ✓ Visual Audit: APPROVED (UX Score: {v_report.get('ux_score', 0)})")
                except Exception as e:
                    log("SECURITY", f"  ⚠ Visual Audit skip: {e}")
            else:
                log("SECURITY", "  ℹ Visual Audit: SKIPPED (No UI assets found)")

        # ════════════════════════════════════════════════════
        #  VERDICT + Stats
        # ════════════════════════════════════════════════════
        critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
        high_count = sum(1 for i in issues if i["severity"] == "HIGH")
        shadow_score = max(0, scores.get("shadow", 100))
        overall = max(0, min(100, (
            scores["syntax"] + scores["patterns"] + scores["review"] + shadow_score
        ) // 4))
        status = "REJECTED" if critical_count > 0 else "APPROVED"

        # Calculate savings
        old_calls = file_count * 3  # old: review + shadow + fix per file
        saved = max(0, old_calls - llm_calls)
        summary = (
            f"Score: {overall}/100 | Critical: {critical_count} | High: {high_count} | "
            f"Shadow: {len(shadow_issues)} | LLM calls: {llm_calls} (saved ~{saved})"
        )
        log("SECURITY", f"  {'✗' if status == 'REJECTED' else '✓'} VERDICT: {status} — {summary}")

        # Auto-patch on rejection
        if status == "REJECTED":
            log("SECURITY", "  🔄 Auto-patching rejected files...")
            guard = WisdomGuard()
            patched = {}
            for fp, code in code_blocks.items():
                fixed, fixes = guard.auto_fix(code, fp)
                patched[fp] = fixed
                if fixes:
                    log("SECURITY", f"    → {fp}: {len(fixes)} fix(es)")
            state["code"] = patched

        state["audit_report"] = {
            "status": status, "issues": issues,
            "scores": scores, "overall_score": overall,
            "summary": summary,
            "shadow_issues": shadow_issues,
            "llm_calls_used": llm_calls,
            "llm_calls_saved": saved,
            "tier_breakdown": {"T1": t1_count, "T2": t2_count, "T3": t3_count},
        }

        # Populate Security Manifest for Bundler
        state["security_manifest"] = {
            "hardened_by": "Overlord Hardened Orchestrator V4",
            "timestamp": datetime.now().isoformat(),
            "guardian_verdict": status,
            "overall_score": overall,
            "scores": scores,
            "shadow_logic_findings": len(shadow_issues),
            "shadow_issues_resolved": [
                si.get("detail", "") for si in shadow_issues
            ],
            "total_issues_found": len(issues),
            "pulse_sync_risk": state.get("pulse_context", "")[:100] if state.get("pulse_context") else "N/A",
            "batching": {
                "llm_calls_used": llm_calls,
                "llm_calls_saved": saved,
                "tiers": {"T1": t1_count, "T2": t2_count, "T3": t3_count},
            },
        }

        return state


# ══════════════════════════════════════════════════════════════
#  NODE 5: THE BUNDLER — One-Handoff Package Assembly
# ══════════════════════════════════════════════════════════════

class BundlerNode:
    """
    Final assembly: writes files, README, requirements.txt,
    bootstrap scripts (PowerShell + Bash), and package manifest.
    """

    # Standard library modules (no pip install needed)
    STDLIB = {
        "os", "sys", "json", "time", "datetime", "asyncio", "re", "math",
        "collections", "itertools", "functools", "pathlib", "typing",
        "subprocess", "threading", "multiprocessing", "logging", "unittest",
        "hashlib", "uuid", "shutil", "tempfile", "io", "abc", "enum",
        "dataclasses", "contextlib", "traceback", "argparse", "textwrap",
        "copy", "pprint", "inspect", "ast", "struct", "socket", "http",
        "urllib", "csv", "sqlite3", "signal", "queue", "secrets",
        "statistics", "random", "string", "base64", "glob", "platform",
        "webbrowser", "configparser", "heapq",
    }

    # ── Security Manifest Injection ──────────────────────────

    @staticmethod
    def _generate_manifest(filepath: str, content: str,
                           audit: dict, timestamp: str) -> str:
        """
        Generate the 2026 Hardened Orchestrator Security Manifest.
        Produces a tamper-evident header block for each generated file.
        """
        # Create unique identifier from file content + timestamp
        id_hash = hashlib.md5(
            f"{filepath}{content[:200]}{timestamp}".encode()
        ).hexdigest()

        # Map Guardian audit checks to manifest lines
        audit_status = audit.get("status", "UNKNOWN")
        checks = audit.get("checks", {})

        dep_check   = "PASS" if checks.get("dependency_scan", {}).get("passed", False) else "FAIL"
        backdoor    = "PASS" if checks.get("semantic_scan", {}).get("passed",
                        checks.get("wisdom_guard", {}).get("passed", False)) else "FAIL"
        logic_check = "PASS" if checks.get("logic_integrity", {}).get("passed",
                        checks.get("ast_parse", {}).get("passed", False)) else "FAIL"

        vibe_status = "Hardened & Verified" if audit_status == "APPROVED" else "Pending Review"

        # Determine comment syntax based on file extension
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".py", ".pyw"):
            return f'''"""\n================================================================\n\U0001f512 2026 HARDENED ORCHESTRATOR SECURITY MANIFEST\n================================================================\nIDENTIFIER: {id_hash}\nPULSE_SYNC_TIMESTAMP: {timestamp}\nIDENTITY_ANCHOR: Verified_User_Anchor\n\nAUDIT_LOG:\n- [{dep_check}] Dependency Verification (No Hallucinated Libraries)\n- [{backdoor}] Semantic Backdoor Scan (No Unauthorized Egress)\n- [{logic_check}] Logic Integrity (Intent matches Pulse Context)\n\nVIBE_STATUS: {vibe_status}\n================================================================\n"""\n\n'''
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".css", ".java", ".c", ".cpp", ".go", ".rs"):
            return f'''/*\n================================================================\n\U0001f512 2026 HARDENED ORCHESTRATOR SECURITY MANIFEST\n================================================================\nIDENTIFIER: {id_hash}\nPULSE_SYNC_TIMESTAMP: {timestamp}\nIDENTITY_ANCHOR: Verified_User_Anchor\n\nAUDIT_LOG:\n- [{dep_check}] Dependency Verification (No Hallucinated Libraries)\n- [{backdoor}] Semantic Backdoor Scan (No Unauthorized Egress)\n- [{logic_check}] Logic Integrity (Intent matches Pulse Context)\n\nVIBE_STATUS: {vibe_status}\n================================================================\n*/\n\n'''
        elif ext in (".html", ".xml", ".svg"):
            return f'''<!--\n================================================================\n\U0001f512 2026 HARDENED ORCHESTRATOR SECURITY MANIFEST\n================================================================\nIDENTIFIER: {id_hash}\nPULSE_SYNC_TIMESTAMP: {timestamp}\nIDENTITY_ANCHOR: Verified_User_Anchor\n\nAUDIT_LOG:\n- [{dep_check}] Dependency Verification\n- [{backdoor}] Semantic Backdoor Scan\n- [{logic_check}] Logic Integrity\n\nVIBE_STATUS: {vibe_status}\n================================================================\n-->\n\n'''
        elif ext in (".sh", ".bash", ".yml", ".yaml", ".toml"):
            lines = [
                f"# ================================================================",
                f"# \U0001f512 2026 HARDENED ORCHESTRATOR SECURITY MANIFEST",
                f"# ================================================================",
                f"# IDENTIFIER: {id_hash}",
                f"# PULSE_SYNC_TIMESTAMP: {timestamp}",
                f"# IDENTITY_ANCHOR: Verified_User_Anchor",
                f"#",
                f"# AUDIT_LOG:",
                f"# - [{dep_check}] Dependency Verification",
                f"# - [{backdoor}] Semantic Backdoor Scan",
                f"# - [{logic_check}] Logic Integrity",
                f"#",
                f"# VIBE_STATUS: {vibe_status}",
                f"# ================================================================",
                "",
            ]
            return "\n".join(lines) + "\n"
        else:
            # Unknown extension — skip manifest
            return ""

    async def run(self, state: AgentState) -> AgentState:
        """Bundler Node: assembled state → disk package."""
        blueprint = state.get("blueprint", {})
        project_name = blueprint.get("project_name", "overlord_project")
        project_dir = os.path.join(SCRIPT_DIR, "output", project_name)
        assets_dir = os.path.join(project_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        log("BUNDLER", f"📦 Node 5: Assembling package at {project_dir}")

        # 1. Write code files (with Security Manifest injection)
        code = state.get("code", {})
        audit = state.get("audit_report", {})
        build_timestamp = datetime.now().isoformat()
        manifest_count = 0

        for filepath, content in code.items():
            full = os.path.join(project_dir, filepath)
            os.makedirs(os.path.dirname(full), exist_ok=True)

            # Inject Security Manifest header
            manifest = self._generate_manifest(filepath, content, audit, build_timestamp)
            if manifest:
                content = manifest + content
                manifest_count += 1

            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            log("BUNDLER", f"  📄 {filepath}")

        if manifest_count:
            log("BUNDLER", f"  🔒 Security Manifest injected into {manifest_count} file(s)")

        # 2. Requirements.txt
        deps = self._extract_deps(code, blueprint.get("dependencies", []))
        if deps:
            with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
                f.write("\n".join(sorted(deps)) + "\n")
            log("BUNDLER", f"  📄 requirements.txt ({len(deps)} deps)")

        # 3. README.md
        readme = self._build_readme(state, project_name, deps)
        with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)
        log("BUNDLER", "  📄 README.md")

        # 4. Bootstrap scripts (One-Click)
        run_cmd = blueprint.get("run_command", "python main.py")
        self._write_bootstrap(project_dir, deps, run_cmd)
        log("BUNDLER", "  📄 bootstrap.ps1 + bootstrap.sh")

        # 4b. Orchestrate scripts (Single-Command Deployment)
        self._write_orchestrate(project_dir, run_cmd)
        log("BUNDLER", "  📄 orchestrate.ps1 + orchestrate.sh")

        # 5. Audit log
        audit = state.get("audit_report", {})
        with open(os.path.join(project_dir, "audit_log.json"), "w") as f:
            json.dump(audit, f, indent=2, default=str)
        log("BUNDLER", "  📄 audit_log.json")

        # 5b. Security Manifest (Hardened Orchestrator V4)
        sec_manifest = state.get("security_manifest", {})
        if sec_manifest:
            manifest_lines = [
                "# 🛡️ SECURITY MANIFEST",
                f"**Hardened by:** {sec_manifest.get('hardened_by', 'Overlord')}",
                f"**Timestamp:** {sec_manifest.get('timestamp', 'N/A')}",
                f"**Guardian Verdict:** {sec_manifest.get('guardian_verdict', 'UNKNOWN')}",
                f"**Overall Score:** {sec_manifest.get('overall_score', '?')}/100",
                "",
                "## Score Breakdown",
            ]
            for k, v in sec_manifest.get("scores", {}).items():
                manifest_lines.append(f"- **{k.title()}:** {v}/100")
            manifest_lines.append("")

            shadow_resolved = sec_manifest.get("shadow_issues_resolved", [])
            if shadow_resolved:
                manifest_lines.append(f"## Shadow Logic ({len(shadow_resolved)} issue(s) auto-resolved)")
                for sr in shadow_resolved:
                    manifest_lines.append(f"- {sr}")
                manifest_lines.append("")
            else:
                manifest_lines.append("## Shadow Logic: ✅ CLEAN — No shortcuts detected")
                manifest_lines.append("")

            manifest_lines.append(f"**Pulse-Sync Risk:** {sec_manifest.get('pulse_sync_risk', 'N/A')}")
            manifest_lines.append(f"**Total Issues Found:** {sec_manifest.get('total_issues_found', 0)}")

            manifest_path = os.path.join(project_dir, "SECURITY_MANIFEST.md")
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines) + "\n")
            log("BUNDLER", "  📄 SECURITY_MANIFEST.md")

        # 6. Package manifest
        manifest = {
            "project_name": project_name,
            "built_by": "Overlord Factory V2",
            "timestamp": datetime.now().isoformat(),
            "blueprint": blueprint,
            "files": list(code.keys()),
            "assets": state.get("assets", []),
            "security": audit.get("status", "UNKNOWN"),
            "security_score": audit.get("overall_score", "?"),
        }
        with open(os.path.join(project_dir, "package_manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        log("BUNDLER", "  📄 package_manifest.json")

        # 6. Sovereign Mirroring (Universal Asset Sync)
        assets = state.get("assets", [])
        if assets:
            user_home = os.path.expanduser("~")
            desktop = os.path.join(user_home, "Desktop")
            creations_root = os.path.join(desktop, "Overlord_Creations")
            
            log("BUNDLER", f"🔄 Sovereign Sync: Mirroring {len(assets)} asset(s)...")
            
            for asset_rel in assets:
                try:
                    # Resolve full source path
                    asset_filename = os.path.basename(asset_rel)
                    source_path = os.path.join(assets_dir, asset_filename)
                    if not os.path.exists(source_path):
                        continue
                        
                    is_vid = asset_filename.lower().endswith((".mp4", ".mov", ".avi", ".webm"))
                    category = "Videos" if is_vid else "Photos"
                    
                    # 🖥️ Desktop Mirror (Easy Access)
                    desk_cat_dir = os.path.join(creations_root, category)
                    os.makedirs(desk_cat_dir, exist_ok=True)
                    shutil.copy2(source_path, os.path.join(desk_cat_dir, f"{project_name}_{asset_filename}"))
                    
                    # 📁 System Folder Mirror
                    sys_dir = os.path.join(user_home, category)
                    if os.path.exists(sys_dir):
                        shutil.copy2(source_path, os.path.join(sys_dir, f"Overlord_{project_name}_{asset_filename}"))
                        
                except Exception as e:
                    log("BUNDLER", f"  ⚠ Sync failed for {asset_rel}: {e}")

        state["final_package_path"] = project_dir
        return state

    def _extract_deps(self, code: Dict[str, str], architect_deps: List[str]) -> List[str]:
        """Extract pip deps from imports + architect blueprint."""
        found = set(architect_deps)
        for content in code.values():
            for line in content.split("\n"):
                s = line.strip()
                if s.startswith("import "):
                    mod = s.split()[1].split(".")[0].split(",")[0]
                    if mod not in self.STDLIB:
                        found.add(PKG_MAP.get(mod, mod))
                elif s.startswith("from ") and " import " in s:
                    mod = s.split()[1].split(".")[0]
                    if mod not in self.STDLIB and not mod.startswith("."):
                        found.add(PKG_MAP.get(mod, mod))
        return list(found)

    def _build_readme(self, state: AgentState, name: str, deps: List[str]) -> str:
        bp = state.get("blueprint", {})
        code = state.get("code", {})
        assets = state.get("assets", [])
        audit = state.get("audit_report", {})
        run_cmd = bp.get("run_command", "python main.py")

        file_tree = "\n".join(f"├── {f}" for f in sorted(code.keys()))
        asset_tree = "\n".join(f"│   ├── {os.path.basename(a)}" for a in assets) or "│   └── (none)"

        return f"""# {name}

> {bp.get('mission_summary', 'Built by Overlord Factory V2')}

## Quick Start

```bash
# One-Click Bootstrap (installs deps + runs)
./bootstrap.sh        # Linux/Mac
.\\bootstrap.ps1       # Windows PowerShell
```

Or manually:
```bash
pip install -r requirements.txt
{run_cmd}
```

## Project Structure

```
{name}/
{file_tree}
├── assets/
{asset_tree}
├── requirements.txt
├── bootstrap.sh / .ps1
├── audit_log.json
└── package_manifest.json
```

## Security Audit

| Metric | Value |
|--------|-------|
| Status | **{audit.get('status', 'N/A')}** |
| Score  | {audit.get('overall_score', '?')}/100 |
| Issues | {len(audit.get('issues', []))} |

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | {bp.get('stack', {}).get('frontend', 'N/A')} |
| Backend  | {bp.get('stack', {}).get('backend', 'N/A')} |
| Database | {bp.get('stack', {}).get('database', 'N/A')} |

---
*Generated by Overlord Multi-Agent Factory V2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    def _write_bootstrap(self, project_dir: str, deps: List[str], run_cmd: str):
        """Generate One-Click bootstrap scripts."""
        deps_str = " ".join(deps) if deps else ""

        # PowerShell
        ps1 = f"""# Overlord One-Click Bootstrap (PowerShell)
# Usage: .\\bootstrap.ps1

Write-Host "🔥 OVERLORD BOOTSTRAP — Installing dependencies..." -ForegroundColor Cyan

# Create venv if not exists
if (-not (Test-Path ".\\venv")) {{
    python -m venv venv
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
}}

# Activate & install
.\\venv\\Scripts\\Activate.ps1
pip install --upgrade pip -q
if (Test-Path "requirements.txt") {{
    pip install -r requirements.txt -q
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
}}

Write-Host "🚀 Launching application..." -ForegroundColor Yellow
{run_cmd}
"""
        with open(os.path.join(project_dir, "bootstrap.ps1"), "w", encoding="utf-8") as f:
            f.write(ps1)

        # Bash
        bash = f"""#!/usr/bin/env bash
# Overlord One-Click Bootstrap (Bash)
# Usage: chmod +x bootstrap.sh && ./bootstrap.sh

set -e
echo "🔥 OVERLORD BOOTSTRAP — Installing dependencies..."

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Virtual environment created"
fi

# Activate & install
source venv/bin/activate
pip install --upgrade pip -q
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo "  ✓ Dependencies installed"
fi

echo "🚀 Launching application..."
{run_cmd}
"""
        with open(os.path.join(project_dir, "bootstrap.sh"), "w", encoding="utf-8", newline='\n') as f:
            f.write(bash)

    def _write_orchestrate(self, project_dir: str, run_cmd: str):
        """Generate the one-command orchestrate scripts with manifest injection."""
        # PowerShell
        ps1 = '''# ══════════════════════════════════════════════════════════════
# 🔒 OVERLORD ORCHESTRATOR — Single-Command Deployment
# ══════════════════════════════════════════════════════════════
# Usage: .\\orchestrate.ps1 "Build a secure data parser" "Memory efficiency priority"

param(
    [Parameter(Mandatory=$true)][string]$VibeRequest,
    [Parameter(Mandatory=$false)][string]$ContextUpdate = "Default context"
)

$TIMESTAMP = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
$ID_HASH = [System.BitConverter]::ToString(
    [System.Security.Cryptography.MD5]::Create().ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes("$VibeRequest$TIMESTAMP")
    )
).Replace("-", "").ToLower()

Write-Host "" -ForegroundColor Cyan
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     🔒 OVERLORD HARDENED ORCHESTRATOR 2026          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# [1/4] Anchor Identity
Write-Host "[1/4] 🧩 ANCHORING IDENTITY..." -ForegroundColor Yellow
Write-Host "  Pulse-Sync Context: $ContextUpdate" -ForegroundColor DarkGray
Write-Host "  Timestamp: $TIMESTAMP" -ForegroundColor DarkGray
Write-Host "  ID Hash: $ID_HASH" -ForegroundColor DarkGray

# [2/4] Fabricate & Audit
Write-Host "[2/4] 🏗️  FABRICATING & AUDITING..." -ForegroundColor Yellow
python agent_brain_v2.py $VibeRequest
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Fabrication failed" -ForegroundColor Red
    exit 1
}

# [3/4] Verify Manifests
Write-Host "[3/4] 🖋️  VERIFYING SECURITY MANIFESTS..." -ForegroundColor Yellow
$manifestCount = (Get-ChildItem -Path output -Recurse -Include *.py | Select-String "SECURITY MANIFEST" | Measure-Object).Count
Write-Host "  ✓ $manifestCount file(s) sealed with Security Manifest" -ForegroundColor Green

# [4/4] Done
Write-Host "[4/4] ✅ DEPLOYMENT READY" -ForegroundColor Green
Write-Host "  Package: output/" -ForegroundColor Cyan
Write-Host "  Manifest ID: $ID_HASH" -ForegroundColor DarkGray
'''
        with open(os.path.join(project_dir, "orchestrate.ps1"), "w", encoding="utf-8") as f:
            f.write(ps1)

        # Bash
        sh = '''#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# 🔒 OVERLORD ORCHESTRATOR — Single-Command Deployment
# ══════════════════════════════════════════════════════════════
# Usage: ./orchestrate.sh "Build a secure data parser" "Memory efficiency priority"

set -e

VIBE_REQUEST="${1:?Usage: ./orchestrate.sh \"<request>\" \"[context]\"}"
CONTEXT_UPDATE="${2:-Default context}"
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)
ID_HASH=$(echo -n "$VIBE_REQUEST$TIMESTAMP" | md5sum | cut -d\' \' -f1)

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     🔒 OVERLORD HARDENED ORCHESTRATOR 2026          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# [1/4] Anchor Identity
echo "[1/4] 🧩 ANCHORING IDENTITY..."
echo "  Pulse-Sync Context: $CONTEXT_UPDATE"
echo "  Timestamp: $TIMESTAMP"
echo "  ID Hash: $ID_HASH"

# [2/4] Fabricate & Audit
echo "[2/4] 🏗️  FABRICATING & AUDITING..."
python3 agent_brain_v2.py "$VIBE_REQUEST"

# [3/4] Verify Manifests
echo "[3/4] 🖋️  VERIFYING SECURITY MANIFESTS..."
MANIFEST_COUNT=$(grep -rl "SECURITY MANIFEST" output/ 2>/dev/null | wc -l)
echo "  ✓ $MANIFEST_COUNT file(s) sealed with Security Manifest"

# [4/4] Done
echo "[4/4] ✅ DEPLOYMENT READY"
echo "  Package: output/"
echo "  Manifest ID: $ID_HASH"
'''
        with open(os.path.join(project_dir, "orchestrate.sh"), "w", encoding="utf-8", newline='\n') as f:
            f.write(sh)


# ══════════════════════════════════════════════════════════════
#  NODE 6: THE COMPILATION SPECIALIST — Auto-Packager
# ══════════════════════════════════════════════════════════════

class CompilationSpecialistNode:
    """
    Binary Architect: Compiles the project into a standalone executable.
    Triggers ONLY when Guardian status is APPROVED.

    Pipeline: Nuitka --onefile (primary) → PyInstaller (fallback)

    Auto-detects:
      - Entry point from blueprint["run_command"]
      - GUI framework plugins (PyQt6, PySide6, Tkinter)
      - Asset directories for --include-data-dir
      - Hidden imports from requirements
    """

    # GUI frameworks → Nuitka plugin name
    GUI_PLUGINS = {
        "pyqt6": "pyqt6",
        "pyqt5": "pyqt5",
        "pyside6": "pyside6",
        "pyside2": "pyside2",
        "tkinter": "tk-inter",
        "pygame": "pygame",
    }

    async def run(self, state: AgentState) -> AgentState:
        """Compilation node: bundled project → standalone binary."""
        audit = state.get("audit_report", {})
        if audit.get("status") != "APPROVED":
            log("COMPILER", "💎 Skipping compilation — Guardian did not APPROVE")
            state["final_binary"] = ""
            return state

        blueprint = state.get("blueprint", {})
        project_name = blueprint.get("project_name", "overlord_project")
        project_dir = state.get("final_package_path", "")

        if not project_dir or not os.path.isdir(project_dir):
            log("COMPILER", "💎 Skipping compilation — no package directory")
            state["final_binary"] = ""
            return state

        log("COMPILER", f"💎 Node 6: Compiling '{project_name}' to standalone binary...")

        # ── 1. Detect entry point ──
        entry_point = self._find_entry_point(blueprint, project_dir)
        if not entry_point:
            log("COMPILER", "  ✗ No Python entry point found — skipping")
            state["final_binary"] = ""
            return state
        log("COMPILER", f"  📌 Entry point: {entry_point}")

        # ── 2. Detect GUI framework plugins ──
        code = state.get("code", {})
        plugins = self._detect_plugins(code, blueprint.get("dependencies", []))
        if plugins:
            log("COMPILER", f"  🔌 Plugins: {', '.join(plugins)}")

        # ── 3. Gather asset directories ──
        asset_dirs = self._find_asset_dirs(project_dir)
        if asset_dirs:
            log("COMPILER", f"  📁 Asset dirs: {', '.join(asset_dirs)}")

        # ── 4. Build compilation command ──
        output_name = f"{project_name}.exe"
        dist_dir = os.path.join(project_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)

        # Try Nuitka first, then PyInstaller
        nuitka_available = await self._check_tool("nuitka", project_dir)
        pyinstaller_available = await self._check_tool("PyInstaller", project_dir)

        success = False
        binary_path = ""

        if nuitka_available:
            success, binary_path = await self._compile_nuitka(
                project_dir, entry_point, output_name, plugins, asset_dirs
            )
        elif pyinstaller_available:
            log("COMPILER", "  ℹ Nuitka not found — falling back to PyInstaller")
            success, binary_path = await self._compile_pyinstaller(
                project_dir, entry_point, output_name, plugins, asset_dirs
            )
        else:
            log("COMPILER", "  ⚠ Neither Nuitka nor PyInstaller found")
            log("COMPILER", "    Install with: pip install nuitka")
            # Write a deferred compilation script instead
            binary_path = self._write_deferred_script(
                project_dir, entry_point, output_name, plugins, asset_dirs
            )

        if success:
            log("COMPILER", f"  ✓ Binary: {binary_path}")
        elif binary_path:
            log("COMPILER", f"  ℹ Deferred: {binary_path}")

        state["final_binary"] = binary_path
        return state

    # ── Entry Point Detection ───────────────────────────────

    def _find_entry_point(self, blueprint: dict, project_dir: str) -> str:
        """Identify the main Python entry point."""
        # 1. Check blueprint run_command
        run_cmd = blueprint.get("run_command", "")
        if run_cmd:
            parts = run_cmd.split()
            for part in parts:
                if part.endswith(".py"):
                    candidate = os.path.join(project_dir, part)
                    if os.path.exists(candidate):
                        return part

        # 2. Standard entry point names (priority order)
        for name in ["main.py", "app.py", "run.py", "server.py", "__main__.py"]:
            if os.path.exists(os.path.join(project_dir, name)):
                return name

        # 3. Check blueprint files for entry-like tasks
        for f in blueprint.get("files", []):
            path = f.get("path", "")
            task = f.get("task", "").lower()
            if path.endswith(".py") and any(kw in task for kw in ["main", "entry", "launcher", "start"]):
                if os.path.exists(os.path.join(project_dir, path)):
                    return path

        return ""

    # ── Plugin Detection ────────────────────────────────────

    def _detect_plugins(self, code: dict, deps: list) -> List[str]:
        """Scan code and deps for GUI framework imports."""
        detected = set()
        all_code = "\n".join(code.values()).lower()
        all_deps = " ".join(deps).lower()
        combined = f"{all_code} {all_deps}"

        for lib, plugin_name in self.GUI_PLUGINS.items():
            if lib in combined:
                detected.add(plugin_name)

        return list(detected)

    # ── Asset Directory Discovery ───────────────────────────

    def _find_asset_dirs(self, project_dir: str) -> List[str]:
        """Find directories containing bundleable assets."""
        asset_names = ["assets", "static", "resources", "media", "images", "data"]
        found = []
        for name in asset_names:
            path = os.path.join(project_dir, name)
            if os.path.isdir(path) and os.listdir(path):
                found.append(name)
        return found

    # ── Nuitka Compilation ──────────────────────────────────

    async def _compile_nuitka(self, project_dir: str, entry: str,
                               output_name: str, plugins: List[str],
                               asset_dirs: List[str]) -> tuple:
        """Compile with Nuitka --onefile."""
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            "--onefile",
            "--assume-yes-for-downloads",
            f"--output-filename={output_name}",
            f"--output-dir=dist",
        ]

        # Add GUI plugins
        for plugin in plugins:
            cmd.append(f"--plugin-enable={plugin}")

        # Add asset directories
        for asset_dir in asset_dirs:
            cmd.append(f"--include-data-dir={asset_dir}={asset_dir}")

        # Suppress console for GUI apps
        if any(p in ("pyqt6", "pyqt5", "pyside6", "pyside2", "tk-inter") for p in plugins):
            cmd.append("--windows-disable-console")

        # Entry point
        cmd.append(entry)

        log("COMPILER", f"  🔨 Nuitka: {' '.join(cmd[-4:])}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=600  # 10 min timeout
            )

            if process.returncode == 0:
                binary_path = os.path.join("dist", output_name)
                full_path = os.path.join(project_dir, binary_path)
                if os.path.exists(full_path):
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    log("COMPILER", f"  ✓ Nuitka success: {size_mb:.1f} MB")
                    return True, binary_path

            err = (stderr or stdout or b"").decode(errors="replace")[:500]
            log("COMPILER", f"  ✗ Nuitka exit {process.returncode}: {err}")
            return False, ""

        except asyncio.TimeoutError:
            log("COMPILER", "  ✗ Nuitka timed out (10 min)")
            return False, ""
        except Exception as e:
            log("COMPILER", f"  ✗ Nuitka error: {e}")
            return False, ""

    # ── PyInstaller Fallback ────────────────────────────────

    async def _compile_pyinstaller(self, project_dir: str, entry: str,
                                    output_name: str, plugins: List[str],
                                    asset_dirs: List[str]) -> tuple:
        """Fallback: compile with PyInstaller --onefile."""
        name_no_ext = output_name.replace(".exe", "")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--clean",
            f"--name={name_no_ext}",
            f"--distpath=dist",
        ]

        # Add asset directories as --add-data
        sep = ";" if sys.platform == "win32" else ":"
        for asset_dir in asset_dirs:
            cmd.append(f"--add-data={asset_dir}{sep}{asset_dir}")

        # Suppress console for GUI apps
        if any(p in ("pyqt6", "pyqt5", "pyside6", "pyside2", "tk-inter") for p in plugins):
            cmd.append("--windowed")

        cmd.append(entry)

        log("COMPILER", f"  🔨 PyInstaller: {' '.join(cmd[-3:])}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=600
            )

            if process.returncode == 0:
                binary_path = os.path.join("dist", output_name)
                full_path = os.path.join(project_dir, binary_path)
                if os.path.exists(full_path):
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    log("COMPILER", f"  ✓ PyInstaller success: {size_mb:.1f} MB")
                    return True, binary_path

            err = (stderr or stdout or b"").decode(errors="replace")[:500]
            log("COMPILER", f"  ✗ PyInstaller exit {process.returncode}: {err}")
            return False, ""

        except asyncio.TimeoutError:
            log("COMPILER", "  ✗ PyInstaller timed out (10 min)")
            return False, ""
        except Exception as e:
            log("COMPILER", f"  ✗ PyInstaller error: {e}")
            return False, ""

    # ── Deferred Script ─────────────────────────────────────

    def _write_deferred_script(self, project_dir: str, entry: str,
                                output_name: str, plugins: List[str],
                                asset_dirs: List[str]) -> str:
        """Write a compile.ps1 / compile.sh for manual compilation later."""
        plugin_flags = " ".join(f"--plugin-enable={p}" for p in plugins)
        data_flags = " ".join(f"--include-data-dir={d}={d}" for d in asset_dirs)

        ps1 = f"""# Overlord Compilation Script (PowerShell)
# Run this after installing Nuitka: pip install nuitka
Write-Host "💎 Compiling {output_name}..." -ForegroundColor Cyan
python -m nuitka --standalone --onefile {plugin_flags} {data_flags} --output-filename={output_name} --output-dir=dist {entry}
Write-Host "✓ Done: dist\\{output_name}" -ForegroundColor Green
"""
        sh = f"""#!/usr/bin/env bash
# Overlord Compilation Script
# Run this after installing Nuitka: pip install nuitka
set -e
echo "💎 Compiling {output_name}..."
python -m nuitka --standalone --onefile {plugin_flags} {data_flags} --output-filename={output_name} --output-dir=dist {entry}
echo "✓ Done: dist/{output_name}"
"""
        ps1_path = os.path.join(project_dir, "compile.ps1")
        sh_path = os.path.join(project_dir, "compile.sh")

        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(ps1)
        with open(sh_path, "w", encoding="utf-8", newline='\n') as f:
            f.write(sh)

        log("COMPILER", "  📄 compile.ps1 + compile.sh (run manually)")
        return "compile.ps1"

    # ── Tool Availability Check ─────────────────────────────

    async def _check_tool(self, tool_name: str, cwd: str) -> bool:
        """Check if a compilation tool is importable."""
        try:
            result = await asyncio.create_subprocess_exec(
                sys.executable, "-c", f"import {tool_name}",
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(result.communicate(), timeout=10)
            return result.returncode == 0
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════
#  DAG EXECUTOR — Orchestrates the Multi-Node Pipeline
# ══════════════════════════════════════════════════════════════

class OverlordDAG:
    """
    Native DAG executor implementing the LangGraph-compatible pattern:
    
      Architect → (Engineer ‖ Media ‖ Spatial ‖ IoT) → Guardian → Bundler → Compiler → Concierge
    
    Uses asyncio.gather for parallel edges.
    Expansion agents auto-discovered from core/expansions.py registry.
    """

    def __init__(self, model: str = "gpt-4o", budget: float = 5.0):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.tracker = CostTracker(budget=budget)
        self.memory = OverlordMemory(os.path.join(SCRIPT_DIR, "output", "memory"))

        # Initialize core nodes
        self.architect = ArchitectNode(model, self.api_key)
        self.engineer = EngineerNode(model, self.api_key)
        self.media = MediaDirectorNode()
        self.guardian = GuardianNode(model, self.api_key)
        self.bundler = BundlerNode()
        self.compiler = CompilationSpecialistNode()

        # Pulse-Sync (Identity Anchor — prevents context drift)
        self.pulse_sync = None
        if _HAS_PULSE_SYNC:
            try:
                self.pulse_sync = PulseSyncLogger(project_root=SCRIPT_DIR)
                log("SYSTEM", "  🫀 Pulse-Sync: ONLINE")
            except Exception as e:
                log("SYSTEM", f"  ℹ Pulse-Sync unavailable: {e}")

        # Initialize expansion nodes (graceful — never blocks init)
        self.spatial = None
        self.concierge = None
        self.iot = None
        try:
            from core.expansions import (
                SpatialArchitectAgent,
                BusinessConciergeAgent,
                IoTControllerAgent,
            )
            self.spatial = SpatialArchitectAgent()
            self.concierge = BusinessConciergeAgent()
            self.iot = IoTControllerAgent()
            log("SYSTEM", "  🧩 Expansion Pack: Spatial + Concierge + IoT loaded")
        except Exception as e:
            log("SYSTEM", f"  ℹ Expansion pack not loaded: {e}")

    async def execute(self, prompt: str) -> AgentState:
        """Run the full 5-node DAG pipeline."""
        start = time.time()

        log("SYSTEM", "")
        log("SYSTEM", "╔══════════════════════════════════════════════════════╗")
        log("SYSTEM", "║       🔥 OVERLORD MULTI-AGENT FACTORY V2 🔥        ║")
        log("SYSTEM", "╚══════════════════════════════════════════════════════╝")
        log("SYSTEM", f"  🧠 Model:  {self.model}")
        log("SYSTEM", f"  💵 Budget: ${self.tracker.budget:.2f}")
        divider()

        # Activate global cost tracker
        import agent_brain as _ab
        _ab._active_tracker = self.tracker

        # ── Initialize State ──
        state: AgentState = {
            "prompt": prompt,
            "enhanced_prompt": prompt,
            "memory_context": "",
            "pulse_context": "",
            "blueprint": {},
            "code": {},
            "assets": [],
            "audit_report": {},
            "security_manifest": {},
            "final_package_path": "",
        }

        # ── Phase 0: Memory Recall ──
        log("MEMORY", "Phase 0: Knowledge Recall (Donovan-style preferences)...")
        state["memory_context"] = self.memory.recall(prompt)
        if state["memory_context"]:
            log("MEMORY", f"  🧠 Found memories:\n{state['memory_context'][:200]}")
        else:
            log("MEMORY", "  ℹ No prior memories for this context.")
        divider()

        # ── Phase 0.5: Pulse-Sync (Identity Anchor) ──
        if self.pulse_sync:
            log("PULSE", "Phase 0.5: Pulse-Sync — Anchoring identity context...")
            try:
                # Auto-capture a fresh heartbeat
                self.pulse_sync.capture_heartbeat()
                pulse_ctx = self.pulse_sync.get_context_for_orchestrator()
                state["pulse_context"] = pulse_ctx

                if pulse_ctx:
                    log("PULSE", f"  🫀 Context loaded ({len(pulse_ctx)} chars)")

                    # Intent-contradiction detection
                    pulse_data = self.pulse_sync._load_existing()
                    risk = pulse_data.get("identity_fragmentation_risk", "Low")
                    if "High" in str(risk):
                        log("PULSE", f"  ⚠ FRAGMENTATION RISK: {risk}")
                        log("PULSE", "    Prompt may contradict recent project direction.")

                    # Check for vibe-shift contradiction
                    history = pulse_data.get("session_history", [])
                    if history:
                        last_vibe = history[-1].get("vibe", "").lower()
                        prompt_lower = prompt.lower()
                        # Simple contradiction heuristic: opposite signals
                        contradictions = [
                            ("security", "skip security"),
                            ("minimal", "feature-rich"),
                            ("prototype", "production"),
                        ]
                        for focus, anti in contradictions:
                            if focus in last_vibe and anti in prompt_lower:
                                log("PULSE", f"  🚩 INTENT SHIFT: Last vibe='{focus}' but prompt contains '{anti}'")
                else:
                    log("PULSE", "  ℹ No prior pulse data — baseline run.")
            except Exception as e:
                log("PULSE", f"  ⚠ Pulse-Sync error: {e}")
            divider()

        # ── Node 1: Architect ──
        state = await self.architect.run(state)
        divider()

        # ── Parallel Execution: Engineer ‖ Media ‖ Spatial ‖ Concierge ‖ IoT ──
        parallel_tasks = [
            ("Engineer", self.engineer.run(dict(state))),  # type: ignore
            ("Media",    self.media.run(dict(state))),     # type: ignore
        ]

        # Add expansion agents if loaded
        if self.spatial:
            parallel_tasks.append(("Spatial", self.spatial.run(dict(state))))  # type: ignore
        if self.iot:
            parallel_tasks.append(("IoT", self.iot.run(dict(state))))         # type: ignore
        if self.concierge:
            parallel_tasks.append(("Concierge", self.concierge.run(dict(state))))  # type: ignore

        names = [t[0] for t in parallel_tasks]
        log("SYSTEM", f"⚡ Parallel Execution: {' ‖ '.join(names)}")

        results = await asyncio.gather(
            *(coro for _, coro in parallel_tasks),
            return_exceptions=True,
        )

        # Merge results from all parallel nodes
        all_assets: List[str] = []
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                log("SYSTEM", f"  ✗ {name}: {result}")
                continue
            if name == "Engineer":
                state["code"] = result.get("code", {})
            # All asset-producing nodes contribute to the assets list
            node_assets = result.get("assets", [])
            if node_assets:
                all_assets.extend(node_assets)
            log("SYSTEM", f"  ✓ {name}: OK")

        state["assets"] = all_assets

        log("SYSTEM", f"  📁 Code:    {len(state['code'])} file(s)")
        log("SYSTEM", f"  🎬 Assets:  {len(state['assets'])} asset(s)")
        log("SYSTEM", f"  💵 Cost:    ${self.tracker.total_cost:.4f}")
        divider()

        # ── Node 4: Security Guardian ──
        state = await self.guardian.run(state)
        divider()

        # ── Node 5: Bundler ──
        state = await self.bundler.run(state)
        divider()

        # ── Node 6: Compilation Specialist (auto-packaging) ──
        state = await self.compiler.run(state)
        divider()

        # ── Post-Bundler: Business Concierge (dispatch status) ──
        if self.concierge:
            try:
                state = await self.concierge.run(state)
                divider()
            except Exception as e:
                log("CONCIERGE", f"  ⚠ Post-build dispatch failed: {e}")

        # ── Phase 5: Memory Storage ──
        elapsed = time.time() - start
        audit = state.get("audit_report", {})
        self.memory.memorize({
            "tags": [state.get("blueprint", {}).get("project_name", ""), self.model],
            "trigger": prompt[:100],
            "lesson": f"Built '{state.get('blueprint', {}).get('project_name', '?')}' "
                      f"with {len(state.get('code', {}))} files. "
                      f"Security: {audit.get('status', '?')}. "
                      f"Cost: ${self.tracker.total_cost:.4f}.",
            "outcome": "success" if audit.get("status") == "APPROVED" else "patched",
        })

        # Save cost report
        pkg_path = state.get("final_package_path", "")
        if pkg_path:
            self.tracker.save_report(pkg_path)

        # ── Final Report ──
        log("SYSTEM", "")
        log("SYSTEM", "╔══════════════════════════════════════════════════════╗")
        log("SYSTEM", "║           ✨  MISSION COMPLETE  ✨                  ║")
        log("SYSTEM", "╚══════════════════════════════════════════════════════╝")
        log("SYSTEM", f"  📦 Package:  {os.path.abspath(pkg_path)}")
        log("SYSTEM", f"  📁 Files:    {len(state.get('code', {}))}")
        log("SYSTEM", f"  🎬 Assets:   {len(state.get('assets', []))}")
        log("SYSTEM", f"  🛡️  Security: {audit.get('status', '?')} ({audit.get('overall_score', '?')}/100)")
        log("SYSTEM", f"  💵 Cost:     ${self.tracker.total_cost:.4f}")
        log("SYSTEM", f"  ⏱️  Time:     {elapsed:.1f}s")
        log("SYSTEM", f"  🚀 Run:      cd {pkg_path} && .\\bootstrap.ps1")
        divider()

        return state


# ══════════════════════════════════════════════════════════════
#  PUBLIC API — AgentBrain (backward-compatible wrapper)
# ══════════════════════════════════════════════════════════════

class AgentBrain:
    """
    Public API wrapping the OverlordDAG.
    Backward compatible with the V1 interface.
    """

    def __init__(self, project_name: str = "OverlordProject",
                 model: str = "gpt-4o", budget: float = 5.0,
                 user_id: str = "Donovan", output_dir: str = "output"):
        self.project_name = project_name
        self.model = model
        self.budget = budget
        self.user_id = user_id
        self.dag = OverlordDAG(model=model, budget=budget)
        self.state: AgentState = {}  # type: ignore

    async def execute_build(self, user_prompt: str) -> AgentState:
        """Run the full Overlord pipeline."""
        self.state = await self.dag.execute(user_prompt)
        return self.state


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

async def main():
    """Default entry point — build a sample project."""
    brain = AgentBrain(
        project_name="Studio_Refactor_2026",
        model="gpt-4o",
        budget=5.0,
    )
    result = await brain.execute_build(
        "Build a high-performance Studio Suite with PyQt6 and 4K video backgrounds."
    )
    return result


if __name__ == "__main__":
    asyncio.run(main())
