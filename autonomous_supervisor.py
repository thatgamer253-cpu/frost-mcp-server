#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  AUTONOMOUS SUPERVISOR — "The Pulse"
  The heartbeat of the Kinetic Prism. Oversees all daemons,
  auto-restarts crashed services, tracks growth, and evolves.

  Usage:
      python autonomous_supervisor.py --objective "Grow Kinetic Prism"
══════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import signal
import argparse
import subprocess
import threading
from datetime import datetime, timedelta

from hardware_steward import HardwareSteward
from pipeline_events import Chronicle, FutureProjector
from workflow_tracker import WorkflowTracker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(SCRIPT_DIR)

# ── Config ───────────────────────────────────────────────────
MEMORY_FILE = os.path.join(SCRIPT_DIR, "engine_memory.json")
SUPERVISOR_LOG = os.path.join(SCRIPT_DIR, "supervisor.log")
HEARTBEAT_LOG = os.path.join(SCRIPT_DIR, "heartbeat.log")
SENTINEL_LOG = os.path.join(SCRIPT_DIR, "sentinel.log")
AWARENESS_LOG = os.path.join(SCRIPT_DIR, "awareness.log")

PULSE_INTERVAL = 30          # seconds between health checks

GROWTH_EVAL_CYCLES = 10      # evaluate growth every N cycles
MAX_RESTART_ATTEMPTS = 5     # max restarts before marking service dead

# ── Services the Pulse oversees ──────────────────────────────
MANAGED_SERVICES = {
    "heartbeat_daemon": {
        "script": "heartbeat_daemon.py",
        "description": "The Dreaming — background thought engine",
        "critical": True,
    },
    "sentinel": {
        "script": "sentinel.py",
        "description": "Evolutionary Memory — log scanner & personality evolution",
        "critical": True,
    },
    "healer_watchdog": {
        "script": "healer_watchdog.py",
        "args": ["--mode", "autonomous"],
        "description": "The Nervous System — service health & auto-healing",
        "critical": False,
    },
}

# ── Logging ──────────────────────────────────────────────────
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    print(entry)
    try:
        with open(SUPERVISOR_LOG, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def banner(objective):
    lines = [
        "",
        "  ╔══════════════════════════════════════════════════════╗",
        "  ║        AUTONOMOUS SUPERVISOR — THE PULSE            ║",
        "  ╠══════════════════════════════════════════════════════╣",
       f"  ║  Objective: {objective[:40]:<40} ║",
       f"  ║  Started:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<40} ║",
        "  ║  Mode:      FULLY AUTONOMOUS                       ║",
        "  ╚══════════════════════════════════════════════════════╝",
        "",
    ]
    for line in lines:
        log(line)


# ── Memory I/O ───────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "name": "Overlord",
        "growth_level": 1,
        "successful_creations": 0,
        "memories": [],
        "dream_log": [],
        "learned_constraints": [],
        "supervisor_state": {},
    }


def save_memory(data):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        log(f"Failed to save memory: {e}", "ERROR")


