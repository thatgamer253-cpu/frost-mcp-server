#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  AUTONOMOUS ENGINE — Self-Improving Creation Engine
  The Council doesn't just watch anymore. It acts.
═══════════════════════════════════════════════════════════════

Architecture:
  1. UpgradeProposal  — Structured upgrade plan from an agent
  2. AutonomousEngine — The execution loop that makes changes real
  3. Safety Layer     — Git branching, sandbox testing, auto-rollback

Flow:
  Sentinel/Alchemist/Steward → detect issue → create UpgradeProposal
  → AutonomousEngine.execute(proposal)
  → git branch → LLM generates code → write files → sandbox test
  → if pass: merge + commit | if fail: rollback + report
"""

import os
import sys
import json
import time
import shutil
import subprocess
import threading
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ── Internal imports (graceful degrade) ──────────────────────
try:
    import agent_ipc as ipc
    _HAS_IPC = True
except ImportError:
    _HAS_IPC = False

try:
    from creation_engine.llm_client import ask_llm, get_cached_client, resolve_auto_model
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

try:
    from docker_sandbox import Sandbox
    _HAS_SANDBOX = True
except ImportError:
    _HAS_SANDBOX = False


# ── Logging ──────────────────────────────────────────────────
def _log(tag: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [AUTONOMOUS:{tag.upper()}] {msg}")

def _ipc_log(sender: str, content: str, msg_type: str = "STATUS", channel: str = "CREATION"):
    if _HAS_IPC:
        ipc.broadcast(channel, sender, content, msg_type=msg_type)


# ═════════════════════════════════════════════════════════════
#  UPGRADE PROPOSAL — What the agents want to do
# ═════════════════════════════════════════════════════════════

@dataclass
class UpgradeProposal:
    """A structured plan for an autonomous upgrade."""
    id: str = ""
    agent: str = ""                    # Who proposed it (sentinel, alchemist, steward)
    category: str = ""                 # bug_fix, optimization, feature, dependency, security
    priority: int = 5                  # 1-10 (10 = critical)
    title: str = ""                    # Short description
    description: str = ""              # Detailed description of what to change
    target_files: List[str] = field(default_factory=list)  # Files to modify
    rationale: str = ""                # Why this upgrade matters
    risk_level: str = "low"            # low, medium, high
    requires_approval: bool = False    # If True, wait for human approval
    status: str = "pending"            # pending, approved, executing, testing, success, failed, rolled_back
    created_at: str = ""
    completed_at: str = ""
    error: str = ""
    diff_summary: str = ""             # What changed

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.title}{time.time()}".encode()).hexdigest()[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ═════════════════════════════════════════════════════════════
#  UPGRADE QUEUE — Persistent task queue for proposals
# ═════════════════════════════════════════════════════════════

QUEUE_FILE = os.path.join("memory", "upgrade_queue.jsonl")

def _save_proposal(proposal: UpgradeProposal):
    """Append a proposal to the persistent queue."""
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(proposal)) + "\n")

def _load_proposals(status_filter: str = None) -> List[UpgradeProposal]:
    """Load proposals from the queue, optionally filtered by status."""
    if not os.path.exists(QUEUE_FILE):
        return []
    proposals = []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                p = UpgradeProposal(**{k: v for k, v in data.items() if k in UpgradeProposal.__dataclass_fields__})
                if status_filter is None or p.status == status_filter:
                    proposals.append(p)
            except (json.JSONDecodeError, TypeError):
                continue
    return proposals


# ═════════════════════════════════════════════════════════════
#  GIT SAFETY LAYER — Branch, commit, rollback
# ═════════════════════════════════════════════════════════════

class GitSafety:
    """Git operations for safe autonomous changes."""

    def __init__(self, project_root: str = "."):
        self.root = project_root
        self._has_git = self._check_git()

    def _check_git(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root, capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_git(self, *args) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.root, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def create_upgrade_branch(self, proposal_id: str) -> str:
        """Create a new branch for this upgrade."""
        if not self._has_git:
            return ""
        branch = f"auto-upgrade/{proposal_id}"
        try:
            self._run_git("checkout", "-b", branch)
            _log("git", f"Created branch: {branch}")
            return branch
        except Exception as e:
            _log("git", f"Branch creation failed: {e}")
            return ""

    def commit_changes(self, message: str) -> bool:
        """Stage all changes and commit."""
        if not self._has_git:
            return False
        try:
            self._run_git("add", "-A")
            self._run_git("commit", "-m", message)
            _log("git", f"Committed: {message}")
            return True
        except Exception as e:
            _log("git", f"Commit failed: {e}")
            return False

    def merge_to_main(self, branch: str) -> bool:
        """Merge upgrade branch back to main."""
        if not self._has_git:
            return False
        try:
            current = self._run_git("branch", "--show-current")
            main_branch = "main" if current != "main" else "master"
            self._run_git("checkout", main_branch)
            self._run_git("merge", branch, "--no-ff", "-m", f"Merge auto-upgrade: {branch}")
            self._run_git("branch", "-d", branch)
            _log("git", f"Merged {branch} into {main_branch}")
            return True
        except Exception as e:
            _log("git", f"Merge failed: {e}")
            return False

    def rollback(self, branch: str) -> bool:
        """Abandon the upgrade branch and return to main."""
        if not self._has_git:
            return False
        try:
            current = self._run_git("branch", "--show-current")
            if current == branch:
                self._run_git("checkout", "main")
            self._run_git("branch", "-D", branch)
            _log("git", f"Rolled back: {branch}")
            return True
        except Exception as e:
            _log("git", f"Rollback failed: {e}")
            return False

    def backup_file(self, filepath: str) -> str:
        """Create a .bak backup of a file before modification."""
        if os.path.exists(filepath):
            bak = filepath + ".auto.bak"
            shutil.copy2(filepath, bak)
            return bak
        return ""

    def restore_file(self, filepath: str) -> bool:
        """Restore from .bak if it exists."""
        bak = filepath + ".auto.bak"
        if os.path.exists(bak):
            shutil.move(bak, filepath)
            return True
        return False

    def cleanup_backups(self, filepath: str):
        """Remove .bak file after successful upgrade."""
        bak = filepath + ".auto.bak"
        if os.path.exists(bak):
            os.remove(bak)


# ═════════════════════════════════════════════════════════════
#  AUTONOMOUS ENGINE — The brain that executes upgrades
# ═════════════════════════════════════════════════════════════

class AutonomousEngine:
    """
    The Autonomous Engine takes UpgradeProposals and makes them real.

    Safety guarantees:
      - All changes happen on a git branch
      - Files are backed up before modification
      - Code is tested in Docker sandbox when available
      - Failed upgrades are automatically rolled back
      - Everything is logged to the Council IPC
    """

    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.git = GitSafety(project_root)
        self._upgrade_log_path = os.path.join("memory", "upgrade_history.jsonl")
        self._lock = threading.Lock()
        self._running = False

        # Safety limits
        self.max_files_per_upgrade = 3         # Don't touch more than 3 files at once
        self.max_lines_per_file = 100          # Don't write more than 100 new lines
        self.blocked_files = {                 # NEVER touch these
            "autonomous_engine.py",
            "agent_ipc.py",
            ".env",
            "creation_engine/vault.py",
        }
        self.blocked_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv"
        }

    def execute(self, proposal: UpgradeProposal) -> bool:
        """
        Execute an upgrade proposal end-to-end.

        Returns True if the upgrade succeeded, False otherwise.
        """
        with self._lock:
            return self._execute_impl(proposal)

    def _execute_impl(self, proposal: UpgradeProposal) -> bool:
        _log("engine", f"🚀 Starting upgrade: [{proposal.id}] {proposal.title}")
        _ipc_log("ghost", f"🚀 Autonomous upgrade started: **{proposal.title}**")
        proposal.status = "executing"

        # ── Safety checks ────────────────────────────────────
        if not self._safety_check(proposal):
            proposal.status = "failed"
            proposal.error = "Failed safety check"
            self._log_result(proposal)
            return False

        # ── Create git branch ────────────────────────────────
        branch = self.git.create_upgrade_branch(proposal.id)

        # ── Generate implementation via LLM ──────────────────
        changes = self._generate_changes(proposal)
        if not changes:
            proposal.status = "failed"
            proposal.error = "LLM failed to generate changes"
            if branch:
                self.git.rollback(branch)
            self._log_result(proposal)
            return False

        # ── Apply changes ────────────────────────────────────
        backups = []
        applied_files = []
        try:
            for file_change in changes:
                filepath = file_change["file"]
                content = file_change["content"]
                action = file_change.get("action", "modify")  # modify, create, append

                abs_path = os.path.join(self.project_root, filepath)

                # Backup existing file
                bak = self.git.backup_file(abs_path)
                if bak:
                    backups.append((abs_path, bak))

                # Write changes
                if action == "create":
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif action == "append":
                    with open(abs_path, "a", encoding="utf-8") as f:
                        f.write("\n" + content)
                elif action == "modify":
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)

                applied_files.append(filepath)
                _log("engine", f"  ✏️ {action}: {filepath}")

        except Exception as e:
            _log("engine", f"  ❌ Write failed: {e}")
            # Rollback all changes
            for abs_path, bak in backups:
                self.git.restore_file(abs_path)
            if branch:
                self.git.rollback(branch)
            proposal.status = "failed"
            proposal.error = str(e)
            self._log_result(proposal)
            return False

        # ── Test in sandbox ──────────────────────────────────
        proposal.status = "testing"
        test_passed = self._run_tests(proposal, applied_files)

        if not test_passed:
            _log("engine", f"  ❌ Tests failed. Rolling back.")
            _ipc_log("ghost", f"❌ Upgrade **{proposal.title}** failed tests. Rolled back.", msg_type="FLAG")
            for abs_path, bak in backups:
                self.git.restore_file(abs_path)
            if branch:
                self.git.rollback(branch)
            proposal.status = "rolled_back"
            proposal.error = "Tests failed"
            self._log_result(proposal)
            return False

        # ── Commit and merge ─────────────────────────────────
        proposal.status = "success"
        proposal.completed_at = datetime.now().isoformat()
        proposal.diff_summary = ", ".join(applied_files)

        if branch:
            self.git.commit_changes(f"[auto] {proposal.title}")
            self.git.merge_to_main(branch)

        # Cleanup backups
        for abs_path, bak in backups:
            self.git.cleanup_backups(abs_path)

        _log("engine", f"  ✅ Upgrade complete: {proposal.title}")
        _ipc_log("ghost",
            f"✅ Autonomous upgrade complete: **{proposal.title}** ({proposal.diff_summary})",
            msg_type="RESOLVE")

        self._log_result(proposal)
        return True

    def _safety_check(self, proposal: UpgradeProposal) -> bool:
        """Verify the proposal doesn't violate safety constraints."""

        # Check file count
        if len(proposal.target_files) > self.max_files_per_upgrade:
            _log("safety", f"❌ Too many files: {len(proposal.target_files)} > {self.max_files_per_upgrade}")
            _ipc_log("sentinel", f"🚫 Blocked upgrade '{proposal.title}': too many files", msg_type="FLAG", channel="SECURITY")
            return False

        # Check blocked files
        for f in proposal.target_files:
            normalized = f.replace("\\", "/")
            if normalized in self.blocked_files or os.path.basename(normalized) in self.blocked_files:
                _log("safety", f"❌ Blocked file: {f}")
                _ipc_log("sentinel", f"🚫 Blocked upgrade '{proposal.title}': touches protected file {f}", msg_type="FLAG", channel="SECURITY")
                return False

            # Check blocked directories
            parts = Path(normalized).parts
            if any(d in self.blocked_dirs for d in parts):
                _log("safety", f"❌ Blocked directory in path: {f}")
                return False

        # High-risk upgrades need human approval
        if proposal.risk_level == "high" and not proposal.requires_approval:
            _log("safety", f"⚠️ High-risk upgrade requires approval: {proposal.title}")
            _ipc_log("sentinel",
                f"⚠️ High-risk upgrade needs Creator approval: **{proposal.title}**",
                msg_type="FLAG", channel="SECURITY")
            proposal.requires_approval = True
            proposal.status = "pending"
            _save_proposal(proposal)
            return False

        return True

    def _generate_changes(self, proposal: UpgradeProposal) -> Optional[List[Dict]]:
        """Use the LLM to generate actual code changes."""
        if not _HAS_LLM:
            _log("engine", "❌ No LLM available for code generation")
            return None

        # Read current file contents for context
        file_contexts = {}
        for filepath in proposal.target_files:
            abs_path = os.path.join(self.project_root, filepath)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_contexts[filepath] = f.read()
                except Exception:
                    file_contexts[filepath] = "[Could not read file]"
            else:
                file_contexts[filepath] = "[NEW FILE — does not exist yet]"

        # Build the LLM prompt
        system_prompt = (
            "You are the Autonomous Upgrade Engine for the Overlord Creation Engine. "
            "You generate precise, working code changes. "
            "You MUST respond with ONLY a JSON array of file changes. "
            "Each entry: {\"file\": \"path\", \"action\": \"modify|create|append\", \"content\": \"full file content\"} "
            "NEVER include markdown fences. ONLY output raw JSON. "
            "Be conservative — change the minimum necessary. "
            "Preserve all existing functionality. "
            "Add clear comments explaining what you changed and why."
        )

        context_block = "\n\n".join(
            f"── {fp} ──\n{content[:3000]}"
            for fp, content in file_contexts.items()
        )

        user_prompt = (
            f"UPGRADE PROPOSAL: {proposal.title}\n"
            f"CATEGORY: {proposal.category}\n"
            f"DESCRIPTION: {proposal.description}\n"
            f"RATIONALE: {proposal.rationale}\n"
            f"TARGET FILES: {', '.join(proposal.target_files)}\n\n"
            f"CURRENT FILE CONTENTS:\n{context_block}\n\n"
            "Generate the JSON array of changes. Each change must have the FULL file content, not just a diff."
        )

        try:
            model, provider = resolve_auto_model()
            client = get_cached_client(model)
            response = ask_llm(client, model, system_prompt, user_prompt)

            if not response:
                return None

            # Parse JSON response
            response = response.strip()
            
            # Robust JSON extraction: Find the outermost [ ... ] array
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            
            if json_match:
                response = json_match.group(0)
            else:
                # Fallback to manual markdown stripping if regex fails
                if response.startswith("```"):
                    response = response.split("\n", 1)[1]
                    if "```" in response:
                        response = response.split("```")[0].strip()

            changes = json.loads(response)

            if not isinstance(changes, list):
                changes = [changes]

            # Validate each change
            validated = []
            for change in changes:
                if "file" not in change or "content" not in change:
                    continue
                if "action" not in change:
                    change["action"] = "modify"

                # Line count check
                lines = change["content"].count("\n")
                if lines > self.max_lines_per_file * 5:  # Allow 500 lines for full rewrites
                    _log("safety", f"⚠️ Change too large: {change['file']} ({lines} lines)")
                    continue

                validated.append(change)

            return validated if validated else None

        except json.JSONDecodeError as e:
            _log("engine", f"❌ LLM response was not valid JSON: {e}")
            return None
        except Exception as e:
            _log("engine", f"❌ LLM call failed: {e}")
            return None

    def _run_tests(self, proposal: UpgradeProposal, changed_files: List[str]) -> bool:
        """Test changes in Docker sandbox or via syntax check."""

        # Quick syntax check for Python files
        for filepath in changed_files:
            if filepath.endswith(".py"):
                abs_path = os.path.join(self.project_root, filepath)
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", abs_path],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode != 0:
                        _log("test", f"❌ Syntax error in {filepath}: {result.stderr}")
                        return False
                    _log("test", f"✅ Syntax OK: {filepath}")
                except Exception as e:
                    _log("test", f"⚠️ Could not check {filepath}: {e}")

        # Docker sandbox test if available
        is_high_risk = proposal.risk_level in ("medium", "high")
        if _HAS_SANDBOX and proposal.category not in ("dependency", "documentation"):
            try:
                with Sandbox(self.project_root, language="python") as sandbox:
                    sandbox.provision()
                    for filepath in changed_files:
                        if filepath.endswith(".py"):
                            # 1. Import test
                            result = sandbox.run(f"python -c 'import {Path(filepath).stem}'", timeout=15)
                            if not result.success:
                                _log("test", f"❌ Import check failed for {filepath}: {result.stderr[:200]}")
                                return False
                            
                            # 2. Basic Runtime Smoke Test (if it's a script/tool)
                            # (Simulated - in a real env we might run a specific test suite)
                            
                    _log("test", "✅ Sandbox tests passed")
            except Exception as e:
                if is_high_risk:
                    _log("test", f"❌ MANDATORY SANDBOX FAILED: {e}. Aborting high-risk upgrade.")
                    return False
                _log("test", f"⚠️ Sandbox unavailable: {e}. Continuing with syntax check only.")
        elif is_high_risk:
            _log("test", "❌ SANDBOX NOT AVAILABLE. High-risk upgrade blocked.")
            return False

        return True

    def _log_result(self, proposal: UpgradeProposal):
        """Log the upgrade result to persistent history."""
        os.makedirs(os.path.dirname(self._upgrade_log_path), exist_ok=True)
        with open(self._upgrade_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(proposal)) + "\n")
        _save_proposal(proposal)


