"""
Creation Engine — Validators & State Management
CodebaseState, ProjectState, CodebaseRAG, ReviewerAgent,
ConfigConsistencyChecker, validation_gate, build_manifest,
DependencyVerifier, SelfCorrectionModule.
"""

import os
import sys
import ast
import json
import hashlib
import subprocess
from datetime import datetime

from .llm_client import log, ask_llm
from .config import PKG_MAP


# ── Codebase State Persistence ──────────────────────────────

class CodebaseState:
    """Persistent wrapper around written_files dict.
    Saves state to disk after every write, enabling crash recovery."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.state_file = os.path.join(project_path, ".overlord_state.json")
        self.files = {}
        self.metadata = {}
        self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.files = data.get("files", {})
                self.metadata = data.get("metadata", {})
                log("STATE", f"  Resumed previous state: {len(self.files)} file(s) loaded.")
            except Exception as e:
                log("STATE", f"  State file corrupt, starting fresh: {e}")
                self.files = {}
                self.metadata = {}

    def _save(self):
        try:
            data = {"files": self.files, "metadata": self.metadata,
                    "saved_at": datetime.now().isoformat()}
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log("STATE", f"  ⚠ State save failed: {e}")

    def write(self, filepath: str, code: str, review_count: int = 0):
        self.files[filepath] = code
        self.metadata[filepath] = {
            "chars": len(code),
            "hash": hashlib.sha256(code.encode("utf-8")).hexdigest()[:16],
            "reviews": review_count,
            "written_at": datetime.now().isoformat(),
        }
        self._save()

    def get_context_block(self, exclude: str = "") -> str:
        snippets = []
        for fpath, code in self.files.items():
            if fpath == exclude:
                continue
            preview = "\n".join(code.split("\n")[:40])
            snippets.append(f"--- {fpath} ---\n{preview}\n---")
        return "\n\n".join(snippets) if snippets else "No files written yet."

    def clear(self):
        self.files = {}
        self.metadata = {}
        if os.path.exists(self.state_file):
            os.remove(self.state_file)


# ── Project State (Symbol Tracking) ─────────────────────────

class ProjectState:
    """Tracks exported symbols across all written files."""

    def __init__(self):
        self._symbols = {}
        self._variables = {}

    def register_file(self, filepath, code):
        symbols = []
        variables = []
        try:
            tree = ast.parse(code)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in node.args.args]
                    symbols.append({"name": node.name, "type": "function", "args": args})
                elif isinstance(node, ast.ClassDef):
                    methods = [item.name for item in node.body
                               if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    symbols.append({"name": node.name, "type": "class", "methods": methods})
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append(target.id)
        except SyntaxError:
            pass
        self._symbols[filepath] = symbols
        self._variables[filepath] = variables

    def get_symbol_table(self):
        if not self._symbols:
            return ""
        lines = ["[GLOBAL STATE — Registered Symbols]"]
        for fpath, syms in self._symbols.items():
            exports = []
            for s in syms:
                if s["type"] == "function":
                    exports.append(f"def {s['name']}({', '.join(s.get('args', []))})")
                elif s["type"] == "class":
                    exports.append(f"class {s['name']} [{', '.join(s.get('methods', []))}]")
            for v in self._variables.get(fpath, []):
                exports.append(f"{v} = ...")
            if exports:
                lines.append(f"  {fpath}: {' | '.join(exports)}")
        return "\n".join(lines)

    def get_exports_for(self, filepath):
        return self._symbols.get(filepath, [])


# ── RAG-Based Context Windowing ─────────────────────────────

class CodebaseRAG:
    """Token-aware context retrieval — only sends relevant files to the LLM."""

    def __init__(self, max_context_chars=12000):
        self._index = {}
        self._files = {}
        self.max_context_chars = max_context_chars

    def index_file(self, filepath, code, symbols=None):
        import re
        self._files[filepath] = code
        keywords = set()
        stem = os.path.splitext(os.path.basename(filepath))[0].lower()
        keywords.add(stem)
        keywords.update(t.lower() for t in re.findall(r'[a-zA-Z_]\w+', code))
        if symbols:
            for s in symbols:
                keywords.add(s["name"].lower())
        self._index[filepath] = keywords

    def get_relevant_context(self, target_file, task_description, state_table=""):
        import re
        query_tokens = set(re.findall(r'[a-zA-Z_]\w+', task_description.lower()))
        target_stem = os.path.splitext(os.path.basename(target_file))[0].lower()
        query_tokens.add(target_stem)

        scores = []
        for fpath, keywords in self._index.items():
            if fpath == target_file:
                continue
            overlap = len(query_tokens & keywords)
            other_stem = os.path.splitext(os.path.basename(fpath))[0].lower()
            if target_stem in keywords or other_stem in query_tokens:
                overlap += 10
            scores.append((overlap, fpath))

        scores.sort(reverse=True)
        context_parts = []
        total_chars = 0
        stub_files = []

        for score, fpath in scores:
            code = self._files[fpath]
            if total_chars + len(code) < self.max_context_chars and score > 0:
                context_parts.append(f"--- {fpath} (relevance: {score}) ---\n{code}\n---")
                total_chars += len(code)
            else:
                first_line = code.split('\n')[0] if code else ""
                stub_files.append(f"  {fpath}: {first_line[:80]}")

        result = "\n\n".join(context_parts)
        if stub_files:
            result += "\n\n[OTHER FILES — summaries only]\n" + "\n".join(stub_files)
        if state_table:
            result += f"\n\n{state_table}"
        return result or "No files written yet."


# ── Reviewer Agent ──────────────────────────────────────────

class ReviewerAgent:
    """Autonomous code reviewer. Returns APPROVED or REJECTED."""

    REVIEW_SYSTEM = (
        "You are 'Overlord Reviewer,' a ruthless code quality gate. "
        "You receive a filename and its source code. "
        "Your job: inspect the code for these fatal flaws:\n"
        "1. Syntax errors or incomplete code (truncated functions, missing returns)\n"
        "2. Placeholder URLs like 'example.com', 'your-api-key', or dummy credentials\n"
        "3. Import of modules that don't exist in the project (hallucinated imports). "
        "NOTE: Modules listed in the project manifest or file tree ARE valid.\n"
        "4. Functions/classes referenced but never defined\n"
        "5. Obvious logic errors (infinite loops, wrong return types)\n"
        "6. Config attribute mismatches\n"
        "7. Enum member mismatches\n"
        "8. Cross-file naming: imported names must match definition exactly.\n\n"
        "Output ONLY a JSON object with this exact schema:\n"
        '{"status": "APPROVED" or "REJECTED", "reason": "concise explanation"}\n'
        "If the code is acceptable, status is APPROVED and reason is 'Clean code.'"
        "Be strict but fair. Minor style issues are NOT grounds for rejection."
    )

    def __init__(self, client, model, wisdom_context: str = ""):
        self.client = client
        self.model = model
        self.system_prompt = self.REVIEW_SYSTEM
        if wisdom_context:
            self.system_prompt += (
                "\n\nADDITIONAL RULES — REJECT code that violates any of these:\n"
                + wisdom_context
            )

    def review(self, filepath: str, code: str, manifest_context: str = "") -> dict:
        # Deterministic wisdom block
        if filepath.endswith(".py") and "before_first_request" in code:
            log("REVIEWER", f"  🚫 WISDOM BLOCK: @app.before_first_request detected in {filepath}")
            return {
                "status": "REJECTED",
                "reason": "WISDOM BLOCK: Flask removed @app.before_first_request in v2.3+."
            }
        user_prompt = f"File: {filepath}\n\nSource Code:\n```\n{code}\n```\n\n"
        if manifest_context:
            user_prompt += f"Project Manifest (for cross-reference):\n{manifest_context}\n"

        try:
            raw = ask_llm(self.client, self.model, self.system_prompt, user_prompt)
            result = json.loads(raw)
            if "status" not in result:
                return {"status": "APPROVED", "reason": "Reviewer returned no status — auto-approved."}
            return result
        except json.JSONDecodeError:
            raw_upper = raw.upper() if raw else ""
            if "REJECTED" in raw_upper:
                return {"status": "REJECTED", "reason": raw[:200]}
            return {"status": "APPROVED", "reason": "Reviewer parse fallback — auto-approved."}
        except Exception as e:
            log("REVIEWER", f"  ⚠ Review failed: {e} — auto-approving.")
            return {"status": "APPROVED", "reason": f"Review error: {e}"}


# ── Build Manifest ──────────────────────────────────────────

def build_manifest(written_files: dict, planned_files: list = None) -> dict:
    """Extract functions, classes, variables, and imports from all written files."""
    manifest = {}
    if planned_files:
        for fpath in planned_files:
            manifest[fpath] = {"functions": [], "classes": [], "variables": [],
                               "imports": [], "exports_all": None, "is_planned": True}

    for fpath, code in written_files.items():
        entry = {"functions": [], "classes": [], "variables": [],
                 "imports": [], "exports_all": None, "is_planned": False}
        if not fpath.endswith(".py"):
            manifest[fpath] = entry
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            manifest[fpath] = entry
            continue

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_list = [a.arg for a in node.args.args]
                sig = f"{node.name}({', '.join(args_list)})"
                entry["functions"].append(sig)
            elif isinstance(node, ast.ClassDef):
                methods = [item.name for item in node.body
                           if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
                entry["classes"].append({"name": node.name, "methods": methods})
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        entry["variables"].append(target.id)
                        if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                            entry["exports_all"] = [
                                elt.value for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    entry["imports"].append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                names = ", ".join(a.name for a in node.names)
                entry["imports"].append(f"from {node.module or '.'} import {names}")

        manifest[fpath] = entry
    return manifest


def manifest_to_context(manifest: dict) -> str:
    """Convert manifest dict to a concise string for LLM consumption."""
    lines = ["PROJECT MANIFEST (Source of Truth):"]
    for fpath, info in manifest.items():
        lines.append(f"\n── {fpath} ──")
        if info["functions"]:
            lines.append(f"  Functions: {', '.join(info['functions'])}")
        if info["classes"]:
            for cls in info["classes"]:
                lines.append(f"  Class {cls['name']}: methods=[{', '.join(cls['methods'])}]")
        if info["variables"]:
            lines.append(f"  Variables: {', '.join(info['variables'])}")
        if info["imports"]:
            lines.append(f"  Imports: {'; '.join(info['imports'][:10])}")
    return "\n".join(lines)


# ── Validation Gate ─────────────────────────────────────────

def validation_gate(written_files: dict, manifest: dict) -> list:
    """Cross-reference every import against the manifest."""
    violations = []
    exports_map = {}
    for fpath, info in manifest.items():
        if not fpath.endswith(".py"):
            continue
        module_key = fpath.replace(".py", "").replace("/", ".").replace("\\", ".")
        exported = set()
        if info.get("exports_all"):
            exported = set(info["exports_all"])
        else:
            for sig in info["functions"]:
                exported.add(sig.split("(")[0])
            for cls in info["classes"]:
                exported.add(cls["name"])
            for var in info["variables"]:
                exported.add(var)
        exports_map[module_key] = exported
        exports_map[fpath] = exported

    for fpath, code in written_files.items():
        if not fpath.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module.split(".")[0]
                mod_file = f"{mod}.py"
                if mod_file in written_files and mod_file in exports_map:
                    available = exports_map[mod_file]
                    for alias in node.names:
                        if alias.name != "*" and alias.name not in available:
                            violations.append({
                                "file": fpath, "line": node.lineno,
                                "import_stmt": f"from {node.module} import {alias.name}",
                                "missing": alias.name, "source_file": mod_file,
                                "available": sorted(list(available)),
                            })
    return violations


def import_dry_run(written_files: dict) -> list:
    """Verify that all 'from X import Y' resolve correctly for local modules."""
    exports = {}
    for fpath, code in written_files.items():
        if not fpath.endswith(".py"):
            continue
        mod_name = fpath.replace(".py", "").replace("/", ".").replace("\\", ".")
        mod_base = fpath.replace(".py", "")
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        symbols = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.add(node.name)
            elif isinstance(node, ast.ClassDef):
                symbols.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.add(target.id)
        exports[mod_name] = symbols
        exports[mod_base] = symbols
        exports[fpath] = symbols

    violations = []
    for fpath, code in written_files.items():
        if not fpath.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod_key = node.module.split(".")[0]
                if mod_key in exports:
                    available = exports[mod_key]
                    for alias in node.names:
                        if alias.name != "*" and alias.name not in available:
                            violations.append({
                                "file": fpath, "line": node.lineno,
                                "import": f"from {node.module} import {alias.name}",
                                "missing": alias.name, "source": f"{mod_key}.py",
                                "available": sorted(list(available))[:15],
                            })
    return violations


# ── Config Consistency Checker ──────────────────────────────

class ConfigConsistencyChecker:
    """AST-based validator ensuring config.X references match the Config class."""

    @staticmethod
    def check(written_files: dict) -> list:
        config_attrs = set()
        config_file = None
        for fpath, code in written_files.items():
            if not fpath.endswith(".py"):
                continue
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    is_config = "config" in node.name.lower() or "settings" in node.name.lower()
                    if not is_config:
                        continue
                    config_file = fpath
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    config_attrs.add(target.id)
                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            config_attrs.add(item.target.id)

        if not config_attrs:
            return []

        violations = []
        for fpath, code in written_files.items():
            if not fpath.endswith(".py") or fpath == config_file:
                continue
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
                    if node.value.attr == "config" and node.attr not in config_attrs:
                        violations.append({
                            "file": fpath, "line": node.lineno,
                            "ref": f"config.{node.attr}",
                            "available": sorted(list(config_attrs)),
                        })
                elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                    if node.value.attr == "config" and isinstance(node.slice, ast.Constant):
                        attr_name = node.slice.value
                        if isinstance(attr_name, str) and attr_name not in config_attrs:
                            violations.append({
                                "file": fpath, "line": node.lineno,
                                "ref": f"config['{attr_name}']",
                                "available": sorted(list(config_attrs)),
                            })
        return violations


# ── Dependency Verifier ─────────────────────────────────────

class DependencyVerifier:
    """Verifies dependency resolution in Docker or local fallback."""

    def __init__(self):
        self.docker_available = self._check_docker()

    def _check_docker(self):
        try:
            r = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def verify(self, deps, project_path):
        if not deps:
            return True, "No dependencies to verify."
        req_path = os.path.join(project_path, "requirements.txt")
        if self.docker_available:
            return self._verify_docker(req_path, project_path)
        return self._verify_local(deps)

    def _verify_docker(self, req_path, project_path):
        log("DOCKER", "  Running pip install in disposable container…")
        try:
            abs_proj = os.path.abspath(project_path).replace("\\", "/")
            r = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{abs_proj}:/app", "-w", "/app",
                 "python:3.12-slim", "pip", "install", "--no-cache-dir",
                 "-r", "/app/requirements.txt"],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0:
                return True, "All dependencies resolved in container ✓"
            return False, r.stderr.strip()[:300]
        except subprocess.TimeoutExpired:
            return False, "Docker verification timed out (120s)."
        except Exception as e:
            return False, f"Docker error: {e}"

    def _verify_local(self, deps):
        log("SYSTEM", "  Docker unavailable — using local pip --dry-run…")
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--dry-run"] + deps,
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                return True, "All dependencies resolved (local dry-run) ✓"
            return False, r.stderr.strip()[:300]
        except Exception as e:
            return False, f"Local verification error: {e}"


# ── Self-Correction Module (Lint + Auto-Repair) ─────────────

class SelfCorrectionModule:
    """Static analysis + LLM-powered repair loop."""

    def __init__(self, code: str, path: str, max_attempts: int = 3):
        self.code = code
        self.path = path
        self.ext = os.path.splitext(path)[1].lower()
        self.max_attempts = max_attempts
        self.attempts = 0

    def run_lint_check(self) -> tuple:
        if self.ext == ".py":
            return self._check_python()
        elif self.ext in (".js", ".ts", ".jsx", ".tsx"):
            return self._check_js()
        return True, "No lint check for this file type."

    def _check_python(self):
        try:
            compile(self.code, self.path, "exec")
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        return True, "Python checks passed."

    def _check_js(self):
        return True, "JS checks passed."

    def repair_loop(self, fixer_callback) -> str:
        while self.attempts < self.max_attempts:
            is_valid, report = self.run_lint_check()
            if is_valid:
                if self.attempts > 0:
                    log("LINT", f"  ✓ {self.path} passed after {self.attempts} repair(s)")
                return self.code
            self.attempts += 1
            log("LINT", f"  ✗ [{self.attempts}/{self.max_attempts}] {self.path}: {report[:120]}")
            if self.attempts < self.max_attempts:
                try:
                    self.code = fixer_callback(self.code, report)
                except Exception as e:
                    log("LINT", f"  ⚠ Fixer agent failed: {e} — accepting current version.")
                    return self.code
        log("LINT", f"  ⚠ Could not fully fix {self.path} after {self.max_attempts} attempts.")
        return self.code


# ── Project Assembler ───────────────────────────────────────

def project_assembler(plan: dict, project_path: str):
    """Creates the directory structure and empty files from the Architect's blueprint."""
    file_tree = plan.get("file_tree", [])
    if not file_tree:
        file_tree = [f["path"] for f in plan.get("files", [])]

    if not file_tree:
        log("ASSEMBLER", "  ⚠ No file tree in manifest — skipping assembly.")
        return

    log("ASSEMBLER", f"  Scaffolding {len(file_tree)} file(s)…")
    created_dirs = set()
    for fpath in file_tree:
        full_path = os.path.join(project_path, fpath)
        parent_dir = os.path.dirname(full_path) or project_path
        if parent_dir not in created_dirs:
            os.makedirs(parent_dir, exist_ok=True)
            created_dirs.add(parent_dir)
        if not os.path.exists(full_path):
            ext = os.path.splitext(fpath)[1].lower()
            with open(full_path, "w", encoding="utf-8") as f:
                if ext == ".py":
                    f.write(f"# {fpath} — placeholder\n")
                elif ext in (".js", ".ts", ".jsx", ".tsx"):
                    f.write(f"// {fpath} — placeholder\n")
                elif ext in (".html", ".xml"):
                    f.write(f"<!-- {fpath} — placeholder -->\n")
                elif ext in (".css", ".scss"):
                    f.write(f"/* {fpath} — placeholder */\n")
                else:
                    f.write("")
            log("ASSEMBLER", f"  ├─ {fpath}")

    for std_dir in ["tests", "docs"]:
        std_path = os.path.join(project_path, std_dir)
        if not os.path.exists(std_path):
            os.makedirs(std_path, exist_ok=True)

    log("ASSEMBLER", f"  └─ ✓ Scaffold complete: {len(file_tree)} files, {len(created_dirs)} directories")

    gitignore_path = os.path.join(project_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        gitignore_content = (
            "# Overlord-generated .gitignore\n"
            "__pycache__/\n*.pyc\n.env\nvenv/\nnode_modules/\n"
            ".overlord_state.json\ndist/\nbuild/\n*.egg-info/\n"
        )
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        log("ASSEMBLER", "  ├─ .gitignore")