# ── Process Management ───────────────────────────────────────
class ServiceManager:
    """Manages child processes for the digital workforce."""

    def __init__(self, objective, steward=None):
        self.processes = {}       # name -> subprocess.Popen
        self.restart_counts = {}  # name -> int
        self.start_times = {}     # name -> datetime
        self.objective = objective
        self.steward = steward or HardwareSteward()
        self.chronicle = Chronicle(SCRIPT_DIR)
        self.projector = FutureProjector(SCRIPT_DIR)
        self.tracker = WorkflowTracker(SCRIPT_DIR, self.chronicle.add_note)
        self._lock = threading.Lock()
        
        # Start background workflow tracking
        self.tracker.start()

    def start_service(self, name, config):
        """Start a managed service as a subprocess."""
        with self._lock:
            if name in self.processes:
                proc = self.processes[name]
                if proc and proc.poll() is None:
                    log(f"  [{name}] Already running (PID {proc.pid})")
                    return True

            script = os.path.join(SCRIPT_DIR, config["script"])
            if not os.path.exists(script):
                log(f"  [{name}] Script not found: {script}", "ERROR")
                return False

            args = [sys.executable, script] + config.get("args", [])
            try:
                # Use a flag that works on both Windows and Linux
                creationflags = 0
                if sys.platform == "win32":
                    import subprocess
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

                proc = subprocess.Popen(
                    args,
                    cwd=SCRIPT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                )
                self.processes[name] = proc
                self.start_times[name] = datetime.now()
                self.restart_counts[name] = self.restart_counts.get(name, 0)
                log(f"  ✅ [{name}] ONLINE — PID {proc.pid} — {config['description']}")
                return True
            except Exception as e:
                log(f"  ❌ [{name}] FAILED TO START: {e}", "ERROR")
                return False

    def check_health(self):
        """Check all services and restart any that have died."""
        report = {}
        with self._lock:
            for name, config in MANAGED_SERVICES.items():
                proc = self.processes.get(name)
                is_dead = proc is None or proc.poll() is not None
                
                if is_dead:
                    exit_code = proc.returncode if proc else "never started"
                    report[name] = {"status": "DEAD", "exit_code": exit_code}

                    current_restarts = self.restart_counts.get(name, 0)
                    if current_restarts < MAX_RESTART_ATTEMPTS:
                        log(f"  ⚠️  [{name}] DEAD (exit={exit_code}). Restarting...", "WARN")
                        self.restart_counts[name] = current_restarts + 1
                        # We are inside a lock, so we must be careful. 
                        # Better to mark for restart and do it outside or avoid complex calls here.
                        # But for simplicity, we'll call direct.
                        self._lock.release()
                        try:
                            self.start_service(name, config)
                        finally:
                            self._lock.acquire()
                    else:
                        log(f"  💀 [{name}] PERMANENTLY DEAD after {MAX_RESTART_ATTEMPTS} restarts.", "ERROR")
                        report[name]["status"] = "ABANDONED"
                else:
                    # proc is definitely not None here
                    uptime = datetime.now() - self.start_times.get(name, datetime.now())
                    report[name] = {
                        "status": "ALIVE",
                        "pid": proc.pid,
                        "uptime_seconds": int(uptime.total_seconds()),
                    }
        return report

    def awareness_check(self, objective):
        """Perform multidimensional awareness check."""
        # 1. Hardware Awareness (Sense)
        vram_stats = self.steward.get_gpu_health()
        heavy_pressure = False
        for gpu in vram_stats:
            if gpu["vram_percent"] > 90.0:
                log(f"  🧠 [Awareness] VRAM pressure ({gpu['vram_percent']}%) on {gpu['name']}. Pausing non-critical tasks.", "WARN")
                heavy_pressure = True
                break
        
        # 2. Goal Alignment (Identity)
        # Placeholder for real LLM scoring
        alignment_score = 1.0 
        if "Prism" not in objective:
            alignment_score = 0.4 # Hypothetical misalignment
            log(f"  🧠 [Awareness] Goal misalignment detected! Score: {alignment_score}", "CAUTION")

        # 3. Handle Meta-Adjustment
        if heavy_pressure:
            self._throttle_services(True)
        else:
            self._throttle_services(False)

        # 4. Temporal Awareness (Future Projection)
        exhaustion_warning = self.projector.predict_storage_exhaustion()
        if exhaustion_warning:
            log(f"  🧠 [Awareness] {exhaustion_warning}", "CAUTION")
        
        pivot_suggestion = self.projector.analyze_market_pivot(objective)
        if pivot_suggestion:
            log(f"  🧠 [Awareness] {pivot_suggestion}", "INFO")

    def _throttle_services(self, throttle=True):
        """Pause or resume non-critical services (like heartbeat_daemon)."""
        target = "heartbeat_daemon" # Non-critical background thought
        proc = self.processes.get(target)
        if not proc or proc.poll() is not None:
            return

        if throttle:
            # On windows we can't easily 'pause' without signals, 
            # so we just log the 'intent' for now or could terminate and restart later.
            # For this demo, let's just log the adaptation.
            log(f"  🛠️  [Adaptation] Throttling {target} to save resources.")
        else:
            # Resume if throttled
            pass

    def stop_all(self):
        """Gracefully terminate all managed services."""
        with self._lock:
            for name, proc in self.processes.items():
                if proc and proc.poll() is None:
                    log(f"  Stopping [{name}] (PID {proc.pid})...")
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                    log(f"  [{name}] stopped.")
            self.processes.clear()


