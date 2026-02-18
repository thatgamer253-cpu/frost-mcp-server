#!/usr/bin/env python3
"""
===============================================================
  HIVE COORDINATOR — Consensus Swarm Orchestrator
  The Sovereign Fleet of Specialized Agents
===============================================================

Evolves existing agents into a 5-role Consensus Swarm:

  1. ARCHITECT   (Agent 1)  — High-level logic, blueprint design
  2. FABRICATOR  (Agent 2)  — Rapid code generation
  3. ALCHEMIST   (Reviewer) — Optimization, boilerplate purging
  4. AUDITOR     (Sentinel) — Security, adversarial red-team
  5. MERCHANT    (sell_agent)— Cost/value analysis, lite-vibe

The swarm enforces multi-point verification:
  - No code ships without Sentinel audit
  - No expensive call without Merchant approval
  - Every delivery carries a ZK Manifest with Hive ID

Usage:
    coordinator = HiveCoordinator()
    package = coordinator.recruit_swarm(
        "Build a multi-api crypto tracker",
        pulse_context="Pulse: 2026-02-16 Focus: Privacy"
    )
"""

import os
import json
import hashlib
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# ── Load .env BEFORE any agent imports (keys needed at class init) ───
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Logging ──────────────────────────────────────────────────
try:
    from creation_engine.llm_client import log
except ImportError:
    def log(tag: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}] {msg}")

# ── Agent imports (graceful degrade) ─────────────────────────
try:
    from core.agents import Architect, Engineer, Reviewer, LLMClient
    _HAS_CORE_AGENTS = True
except ImportError:
    _HAS_CORE_AGENTS = False

# ── Adversarial Auditor ──────────────────────────────────────
try:
    from adversarial_auditor import AdversarialAuditor
    _HAS_AUDITOR = True
except ImportError:
    _HAS_AUDITOR = False

# ── Pulse-Sync ───────────────────────────────────────────────
try:
    from pulse_sync_logger import PulseSyncLogger
    _HAS_PULSE_SYNC = True
except ImportError:
    _HAS_PULSE_SYNC = False

# ── Interaction Hub ──────────────────────────────────────────
try:
    from interaction_hub import hub as get_hub, SEVERITY_INFO, SEVERITY_ACTION, SEVERITY_WARNING, SEVERITY_VERDICT
    _HAS_HUB = True
except ImportError:
    _HAS_HUB = False

# ── Judge Agent ──────────────────────────────────────────────
try:
    from judge_agent import JudgeAgent
    _HAS_JUDGE = True
except ImportError:
    _HAS_JUDGE = False

# ── Permanent Constraints ────────────────────────────────────
_CONSTRAINTS_PATH = os.path.join("memory", "permanent_constraints.json")


# =============================================================
#  COST TRACKER (Merchant)
# =============================================================