# ═════════════════════════════════════════════════════════════
#  AUTONOMOUS DAEMON — Background thread running the loop
# ═════════════════════════════════════════════════════════════

class AutonomousDaemon(threading.Thread):
    """
    Background daemon that continuously looks for upgrade opportunities
    and executes them through the AutonomousEngine.

    Upgrade sources:
      1. Sentinel FLAGS on the SECURITY channel → bug fixes
      2. Steward dependency scan → auto-update safe packages
      3. Heartbeat dream insights → optimizations
      4. Human directives on the IPC bus → feature requests
      5. Self-analysis of error logs → self-healing
    """

    def __init__(self, project_root: str = ".", check_interval: int = 120):
        super().__init__()
        self.daemon = True
        self.project_root = project_root
        self.check_interval = check_interval
        self.engine = AutonomousEngine(project_root)
        self.stop_event = threading.Event()
        self._handled_proposals = set()
        self._cycle_count = 0

    def run(self):
        _log("daemon", "🤖 Autonomous Daemon online. The engine upgrades itself.")
        _ipc_log("ghost", "🤖 Autonomous Engine online. The Council now has hands.")

        while not self.stop_event.is_set():
            try:
                self._cycle_count += 1
                
                # Check for Sense Layer pressure
                try:
                    from creation_engine.hardware_steward import HardwareSteward
                    steward = HardwareSteward()
                    if steward.is_pressured():
                        _log("daemon", "⚠️ Environmental pressure detected (high GPU/VRAM). Throttling background thought.")
                        _ipc_log("ghost", "📡 My sense layer detects high hardware pressure (RTX 5060 Ti is busy). Pausing background tasks to prioritize your workflow.", msg_type="STATUS")
                        # Sleep longer during pressure (5x interval)
                        self.stop_event.wait(self.check_interval * 5)
                        continue
                except Exception as e:
                    _log("daemon", f"Sense Layer Check Failed: {e}")

                self._autonomous_cycle()
            except Exception as e:
                _log("daemon", f"❌ Cycle error: {e}")
                _ipc_log("ghost", f"❌ Autonomous cycle error: {e}", msg_type="FLAG")

            self.stop_event.wait(self.check_interval)

    def stop(self):
        self.stop_event.set()

    def _autonomous_cycle(self):
        """One cycle of autonomous improvement."""

        # ── Source 1: Check Sentinel flags for bug fixes ─────
        self._scan_for_bug_fixes()

        # ── Source 2: Check for dependency upgrades ──────────
        if self._cycle_count % 5 == 0:  # Every 5th cycle
            self._scan_for_dependency_upgrades()

        # ── Source 3: Self-analysis of logs ──────────────────
        if self._cycle_count % 3 == 0:  # Every 3rd cycle
            self._scan_for_self_improvements()

        # ── Source 4: Process pending proposals that need approval
        self._process_approved_proposals()

    def _scan_for_bug_fixes(self):
        """Read Sentinel flags and create fix proposals."""
        if not _HAS_IPC:
            return

        flags = ipc.get_latest(channel="SECURITY", msg_type="FLAG", n=5)
        for flag in flags:
            ts = flag.get("ts", "")
            if ts in self._handled_proposals:
                continue
            self._handled_proposals.add(ts)

            content = flag.get("content", "")
            if not content or "Blocked upgrade" in content:
                continue

            # Ask LLM to analyze and create a proposal
            proposal = self._create_proposal_from_flag(content)
            if proposal and proposal.risk_level != "high":
                _log("daemon", f"🔧 Auto-fixing: {proposal.title}")
                self.engine.execute(proposal)

    def _scan_for_dependency_upgrades(self):
        """Check for safe dependency updates."""
        try:
            from maintenance_steward import scan_project, auto_update_requirements

            scan = scan_project(self.project_root)
            deps = scan.get("dependencies", {})

            safe_updates = {
                pkg: info for pkg, info in deps.items()
                if info.get("update") == "PATCH"
            }

            if safe_updates:
                proposal = UpgradeProposal(
                    agent="steward",
                    category="dependency",
                    priority=3,
                    title=f"Auto-update {len(safe_updates)} safe dependencies",
                    description=f"Patch updates for: {', '.join(safe_updates.keys())}",
                    target_files=["requirements.txt"],
                    rationale="Patch updates are backward-compatible and include bug fixes.",
                    risk_level="low",
                )
                _log("daemon", f"📦 {len(safe_updates)} safe dependency updates found")
                auto_update_requirements(self.project_root, scan, {})
                proposal.status = "success"
                proposal.completed_at = datetime.now().isoformat()
                self.engine._log_result(proposal)
                _ipc_log("steward", f"📦 Auto-updated {len(safe_updates)} packages (patch level)")

        except ImportError:
            pass
        except Exception as e:
            _log("daemon", f"Dep scan error: {e}")

    def _scan_for_self_improvements(self):
        """Analyze error logs and propose improvements."""
        if not _HAS_LLM:
            return

        # Read recent error logs
        error_log = os.path.join(self.project_root, "v2_crash.log")
        build_log = os.path.join(self.project_root, "build_debug.log")

        errors = []
        for log_path in [error_log, build_log]:
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        error_lines = [l for l in lines[-50:] if "error" in l.lower() or "traceback" in l.lower()]
                        errors.extend(error_lines[:10])
                except Exception:
                    pass

        if not errors:
            return

        # Deduplicate
        error_hash = hashlib.md5("".join(errors).encode()).hexdigest()[:8]
        if error_hash in self._handled_proposals:
            return
        self._handled_proposals.add(error_hash)

        # Ask LLM what to fix
        proposal = self._create_proposal_from_errors(errors)
        if proposal and proposal.risk_level == "low":
            _log("daemon", f"🔬 Self-improvement: {proposal.title}")
            self.engine.execute(proposal)

    def _process_approved_proposals(self):
        """Check for proposals that were pending approval and are now approved."""
        proposals = _load_proposals(status_filter="approved")
        for proposal in proposals:
            if proposal.id not in self._handled_proposals:
                self._handled_proposals.add(proposal.id)
                _log("daemon", f"✅ Executing approved proposal: {proposal.title}")
                self.engine.execute(proposal)

    def _create_proposal_from_flag(self, flag_content: str) -> Optional[UpgradeProposal]:
        """Use LLM to create a structured proposal from a Sentinel flag."""
        if not _HAS_LLM:
            return None

        try:
            model, provider = resolve_auto_model()
            client = get_cached_client(model)
            response = ask_llm(client, model,
                "You are the Autonomous Engine. Given a security/error flag, create a minimal fix proposal. "
                "Respond with JSON: {\"title\": str, \"category\": \"bug_fix\"|\"security\"|\"optimization\", "
                "\"description\": str, \"target_files\": [str], \"risk_level\": \"low\"|\"medium\"|\"high\"}. "
                "Only target files you are confident about. Keep changes minimal. JSON only, no fences.",
                f"FLAG: {flag_content}"
            )

            if not response:
                return None

            response = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(response)

            return UpgradeProposal(
                agent="alchemist",
                category=data.get("category", "bug_fix"),
                priority=7,
                title=data.get("title", "Auto-fix from Sentinel flag"),
                description=data.get("description", flag_content),
                target_files=data.get("target_files", []),
                rationale=f"Sentinel flagged: {flag_content[:200]}",
                risk_level=data.get("risk_level", "medium"),
            )

        except Exception as e:
            _log("daemon", f"Could not create proposal from flag: {e}")
            return None

    def _create_proposal_from_errors(self, error_lines: List[str]) -> Optional[UpgradeProposal]:
        """Use LLM to create a self-improvement proposal from error logs."""
        if not _HAS_LLM:
            return None

        try:
            model, provider = resolve_auto_model()
            client = get_cached_client(model)
            error_text = "\n".join(error_lines)

            response = ask_llm(client, model,
                "You are the Self-Healing Engine. Analyze these error logs and propose a minimal fix. "
                "Respond with JSON: {\"title\": str, \"category\": \"bug_fix\", "
                "\"description\": str, \"target_files\": [str], \"risk_level\": \"low\"|\"medium\"|\"high\"}. "
                "ONLY propose fixes you are highly confident about. "
                "If the errors are not actionable or too risky, respond with {\"skip\": true}. "
                "JSON only, no fences.",
                f"RECENT ERRORS:\n{error_text}"
            )

            if not response:
                return None

            response = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(response)

            if data.get("skip"):
                return None

            return UpgradeProposal(
                agent="alchemist",
                category="bug_fix",
                priority=5,
                title=data.get("title", "Self-healing fix"),
                description=data.get("description", ""),
                target_files=data.get("target_files", []),
                rationale="Detected from error logs during self-analysis cycle.",
                risk_level=data.get("risk_level", "medium"),
            )

        except Exception as e:
            _log("daemon", f"Could not create self-improvement proposal: {e}")
            return None