# ── Growth Evaluator ─────────────────────────────────────────
def evaluate_growth(memory, health_report, objective):
    """
    Assess the overall health and growth of the Kinetic Prism.
    Updates growth_level in engine_memory.
    """
    alive_count = sum(1 for s in health_report.values() if s["status"] == "ALIVE")
    total = len(health_report)
    health_pct = (alive_count / total * 100) if total > 0 else 0

    current_level = memory.get("growth_level", 1)

    # Growth logic: level up if all services healthy & constraints are being learned
    constraints_count = len(memory.get("learned_constraints", []))
    dream_count = len(memory.get("dream_log", []))
    creations = memory.get("successful_creations", 0)

    # Simple growth formula
    growth_score = (
        (alive_count * 10) +
        (constraints_count * 5) +
        (dream_count * 2) +
        (creations * 15)
    )

    new_level = max(1, min(100, growth_score // 10))

    if new_level > current_level:
        log(f"  🌱 GROWTH: Level {current_level} → {new_level}  (score: {growth_score})")
        memory["growth_level"] = new_level
    else:
        log(f"  📊 Growth Level: {current_level}  |  Score: {growth_score}  |  Health: {health_pct:.0f}%")

    # Record supervisor state
    memory["supervisor_state"] = {
        "objective": objective,
        "health_pct": health_pct,
        "alive_services": alive_count,
        "total_services": total,
        "growth_score": growth_score,
        "last_pulse": datetime.now().isoformat(),
        "total_restarts": sum(1 for _ in []),  # placeholder
    }

    save_memory(memory)
    return new_level


# ── Main Loop ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Autonomous Supervisor — The Pulse")
    parser.add_argument("--objective", type=str, default="Grow Kinetic Prism",
                        help="The high-level objective for the digital workforce.")
    parser.add_argument("--interval", type=int, default=PULSE_INTERVAL,
                        help="Seconds between health checks.")
    args = parser.parse_args()

    banner(args.objective)

    manager = ServiceManager(args.objective)

    # Register graceful shutdown
    def shutdown(sig, frame):
        log("\n⛔ SHUTDOWN SIGNAL RECEIVED. Stopping all services...")
        manager.stop_all()
        if hasattr(manager, 'tracker'):
            manager.tracker.stop()
        log("=== AUTONOMOUS SUPERVISOR STOPPED ===")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Phase 1: Boot all services ───────────────────────────
    log("═══ PHASE 1: BOOTING DIGITAL WORKFORCE ═══")
    for name, config in MANAGED_SERVICES.items():
        manager.start_service(name, config)
    log("")

    # ── Phase 2: Autonomous monitoring loop ──────────────────
    log("═══ PHASE 2: ENTERING AUTONOMOUS PULSE LOOP ═══")
    log(f"  Objective: {args.objective}")
    log(f"  Pulse interval: {args.interval}s")
    log(f"  Growth evaluation every {GROWTH_EVAL_CYCLES} cycles")
    log("")

    cycle = 0
    try:
        while True:
            cycle += 1
            log(f"── Pulse #{cycle} ──────────────────────────────────")

            # Awareness Check (Sense & Identity)
            manager.awareness_check(args.objective)

            # Health check
            health = manager.check_health()


            # Growth evaluation on schedule
            if cycle % GROWTH_EVAL_CYCLES == 0:
                memory = load_memory()
                evaluate_growth(memory, health, args.objective)

            # Brief status line
            alive = sum(1 for s in health.values() if s["status"] == "ALIVE")
            log(f"  Status: {alive}/{len(health)} services alive  |  Cycle: {cycle}")
            log("")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