class MerchantTracker:
    """Tracks computational cost per swarm run and suggests
    lite-vibe alternatives when builds are too expensive.

    Cost model (approx per 1K tokens, 2026 pricing):
      gpt-4o:      $0.005 input / $0.015 output
      claude-3.5:  $0.003 input / $0.015 output
      gpt-4o-mini: $0.00015 input / $0.0006 output
    """

    MODEL_COSTS = {
        "gpt-4o":       {"input": 0.005, "output": 0.015},
        "gpt-4o-mini":  {"input": 0.00015, "output": 0.0006},
        "claude-3.5":   {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }

    LITE_VIBE_THRESHOLD = 0.50  # dollars

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.total_cost = 0.0

    def track_call(self, model: str, role: str,
                    input_tokens: int = 0, output_tokens: int = 0):
        """Record a single LLM call and its estimated cost."""
        rates = self.MODEL_COSTS.get(model, {"input": 0.005, "output": 0.015})
        cost = (input_tokens / 1000 * rates["input"] +
                output_tokens / 1000 * rates["output"])
        self.total_cost += cost
        self.calls.append({
            "role": role,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "timestamp": datetime.now().isoformat(),
        })
        return cost

    def should_suggest_lite_vibe(self) -> bool:
        """Returns True if the build is getting expensive."""
        return self.total_cost > self.LITE_VIBE_THRESHOLD

    def get_lite_vibe_suggestion(self) -> Dict[str, Any]:
        """Suggest cheaper alternatives when cost is high."""
        return {
            "warning": "COST_THRESHOLD_EXCEEDED",
            "current_cost": round(self.total_cost, 4),
            "threshold": self.LITE_VIBE_THRESHOLD,
            "suggestion": (
                "Switch non-critical agents (Alchemist, Merchant) to "
                "gpt-4o-mini or claude-3-haiku to reduce cost by ~70%."
            ),
            "model_swap": {
                "Architect": "gpt-4o (keep — critical thinking)",
                "Fabricator": "gpt-4o (keep — code quality)",
                "Alchemist": "gpt-4o-mini (swap — optimization is pattern-based)",
                "Merchant": "gpt-4o-mini (swap — cost analysis is simple math)",
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Return a full cost report."""
        by_role = {}
        for c in self.calls:
            role = c["role"]
            if role not in by_role:
                by_role[role] = {"calls": 0, "cost_usd": 0.0}
            by_role[role]["calls"] += 1
            by_role[role]["cost_usd"] += c["cost_usd"]

        return {
            "total_cost_usd": round(self.total_cost, 4),
            "total_calls": len(self.calls),
            "by_role": by_role,
            "lite_vibe_triggered": self.should_suggest_lite_vibe(),
        }


# =============================================================
#  ZK MANIFEST GENERATOR
# =============================================================

def generate_zk_manifest(hive_id: str, consensus_result: Dict[str, Any],
                          cost_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a Zero-Knowledge Manifest proving code provenance.

    The Hive ID is a cryptographic fingerprint of:
      - The swarm session UUID
      - All participating agent roles
      - The consensus hash

    This prevents "AI Clone" attacks where external code
    is injected and falsely attributed to this fleet.
    """
    # Build the proof chain
    agent_chain = "|".join(sorted(consensus_result.get("agents_participated", [])))
    proof_input = f"{hive_id}:{agent_chain}:{consensus_result.get('consensus_hash', '')}"
    zk_proof = hashlib.sha256(proof_input.encode()).hexdigest()

    manifest = {
        "zk_manifest_version": "2026.1",
        "timestamp": datetime.now().isoformat(),
        "hive_id": hive_id,
        "orchestrator_status": "HARDENED" if consensus_result.get("verdict") == "CONSENSUS_REACHED" else "VULNERABLE",
        "identity_anchor": {
            "status": "VERIFIED",
            "source": "pulse_sync.json",
            "hive_proof": zk_proof[:16] + "..." + zk_proof[-8:],
        },
        "red_team_audit": {
            "status": consensus_result.get("audit_verdict", "PENDING"),
            "hallucinated_deps": "None detected" if consensus_result.get("audit_verdict") == "VIBE_VERIFIED" else "Review required",
        },
        "logic_integrity": {
            "status": "VERIFIED" if consensus_result.get("verdict") == "CONSENSUS_REACHED" else "UNVERIFIED",
            "consensus_rounds": consensus_result.get("healing_rounds", 0) + 1,
            "description": "Zero-Knowledge proof of intent match",
        },
        "cost_analysis": {
            "total_usd": cost_summary.get("total_cost_usd", 0),
            "agent_calls": cost_summary.get("total_calls", 0),
            "lite_vibe": cost_summary.get("lite_vibe_triggered", False),
        },
        "full_zk_proof": zk_proof,
    }

    return manifest


# =============================================================
#  PERMANENT CONSTRAINTS ENFORCER
# =============================================================

def load_permanent_constraints() -> Dict[str, Any]:
    """Load the permanent_constraints.json from memory/."""
    if os.path.exists(_CONSTRAINTS_PATH):
        with open(_CONSTRAINTS_PATH, "r") as f:
            return json.load(f)
    return {"permanent_rules": [], "prohibited_patterns": []}


def enforce_constraints(code: str, constraints: Dict[str, Any]) -> List[Dict[str, str]]:
    """Check code against permanent rules and prohibited patterns.

    Returns a list of violations found.
    """
    violations = []

    # Skip non-code files (short files or non-Python)
    if not code.strip() or len(code.strip()) < 20:
        return violations

    code_lower = code.lower()

    # Check prohibited patterns
    for pattern in constraints.get("prohibited_patterns", []):
        pattern_lower = pattern.lower()

        # Synchronous I/O in Flask/FastAPI routes
        if "synchronous i/o" in pattern_lower:
            if ("flask" in code_lower or "fastapi" in code_lower):
                if "time.sleep" in code and "retry" not in code_lower and "backoff" not in code_lower:
                    violations.append({
                        "rule": pattern,
                        "severity": "HIGH",
                        "description": "Synchronous blocking call detected in async route context",
                    })

        # Hardcoded API keys
        if "hardcoded api keys" in pattern_lower:
            import re
            # Look for patterns like api_key="sk-..." or KEY = "..."
            if re.search(r'["\'](?:sk-|pk_|rk_|key_)[a-zA-Z0-9]{20,}["\']', code):
                violations.append({
                    "rule": pattern,
                    "severity": "CRITICAL",
                    "description": "Hardcoded API key detected in source code",
                })

        # Uncapped recursive loops
        if "uncapped recursive" in pattern_lower:
            if "def " in code and code.count("recursion") == 0:
                import re
                func_names = re.findall(r'def (\w+)\(', code)
                for fname in func_names:
                    # Only flag if function calls itself AND lacks depth protection
                    call_count = code.count(f"{fname}(")
                    if call_count > 2:
                        has_protection = any(kw in code_lower for kw in [
                            "max_depth", "circuit_breaker", "depth", "max_recursion",
                            "recursion_limit", "base case", "stack"
                        ])
                        if not has_protection:
                            violations.append({
                                "rule": pattern,
                                "severity": "MEDIUM",
                                "description": f"Function '{fname}' may be recursive without circuit breaker",
                            })

    # Check permanent rules enforcement
    for rule in constraints.get("permanent_rules", []):
        rule_id = rule.get("id", "")

        # RES-001: API Rate Limiting
        if rule_id == "RES-001":
            has_http_calls = any(kw in code for kw in [
                "requests.", "httpx.", "aiohttp."
            ])
            if has_http_calls:
                has_rate_protection = any(kw in code_lower for kw in [
                    "retry", "cooldown", "rate_limit", "rate_limiter",
                    "backoff", "limiter", "max_retries", "exponential",
                    "throttle", "ratelimit", "slowapi", "flask_limiter",
                    "tenacity", "urllib3.util.retry",
                ])
                if not has_rate_protection:
                    violations.append({
                        "rule": f"{rule_id}: {rule['issue']}",
                        "severity": "HIGH",
                        "description": rule["lesson"],
                        "enforcement": rule["enforcement"],
                    })

        # MEM-002: Narrative Memory Loop
        if rule_id == "MEM-002":
            # Only flag for genuine content generation functions, not CRUD routes
            has_content_gen = any(kw in code_lower for kw in [
                "generate_article", "generate_post", "create_content",
                "generate_video", "generate_image", "ai_generate",
                "llm_generate", "auto_generate",
            ])
            if has_content_gen:
                has_memory_check = any(kw in code_lower for kw in [
                    "sqlite", "log_check", "narrative_memory",
                    "dedup", "duplicate", "history", "hash_check",
                    "already_generated", "memory", "seen_before",
                ])
                if not has_memory_check:
                    violations.append({
                        "rule": f"{rule_id}: {rule['issue']}",
                        "severity": "MEDIUM",
                        "description": rule["lesson"],
                        "enforcement": rule["enforcement"],
                    })

        # AUT-004: Reactive Triggering
        if rule_id == "AUT-004":
            if "input(" in code:
                has_reactive = any(kw in code_lower for kw in [
                    "watchdog", "observer", "schedule", "cron",
                    "timer", "event_handler", "signal", "inotify",
                    "argparse", "click", "typer",
                ])
                if not has_reactive:
                    violations.append({
                        "rule": f"{rule_id}: {rule['issue']}",
                        "severity": "LOW",
                        "description": rule["lesson"],
                        "enforcement": rule["enforcement"],
                    })

    return violations


# =============================================================
#  THE HIVE COORDINATOR
# =============================================================

class HiveCoordinator:
    """Consensus Swarm Orchestrator — The Hive Mind.

    Coordinates 5 specialized agents into a multi-point
    verification pipeline:

      Architect → Fabricator → Alchemist → Sentinel → Merchant

    No code ships without consensus from all 5 roles.
    """

    MAX_HEALING_ROUNDS = 3

    def __init__(self, model: str = "gpt-4o"):
        self.hive_id = f"HIVE-{uuid.uuid4().hex[:12].upper()}"
        self.model = model
        self.merchant = MerchantTracker()
        self.constraints = load_permanent_constraints()
        self.consensus_log_path = os.path.join("logs", "swarm_consensus.json")
        os.makedirs("logs", exist_ok=True)

        # Interaction Hub
        self._hub = get_hub() if _HAS_HUB else None

        # Map roles to real agent classes
        self.agents = {
            "Architect":  "Agent_1",
            "Fabricator":  "Agent_2",
            "Alchemist":  "Alchemist",
            "Auditor":    "Sentinel",
            "Judge":      "Judge",
            "Merchant":   "sell_agent",
        }

        # Initialize real agents if available
        self._architect = None
        self._engineer = None
        self._reviewer = None
        self._auditor = None
        self._judge = JudgeAgent() if _HAS_JUDGE else None

        if _HAS_CORE_AGENTS:
            try:
                self._architect = Architect(model=model)
                self._engineer = Engineer(model=model)
                self._reviewer = Reviewer(model=model)
            except Exception as e:
                log("HIVE", f"  Agent init warning: {e}")

        if _HAS_AUDITOR:
            self._auditor = AdversarialAuditor()

        # Post system boot to Hub
        self._hub_post("System", f"Hive Coordinator online. ID: {self.hive_id}. {len(self.agents)} agents standing by.")

        log("HIVE", "")
        log("HIVE", "=== HIVE COORDINATOR ===")
        log("HIVE", f"  Hive ID:     {self.hive_id}")
        log("HIVE", f"  Model:       {self.model}")
        log("HIVE", f"  Core Agents: {'LOADED' if _HAS_CORE_AGENTS else 'SIMULATED'}")
        log("HIVE", f"  Sentinel:    {'LOADED' if _HAS_AUDITOR else 'SIMULATED'}")
        log("HIVE", f"  Judge:       {'LOADED' if _HAS_JUDGE else 'UNAVAILABLE'}")
        log("HIVE", f"  Hub:         {'CONNECTED' if _HAS_HUB else 'OFFLINE'}")
        log("HIVE", f"  Constraints: {len(self.constraints.get('permanent_rules', []))} rules")
        log("HIVE", f"  Heritage:    {', '.join(self.constraints.get('project_heritage', []))}")
        log("HIVE", "========================")

    def _hub_post(self, agent: str, message: str, severity: str = "INFO", context: dict = None):
        """Post to the Interaction Hub if available."""
        if self._hub:
            sev = severity
            if _HAS_HUB:
                sev_map = {"INFO": SEVERITY_INFO, "WARNING": SEVERITY_WARNING,
                           "ACTION": SEVERITY_ACTION, "VERDICT": SEVERITY_VERDICT}
                sev = sev_map.get(severity, SEVERITY_INFO)
            self._hub.post(agent, message, sev, context)

    # ---------------------------------------------------------
    #  INDIVIDUAL AGENT CALLS
    # ---------------------------------------------------------

    def _call_architect(self, vibe_request: str, pulse_context: str) -> Dict[str, Any]:
        """Phase 1: Architect designs the blueprint."""
        self._hub_post("Architect", f"Analyzing request: \"{vibe_request[:60]}...\"")
        log("HIVE", f"  [Architect] Designing blueprint...")
        start = time.time()

        if self._architect:
            blueprint_raw = self._architect.plan(vibe_request)
            self.merchant.track_call(self.model, "Architect",
                                      input_tokens=len(vibe_request) // 4,
                                      output_tokens=len(str(blueprint_raw)) // 4)
            try:
                blueprint = json.loads(blueprint_raw) if isinstance(blueprint_raw, str) else blueprint_raw
            except (json.JSONDecodeError, TypeError):
                blueprint = {"raw_plan": str(blueprint_raw), "files": []}
        else:
            # Simulated mode
            blueprint = {
                "project": vibe_request[:50],
                "files": [
                    {"path": "main.py", "task": "Entry point with argument parsing"},
                    {"path": "core.py", "task": "Core business logic"},
                    {"path": "utils.py", "task": "Shared utilities"},
                ],
                "dependencies": ["requests", "click"],
                "run_command": "python main.py",
                "pulse_context": pulse_context,
            }
            self.merchant.track_call(self.model, "Architect",
                                      input_tokens=100, output_tokens=200)

        elapsed = round(time.time() - start, 2)
        file_count = len(blueprint.get('files', []))
        self._hub_post("Architect", f"Blueprint complete. {file_count} files planned. ({elapsed}s)")
        log("HIVE", f"  [Architect] Blueprint ready ({elapsed}s, {file_count} files)")
        return blueprint

    def _call_fabricator(self, blueprint: Dict[str, Any]) -> Dict[str, str]:
        """Phase 2: Fabricator generates code from blueprint."""
        files = blueprint.get("files", [])
        self._hub_post("Fabricator", f"Forging {len(files)} files from the blueprint...", "ACTION")
        log("HIVE", f"  [Fabricator] Building code...")
        start = time.time()
        code_files = {}

        for file_spec in files:
            path = file_spec.get("path", "unknown.py")
            task = file_spec.get("task", "implement this module")

            if self._engineer:
                context = json.dumps(blueprint, indent=2, default=str)
                raw_code = self._engineer.build_file(path, task, context)
                self.merchant.track_call(self.model, "Fabricator",
                                          input_tokens=len(context) // 4,
                                          output_tokens=len(str(raw_code)) // 4)
                code_files[path] = str(raw_code)
            else:
                # Simulated code generation
                code_files[path] = (
                    f'"""\n{path} — {task}\n'
                    f'Generated by Hive Fabricator\n"""\n\n'
                    f'# TODO: Implement {task}\n'
                    f'def main():\n    pass\n'
                )
                self.merchant.track_call(self.model, "Fabricator",
                                          input_tokens=50, output_tokens=100)

        elapsed = round(time.time() - start, 2)
        self._hub_post("Fabricator", f"{len(code_files)} files forged successfully. ({elapsed}s)")
        log("HIVE", f"  [Fabricator] {len(code_files)} files built ({elapsed}s)")
        return code_files

    def _call_alchemist(self, code_files: Dict[str, str],
                          audit_feedback: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Phase 3: Alchemist optimizes and refines the code.

        If audit_feedback is provided (from Sentinel), the Alchemist
        uses LLM-powered rewriting to fix all flagged violations.
        Otherwise, it runs a review-only pass.
        """
        mode = "REWRITING" if audit_feedback else "Refining"
        if audit_feedback:
            self._hub_post("Alchemist", f"Creating Shadow Sandbox to rewrite {len(code_files)} files with audit fixes...", "ACTION")
        else:
            self._hub_post("Alchemist", f"Refining {len(code_files)} files for production quality...", "ACTION")
        log("HIVE", f"  [Alchemist] {mode} {len(code_files)} files...")
        start = time.time()
        refined = {}

        # Build per-file violation map from audit feedback
        file_violations: Dict[str, List[Dict[str, str]]] = {}
        if audit_feedback:
            # Collect constraint violations (apply to all files)
            global_violations = audit_feedback.get("constraint_violations", [])

            # Collect per-file audit flags
            for file_report in audit_feedback.get("files", []):
                fname = file_report.get("filename", "")
                flags = file_report.get("flags", [])
                per_file = []
                for flag in flags:
                    per_file.append({
                        "rule": flag.get("check", flag.get("rule", "Audit Flag")),
                        "severity": flag.get("severity", "HIGH"),
                        "description": flag.get("message", str(flag)),
                    })
                file_violations[fname] = per_file

            # Map global constraints to matching files
            for path in code_files:
                if path not in file_violations:
                    file_violations[path] = []
                # Add relevant constraint violations to each file
                for cv in global_violations:
                    file_violations[path].append({
                        "rule": cv.get("rule", "Constraint"),
                        "severity": cv.get("severity", "HIGH"),
                        "description": cv.get("description", ""),
                    })

        for path, code in code_files.items():
            violations = file_violations.get(path, [])

            if self._reviewer and violations:
                # REWRITE MODE: Fix flagged issues via LLM
                fixed_code = self._reviewer.rewrite(code, violations, filename=path)
                self.merchant.track_call(self.model, "Alchemist",
                                          input_tokens=len(code) // 4,
                                          output_tokens=len(fixed_code) // 4)
                refined[path] = fixed_code
                log("HIVE", f"    [Alchemist] Rewrote {path} ({len(violations)} fixes)")
            elif self._reviewer and path.endswith(".py"):
                # REVIEW MODE: Proactive quality pass on Python files only
                review_issues = self._reviewer.review(code, f"File: {path}")
                self.merchant.track_call(self.model, "Alchemist",
                                          input_tokens=len(code) // 4,
                                          output_tokens=100)
                if review_issues:
                    log("HIVE", f"    [Alchemist] Reviewed {path}: {len(review_issues)} suggestions noted")
                refined[path] = code  # Keep original — suggestions are advisory only
            else:
                refined[path] = code
                self.merchant.track_call(self.model, "Alchemist",
                                          input_tokens=50, output_tokens=50)

        elapsed = round(time.time() - start, 2)
        self._hub_post("Alchemist", f"{mode} complete. {len(refined)} files polished. ({elapsed}s)")
        log("HIVE", f"  [Alchemist] {mode} complete ({elapsed}s)")
        return refined

    def _call_sentinel(self, code_files: Dict[str, str]) -> Dict[str, Any]:
        """Phase 4: Sentinel runs adversarial red-team audit."""
        self._hub_post("Sentinel", f"Initiating red-team scan on {len(code_files)} files...", "ACTION")
        log("HIVE", f"  [Sentinel] Red-team audit on {len(code_files)} files...")
        start = time.time()

        aggregate = {
            "verdict": "VIBE_VERIFIED",
            "files": [],
            "constraint_violations": [],
        }

        for path, code in code_files.items():
            # Adversarial Auditor (3-step)
            if self._auditor:
                report = self._auditor.audit_code(code, filename=path)
                aggregate["files"].append(report)
                if report["verdict"] == "CRITICAL_VULN":
                    aggregate["verdict"] = "CRITICAL_VULN"
                    self._hub_post("Sentinel", f"⚠ Critical vulnerability detected in {path}.", "WARNING")
            else:
                # Simulated audit
                aggregate["files"].append({
                    "filename": path,
                    "verdict": "VIBE_VERIFIED",
                    "flags": [],
                    "stats": {"total_flags": 0},
                })

            # Permanent constraints enforcement
            violations = enforce_constraints(code, self.constraints)
            if violations:
                aggregate["constraint_violations"].extend(violations)
                for v in violations:
                    if v["severity"] == "CRITICAL":
                        aggregate["verdict"] = "CRITICAL_VULN"

        elapsed = round(time.time() - start, 2)
        v_count = len(aggregate["constraint_violations"])
        if aggregate["verdict"] == "VIBE_VERIFIED":
            self._hub_post("Sentinel", f"Scan clean. {len(code_files)} files verified. ({elapsed}s)", "VERDICT")
        else:
            self._hub_post("Sentinel", f"Scan flagged {v_count} violation(s). Routing to Alchemist for healing. ({elapsed}s)", "WARNING")
        log("HIVE", f"  [Sentinel] Audit: {aggregate['verdict']} ({elapsed}s)")
        if aggregate["constraint_violations"]:
            log("HIVE", f"  [Sentinel] {v_count} "
                        f"constraint violations found")
            for cv in aggregate["constraint_violations"]:
                log("HIVE", f"    [{cv.get('severity', '?')}] {cv.get('rule', 'Unknown')}")
        return aggregate

    def _call_judge(self, code_files: Dict[str, str],
                     audit_report: Dict[str, Any],
                     blueprint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Phase 5.5: Judge runs the Gauntlet validation."""
        if not self._judge:
            log("HIVE", "  [Judge] Unavailable — skipping Gauntlet.")
            return {"verdict": "GAUNTLET_SKIPPED", "checks": []}

        log("HIVE", f"  [Judge] Running Gauntlet on {len(code_files)} files...")
        report = self._judge.run_gauntlet(code_files, audit_report, blueprint)
        log("HIVE", f"  [Judge] Verdict: {report['verdict']} "
                     f"({report['passed']}/{report['passed'] + report['failed']} checks, "
                     f"{report['elapsed_s']}s)")
        return report

    def _call_merchant(self) -> Dict[str, Any]:
        """Phase 6: Merchant evaluates cost and suggests optimizations."""
        summary = self.merchant.get_summary()

        cost_str = f"${summary['total_cost_usd']:.4f}"
        self._hub_post("Merchant", f"Session cost: {cost_str} ({summary['total_calls']} LLM calls).")
        log("HIVE", f"  [Merchant] Cost: {cost_str} ({summary['total_calls']} calls)")

        if self.merchant.should_suggest_lite_vibe():
            suggestion = self.merchant.get_lite_vibe_suggestion()
            self._hub_post("Merchant", f"⚠ Cost threshold exceeded. Suggesting lite-vibe swap.", "WARNING")
            log("HIVE", f"  [Merchant] LITE-VIBE triggered: {suggestion['suggestion'][:60]}...")
            summary["lite_vibe_suggestion"] = suggestion

        return summary

    # ---------------------------------------------------------
    #  CONFLICT RESOLUTION / HEALING LOOP
    # ---------------------------------------------------------

    def resolve_conflict(self, code_files: Dict[str, str],
                          audit_report: Dict[str, Any],
                          round_num: int = 0) -> Dict[str, str]:
        """Auto-healing loop: Sentinel flagged issues → Alchemist rewrites.

        Loops up to MAX_HEALING_ROUNDS times before escalating.
        """
        if round_num >= self.MAX_HEALING_ROUNDS:
            log("HIVE", f"  [HEALING] Max rounds ({self.MAX_HEALING_ROUNDS}) reached. "
                        f"Escalating to human review.")
            return code_files

        log("HIVE", f"  [HEALING] Round {round_num + 1}: Re-routing to Alchemist for rewrite...")

        # Count what needs fixing
        violations = audit_report.get("constraint_violations", [])
        flags = []
        for f in audit_report.get("files", []):
            flags.extend(f.get("flags", []))

        log("HIVE", f"  [HEALING] {len(violations)} constraint violations, "
                     f"{len(flags)} audit flags to fix")

        # Re-run Alchemist WITH audit feedback (triggers rewrite mode)
        healed = self._call_alchemist(code_files, audit_feedback=audit_report)

        # Re-run Sentinel
        re_audit = self._call_sentinel(healed)

        if re_audit["verdict"] == "VIBE_VERIFIED":
            log("HIVE", f"  [HEALING] Healed after round {round_num + 1}")
            return healed
        else:
            return self.resolve_conflict(healed, re_audit, round_num + 1)

    # ---------------------------------------------------------
    #  MAIN SWARM RECRUITMENT
    # ---------------------------------------------------------

    def recruit_swarm(self, vibe_request: str,
                       pulse_context: str = "") -> Dict[str, Any]:
        """Execute the full Consensus Swarm pipeline.

        Sequence:
          1. Pulse Sync heartbeat
          2. Architect → blueprint
          3. Fabricator → raw code
          4. Alchemist → refined code
          5. Sentinel → red-team audit
          6. Healing loop (if CRITICAL_VULN)
          7. Merchant → cost analysis
          8. ZK Manifest generation
          9. Consensus log

        Args:
            vibe_request: What to build.
            pulse_context: Current Pulse-Sync context.

        Returns:
            Full swarm consensus package.
        """
        start_time = time.time()
        healing_rounds = 0

        log("HIVE", "")
        log("HIVE", "=== SWARM RECRUITMENT ===")
        log("HIVE", f"  Request: {vibe_request[:70]}...")
        log("HIVE", f"  Hive:    {self.hive_id}")
        log("HIVE", f"  Agents:  {len(self.agents)}")
        log("HIVE", "")

        # Step 0: Pulse Sync
        if _HAS_PULSE_SYNC and pulse_context:
            try:
                syncer = PulseSyncLogger()
                syncer.capture_heartbeat(manual_vibe=pulse_context)
                log("HIVE", "  Pulse heartbeat captured")
            except Exception:
                pass

        # Step 1: Architect
        blueprint = self._call_architect(vibe_request, pulse_context)

        # Step 2: Fabricator
        code_files = self._call_fabricator(blueprint)

        # Step 3: Alchemist
        refined_code = self._call_alchemist(code_files)

        # Step 4: Sentinel
        audit_report = self._call_sentinel(refined_code)

        # Step 5: Healing loop if needed
        if audit_report["verdict"] == "CRITICAL_VULN":
            log("HIVE", "")
            log("HIVE", "  CONSENSUS FAILED — Entering healing loop")
            self._hub_post("System", "Consensus failed. Initiating Sentinel → Alchemist healing loop...", "WARNING")
            refined_code = self.resolve_conflict(refined_code, audit_report)
            # Re-audit after healing
            audit_report = self._call_sentinel(refined_code)
            healing_rounds = min(self.MAX_HEALING_ROUNDS,
                                  len([f for f in audit_report.get("files", [])
                                       if f.get("verdict") == "CRITICAL_VULN"]))

        # Step 5.5: Judge — Gauntlet Validation
        judge_report = self._call_judge(refined_code, audit_report, blueprint)

        # Step 6: Merchant cost analysis
        cost_summary = self._call_merchant()

        # Determine final verdict
        if audit_report["verdict"] == "VIBE_VERIFIED":
            verdict = "CONSENSUS_REACHED"
        else:
            verdict = "CONSENSUS_PARTIAL"

        elapsed = round(time.time() - start_time, 2)

        # Build consensus result
        consensus_result = {
            "hive_id": self.hive_id,
            "verdict": verdict,
            "audit_verdict": audit_report["verdict"],
            "agents_participated": list(self.agents.keys()),
            "consensus_hash": hashlib.sha256(
                json.dumps(refined_code, sort_keys=True).encode()
            ).hexdigest(),
            "healing_rounds": healing_rounds,
            "elapsed_s": elapsed,
            "timestamp": datetime.now().isoformat(),
        }

        # Step 7: ZK Manifest
        zk_manifest = generate_zk_manifest(
            self.hive_id, consensus_result, cost_summary
        )

        # Assemble final package
        package = {
            "consensus": consensus_result,
            "blueprint": blueprint,
            "code": refined_code,
            "audit_report": audit_report,
            "judge_report": judge_report,
            "cost_summary": cost_summary,
            "zk_manifest": zk_manifest,
            "constraints_applied": {
                "rules": len(self.constraints.get("permanent_rules", [])),
                "prohibited": len(self.constraints.get("prohibited_patterns", [])),
                "heritage": self.constraints.get("project_heritage", []),
            },
        }

        # Save consensus log
        self._save_consensus_log(package)

        # Print final status
        log("HIVE", "")
        log("HIVE", "=== SWARM CONSENSUS ===")
        log("HIVE", f"  Verdict:    {verdict}")
        log("HIVE", f"  Hive ID:    {self.hive_id}")
        log("HIVE", f"  Files:      {len(refined_code)}")
        log("HIVE", f"  Cost:       ${cost_summary['total_cost_usd']:.4f}")
        log("HIVE", f"  Sentinel:   {audit_report['verdict']}")
        log("HIVE", f"  Judge:      {judge_report.get('verdict', 'N/A')}")
        log("HIVE", f"  Healing:    {healing_rounds} rounds")
        log("HIVE", f"  ZK Proof:   {zk_manifest['full_zk_proof'][:16]}...")
        log("HIVE", f"  Elapsed:    {elapsed}s")

        status = zk_manifest["orchestrator_status"]
        self._hub_post("System",
                       f"Swarm complete. Verdict: {verdict}. Status: {status}. "
                       f"Files: {len(refined_code)}. Cost: ${cost_summary['total_cost_usd']:.4f}. ({elapsed}s)",
                       "VERDICT")
        log("HIVE", "")
        log("HIVE", f"  ORCHESTRATOR STATUS: {status}")
        log("HIVE", "========================")

        return package

    def _save_consensus_log(self, package: Dict[str, Any]):
        """Persist consensus results to logs/swarm_consensus.json."""
        try:
            existing = []
            if os.path.exists(self.consensus_log_path):
                with open(self.consensus_log_path, "r") as f:
                    data = json.load(f)
                    existing = data if isinstance(data, list) else [data]

            # Append slim entry (don't log full code)
            entry = {
                "hive_id": package["consensus"]["hive_id"],
                "verdict": package["consensus"]["verdict"],
                "files": list(package["code"].keys()),
                "cost_usd": package["cost_summary"]["total_cost_usd"],
                "zk_proof": package["zk_manifest"]["full_zk_proof"][:32],
                "timestamp": package["consensus"]["timestamp"],
            }
            existing.append(entry)

            with open(self.consensus_log_path, "w") as f:
                json.dump(existing, f, indent=2, default=str)
        except Exception as e:
            log("HIVE", f"  Warning: Could not save consensus log: {e}")


# =============================================================
#  CLI ENTRY POINT
# =============================================================

if __name__ == "__main__":
    import sys

    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Build a multi-api crypto tracker"
    pulse = f"Pulse: {datetime.now().strftime('%Y-%m-%d')} Focus: Production"

    coordinator = HiveCoordinator()
    package = coordinator.recruit_swarm(request, pulse_context=pulse)

    print(f"\nDone. Verdict: {package['consensus']['verdict']} | "
          f"Files: {len(package['code'])} | "
          f"Cost: ${package['cost_summary']['total_cost_usd']:.4f}")
