"""
Sovereign Module — Healing Swarm
The Engine's immune system. Lightweight background Medics
that run health checks and trigger rollback on failure.

Usage:
    from creation_engine.sovereign.healer import swarm

    report = swarm.run_health_check()
    if not report["healthy"]:
        swarm.auto_rollback_if_needed()
"""

import os
import sys
import json
import importlib
import traceback
from datetime import datetime
from pathlib import Path


class HealthReport:
    """Result of a full health check across all medics."""

    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.checks = []  # List of {name, passed, message}
        self.healthy = True

    def add(self, name: str, passed: bool, message: str = ""):
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
        })
        if not passed:
            self.healthy = False

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "healthy": self.healthy,
            "checks": self.checks,
            "passed": sum(1 for c in self.checks if c["passed"]),
            "failed": sum(1 for c in self.checks if not c["passed"]),
        }

    def summary(self) -> str:
        status = "✅ HEALTHY" if self.healthy else "🚨 DEGRADED"
        lines = [f"**System Health**: {status}"]
        for c in self.checks:
            icon = "✅" if c["passed"] else "❌"
            lines.append(f"  {icon} {c['name']}: {c['message']}")
        return "\n".join(lines)


class HealingSwarm:
    """
    Recursive hardening: the Engine's immune system.

    Registers 'Medics' — small functions that check system health.
    When called, runs all medics and returns a HealthReport.
    If critical failures are found, triggers auto-rollback.
    """

    def __init__(self):
        self._medics = []
        self._last_report = None
        self._register_builtin_medics()

    # ── Medic Registration ───────────────────────────────────

    def register_medic(self, name: str, check_fn):
        """
        Register a health check function.
        check_fn() should return (passed: bool, message: str)
        """
        self._medics.append({"name": name, "fn": check_fn})

    def _register_builtin_medics(self):
        """Register the default set of health checks."""
        self.register_medic("ImportMedic", self._check_imports)
        self.register_medic("MemoryMedic", self._check_memory_integrity)
        self.register_medic("ConfigMedic", self._check_config)
        self.register_medic("DiskMedic", self._check_disk_space)
        self.register_medic("IPCMedic", self._check_ipc_health)

    # ── Execution ────────────────────────────────────────────

    def run_health_check(self) -> HealthReport:
        """Run all registered medics and return a HealthReport."""
        report = HealthReport()

        for medic in self._medics:
            try:
                passed, message = medic["fn"]()
                report.add(medic["name"], passed, message)
            except Exception as e:
                report.add(medic["name"], False, f"Medic crashed: {e}")

        self._last_report = report

        # Log the report
        ts = datetime.now().strftime("%H:%M:%S")
        status = "✅" if report.healthy else "🚨"
        print(f"[{ts}] [HEALER] {status} Health check: "
              f"{report.to_dict()['passed']}/{len(report.checks)} passed")

        # Post to Hub if available
        try:
            from creation_engine.sovereign.hub import hub, Channel
            hub.broadcast(
                Channel.HEALING,
                "medic",
                report.summary(),
                msg_type="STATUS" if report.healthy else "FLAG",
                priority=0 if report.healthy else 2,
            )
        except Exception:
            pass

        return report

    def auto_rollback_if_needed(self) -> bool:
        """
        If the last health check failed, attempt to rollback
        engine_memory.json to the last snapshot.
        """
        if self._last_report and self._last_report.healthy:
            return False  # No rollback needed

        try:
            from creation_engine.sovereign.sandbox import sandbox

            snapshots = sandbox.list_snapshots()
            if not snapshots:
                print("[HEALER] ⚠️ No snapshots available for rollback")
                return False

            latest = snapshots[0]
            print(f"[HEALER] ⏪ Attempting rollback to {latest['id']}...")
            success = sandbox.rollback(latest["id"])

            if success:
                # Post recovery to Hub
                try:
                    from creation_engine.sovereign.hub import hub, Channel
                    hub.broadcast(
                        Channel.HEALING, "medic",
                        f"Auto-rollback to snapshot {latest['id']} completed.",
                        msg_type="RESOLVE", priority=2,
                    )
                except Exception:
                    pass

            return success
        except Exception as e:
            print(f"[HEALER] ❌ Rollback failed: {e}")
            return False

    @property
    def last_report(self):
        return self._last_report

    # ── Built-in Medics ──────────────────────────────────────

    def _check_imports(self):
        """Validate core creation_engine modules can be imported."""
        critical_modules = [
            "creation_engine.llm_client",
            "creation_engine.architect",
            "creation_engine.developer",
            "creation_engine.supervisor",
        ]
        failures = []
        for mod_name in critical_modules:
            try:
                if mod_name in sys.modules:
                    importlib.reload(sys.modules[mod_name])
                else:
                    importlib.import_module(mod_name)
            except Exception as e:
                failures.append(f"{mod_name}: {e}")

        if failures:
            return False, f"Import failures: {'; '.join(failures)}"
        return True, f"All {len(critical_modules)} core modules OK"

    def _check_memory_integrity(self):
        """Validate engine_memory.json is well-formed."""
        mem_path = "engine_memory.json"
        if not os.path.exists(mem_path):
            return True, "No engine_memory.json (fresh state)"

        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return True, f"Valid JSON ({len(json.dumps(data))} chars)"
        except json.JSONDecodeError as e:
            return False, f"Corrupted: {e}"
        except Exception as e:
            return False, f"Read error: {e}"

    def _check_config(self):
        """Verify essential environment variables exist."""
        # Check for at least one LLM API key
        key_vars = [
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY", "GEMINI_API_KEY",
        ]
        found = [k for k in key_vars if os.environ.get(k)]
        if found:
            return True, f"LLM keys found: {', '.join(found)}"
        return False, "No LLM API keys detected in environment"

    def _check_disk_space(self):
        """Check output directory isn't consuming too much space."""
        output_dir = "output"
        if not os.path.exists(output_dir):
            return True, "Output dir doesn't exist yet"

        total_size = 0
        for dirpath, _, filenames in os.walk(output_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass

        size_mb = total_size / (1024 * 1024)
        if size_mb > 5000:  # > 5GB warning
            return False, f"Output dir is {size_mb:.0f}MB (>5GB)"
        return True, f"Output dir: {size_mb:.0f}MB"

    def _check_ipc_health(self):
        """Verify the agent IPC bus is writable."""
        ipc_path = os.path.join("memory", "agent_chat.jsonl")
        try:
            os.makedirs(os.path.dirname(ipc_path), exist_ok=True)
            # Test atomic write
            with open(ipc_path, "a", encoding="utf-8") as f:
                pass  # Just open in append mode
            return True, "IPC bus writable"
        except Exception as e:
            return False, f"IPC not writable: {e}"


# ── Global Singleton ─────────────────────────────────────────

swarm = HealingSwarm()
