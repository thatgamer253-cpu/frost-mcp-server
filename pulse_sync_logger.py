#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  PULSE-SYNC LOGGER — Continuous Context Integration (CCI)

  Prevents "Identity Fragmentation" by maintaining a temporal
  thread of what you're working on, why, and when you pivoted.

  The Overlord Orchestrator reads pulse_sync.json before every
  generation to stay on your current wavelength.

  Usage:
    # Background heartbeat (auto-captures active files)
    python pulse_sync_logger.py

    # Manual vibe-shift (tell the AI you pivoted)
    python pulse_sync_logger.py "Switching to extreme security mode for API layer"

    # Import and use programmatically
    from pulse_sync_logger import PulseSyncLogger
    logger = PulseSyncLogger()
    logger.capture_heartbeat("Focus: performance optimization")

══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import datetime
import glob
import hashlib


class PulseSyncLogger:
    """
    Lightweight heartbeat logger that captures project state and developer intent.

    Outputs pulse_sync.json with:
      - timestamp: when the pulse was captured
      - last_active_files: 5 most recently modified files
      - current_vibe_shift: manual context note or "Steady-state"
      - identity_fragmentation_risk: Low / Medium / High
      - session_history: rolling log of the last 10 vibe shifts
      - file_delta: files changed since last pulse
    """

    def __init__(self, project_root=".", output_file="logs/pulse_sync.json"):
        self.project_root = os.path.abspath(project_root)
        self.output_file = os.path.join(self.project_root, output_file)
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        self._previous_snapshot = self._snapshot_files()

    # ── File System Scanning ─────────────────────────────────

    def _get_project_files(self):
        """Get all trackable files, excluding common noise directories."""
        exclude = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', '.cache', 'logs', '.mypy_cache',
        }
        results = []
        for root, dirs, files in os.walk(self.project_root):
            # Prune excluded dirs in-place
            dirs[:] = [d for d in dirs if d not in exclude]
            for f in files:
                full = os.path.join(root, f)
                try:
                    results.append(full)
                except Exception:
                    pass
        return results

    def _snapshot_files(self):
        """Create a hash-based snapshot of project files for delta detection."""
        snapshot = {}
        for f in self._get_project_files():
            try:
                stat = os.stat(f)
                snapshot[f] = stat.st_mtime
            except Exception:
                pass
        return snapshot

    def _detect_delta(self):
        """Find files that changed since the last pulse."""
        current = self._snapshot_files()
        changed = []
        new_files = []

        for f, mtime in current.items():
            if f not in self._previous_snapshot:
                new_files.append(os.path.relpath(f, self.project_root))
            elif mtime != self._previous_snapshot[f]:
                changed.append(os.path.relpath(f, self.project_root))

        deleted = [
            os.path.relpath(f, self.project_root)
            for f in self._previous_snapshot
            if f not in current
        ]

        self._previous_snapshot = current

        return {
            "modified": changed[:10],
            "new": new_files[:10],
            "deleted": deleted[:10],
        }

    # ── Risk Assessment ─────────────────────────────────────

    def _assess_risk(self, manual_vibe, delta, hours_since_last):
        """
        Assess identity fragmentation risk based on signals:
          - No manual vibe + long idle = High risk
          - Manual vibe present = Low risk (developer is actively steering)
          - Many file changes without vibe context = Medium risk
        """
        if manual_vibe:
            return "Low"

        total_changes = len(delta.get("modified", [])) + len(delta.get("new", []))

        if hours_since_last > 4:
            return "High (Extended idle — context may have drifted)"
        if total_changes > 15:
            return "Medium (Many changes without vibe context)"
        if hours_since_last > 1:
            return "Medium (Idle)"
        return "Low"

    # ── Session History ──────────────────────────────────────

    def _load_existing(self):
        """Load existing pulse data if present."""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _get_hours_since_last(self, existing):
        """Calculate hours since last pulse."""
        last_ts = existing.get("timestamp")
        if last_ts:
            try:
                last = datetime.datetime.fromisoformat(last_ts)
                now = datetime.datetime.now()
                return (now - last).total_seconds() / 3600
            except Exception:
                pass
        return 999  # First run

    # ── Core: Capture Heartbeat ─────────────────────────────

    def capture_heartbeat(self, manual_vibe=None):
        """
        Gathers automated project stats and manual 'vibe' updates.
        Writes pulse_sync.json for the Orchestrator to consume.
        """
        existing = self._load_existing()
        hours_since = self._get_hours_since_last(existing)

        # 1. Automated: Get most recently modified files
        all_files = self._get_project_files()
        try:
            recent_files = sorted(all_files, key=os.path.getmtime, reverse=True)[:5]
        except Exception:
            recent_files = all_files[:5]

        # 2. Detect what changed since last pulse
        delta = self._detect_delta()

        # 3. Assess fragmentation risk
        risk = self._assess_risk(manual_vibe, delta, hours_since)

        # 4. Maintain rolling session history (last 10 vibes)
        session_history = existing.get("session_history", [])
        if manual_vibe:
            session_history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "vibe": manual_vibe,
            })
            session_history = session_history[-10:]  # Keep last 10

        # 5. Build the Pulse Data
        pulse_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "last_active_files": [
                os.path.relpath(f, self.project_root) for f in recent_files
            ],
            "current_vibe_shift": manual_vibe or "Steady-state development",
            "identity_fragmentation_risk": risk,
            "file_delta_since_last_pulse": delta,
            "hours_since_last_pulse": round(hours_since, 2),
            "session_history": session_history,
            "pulse_count": existing.get("pulse_count", 0) + 1,
        }

        # 6. Commit to the Anchor
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(pulse_data, f, indent=4)

        print(f"[+] Pulse Anchored: {pulse_data['timestamp']}")
        print(f"    Risk: {risk}")
        print(f"    Active: {', '.join(pulse_data['last_active_files'][:3])}")
        if delta["modified"]:
            print(f"    Changed: {', '.join(delta['modified'][:3])}")
        if manual_vibe:
            print(f"    Vibe: {manual_vibe}")

        return pulse_data

    # ── Orchestrator Integration ─────────────────────────────

    def get_context_for_orchestrator(self):
        """
        Returns a formatted string for injection into LLM system prompts.
        Called by the Orchestrator before every generation phase.
        """
        data = self._load_existing()
        if not data:
            return ""

        lines = [
            "PULSE-SYNC CONTEXT (Developer's Current State):",
            f"  Timestamp: {data.get('timestamp', 'unknown')}",
            f"  Vibe: {data.get('current_vibe_shift', 'unknown')}",
            f"  Risk Level: {data.get('identity_fragmentation_risk', 'unknown')}",
            f"  Active Files: {', '.join(data.get('last_active_files', [])[:3])}",
        ]

        # Add session history for temporal thread
        history = data.get("session_history", [])
        if history:
            lines.append("  Recent Vibes:")
            for h in history[-3:]:
                lines.append(f"    - [{h.get('timestamp', '?')[:16]}] {h.get('vibe', '?')}")

        # Add delta for change awareness
        delta = data.get("file_delta_since_last_pulse", {})
        if delta.get("modified"):
            lines.append(f"  Recently Modified: {', '.join(delta['modified'][:5])}")

        return "\n".join(lines)

    # ── Background Daemon Mode ──────────────────────────────

    def run_daemon(self, interval_minutes=15):
        """
        Run as a background heartbeat daemon.
        Captures a pulse every N minutes automatically.
        """
        print(f"[*] Pulse-Sync Daemon started (interval: {interval_minutes}min)")
        print(f"    Monitoring: {self.project_root}")
        print(f"    Output:     {self.output_file}")
        print(f"    Press Ctrl+C to stop.\n")

        try:
            while True:
                self.capture_heartbeat()
                print(f"    Next pulse in {interval_minutes} minutes...\n")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n[*] Pulse-Sync Daemon stopped.")


# ═══════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="pulse_sync",
        description="Pulse-Sync Logger — Continuous Context Integration for Overlord"
    )
    parser.add_argument(
        "vibe", nargs="?", default=None,
        help="Manual vibe-shift note (e.g. 'Switching to security hardening')"
    )
    parser.add_argument(
        "--daemon", "-d", action="store_true",
        help="Run as background daemon with periodic heartbeats"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=15,
        help="Daemon heartbeat interval in minutes (default: 15)"
    )
    parser.add_argument(
        "--project", "-p", default=".",
        help="Project root directory to monitor (default: current dir)"
    )

    args = parser.parse_args()

    logger = PulseSyncLogger(project_root=args.project)

    if args.daemon:
        logger.run_daemon(interval_minutes=args.interval)
    else:
        logger.capture_heartbeat(manual_vibe=args.vibe)
