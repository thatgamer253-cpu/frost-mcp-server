#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  MASTER HIVE MANIFEST — Sovereign Fleet Status & Auto-Maintenance
  
  Tracks agent consensus accuracy and sovereign reliability across
  the Overlord fleet: Agent (Architect), Agent 2 (Fabricator),
  sell_agent (Merchant), Sentinel (Auditor), and Alchemist (Optimizer).

  Features:
    1. Live fleet health dashboard (from log aggregation)
    2. Self-Pruning: Auto context-purge if agent drops below 80%
    3. Adversarial Training: Scheduled Red-Team Siege
    4. Financial Capping: Pause builds if daily spend exceeds threshold

  Usage:
    python hive_status.py                 # Print dashboard
    python hive_status.py --watch         # Live monitor (refreshes every 60s)
    python hive_status.py --auto-maintain # Run auto-maintenance protocols
    python hive_status.py --json          # Output as JSON

══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import datetime
import re
import glob
from typing import Dict, List, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
OVERLORD_LOG = os.path.join(SCRIPT_DIR, "overlord.log")
HIVE_STATE_FILE = os.path.join(LOG_DIR, "hive_state.json")
SWARM_CONSENSUS_FILE = os.path.join(LOG_DIR, "swarm_consensus.json")

os.makedirs(LOG_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  AGENT REGISTRY — Fleet Roster
# ══════════════════════════════════════════════════════════════

AGENT_REGISTRY = {
    "Agent": {
        "role": "Architect",
        "tags": ["ARCHITECT", "MEMORY", "PULSE"],
        "description": "Blueprint decomposition and design orchestration",
    },
    "Agent 2": {
        "role": "Fabricator",
        "tags": ["ENGINEER", "BUNDLER"],
        "description": "Code synthesis and package assembly",
    },
    "sell_agent": {
        "role": "Merchant",
        "tags": ["COST", "API", "REVENUE"],
        "description": "Cost optimization and API expenditure management",
    },
    "Sentinel": {
        "role": "Auditor",
        "tags": ["SECURITY", "GUARDIAN", "SHADOW"],
        "description": "Zero-trust audit, Shadow Logic detection, Bandit SAST",
    },
    "Alchemist": {
        "role": "Optimizer",
        "tags": ["COMPILER", "OPTIMIZER", "WISDOM"],
        "description": "Post-fabrication refinement, compilation, code overhead reduction",
    },
}

# Reputation tiers
REPUTATION_TIERS = [
    (97, "🎖️ Elite"),
    (93, "⚡ Rapid"),
    (88, "💰 Stable"),
    (80, "🧪 Refined"),
    (70, "⚠️ Degraded"),
    (0,  "🔴 Critical"),
]


def get_reputation(success_rate: float) -> str:
    """Map success rate to reputation tier."""
    for threshold, label in REPUTATION_TIERS:
        if success_rate >= threshold:
            return label
    return "🔴 Critical"


# ══════════════════════════════════════════════════════════════
#  LOG AGGREGATION — Scan overlord.log + audit files
# ══════════════════════════════════════════════════════════════

class HiveLogAggregator:
    """
    Scans the overlord.log and logs/ directory to compute per-agent
    success rates, recent actions, and fleet-wide consensus metrics.
    """

    def __init__(self):
        self.agent_stats: Dict[str, Dict[str, Any]] = {}
        for name, meta in AGENT_REGISTRY.items():
            self.agent_stats[name] = {
                "role": meta["role"],
                "successes": 0,
                "failures": 0,
                "recent_action": "Awaiting first task",
                "tags": meta["tags"],
            }

    def scan_overlord_log(self):
        """Parse overlord.log for tagged events — [TAG] ✓/✗ patterns."""
        if not os.path.exists(OVERLORD_LOG):
            return

        try:
            with open(OVERLORD_LOG, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return

        # Process last 500 lines for performance
        for line in lines[-500:]:
            line_upper = line.upper()
            for agent_name, meta in AGENT_REGISTRY.items():
                for tag in meta["tags"]:
                    if tag in line_upper:
                        if "✓" in line or "SUCCESS" in line_upper or "APPROVED" in line_upper or "CLEAN" in line_upper:
                            self.agent_stats[agent_name]["successes"] += 1
                            # Extract recent action (last matching line wins)
                            action = line.strip()
                            if len(action) > 120:
                                action = action[:117] + "..."
                            self.agent_stats[agent_name]["recent_action"] = action
                        elif "✗" in line or "FAIL" in line_upper or "REJECTED" in line_upper or "CRASH" in line_upper:
                            self.agent_stats[agent_name]["failures"] += 1
                            action = line.strip()
                            if len(action) > 120:
                                action = action[:117] + "..."
                            self.agent_stats[agent_name]["recent_action"] = action

    def scan_audit_files(self):
        """Parse audit_log.json files in built projects for guardian results."""
        audit_files = glob.glob(os.path.join(SCRIPT_DIR, "builds", "**", "audit_log.json"), recursive=True)
        for af in audit_files[-10:]:  # Last 10 builds
            try:
                with open(af, "r", encoding="utf-8") as f:
                    audit = json.load(f)
                if audit.get("status") == "APPROVED":
                    self.agent_stats["Sentinel"]["successes"] += 1
                elif audit.get("status") == "REJECTED":
                    self.agent_stats["Sentinel"]["failures"] += 1

                shadow = audit.get("shadow_issues", [])
                if shadow:
                    self.agent_stats["Sentinel"]["recent_action"] = (
                        f"Blocked {len(shadow)} Shadow Logic leak(s)"
                    )
            except Exception:
                pass

    def scan_cost_reports(self):
        """Parse cost_report.json files for sell_agent metrics."""
        cost_files = glob.glob(os.path.join(SCRIPT_DIR, "builds", "**", "cost_report.json"), recursive=True)
        for cf in cost_files[-10:]:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    report = json.load(f)
                if not report.get("budget_exceeded", False):
                    self.agent_stats["sell_agent"]["successes"] += 1
                else:
                    self.agent_stats["sell_agent"]["failures"] += 1

                total_cost = report.get("total_cost", 0)
                budget = report.get("budget", 5.0)
                savings_pct = round((1 - total_cost / max(budget, 0.01)) * 100, 1)
                self.agent_stats["sell_agent"]["recent_action"] = (
                    f"Optimized: ${total_cost:.4f} / ${budget:.2f} ({savings_pct}% saved)"
                )
            except Exception:
                pass

    def aggregate(self) -> Dict[str, Dict[str, Any]]:
        """Run all scans and compute final stats."""
        self.scan_overlord_log()
        self.scan_audit_files()
        self.scan_cost_reports()

        results = {}
        for name, stats in self.agent_stats.items():
            total = stats["successes"] + stats["failures"]
            if total == 0:
                success_rate = 95.0  # Default baseline for new agents
            else:
                success_rate = round((stats["successes"] / total) * 100, 1)

            results[name] = {
                "role": stats["role"],
                "success_rate": success_rate,
                "reputation": get_reputation(success_rate),
                "successes": stats["successes"],
                "failures": stats["failures"],
                "recent_action": stats["recent_action"],
            }

        return results


# ══════════════════════════════════════════════════════════════
#  AUTO-MAINTENANCE PROTOCOLS
# ══════════════════════════════════════════════════════════════

class HiveAutoMaintenance:
    """
    Sovereign auto-maintenance protocols for the Overlord fleet.
    Runs without human intervention to keep agents at peak performance.
    """

    def __init__(self, stats: Dict[str, Dict[str, Any]]):
        self.stats = stats
        self.actions_taken: List[str] = []

    def self_prune(self):
        """
        PROTOCOL 1: Self-Pruning
        If an agent's success rate drops below 80%, trigger a "Context Purge"
        and re-sync it with the latest pulse_sync.json.
        """
        try:
            from pulse_sync_logger import PulseSyncLogger
        except ImportError:
            self.actions_taken.append("[PRUNE] PulseSyncLogger unavailable — skipped")
            return

        for name, data in self.stats.items():
            if data["success_rate"] < 80.0:
                self.actions_taken.append(
                    f"[PRUNE] {name} ({data['role']}) at {data['success_rate']}% — "
                    f"triggering context purge + re-sync"
                )
                # Re-sync: capture a fresh heartbeat with the degraded agent noted
                try:
                    logger = PulseSyncLogger(project_root=SCRIPT_DIR)
                    logger.capture_heartbeat(
                        manual_vibe=f"Auto-prune: {name} degraded to {data['success_rate']}%. "
                                    f"Context refresh triggered."
                    )
                    self.actions_taken.append(
                        f"[PRUNE] {name}: Pulse-Sync refreshed successfully"
                    )
                except Exception as e:
                    self.actions_taken.append(f"[PRUNE] {name}: refresh failed — {e}")

    def adversarial_training(self):
        """
        PROTOCOL 2: Adversarial Training
        Weekly Red-Team Siege — Sentinel runs a hostile audit on the Fabricator's
        last output to test for newly learned vulnerabilities.
        """
        state_file = os.path.join(LOG_DIR, "last_siege.json")
        now = datetime.datetime.now()

        # Check if a siege has run in the last 7 days
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    last = json.load(f)
                last_run = datetime.datetime.fromisoformat(last.get("timestamp", "2000-01-01"))
                days_since = (now - last_run).days
                if days_since < 7:
                    self.actions_taken.append(
                        f"[SIEGE] Last Red-Team Siege was {days_since} day(s) ago — "
                        f"next in {7 - days_since} day(s)"
                    )
                    return
            except Exception:
                pass

        self.actions_taken.append("[SIEGE] Initiating weekly Red-Team Siege on Fabricator output...")

        # Find the most recent build's code files
        builds_dir = os.path.join(SCRIPT_DIR, "builds")
        if not os.path.isdir(builds_dir):
            self.actions_taken.append("[SIEGE] No builds directory found — skipping")
            return

        # Get latest build
        build_dirs = sorted(
            [d for d in os.listdir(builds_dir) if os.path.isdir(os.path.join(builds_dir, d))],
            key=lambda d: os.path.getmtime(os.path.join(builds_dir, d)),
            reverse=True
        )

        if not build_dirs:
            self.actions_taken.append("[SIEGE] No build artifacts found — skipping")
            return

        latest_build = os.path.join(builds_dir, build_dirs[0])
        py_files = glob.glob(os.path.join(latest_build, "*.py"))

        siege_results = {
            "timestamp": now.isoformat(),
            "target_build": build_dirs[0],
            "files_audited": len(py_files),
            "vulnerabilities_found": 0,
        }

        # Run lightweight static checks (no LLM required)
        vuln_patterns = [
            (r"eval\s*\(", "eval() usage — potential code injection"),
            (r"exec\s*\(", "exec() usage — potential code injection"),
            (r"subprocess\..*shell\s*=\s*True", "Shell injection risk"),
            (r"(password|secret|api_key)\s*=\s*['\"]", "Hardcoded credential"),
            (r"\*\s*import", "Wildcard import — namespace pollution"),
            (r"except\s*:", "Bare except — swallows all errors"),
        ]

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                for pattern, desc in vuln_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        siege_results["vulnerabilities_found"] += 1
                        self.actions_taken.append(
                            f"[SIEGE] {os.path.basename(py_file)}: {desc}"
                        )
            except Exception:
                pass

        self.actions_taken.append(
            f"[SIEGE] Complete: {siege_results['files_audited']} file(s) audited, "
            f"{siege_results['vulnerabilities_found']} vulnerability(ies) flagged"
        )

        # Save siege timestamp
        with open(state_file, "w") as f:
            json.dump(siege_results, f, indent=2)

    def financial_cap(self, daily_threshold: float = 5.0):
        """
        PROTOCOL 3: Financial Capping
        If the daily API expenditure exceeds the threshold, write a pause signal
        that the orchestrator checks before each build.
        """
        pause_signal = os.path.join(LOG_DIR, "financial_pause.json")

        # Aggregate today's costs from cost_report.json files
        today = datetime.datetime.now().date()
        daily_spend = 0.0

        cost_files = glob.glob(os.path.join(SCRIPT_DIR, "builds", "**", "cost_report.json"), recursive=True)
        for cf in cost_files:
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(cf)).date()
                if mtime == today:
                    with open(cf, "r") as f:
                        report = json.load(f)
                    daily_spend += report.get("total_cost", 0)
            except Exception:
                pass

        if daily_spend >= daily_threshold:
            pause_data = {
                "paused": True,
                "timestamp": datetime.datetime.now().isoformat(),
                "daily_spend": round(daily_spend, 4),
                "threshold": daily_threshold,
                "reason": f"Daily spend ${daily_spend:.4f} exceeds ${daily_threshold:.2f} cap",
            }
            with open(pause_signal, "w") as f:
                json.dump(pause_data, f, indent=2)
            self.actions_taken.append(
                f"[CAP] 🚨 PAUSED: Daily spend ${daily_spend:.4f} exceeds ${daily_threshold:.2f} threshold"
            )
        else:
            # Clear pause if it exists and we're under budget
            if os.path.exists(pause_signal):
                try:
                    os.remove(pause_signal)
                    self.actions_taken.append("[CAP] Pause signal cleared — spend under threshold")
                except Exception:
                    pass
            remaining = daily_threshold - daily_spend
            self.actions_taken.append(
                f"[CAP] Budget OK: ${daily_spend:.4f} / ${daily_threshold:.2f} "
                f"(${remaining:.4f} remaining)"
            )

    def run_all(self) -> List[str]:
        """Execute all auto-maintenance protocols."""
        self.self_prune()
        self.adversarial_training()
        self.financial_cap()
        return self.actions_taken


# ══════════════════════════════════════════════════════════════
#  DASHBOARD RENDERER
# ══════════════════════════════════════════════════════════════

def render_dashboard(stats: Dict[str, Dict[str, Any]],
                     maintenance_log: Optional[List[str]] = None):
    """Print the Master Hive Manifest dashboard to stdout."""
    hr = "═" * 72

    print(f"\n{hr}")
    print("  🐝 MASTER HIVE MANIFEST — SOVEREIGN FLEET STATUS")
    print(f"{hr}\n")

    # Fleet table
    header = f"  {'Agent':<14} {'Role':<12} {'Rate':>6} {'Reputation':<16} Recent Action"
    print(header)
    print(f"  {'─' * 14} {'─' * 12} {'─' * 6} {'─' * 16} {'─' * 20}")

    for name, data in stats.items():
        rate_str = f"{data['success_rate']:.0f}%"
        action = data["recent_action"]
        if len(action) > 45:
            action = action[:42] + "..."
        print(f"  {name:<14} {data['role']:<12} {rate_str:>6} {data['reputation']:<16} {action}")

    # Fleet consensus metrics
    total_success = sum(d["successes"] for d in stats.values())
    total_fail = sum(d["failures"] for d in stats.values())
    total = total_success + total_fail
    consensus = round((total_success / max(total, 1)) * 100, 1)

    print(f"\n  {'─' * 68}")
    print(f"  Fleet Consensus Accuracy: {consensus}%")
    print(f"  Total Operations: {total} ({total_success} ✓ / {total_fail} ✗)")

    # Pulse-Sync status
    pulse_file = os.path.join(LOG_DIR, "pulse_sync.json")
    if os.path.exists(pulse_file):
        try:
            with open(pulse_file, "r") as f:
                pulse = json.load(f)
            risk = pulse.get("identity_fragmentation_risk", "Unknown")
            vibe = pulse.get("current_vibe_shift", "Steady-state")
            print(f"  Pulse-Sync Risk: {risk}")
            print(f"  Current Vibe: {vibe}")
        except Exception:
            pass

    # Financial status
    pause_file = os.path.join(LOG_DIR, "financial_pause.json")
    if os.path.exists(pause_file):
        try:
            with open(pause_file, "r") as f:
                pause = json.load(f)
            if pause.get("paused"):
                print(f"  🚨 FINANCIAL PAUSE ACTIVE: {pause.get('reason', '?')}")
        except Exception:
            pass

    # Auto-maintenance log
    if maintenance_log:
        print(f"\n  {'─' * 68}")
        print("  Auto-Maintenance Protocol Log:")
        for entry in maintenance_log:
            print(f"    {entry}")

    print(f"\n{hr}")
    print(f"  Timestamp: {datetime.datetime.now().isoformat()}")
    print(f"{hr}\n")


def export_json(stats: Dict[str, Dict[str, Any]],
                maintenance_log: Optional[List[str]] = None) -> dict:
    """Export the dashboard as a JSON-serializable dict."""
    total_success = sum(d["successes"] for d in stats.values())
    total_fail = sum(d["failures"] for d in stats.values())
    total = total_success + total_fail

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "fleet_consensus_accuracy": round((total_success / max(total, 1)) * 100, 1),
        "total_operations": total,
        "agents": stats,
        "maintenance_log": maintenance_log or [],
    }


