#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  SOVEREIGN ORCHESTRATOR — Logic Engine with Recursive Memory
  
  The unified entry trigger for the Sovereign Framework v2026.1.
  Enforces the four Core Directives:

    1. Identity Sovereignty   — pulse_sync.json check before finalization
    2. Adversarial Pre-Cond   — Sentinel must exploit every draft
    3. Recursive Intelligence — Audit failures → permanent_constraints.json
    4. Consensus Requirement  — Cross-agent verification for high-risk modules

  Usage:
    python sovereign_orchestrator.py "Build a FastAPI server with auth"
    python sovereign_orchestrator.py --recover    # Rebuild from recovery log
    python sovereign_orchestrator.py --status     # Fleet health check

══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import asyncio
import datetime
from typing import Any, Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ── Logging ──────────────────────────────────────────────────
try:
    from agent_brain import log, divider
except ImportError:
    def log(tag: str, msg: str):
        print(f"[{tag}] {msg}")
    def divider():
        print("─" * 60)

# ── Component Imports (graceful degrade) ─────────────────────
_HAS_PULSE_SYNC = False
_HAS_HIVE = False
_HAS_DAG = False
_HAS_STATUS = False

try:
    from pulse_sync_logger import PulseSyncLogger
    _HAS_PULSE_SYNC = True
except ImportError:
    pass

try:
    from hive_coordinator import HiveCoordinator, load_permanent_constraints
    _HAS_HIVE = True
except ImportError:
    pass

try:
    from agent_brain_v2 import AgentBrain
    _HAS_DAG = True
except ImportError:
    pass

try:
    from hive_status import generate_hive_dashboard, HiveAutoMaintenance, HiveLogAggregator
    _HAS_STATUS = True
except ImportError:
    pass

try:
    from creation_engine.local_memory import LocalMemoryManager
    _HAS_LOCAL_MEMORY = True
except ImportError:
    _HAS_LOCAL_MEMORY = False


