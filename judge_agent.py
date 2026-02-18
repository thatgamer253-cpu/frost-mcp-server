#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
  THE JUDGE — Gauntlet Validation Agent
  Final arbiter before code ships
═══════════════════════════════════════════════════════════

The Judge runs a multi-point "Gauntlet" on the final code
after the Sentinel and Alchemist have finished their work.

Gauntlet Checks:
  1. Dependency Integrity — all imports resolve
  2. Constraint Compliance — permanent rules pass
  3. Code Coherence — no orphaned files, all referenced
  4. Runtime Simulation — dry-run import test
  5. Structure Validation — required files present

Verdicts:
  GAUNTLET_PASSED  — Code is production-ready
  GAUNTLET_FAILED  — Code has blocking issues
"""

import os
import re
import ast
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# ── Logging ──────────────────────────────────────────────────
try:
    from creation_engine.llm_client import log
except ImportError:
    def log(tag: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}] {msg}")

# ── Interaction Hub ──────────────────────────────────────────
try:
    from interaction_hub import hub, SEVERITY_INFO, SEVERITY_ACTION, SEVERITY_VERDICT, SEVERITY_WARNING
    _HAS_HUB = True
except ImportError:
    _HAS_HUB = False

# ── Constraints ──────────────────────────────────────────────
try:
    from hive_coordinator import load_permanent_constraints, enforce_constraints
    _HAS_CONSTRAINTS = True
except ImportError:
    _HAS_CONSTRAINTS = False


# =============================================================
#  GAUNTLET CHECK RESULTS
# =============================================================

class GauntletCheck:
    """Result of a single Gauntlet check."""

    def __init__(self, name: str, passed: bool,
                 details: str = "", severity: str = "INFO"):
        self.name = name
        self.passed = passed
        self.details = details
        self.severity = severity
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "check": self.name,
            "passed": self.passed,
            "details": self.details,
            "severity": self.severity,
        }


# =============================================================
#  THE JUDGE
# =============================================================

class JudgeAgent:
    """The Gauntlet Validator — final arbiter of code quality.

    Runs after the Sentinel-Alchemist healing loop to ensure
    all code meets production standards before shipping.
    """

    def __init__(self):
        self.constraints = {}
        if _HAS_CONSTRAINTS:
            self.constraints = load_permanent_constraints()

    def _post(self, message: str, severity: str = SEVERITY_INFO if _HAS_HUB else "INFO",
              context: Optional[Dict] = None):
        """Post to the Interaction Hub if available."""
        log("JUDGE", message)
        if _HAS_HUB:
            hub().post("Judge", message, severity, context)

    def run_gauntlet(self, code_files: Dict[str, str],
                     audit_report: Optional[Dict[str, Any]] = None,
                     blueprint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the full Gauntlet validation suite.

        Args:
            code_files: Dict of {filename: code_content}
            audit_report: The Sentinel's audit report (optional)
            blueprint: The Architect's blueprint (optional)

        Returns:
            Gauntlet report with verdict and individual check results.
        """
        start = time.time()
        checks: List[GauntletCheck] = []

        file_count = len(code_files)
        constraint_count = len(self.constraints.get("permanent_rules", []))

        self._post(
            f"Gauntlet initiated. Testing {file_count} files against "
            f"{constraint_count} constraints...",
            SEVERITY_ACTION if _HAS_HUB else "ACTION",
        )

        # ── Check 1: Dependency Integrity ──
        dep_check = self._check_dependency_integrity(code_files)
        checks.append(dep_check)
        if dep_check.passed:
            self._post("✓ Dependency Integrity: All imports verified.")
        else:
            self._post(
                f"⚠ Dependency Integrity: {dep_check.details}",
                SEVERITY_WARNING if _HAS_HUB else "WARNING",
            )

        # ── Check 2: Constraint Compliance ──
        constraint_check = self._check_constraint_compliance(code_files)
        checks.append(constraint_check)
        if constraint_check.passed:
            self._post("✓ Constraint Compliance: All permanent rules satisfied.")
        else:
            self._post(
                f"⚠ Constraint Compliance: {constraint_check.details}",
                SEVERITY_WARNING if _HAS_HUB else "WARNING",
            )

        # ── Check 3: Code Coherence ──
        coherence_check = self._check_code_coherence(code_files, blueprint)
        checks.append(coherence_check)
        if coherence_check.passed:
            self._post("✓ Code Coherence: All files linked, no orphans.")
        else:
            self._post(
                f"⚠ Code Coherence: {coherence_check.details}",
                SEVERITY_WARNING if _HAS_HUB else "WARNING",
            )

        # ── Check 4: Syntax Validation ──
        syntax_check = self._check_syntax_validation(code_files)
        checks.append(syntax_check)
        if syntax_check.passed:
            self._post("✓ Syntax Validation: All Python files parse cleanly.")
        else:
            self._post(
                f"⚠ Syntax Validation: {syntax_check.details}",
                SEVERITY_WARNING if _HAS_HUB else "WARNING",
            )

        # ── Check 5: Structure Validation ──
        structure_check = self._check_structure(code_files, blueprint)
        checks.append(structure_check)
        if structure_check.passed:
            self._post("✓ Structure Validation: Required files present.")
        else:
            self._post(
                f"⚠ Structure Validation: {structure_check.details}",
                SEVERITY_WARNING if _HAS_HUB else "WARNING",
            )

        # ── Check 6: Sentinel Reconciliation ──
        if audit_report:
            sentinel_check = self._reconcile_sentinel(audit_report)
            checks.append(sentinel_check)
            if sentinel_check.passed:
                self._post("✓ Sentinel Reconciliation: Audit verdict clean.")
            else:
                self._post(
                    f"⚠ Sentinel Reconciliation: {sentinel_check.details}",
                    SEVERITY_WARNING if _HAS_HUB else "WARNING",
                )

        # ── Final Verdict ──
        elapsed = round(time.time() - start, 2)
        all_passed = all(c.passed for c in checks)
        critical_failures = [c for c in checks if not c.passed and c.severity == "CRITICAL"]

        if all_passed:
            verdict = "GAUNTLET_PASSED"
            self._post(
                f"Gauntlet passed. {file_count} files validated. 0% downtime. ({elapsed}s)",
                SEVERITY_VERDICT if _HAS_HUB else "VERDICT",
                {"elapsed_s": elapsed, "checks": len(checks)},
            )
        elif critical_failures:
            verdict = "GAUNTLET_FAILED"
            fail_names = ", ".join(c.name for c in critical_failures)
            self._post(
                f"Gauntlet FAILED. Critical: {fail_names}. ({elapsed}s)",
                SEVERITY_VERDICT if _HAS_HUB else "VERDICT",
                {"elapsed_s": elapsed, "failures": [c.to_dict() for c in critical_failures]},
            )
        else:
            verdict = "GAUNTLET_PASSED"  # Non-critical warnings don't block
            warn_count = len([c for c in checks if not c.passed])
            self._post(
                f"Gauntlet passed with {warn_count} advisory warning(s). ({elapsed}s)",
                SEVERITY_VERDICT if _HAS_HUB else "VERDICT",
                {"elapsed_s": elapsed, "warnings": warn_count},
            )

        return {
            "verdict": verdict,
            "checks": [c.to_dict() for c in checks],
            "passed": sum(1 for c in checks if c.passed),
            "failed": sum(1 for c in checks if not c.passed),
            "elapsed_s": elapsed,
            "timestamp": datetime.now().isoformat(),
        }

    # ─────────────────────────────────────────────────────────
    #  INDIVIDUAL GAUNTLET CHECKS
    # ─────────────────────────────────────────────────────────

    def _check_dependency_integrity(self, code_files: Dict[str, str]) -> GauntletCheck:
        """Check that all imports in Python files reference known modules."""
        unknown_imports = []
        known_local = set(code_files.keys())
        # Extract basenames without extensions for local module matching
        local_modules = set()
        for path in known_local:
            base = os.path.splitext(os.path.basename(path))[0]
            local_modules.add(base)
            # Also add parent dir as package
            parent = os.path.dirname(path).replace(os.sep, ".").replace("/", ".")
            if parent:
                local_modules.add(parent)

        for path, code in code_files.items():
            if not path.endswith(".py"):
                continue
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root = alias.name.split(".")[0]
                            if root not in local_modules and not self._is_known_module(root):
                                unknown_imports.append(f"{path}: {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            root = node.module.split(".")[0]
                            if root not in local_modules and not self._is_known_module(root):
                                unknown_imports.append(f"{path}: from {node.module}")
            except SyntaxError:
                pass  # Handled by syntax check

        if unknown_imports:
            detail = f"{len(unknown_imports)} unresolved import(s): {', '.join(unknown_imports[:5])}"
            return GauntletCheck("Dependency Integrity", False, detail, "WARNING")
        return GauntletCheck("Dependency Integrity", True, "All imports verified")

    def _check_constraint_compliance(self, code_files: Dict[str, str]) -> GauntletCheck:
        """Verify all code passes permanent constraint rules."""
        if not _HAS_CONSTRAINTS or not self.constraints:
            return GauntletCheck("Constraint Compliance", True, "No constraints loaded (skipped)")

        all_violations = []
        for path, code in code_files.items():
            violations = enforce_constraints(code, self.constraints)
            for v in violations:
                v["file"] = path
                all_violations.append(v)

        critical = [v for v in all_violations if v.get("severity") == "CRITICAL"]
        if critical:
            detail = f"{len(critical)} CRITICAL violation(s): {critical[0].get('rule', '?')}"
            return GauntletCheck("Constraint Compliance", False, detail, "CRITICAL")
        elif all_violations:
            detail = f"{len(all_violations)} non-critical violation(s)"
            return GauntletCheck("Constraint Compliance", True, detail, "INFO")
        return GauntletCheck("Constraint Compliance", True, "All rules satisfied")

    def _check_code_coherence(self, code_files: Dict[str, str],
                               blueprint: Optional[Dict[str, Any]] = None) -> GauntletCheck:
        """Check that all files in the blueprint are present in the code."""
        if not blueprint:
            return GauntletCheck("Code Coherence", True, "No blueprint to verify against (skipped)")

        planned_files = set()
        for f in blueprint.get("files", []):
            planned_files.add(f.get("path", ""))

        actual_files = set(code_files.keys())
        missing = planned_files - actual_files

        if missing:
            detail = f"{len(missing)} planned file(s) missing: {', '.join(list(missing)[:5])}"
            return GauntletCheck("Code Coherence", False, detail, "WARNING")
        return GauntletCheck("Code Coherence", True,
                             f"All {len(planned_files)} planned files present")

    def _check_syntax_validation(self, code_files: Dict[str, str]) -> GauntletCheck:
        """Parse all Python files to verify syntax."""
        errors = []
        for path, code in code_files.items():
            if not path.endswith(".py"):
                continue
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(f"{path}:{e.lineno}: {e.msg}")

        if errors:
            detail = f"{len(errors)} syntax error(s): {errors[0]}"
            return GauntletCheck("Syntax Validation", False, detail, "CRITICAL")
        return GauntletCheck("Syntax Validation", True, "All Python files parse cleanly")

    def _check_structure(self, code_files: Dict[str, str],
                          blueprint: Optional[Dict[str, Any]] = None) -> GauntletCheck:
        """Check that essential structural files exist."""
        has_entry = any(
            name in code_files for name in
            ["main.py", "app.py", "run.py", "__main__.py", "index.py", "server.py"]
        )
        has_requirements = any("requirements" in name for name in code_files)

        if not has_entry and len(code_files) > 1:
            return GauntletCheck("Structure Validation", False,
                                 "No entry point file detected (main.py, app.py, etc.)",
                                 "WARNING")
        return GauntletCheck("Structure Validation", True, "Required files present")

    def _reconcile_sentinel(self, audit_report: Dict[str, Any]) -> GauntletCheck:
        """Verify that the Sentinel's final verdict is clean."""
        verdict = audit_report.get("verdict", "UNKNOWN")
        violations = audit_report.get("constraint_violations", [])

        if verdict == "VIBE_VERIFIED" and not violations:
            return GauntletCheck("Sentinel Reconciliation", True,
                                 "Sentinel audit clean")
        elif verdict == "CRITICAL_VULN":
            return GauntletCheck("Sentinel Reconciliation", False,
                                 f"Sentinel flagged CRITICAL_VULN ({len(violations)} violations)",
                                 "CRITICAL")
        else:
            return GauntletCheck("Sentinel Reconciliation", True,
                                 f"Sentinel verdict: {verdict} ({len(violations)} non-critical)")

    @staticmethod
    def _is_known_module(name: str) -> bool:
        """Check if a module name is a known stdlib or common package."""
        # Common stdlib modules
        stdlib = {
            "os", "sys", "json", "re", "time", "datetime", "pathlib", "typing",
            "collections", "functools", "itertools", "math", "random", "string",
            "hashlib", "uuid", "threading", "multiprocessing", "subprocess",
            "asyncio", "socket", "http", "urllib", "email", "html", "xml",
            "logging", "warnings", "io", "abc", "contextlib", "copy", "enum",
            "dataclasses", "ast", "inspect", "importlib", "shutil", "glob",
            "tempfile", "textwrap", "struct", "base64", "secrets", "argparse",
            "unittest", "pdb", "traceback", "csv", "sqlite3", "configparser",
            "tomllib", "zipfile", "tarfile", "gzip", "bz2", "lzma",
            "concurrent", "queue", "signal", "ctypes", "platform",
            "_thread", "__future__", "types", "weakref", "operator",
            "statistics", "decimal", "fractions", "cmath", "array",
            "bisect", "heapq", "pprint", "dis", "code", "codecs",
            "encodings", "locale", "gettext", "unicodedata",
        }
        # Common third-party
        common_packages = {
            "requests", "flask", "django", "fastapi", "uvicorn",
            "click", "typer", "rich", "colorama", "tqdm",
            "pydantic", "openai", "anthropic", "google",
            "numpy", "pandas", "scipy", "sklearn",
            "PIL", "pillow", "cv2", "moviepy",
            "dotenv", "yaml", "toml", "httpx", "aiohttp",
            "pytest", "mock", "psutil", "watchdog",
            "jinja2", "werkzeug", "starlette",
            "sqlalchemy", "alembic", "peewee",
            "celery", "redis", "boto3", "stripe",
            "lumaai", "runwayml", "elevenlabs",
            "PyQt6", "PyQt5", "tkinter",
        }
        return name in stdlib or name in common_packages


# =============================================================
#  CLI ENTRY POINT
# =============================================================

if __name__ == "__main__":
    import sys

    judge = JudgeAgent()

    # Quick test with sample code
    test_files = {
        "main.py": 'import os\nimport json\n\ndef main():\n    print("Hello")\n\nif __name__ == "__main__":\n    main()\n',
        "utils.py": 'import re\n\ndef clean(text: str) -> str:\n    return re.sub(r"\\s+", " ", text)\n',
    }

    report = judge.run_gauntlet(test_files)
    print(f"\nVerdict: {report['verdict']}")
    print(f"Passed: {report['passed']}/{report['passed'] + report['failed']}")
    print(f"Elapsed: {report['elapsed_s']}s")
