"""
Sovereign Module — Shadow Sandbox
Isolated execution environment for self-upgrade validation.

Before any self-modification, the engine takes a snapshot.
If the upgrade breaks something, it auto-rolls back.

Usage:
    from creation_engine.sovereign.sandbox import sandbox

    sid = sandbox.snapshot("engine_memory.json")
    try:
        # dangerous self-upgrade here
        sandbox.validate_import("creation_engine")
    except:
        sandbox.rollback(sid)
"""

import os
import sys
import json
import shutil
import importlib
import traceback
from datetime import datetime
from pathlib import Path


SNAPSHOT_DIR = os.path.join("memory", "snapshots")


class ShadowSandbox:
    """
    Snapshot/rollback system for safe self-modification.

    Workflow:
        1. snapshot(target) → saves current state
        2. Apply the upgrade
        3. validate_import() → dry-run import check
        4. If validation fails → rollback(snapshot_id)
    """

    def __init__(self, snapshot_dir: str = SNAPSHOT_DIR):
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)

    # ── Snapshot ─────────────────────────────────────────────

    def snapshot(self, *target_paths: str) -> str:
        """
        Create a snapshot of one or more files.
        Returns a snapshot ID that can be used for rollback.
        """
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snap_dir = os.path.join(self.snapshot_dir, snapshot_id)
        os.makedirs(snap_dir, exist_ok=True)

        manifest = {
            "id": snapshot_id,
            "timestamp": datetime.now().isoformat(),
            "files": [],
        }

        for path in target_paths:
            if os.path.exists(path):
                # Preserve directory structure
                rel = os.path.basename(path)
                dest = os.path.join(snap_dir, rel)
                shutil.copy2(path, dest)
                manifest["files"].append({
                    "original": os.path.abspath(path),
                    "backup": dest,
                })

        # Save manifest
        with open(os.path.join(snap_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"[SANDBOX] 📸 Snapshot {snapshot_id}: {len(manifest['files'])} files saved")
        return snapshot_id

    # ── Rollback ─────────────────────────────────────────────

    def rollback(self, snapshot_id: str) -> bool:
        """
        Restore files from a snapshot.
        Returns True if successful.
        """
        snap_dir = os.path.join(self.snapshot_dir, snapshot_id)
        manifest_path = os.path.join(snap_dir, "manifest.json")

        if not os.path.exists(manifest_path):
            print(f"[SANDBOX] ❌ Snapshot {snapshot_id} not found")
            return False

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        restored = 0
        for entry in manifest["files"]:
            src = entry["backup"]
            dest = entry["original"]
            if os.path.exists(src):
                shutil.copy2(src, dest)
                restored += 1

        print(f"[SANDBOX] ⏪ Rolled back {restored} files from snapshot {snapshot_id}")
        return True

    # ── Validation ───────────────────────────────────────────

    def validate_import(self, module_name: str) -> dict:
        """
        Dry-run import check. Attempts to import (or reimport)
        a module to verify it doesn't crash.

        Returns: {"success": bool, "error": str or None}
        """
        try:
            if module_name in sys.modules:
                # Reload to catch changes
                mod = sys.modules[module_name]
                importlib.reload(mod)
            else:
                importlib.import_module(module_name)

            return {"success": True, "error": None}
        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }

    def test_json_integrity(self, file_path: str) -> dict:
        """
        Validate that a JSON file is well-formed and loadable.
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "success": True,
                "error": None,
                "type": type(data).__name__,
                "size": os.path.getsize(file_path),
            }
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Listing ──────────────────────────────────────────────

    def list_snapshots(self) -> list:
        """List all available snapshots with metadata."""
        snapshots = []
        if not os.path.exists(self.snapshot_dir):
            return snapshots

        for entry in sorted(os.listdir(self.snapshot_dir), reverse=True):
            manifest_path = os.path.join(self.snapshot_dir, entry, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                snapshots.append(manifest)

        return snapshots

    def cleanup(self, keep: int = 10):
        """Remove old snapshots, keeping only the most recent N."""
        snapshots = self.list_snapshots()
        if len(snapshots) <= keep:
            return

        for snap in snapshots[keep:]:
            snap_dir = os.path.join(self.snapshot_dir, snap["id"])
            if os.path.exists(snap_dir):
                shutil.rmtree(snap_dir)
                print(f"[SANDBOX] 🗑️ Cleaned snapshot {snap['id']}")


# ── Global Singleton ─────────────────────────────────────────

sandbox = ShadowSandbox()
