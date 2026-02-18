#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  OVERLORD AUTONOMOUS SUPERVISOR
  The self-improvement daemon. When idle, it refines past
  projects and evolves the engine's knowledge base.

  Usage:
    python overlord_auto.py              # Foreground
    pythonw overlord_auto.py             # Background (no console)
    python overlord_auto.py --now        # Force an immediate cycle
═══════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────
VAULT_PATH = os.path.join(os.path.dirname(__file__), "output")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "engine_memory.json")
IDLE_LIMIT_HOURS = 12
CYCLE_CHECK_INTERVAL = 300  # Check every 5 minutes
LOG_FILE = os.path.join(os.path.dirname(__file__), "overlord_auto.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("OverlordAuto")

# Also print to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


class AutonomousSupervisor:
    """
    The Overlord's autonomous improvement loop.
    
    When the Creator hasn't interacted for `idle_limit_hours`,
    the Supervisor wakes up and:
      1. Finds the most recent project in the vault.
      2. Runs the CreationEngine in 'upgrade' mode to refine it.
      3. Logs the results and updates engine memory.
    """

    def __init__(self, vault_path=VAULT_PATH, idle_limit_hours=IDLE_LIMIT_HOURS):
        self.vault = vault_path
        self.limit = idle_limit_hours
        self.last_interaction = self._get_last_interaction_time()
        self.cycle_count = 0

    def _get_last_interaction_time(self) -> datetime:
        """Infer last interaction from engine_memory.json timestamps."""
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                memories = data.get("memories", [])
                if memories:
                    last_ts = memories[-1].get("timestamp", "")
                    return datetime.fromisoformat(last_ts)
        except Exception:
            pass
        return datetime.now()

    def check_idle_status(self) -> bool:
        """Returns True if the engine should take initiative."""
        idle_duration = datetime.now() - self.last_interaction
        idle_hours = idle_duration.total_seconds() / 3600

        if idle_hours > self.limit:
            logger.info(f"⏰ Idle for {idle_hours:.1f}h (limit: {self.limit}h). Initiating Self-Improvement...")
            return True
        return False

    def get_latest_project(self) -> str:
        """Find the most recently modified project directory in the vault."""
        if not os.path.exists(self.vault):
            return None

        projects = []
        for name in os.listdir(self.vault):
            full_path = os.path.join(self.vault, name)
            if os.path.isdir(full_path):
                # Skip hidden dirs and __pycache__
                if name.startswith(".") or name == "__pycache__":
                    continue
                projects.append(full_path)

        if not projects:
            return None

        # Sort by modification time, newest first
        projects.sort(key=os.path.getmtime, reverse=True)
        return projects[0]

    def execute_refinement(self, project_path: str) -> dict:
        """
        Run the CreationEngine in 'upgrade' mode on the target project.
        This is the actual self-improvement step.
        """
        project_name = os.path.basename(project_path)
        logger.info(f"🔧 Refining: {project_name}")

        try:
            # Import the engine locally to avoid circular deps
            sys.path.insert(0, os.path.dirname(__file__))
            from creation_engine.orchestrator import CreationEngine

            engine = CreationEngine(
                project_name=project_name,
                prompt=f"Analyze and optimize this project. Fix any bugs, improve performance, add error handling, and clean up code style.",
                output_dir=self.vault,
                mode="upgrade",
                source_path=project_path,
                force_local=True,
                phase="all",
                max_fix_cycles=2,
            )

            result = engine.run()

            if result.get("success"):
                logger.info(f"✅ Refinement succeeded: {project_name}")
                self._log_refinement(project_name, "success", result)
            else:
                logger.warning(f"⚠ Refinement partial: {project_name} — {result.get('error', 'Unknown')}")
                self._log_refinement(project_name, "partial", result)

            return result

        except Exception as e:
            logger.error(f"❌ Refinement crashed: {project_name} — {e}")
            self._log_refinement(project_name, "failed", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _log_refinement(self, project_name: str, status: str, result: dict):
        """Append refinement record to engine_memory.json."""
        try:
            data = {}
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)

            if "autonomous_refinements" not in data:
                data["autonomous_refinements"] = []

            entry = {
                "project": project_name,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "cycle": self.cycle_count,
            }

            # Cap to last 20 refinements
            data["autonomous_refinements"].append(entry)
            data["autonomous_refinements"] = data["autonomous_refinements"][-20:]

            with open(MEMORY_FILE, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            logger.error(f"Failed to log refinement: {e}")

    def trigger_autonomous_cycle(self):
        """Execute one full autonomous improvement cycle."""
        self.cycle_count += 1
        logger.info(f"═══ AUTONOMOUS CYCLE #{self.cycle_count} ═══")

        # 1. Find target
        project = self.get_latest_project()
        if not project:
            logger.info("No projects found in vault. Skipping cycle.")
            return

        logger.info(f"🎯 Target: {os.path.basename(project)}")

        # 2. Refine
        self.execute_refinement(project)

        # 3. Reset idle clock
        self.last_interaction = datetime.now()

        logger.info(f"═══ CYCLE #{self.cycle_count} COMPLETE ═══\n")

    def run(self, force_now=False):
        """Main daemon loop."""
        logger.info("🤖 Overlord Autonomous Supervisor started.")
        logger.info(f"   Vault: {self.vault}")
        logger.info(f"   Idle limit: {self.limit}h")
        logger.info(f"   Last interaction: {self.last_interaction.strftime('%Y-%m-%d %H:%M')}")

        if force_now:
            logger.info("⚡ --now flag detected. Forcing immediate cycle.")
            self.trigger_autonomous_cycle()
            return

        while True:
            try:
                # Re-check last interaction (it may update from live usage)
                self.last_interaction = self._get_last_interaction_time()

                if self.check_idle_status():
                    self.trigger_autonomous_cycle()

                time.sleep(CYCLE_CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Supervisor stopped by user.")
                break
            except Exception as e:
                logger.error(f"Supervisor error: {e}")
                time.sleep(60)  # Back off on errors


if __name__ == "__main__":
    force = "--now" in sys.argv
    supervisor = AutonomousSupervisor()
    supervisor.run(force_now=force)