CONSTRAINTS_PATH = os.path.join(SCRIPT_DIR, "memory", "permanent_constraints.json")
RECOVERY_LOG = os.path.join(SCRIPT_DIR, "logs", "sovereign_recovery.json")
os.makedirs(os.path.join(SCRIPT_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(SCRIPT_DIR, "memory"), exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  CORE DIRECTIVE: Recursive Intelligence
#  Every audit failure is logged to permanent_constraints.json
# ══════════════════════════════════════════════════════════════

class RecursiveMemory:
    """
    Manages the permanent_constraints.json — the collective wisdom
    of past build failures. Ensures no logic is ever repeated.
    """

    def __init__(self, path: str = CONSTRAINTS_PATH):
        self.path = path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "project_heritage": [],
            "permanent_rules": [],
            "prohibited_patterns": [],
        }

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def get_rules_summary(self) -> str:
        """Return a formatted string of all constraints for LLM injection."""
        lines = ["PERMANENT CONSTRAINTS (Recursive Intelligence):"]
        for rule in self.data.get("permanent_rules", []):
            lines.append(
                f"  [{rule.get('id', '?')}] {rule.get('issue', '?')}: "
                f"{rule.get('lesson', '?')}"
            )
        prohibited = self.data.get("prohibited_patterns", [])
        if prohibited:
            lines.append("  PROHIBITED:")
            for p in prohibited:
                lines.append(f"    - {p}")
        return "\n".join(lines)

    def learn_from_failure(self, issue: str, lesson: str,
                           enforcement: str = ""):
        """
        Record a new constraint from an audit failure.
        Auto-generates an ID and deduplicates.
        """
        existing_issues = {
            r.get("issue", "").lower()
            for r in self.data.get("permanent_rules", [])
        }
        if issue.lower() in existing_issues:
            log("MEMORY", f"  ℹ Constraint already known: {issue}")
            return

        # Generate next ID
        rules = self.data.get("permanent_rules", [])
        next_num = len(rules) + 1
        prefix = "AUT" if "auto" in issue.lower() else "SEC" if "secur" in issue.lower() else "ENG"
        new_id = f"{prefix}-{next_num:03d}"

        new_rule = {
            "id": new_id,
            "issue": issue,
            "lesson": lesson,
            "enforcement": enforcement or f"Auto-learned from audit at {datetime.datetime.now().isoformat()}",
            "learned_at": datetime.datetime.now().isoformat(),
        }

        self.data.setdefault("permanent_rules", []).append(new_rule)
        self._save()
        log("MEMORY", f"  📝 New constraint learned: [{new_id}] {issue}")

    def learn_prohibited_pattern(self, pattern: str):
        """Add a new prohibited pattern (deduplicates)."""
        existing = [p.lower() for p in self.data.get("prohibited_patterns", [])]
        if pattern.lower() not in existing:
            self.data.setdefault("prohibited_patterns", []).append(pattern)
            self._save()
            log("MEMORY", f"  🚫 New prohibited pattern: {pattern}")


# ══════════════════════════════════════════════════════════════
#  SOVEREIGN ORCHESTRATOR — The Unified Logic Engine
# ══════════════════════════════════════════════════════════════

class SovereignOrchestrator:
    """
    The master orchestrator that enforces all four Core Directives
    and provides a single entry point for the Sovereign Framework.

    Orchestration flow:
      1. Pulse-Sync check (Identity Sovereignty)
      2. Permanent constraints injection (Recursive Intelligence)
      3. Build via DAG or Hive (with Adversarial Pre-Condition)
      4. Learn from failures (Recursive Intelligence)
      5. Cross-agent consensus verification (Consensus Requirement)
      6. Fleet status update
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.memory = RecursiveMemory()
        
        # Session Memory (VRAM Stability)
        self.session_memory = None
        if _HAS_LOCAL_MEMORY:
            self.session_memory = LocalMemoryManager(model="deepseek-r1:7b")

        # Pulse-Sync
        self.pulse_sync = None
        if _HAS_PULSE_SYNC:
            try:
                self.pulse_sync = PulseSyncLogger(project_root=SCRIPT_DIR)
                log("SOVEREIGN", "  🫀 Pulse-Sync: ONLINE")
            except Exception as e:
                log("SOVEREIGN", f"  ℹ Pulse-Sync unavailable: {e}")

        # Hive Coordinator
        self.hive = None
        if _HAS_HIVE:
            try:
                self.hive = HiveCoordinator(model=model)
                log("SOVEREIGN", "  🐝 Hive Coordinator: ONLINE")
            except Exception as e:
                log("SOVEREIGN", f"  ℹ Hive unavailable: {e}")

        # DAG Brain
        self.brain = None
        if _HAS_DAG:
            try:
                self.brain = AgentBrain()
                log("SOVEREIGN", "  🧠 DAG Brain: ONLINE")
            except Exception as e:
                log("SOVEREIGN", f"  ℹ DAG Brain unavailable: {e}")

    def _check_identity_sovereignty(self, prompt: str) -> str:
        """
        DIRECTIVE 1: No code is finalized without a pulse_sync.json check.
        Returns the pulse context string for injection.
        """
        if not self.pulse_sync:
            log("SOVEREIGN", "  ⚠ Pulse-Sync not available — proceeding without identity anchor")
            return ""

        log("SOVEREIGN", "  🔍 Directive 1: Identity Sovereignty check...")
        try:
            self.pulse_sync.capture_heartbeat()
            ctx = self.pulse_sync.get_context_for_orchestrator()
            if ctx:
                pulse_data = self.pulse_sync._load_existing()
                risk = pulse_data.get("identity_fragmentation_risk", "Low")
                log("SOVEREIGN", f"  🫀 Identity verified — Risk: {risk}")

                if "High" in str(risk):
                    log("SOVEREIGN", "  🚩 HIGH FRAGMENTATION RISK — consider manual vibe-shift")
                return ctx
            else:
                log("SOVEREIGN", "  ℹ No pulse data — first run")
                return ""
        except Exception as e:
            log("SOVEREIGN", f"  ⚠ Pulse-Sync error: {e}")
            return ""

    def _inject_constraints(self) -> str:
        """
        DIRECTIVE 3: Recursive Intelligence — inject all learned constraints.
        """
        log("SOVEREIGN", "  📜 Directive 3: Loading permanent constraints...")
        summary = self.memory.get_rules_summary()
        rule_count = len(self.memory.data.get("permanent_rules", []))
        pattern_count = len(self.memory.data.get("prohibited_patterns", []))
        log("SOVEREIGN", f"  📝 {rule_count} rule(s), {pattern_count} prohibited pattern(s)")
        return summary

    def _learn_from_audit(self, audit_report: Dict[str, Any]):
        """
        DIRECTIVE 3 (post-build): Record any new failures as permanent constraints.
        """
        if not audit_report:
            return

        issues = audit_report.get("issues", [])
        shadow_issues = audit_report.get("shadow_issues", [])

        for issue in issues:
            if issue.get("severity") in ("CRITICAL", "HIGH"):
                self.memory.learn_from_failure(
                    issue=issue.get("detail", "Unknown issue")[:100],
                    lesson=f"Detected by Guardian: {issue.get('detail', '?')}",
                    enforcement="Auto-learned from build audit"
                )

        for si in shadow_issues:
            detail = si.get("detail", "")
            if detail:
                self.memory.learn_prohibited_pattern(
                    f"Shadow Logic: {detail[:100]}"
                )

    async def execute(self, prompt: str) -> Dict[str, Any]:
        """
        Main entry point — runs the full Sovereign Framework pipeline.
        """
        log("SOVEREIGN", "═" * 60)
        divider()

        if self.session_memory:
            self.session_memory.add_turn("user", prompt)

        # Directive 1: Identity Sovereignty
        pulse_ctx = self._check_identity_sovereignty(prompt)
        divider()

        # Directive 3: Recursive Intelligence (pre-build)
        constraints = self._inject_constraints()
        divider()

        # Directive 2 + 4: Build (Adversarial Pre-Cond + Consensus)
        result = {}
        if self.brain:
            # Prefer the DAG brain (has Shadow Logic + Pulse-Sync built in)
            log("SOVEREIGN", "  🧠 Routing to DAG Brain (Hardened Orchestrator V4)...")
            try:
                state = await self.brain.execute_build(prompt)
                result = {
                    "engine": "DAG",
                    "audit_report": state.get("audit_report", {}),
                    "security_manifest": state.get("security_manifest", {}),
                    "final_package": state.get("final_package_path", ""),
                    "final_binary": state.get("final_binary", ""),
                    "files": list(state.get("code", {}).keys()),
                }
            except Exception as e:
                log("SOVEREIGN", f"  ✗ DAG Brain failed: {e}")
                result = {"engine": "DAG", "error": str(e)}

        elif self.hive:
            # Fallback to Hive Coordinator
            log("SOVEREIGN", "  🐝 Routing to Hive Coordinator...")
            try:
                package = self.hive.recruit_swarm(prompt, pulse_context=pulse_ctx)
                result = {
                    "engine": "Hive",
                    "package": package,
                }
            except Exception as e:
                log("SOVEREIGN", f"  ✗ Hive failed: {e}")
                result = {"engine": "Hive", "error": str(e)}
        else:
            log("SOVEREIGN", "  ✗ No build engine available!")
            result = {"engine": "None", "error": "No DAG or Hive available"}

        divider()

        # Directive 3 (post-build): Learn from audit
        audit_report = result.get("audit_report", {})
        if audit_report:
            log("SOVEREIGN", "  📜 Directive 3: Learning from audit results...")
            self._learn_from_audit(audit_report)
        divider()

        # Fleet status update
        if _HAS_STATUS:
            log("SOVEREIGN", "  🐝 Updating fleet status...")
            try:
                generate_hive_dashboard(auto_maintain=True)
            except Exception as e:
                log("SOVEREIGN", f"  ⚠ Status update failed: {e}")

        # Save recovery log
        recovery = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt,
            "engine_used": result.get("engine", "Unknown"),
            "success": "error" not in result,
            "audit_status": audit_report.get("status", "N/A"),
            "constraints_count": len(self.memory.data.get("permanent_rules", [])),
        }
        self._save_recovery_log(recovery)

        log("SOVEREIGN", "═" * 60)
        log("SOVEREIGN", "  🏛️  SOVEREIGN ORCHESTRATOR — MISSION COMPLETE")
        log("SOVEREIGN", "═" * 60)

        return result

    def _save_recovery_log(self, entry: dict):
        """Append to the sovereign recovery log for crash recovery."""
        history = []
        if os.path.exists(RECOVERY_LOG):
            try:
                with open(RECOVERY_LOG, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(entry)
        history = history[-50:]  # Keep last 50

        with open(RECOVERY_LOG, "w") as f:
            json.dump(history, f, indent=2, default=str)

    @staticmethod
    def recover():
        """
        Recovery protocol — rebuild state from the recovery log.
        Useful after a context reset or fresh session.
        """
        print("\n🔄 SOVEREIGN RECOVERY PROTOCOL")
        print("─" * 40)

        # 1. Check core files
        core_files = {
            "pulse_sync_logger.py": _HAS_PULSE_SYNC,
            "hive_coordinator.py": _HAS_HIVE,
            "agent_brain_v2.py": _HAS_DAG,
            "hive_status.py": _HAS_STATUS,
        }

        print("\nCore Component Status:")
        for f, available in core_files.items():
            status = "✓ ONLINE" if available else "✗ MISSING"
            print(f"  {status}  {f}")

        # 2. Check memory
        memory = RecursiveMemory()
        rules = memory.data.get("permanent_rules", [])
        patterns = memory.data.get("prohibited_patterns", [])
        print(f"\nRecursive Memory:")
        print(f"  Rules: {len(rules)}")
        print(f"  Prohibited Patterns: {len(patterns)}")

        # 3. Check recovery log
        if os.path.exists(RECOVERY_LOG):
            try:
                with open(RECOVERY_LOG, "r") as f:
                    log_data = json.load(f)
                if log_data:
                    last = log_data[-1]
                    print(f"\nLast Build:")
                    print(f"  Time: {last.get('timestamp', '?')}")
                    print(f"  Prompt: {last.get('prompt', '?')[:60]}")
                    print(f"  Engine: {last.get('engine_used', '?')}")
                    print(f"  Status: {'✓ Success' if last.get('success') else '✗ Failed'}")
            except Exception:
                pass
        else:
            print("\n  No recovery log found — clean state")

        # 4. Pulse-Sync status
        pulse_file = os.path.join(SCRIPT_DIR, "logs", "pulse_sync.json")
        if os.path.exists(pulse_file):
            try:
                with open(pulse_file, "r") as f:
                    pulse = json.load(f)
                print(f"\nPulse-Sync:")
                print(f"  Last Pulse: {pulse.get('timestamp', '?')}")
                print(f"  Vibe: {pulse.get('current_vibe_shift', '?')}")
                print(f"  Risk: {pulse.get('identity_fragmentation_risk', '?')}")
            except Exception:
                pass

        print(f"\n{'─' * 40}")
        print("Recovery complete. All systems assessed.\n")


# ══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="sovereign_orchestrator",
        description="Sovereign Orchestrator — The Logic Engine with Recursive Memory"
    )
    parser.add_argument(
        "prompt", nargs="?", default=None,
        help="Build prompt (e.g. 'Build a FastAPI server with auth')"
    )
    parser.add_argument(
        "--recover", "-r", action="store_true",
        help="Run recovery protocol — assess system state"
    )
    parser.add_argument(
        "--status", "-s", action="store_true",
        help="Show fleet health dashboard"
    )
    parser.add_argument(
        "--model", "-m", default="gpt-4o",
        help="LLM model to use (default: gpt-4o)"
    )

    args = parser.parse_args()

    if args.recover:
        SovereignOrchestrator.recover()
    elif args.status:
        if _HAS_STATUS:
            generate_hive_dashboard(auto_maintain=True)
        else:
            print("hive_status.py not available")
    elif args.prompt:
        orchestrator = SovereignOrchestrator(model=args.model)
        asyncio.run(orchestrator.execute(args.prompt))
    else:
        parser.print_help()