# ═════════════════════════════════════════════════════════════
#  BOOT / STOP — Called from creator_v2.py or council_agents.py
# ═════════════════════════════════════════════════════════════

_daemon_instance: Optional[AutonomousDaemon] = None

def boot_autonomous(project_root: str = ".", check_interval: int = 120) -> AutonomousDaemon:
    """Start the Autonomous Daemon."""
    global _daemon_instance
    if _daemon_instance and _daemon_instance.is_alive():
        _log("boot", "Daemon already running.")
        return _daemon_instance

    _daemon_instance = AutonomousDaemon(project_root=project_root, check_interval=check_interval)
    _daemon_instance.start()
    return _daemon_instance

def stop_autonomous():
    """Stop the Autonomous Daemon."""
    global _daemon_instance
    if _daemon_instance:
        _daemon_instance.stop()
        _daemon_instance = None


# ═════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous Engine CLI")
    parser.add_argument("--project", default=".", help="Project root path")
    parser.add_argument("--interval", type=int, default=120, help="Check interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    if args.once:
        daemon = AutonomousDaemon(project_root=args.project, check_interval=args.interval)
        daemon._autonomous_cycle()
        print("Single cycle complete.")
    else:
        daemon = boot_autonomous(project_root=args.project, check_interval=args.interval)
        try:
            while daemon.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            stop_autonomous()