def save_hive_state(data: dict):
    """Persist hive state to disk for historical tracking."""
    # Load existing history
    history = []
    if os.path.exists(HIVE_STATE_FILE):
        try:
            with open(HIVE_STATE_FILE, "r") as f:
                history = json.load(f)
        except Exception:
            history = []

    # Append current snapshot (keep last 100)
    history.append(data)
    history = history[-100:]

    with open(HIVE_STATE_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)

    # Also write swarm_consensus.json for compatibility
    with open(SWARM_CONSENSUS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════

def generate_hive_dashboard(auto_maintain: bool = False,
                            as_json: bool = False) -> dict:
    """Main entry point — aggregate, render, and optionally maintain."""
    aggregator = HiveLogAggregator()
    stats = aggregator.aggregate()

    maintenance_log = None
    if auto_maintain:
        maintainer = HiveAutoMaintenance(stats)
        maintenance_log = maintainer.run_all()

    if as_json:
        data = export_json(stats, maintenance_log)
        print(json.dumps(data, indent=2, default=str))
    else:
        render_dashboard(stats, maintenance_log)

    # Always persist state
    data = export_json(stats, maintenance_log)
    save_hive_state(data)

    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="hive_status",
        description="Master Hive Manifest — Sovereign Fleet Status Dashboard"
    )
    parser.add_argument(
        "--watch", "-w", action="store_true",
        help="Live monitor mode (refreshes every 60s)"
    )
    parser.add_argument(
        "--auto-maintain", "-m", action="store_true",
        help="Run auto-maintenance protocols (prune, siege, cap)"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output as JSON instead of formatted table"
    )
    parser.add_argument(
        "--cap", type=float, default=5.0,
        help="Daily API spend cap in dollars (default: $5.00)"
    )

    args = parser.parse_args()

    if args.watch:
        print("Hive Watchdog active. Press Ctrl+C to stop.\n")
        try:
            while True:
                generate_hive_dashboard(
                    auto_maintain=args.auto_maintain,
                    as_json=args.json
                )
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nHive Watchdog stopped.")
    else:
        generate_hive_dashboard(
            auto_maintain=args.auto_maintain,
            as_json=args.json
        )
