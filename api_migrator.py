#!/usr/bin/env python3
"""
API Migrator — Creation Engine Utility
Automates the migration of legacy projects to the unified Creation Engine API standard.
1. Scans for hardcoded keys.
2. Refactors client initializations to use llm_client.
3. Populates .env files.
4. Supports dry-run and backups.
"""

import os
import re
import sys
import shutil
import json
from datetime import datetime

# --- CONFIGURATION ---
SUPPORTED_EXTENSIONS = {".py", ".env", ".js", ".ts", ".json"}
KEY_PATTERNS = {
    "OPENAI": r"sk-[a-zA-Z0-9]{32,}",
    "ANTHROPIC": r"sk-ant-sid01-[a-zA-Z0-9-]{40,}",
    "GEMINI": r"AIzaSy[a-zA-Z0-9_-]{33}",
    "GROQ": r"gsk_[a-zA-Z0-9]{40,}",
    "DEEPSEEK": r"sk-[a-f0-9]{32}",
    "OPENROUTER": r"sk-or-v1-[a-f0-9]{64}",
}

REFACTOR_MAP = {
    # Replace OpenAI/Anthropic initialization (handles module prefix and literal/variable)
    r"(?:openai\.)?OpenAI\((?:api_key=)?([^)]+)\)": "get_cached_client('auto')",
    r"(?:anthropic\.)?Anthropic\((?:api_key=)?([^)]+)\)": "get_cached_client('auto')",
}

IMPORT_INJECTION = "from creation_engine.llm_client import get_cached_client, ask_llm\nimport os\n"

class Migrator:
    def __init__(self, target_dir: str, dry_run: bool = True):
        self.target_dir = os.path.abspath(target_dir)
        self.dry_run = dry_run
        self.backups_dir = os.path.join(self.target_dir, ".migrator_backups")
        self.found_keys: dict[str, str] = {} # var_name -> key_value
        self.stats = {"scanned": 0, "modified": 0, "keys_found": 0}

    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [MIGRATOR] {msg}")

    def create_backup(self, file_path: str):
        if self.dry_run: return
        os.makedirs(self.backups_dir, exist_ok=True)
        rel_path = os.path.relpath(file_path, self.target_dir)
        backup_path = os.path.join(self.backups_dir, rel_path + ".bak")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(file_path, backup_path)

    def revert(self):
        """Restore files from .migrator_backups."""
        if not os.path.exists(self.backups_dir):
            self.log("❌ No backups found to revert.")
            return

        self.log("⏪ Reverting changes from backups...")
        for root, _, files in os.walk(self.backups_dir):
            for file in files:
                if not file.endswith(".bak"): continue
                backup_path = os.path.join(root, file)
                rel_path = os.path.relpath(backup_path, self.backups_dir)[:-4] # Remove .bak
                original_path = os.path.join(self.target_dir, rel_path)
                
                self.log(f"  📂 Restoring {rel_path}")
                shutil.copy2(backup_path, original_path)
        
        self.log("✅ Revert complete.")

    def scan_and_refactor(self):
        self.log(f"🚀 Starting migration scan in: {self.target_dir}")
        if self.dry_run:
            self.log("🧪 DRY-RUN MODE: No files will be modified.")

        for root, _, files in os.walk(self.target_dir):
            if any(x in root for x in [".git", "node_modules", "venv", ".migrator_backups"]):
                continue
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in SUPPORTED_EXTENSIONS:
                    self.process_file(os.path.join(root, file))

        self.update_env()
        self.summarize()

    def process_file(self, file_path: str):
        self.stats["scanned"] += 1
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        new_content = str(content)
        modified = False

        # 1. Detect Keys
        for provider, pattern in KEY_PATTERNS.items():
            matches = re.findall(pattern, new_content)
            for match in matches:
                env_var = f"{provider}_API_KEY"
                self.found_keys[env_var] = match
                self.stats["keys_found"] += 1
                # Replace literal string with env lookup
                new_content = new_content.replace(f"'{match}'", f"os.environ.get('{env_var}')")
                new_content = new_content.replace(f"\"{match}\"", f"os.environ.get('{env_var}')")
                modified = True

        # 2. Refactor Common Initializations
        for pattern, replacement in REFACTOR_MAP.items():
            if re.search(pattern, new_content):
                new_content = re.sub(pattern, replacement, new_content)
                modified = True

        # 3. Inject Imports if modified
        if modified and file_path.endswith(".py") and "creation_engine.llm_client" not in new_content:
            text_lines = new_content.split("\n")
            insert_idx = 0
            # Skip shebang
            if text_lines and text_lines[0].startswith("#!"):
                insert_idx = 1
            
            # Skip docstring if it starts right after shebang or at top
            if len(text_lines) > insert_idx and text_lines[insert_idx].strip().startswith(('"""', "'''")):
                start_marker = text_lines[insert_idx].strip()[:3]
                # Find end of docstring
                for j in range(insert_idx, len(text_lines)):
                    this_line = text_lines[j].strip()
                    if j > insert_idx and this_line.endswith(start_marker):
                        insert_idx = j + 1
                        break
                    elif j == insert_idx and len(this_line) > 3 and this_line[3:].endswith(start_marker):
                        # Single line docstring
                        insert_idx = j + 1
                        break
            
            text_lines.insert(insert_idx, IMPORT_INJECTION)
            new_content = "\n".join(text_lines)

        if modified:
            self.log(f"  ✨ {'[WOULD MODIFY]' if self.dry_run else '[MODIFY]'} {os.path.relpath(file_path, self.target_dir)}")
            if not self.dry_run:
                self.create_backup(file_path)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            self.stats["modified"] += 1

    def update_env(self):
        if not self.found_keys: return
        env_path = os.path.join(self.target_dir, ".env")
        exists = os.path.exists(env_path)
        
        mode = "a" if exists else "w"
        self.log(f"  📝 {'[WOULD UPDATE]' if self.dry_run else '[UPDATE]'} .env with {len(self.found_keys)} keys")
        
        if not self.dry_run:
            self.create_backup(env_path) if exists else None
            with open(env_path, mode, encoding="utf-8") as f:
                if not exists: f.write("# Generated by API Migrator\n")
                else: f.write("\n# Keys added by API Migrator\n")
                for var, val in self.found_keys.items():
                    f.write(f"{var}={val}\n")

    def summarize(self):
        print("\n" + "="*40)
        print("  MIGRATION SUMMARY")
        print("="*40)
        print(f"  Scanned:  {self.stats['scanned']} files")
        print(f"  Modified: {self.stats['modified']} files")
        print(f"  Keys Migrated: {self.stats['keys_found']}")
        if self.found_keys:
            print("  Variables Added to .env:")
            for var in self.found_keys:
                print(f"    - {var}")
        print("="*40 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python api_migrator.py <directory> [--apply | --revert]")
        sys.exit(1)

    target = sys.argv[1]
    is_apply = "--apply" in sys.argv
    is_revert = "--revert" in sys.argv
    is_dry = not (is_apply or is_revert)
    
    if not os.path.isdir(target):
        print(f"Error: {target} is not a directory.")
        sys.exit(1)

    migrator = Migrator(target, dry_run=is_dry)
    
    if is_revert:
        migrator.revert()
    else:
        migrator.scan_and_refactor()
        if is_dry:
            print("\n💡 Run with --apply to perform the migration.")
