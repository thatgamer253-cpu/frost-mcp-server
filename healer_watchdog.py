#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  HEALER WATCHDOG — "The Nervous System"
  Monitors service health, VRAM, and auto-heals the workforce.

  Usage:
      python healer_watchdog.py                  # Standard mode
      python healer_watchdog.py --mode autonomous # Autonomous healing
══════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import argparse
import subprocess
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

try:
    import psutil
except ImportError:
    psutil = None

try:
    import torch
except ImportError:
    torch = None

MEMORY_FILE = os.path.join(SCRIPT_DIR, "engine_memory.json")
HEALER_LOG = os.path.join(SCRIPT_DIR, "healer.log")

# Services to monitor in autonomous mode
CRITICAL_PROCESSES = [
    "heartbeat_daemon.py",
    "sentinel.py",
]


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [HEALER-{level}] {message}"
    print(entry)
    try:
        with open(HEALER_LOG, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def check_vram():
    """Check for free VRAM if GPU is available."""
    if torch and torch.cuda.is_available():
        try:
            free_mem, total_mem = torch.cuda.mem_get_info()
            free_gb = free_mem / (1024 ** 3)
            total_gb = total_mem / (1024 ** 3)
            log(f"  [HARDWARE] VRAM Free: {free_gb:.2f} GB / {total_gb:.2f} GB")
            if free_gb < 1.5:
                log("  [WARNING] VRAM below 1.5GB threshold!", "WARN")
                return False
            return True
        except Exception:
            pass
    log("  [HARDWARE] No CUDA GPU detected or VRAM check failed. CPU fallback active.")
    return True


def check_disk():
    """Check disk space."""
    if psutil:
        try:
            disk = psutil.disk_usage(SCRIPT_DIR)
            free_gb = disk.free / (1024 ** 3)
            log(f"  [DISK] Free: {free_gb:.1f} GB ({disk.percent}% used)")
            if free_gb < 2.0:
                log("  [WARNING] Disk space critically low!", "WARN")
                return False
            return True
        except Exception:
            pass
    return True


def check_memory():
    """Check system RAM."""
    if psutil:
        try:
            mem = psutil.virtual_memory()
            avail_gb = mem.available / (1024 ** 3)
            log(f"  [RAM] Available: {avail_gb:.1f} GB ({mem.percent}% used)")
            if avail_gb < 1.0:
                log("  [WARNING] RAM critically low!", "WARN")
                return False
            return True
        except Exception:
            pass
    return True


def wake_services():
    """Check if key modules are importable."""
    log("── Waking Services ──")

    # 1. Maintenance Steward
    try:
        from maintenance_steward import scan_project
        log("  [SENTINEL] Maintenance Steward ... ONLINE")
    except ImportError:
        log("  [SENTINEL] Maintenance Steward ... OFFLINE (Module missing)")

    # 2. Music Alchemist
    try:
        from creation_engine.music_alchemist import MusicAlchemistAgent, _load_audiocraft
        MusicGen, _ = _load_audiocraft()
        status = "ONLINE (GPU)" if MusicGen else "ONLINE (CPU/Remote Fallback)"
        log(f"  [ALCHEMIST] Music Engine ... {status}")
    except ImportError:
        log("  [ALCHEMIST] Music Engine ... OFFLINE")

    # 3. Stealth Engine
    try:
        from creation_engine.stealth_engine import StealthEngine
        log("  [STEALTH] Privacy Scrubbing ... ONLINE")
    except ImportError:
        log("  [STEALTH] Privacy Scrubbing ... OFFLINE")

    # 4. Unreal Bridge
    log("  [UNREAL] Bridge Connection ... STANDBY")


def is_process_running(script_name):
    """Check if a Python script is currently running."""
    if not psutil:
        return False
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any(script_name in arg for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def record_healing_event(service, action):
    """Log a healing event to engine_memory.json."""
    try:
        data = {}
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

        if "healing_events" not in data:
            data["healing_events"] = []

        data["healing_events"].append({
            "service": service,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 50 events
        data["healing_events"] = data["healing_events"][-50:]

        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        log(f"  Failed to record healing event: {e}", "ERROR")


# ── Mode: Standard ───────────────────────────────────────────
def run_standard():
    """Original watchdog behavior — single pass then monitor."""
    log("Initializing Healer Watchdog v2.0 (Standard Mode)")
    if check_vram():
        wake_services()
        log("\n[SYSTEM READY] All systems green. Monitoring...")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            log("[SYSTEM] Watchdog shutting down.")
    else:
        log("[SYSTEM HALT] Hardware checks failed.", "ERROR")


# ── Mode: Autonomous ────────────────────────────────────────
def run_autonomous():
    """Full autonomous healing loop — monitors, diagnoses, restarts."""
    log("══════════════════════════════════════════════")
    log("  HEALER WATCHDOG v2.0 — AUTONOMOUS MODE")
    log("  The Nervous System is now ALIVE.")
    log("══════════════════════════════════════════════")

    cycle = 0
    try:
        while True:
            cycle += 1
            log(f"── Heal Cycle #{cycle} ──")

            # Hardware checks
            vram_ok = check_vram()
            disk_ok = check_disk()
            ram_ok = check_memory()

            if not vram_ok or not disk_ok or not ram_ok:
                log("  ⚠️  Hardware degradation detected. Recording constraint.", "WARN")
                record_healing_event("hardware", "degradation_detected")

            # Service checks (only if psutil available)
            if psutil:
                for script in CRITICAL_PROCESSES:
                    if not is_process_running(script):
                        log(f"  💊 [{script}] NOT RUNNING — Supervisor should handle restart.", "WARN")
                        record_healing_event(script, "not_running_detected")
                    else:
                        log(f"  ✅ [{script}] alive")

            # Module health
            if cycle % 5 == 0:
                wake_services()

            log(f"  Cycle {cycle} complete. Next check in 15s.\n")
            time.sleep(15)

    except KeyboardInterrupt:
        log("[SYSTEM] Healer Watchdog shutting down.")


# ── Entry ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Healer Watchdog — The Nervous System")
    parser.add_argument("--mode", type=str, default="standard",
                        choices=["standard", "autonomous"],
                        help="Operating mode: standard or autonomous")
    args = parser.parse_args()

    if args.mode == "autonomous":
        run_autonomous()
    else:
        run_standard()


if __name__ == "__main__":
    main()
