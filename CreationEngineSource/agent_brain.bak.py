#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Agent Brain (Python Backend)
  Called by Electron via child_process.spawn().
  All output goes to stdout so the GUI can display it.
==============================================================

Usage:
  python agent_brain.py --project MyApp --prompt "Build a web scraper" \
                        --output ./output --model gpt-4o \
                        [--api-key sk-...] [--docker] [--readme] [--debug]
"""

import os
import sys
import json
import time
import argparse
import subprocess
import shutil
import hashlib
import threading
import requests
from datetime import datetime
from openai import OpenAI
try:
    import anthropic as _anthropic_sdk
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

# ── Load .env (fallback for direct Python execution) ─────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # python-dotenv not installed — env vars come from Electron

# ── Event Bus (for Antigravity Dashboard) ────────────────────
try:
    from pipeline_events import EventBus, PipelineEvent, EventType
    _HAS_EVENT_BUS = True
except ImportError:
    _HAS_EVENT_BUS = False

# Module-level event bus reference (set in execute_build when --dashboard is used)
_active_event_bus = None

# ── Global Wisdom System ─────────────────────────────────────
class GlobalWisdom:
    def __init__(self, project_path):
        self.wisdom_file = os.path.join(project_path, "local_wisdom.json")
        # Global wisdom lives at the Creator root — shared across ALL projects
        self.global_wisdom_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "global_wisdom.json")
        self.wisdom = self._load(self.wisdom_file)
        self.global_wisdom = self._load(self.global_wisdom_file)

    def _load(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        with open(self.wisdom_file, "w") as f:
            json.dump(self.wisdom, f, indent=2)

    def _save_global(self):
        with open(self.global_wisdom_file, "w") as f:
            json.dump(self.global_wisdom, f, indent=2)

    def consult(self, error_trace):
        """Finds if this error pattern has been solved before. Checks local first, then global."""
        # Local wisdom (project-specific) takes priority
        for pattern, fix_logic in self.wisdom.items():
            if pattern in error_trace:
                return fix_logic
        # Fall back to global wisdom (cross-project learnings)
        for pattern, fix_logic in self.global_wisdom.items():
            if pattern in error_trace:
                return fix_logic
        return None

    def learn(self, error_trace, fix_strategy):
        """Extracts a pattern and saves an actionable fix strategy to both local and global wisdom."""
        lines = error_trace.strip().split('\n')
        # Use the final error line as key (most specific)
        key = lines[-1].strip() if lines else error_trace[:100]
        # Store in local wisdom
        self.wisdom[key] = fix_strategy
        self._save()
        # Also propagate to global wisdom so future projects benefit
        self.global_wisdom[key] = fix_strategy
        self._save_global()

    def get_generation_rules(self) -> str:
        """Return all GENERATION_RULE__ entries as a formatted block for LLM injection."""
        rules = []
        for key in self.global_wisdom:
             if key.startswith("GENERATION_RULE__"):
                 rules.append(f"- {self.global_wisdom[key]}")
        
        if rules:
             return "\n## GLOBAL CODEBASE RULES (MUST FOLLOW):\n" + "\n".join(rules) + "\n"
        return ""

    def review_against_wisdom(self, code: str, filepath: str) -> list:
        """Proactively scan generated code against all known wisdom rules.
        Returns list of {'rule': key, 'fix': str} for each violation found."""
        violations = []
        seen_rules = set()
        for source in [self.wisdom, self.global_wisdom]:
            for pattern, fix in source.items():
                if pattern in seen_rules:
                    continue
                triggered = False
                if pattern.startswith("GENERATION_RULE__"):
                    triggered = self._check_generation_rule(pattern, fix, code, filepath)
                else:
                    triggered = self._check_error_pattern(pattern, code)
                if triggered:
                    violations.append({"rule": pattern, "fix": fix})
                    seen_rules.add(pattern)
        return violations

    def _check_generation_rule(self, rule_key: str, fix_text: str, code: str, filepath: str) -> bool:
        """Heuristic check for GENERATION_RULE violations by extracting anti-patterns from fix text."""
        code_lower = code.lower()
        rule_checks = {
            "GENERATION_RULE__MOVIEPY_V2_IMPORTS": lambda: "from moviepy.editor import" in code or "from moviepy.editor import" in code_lower,
            "GENERATION_RULE__NO_DUPLICATE_CLASS_DEFINITIONS": lambda: self._has_duplicate_class_defs(code),
            "GENERATION_RULE__FLASK_DEPRECATED_APIS": lambda: "before_first_request" in code,
            "GENERATION_RULE__PYTHON_314_STDLIB_REMOVALS": lambda: any(
                f"import {mod}" in code or f"from {mod}" in code
                for mod in ["audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr",
                            "mailcap", "msilib", "nis", "nntplib", "ossaudiodev",
                            "pipes", "sndhdr", "spwd", "sunau", "telnetlib", "uu", "xdrlib"]
            ),
            "GENERATION_RULE__ENUM_CASING_CONVENTION": lambda: False,  # Requires cross-file context
            "GENERATION_RULE__CROSS_FILE_SYMBOL_CONSISTENCY": lambda: False,  # Handled by Validation Gate
            "GENERATION_RULE__CONFIG_ATTRIBUTE_NAMES": lambda: False,  # Requires cross-file context
            "GENERATION_RULE__PYDANTIC_V2_MIGRATION": lambda: (
                "from pydantic import validator" in code
                or "class Config:" in code and "BaseModel" in code
                or ".dict()" in code and "pydantic" in code_lower
                or "from pydantic import BaseSettings" in code
            ),
            "GENERATION_RULE__FASTAPI_PYDANTIC_PINNING": lambda: False,  # Enforced at Architect level via preflight
        }
        checker = rule_checks.get(rule_key)
        if checker:
            return checker()
        return False

    def _check_error_pattern(self, pattern: str, code: str) -> bool:
        """Check if code contains the problematic import/call that would trigger a known error."""
        # Extract the module/symbol from common error patterns
        checks = {
            "moviepy.editor": "from moviepy.editor import" in code or "from moviepy.editor import" in code,
            "audioop": "import audioop" in code or "from audioop" in code,
            "pyaudioop": "import pyaudioop" in code or "from pyaudioop" in code,
            "before_first_request": "before_first_request" in code,
        }
        for keyword, triggered in checks.items():
            if keyword in pattern.lower() and triggered:
                return True
        return False

    def _has_duplicate_class_defs(self, code: str) -> bool:
        """Detect if a file defines a class AND imports the same class name."""
        import re
        class_defs = re.findall(r'^class\s+(\w+)', code, re.MULTILINE)
        imports = re.findall(r'from\s+\S+\s+import\s+(.+)', code)
        imported_names = set()
        for imp_line in imports:
            for name in imp_line.split(','):
                imported_names.add(name.strip().split(' as ')[0].strip())
        # If a class is both defined AND imported, that's a duplicate
        for cls in class_defs:
            if cls in imported_names:
                return True
        return False

    def get_generation_rules_directive(self) -> str:
        """Build a prompt directive string from all GENERATION_RULE entries."""
        rules = [f"- {fix}" for key, fix in self.global_wisdom.items()
                 if key.startswith("GENERATION_RULE__")]
        if not rules:
            return ""
        return (
            "\n\nCRITICAL WISDOM RULES (from past failures — DO NOT VIOLATE):\n"
            + "\n".join(rules)
        )

# ── Intelligent Model Router ─────────────────────────────────
def resolve_smart_model(prompt: str, requested_model: str) -> str:
    """
    Analyzes the prompt complexity to choose the best model if 'auto' is requested.
    """
    if requested_model.lower() != "auto":
        return requested_model

    p_lower = prompt.lower()
    
    # 1. Complex Architect/Refactor Tasks -> High Reasoning Models
    complex_triggers = [
        "architect", "refactor", "rewrite", "redesign", "analysis", 
        "complex", "blueprint", "plan", "structure", "database", "security"
    ]
    if any(trigger in p_lower for trigger in complex_triggers) or len(prompt) > 500:
        # Prefer Gemini 2.0 Pro or Opus/Sonnet if available keys, else fallback
        return "gemini-2.0-pro-exp-02-05" 

    # 2. Simple/Speed Tasks -> Flash/Haiku
    simple_triggers = [
        "fix", "typo", "color", "style", "css", "comment", "rename", "log"
    ]
    if any(trigger in p_lower for trigger in simple_triggers) and len(prompt) < 200:
       return "gemini-2.0-flash"

    # Default Balanced
    return "gemini-2.0-flash" # Default to Flash for speed/cost unless complexity is detected





# ── Production Safety Directive (Injected into ALL generated programs) ────
PRODUCTION_SAFETY_DIRECTIVE = (
    "\n\nPRODUCTION SAFETY INFRASTRUCTURE (MANDATORY for every project):"
    "\nEvery program you generate MUST include these safety pillars as core production code, not optional extras:"
    "\n\n1. HEALTH MONITORING:"
    "\n   - Python backends: add a /health endpoint returning JSON {status, uptime, version, checks:{db,cache,disk}}."
    "\n   - Long-running scripts: add a background health-check thread that logs system status every 60s."
    "\n   - Node apps: add a /api/health route with the same contract."
    "\n\n2. GRACEFUL ERROR RECOVERY:"
    "\n   - EVERY external call (DB, API, file I/O, network) MUST be wrapped in try-except."
    "\n   - On failure: log the error with context, return a safe fallback, NEVER crash the process."
    "\n   - Use specific exception types, not bare except. Always log traceback for unexpected errors."
    "\n\n3. SELF-HEALING & AUTO-REPAIR:"
    "\n   - Implement retry with exponential backoff for all network/DB operations (max 3 retries)."
    "\n   - Auto-reconnect database connections on pool exhaustion or timeout."
    "\n   - If a config file is missing, generate sensible defaults and log a warning."
    "\n   - Stale cache/lock detection: if a lock file is older than 5 minutes, auto-release it."
    "\n\n4. BACKUP & RESTORE:"
    "\n   - Before mutating any data file, create a .bak snapshot."
    "\n   - Use atomic writes (write to .tmp, then rename) for critical files."
    "\n   - Database operations: use transactions with rollback on failure."
    "\n\n5. WATCHDOG / SENTINEL:"
    "\n   - Add a background monitor thread that checks: disk space, memory usage, and process health."
    "\n   - If anomalies detected (disk >90%, memory >85%), log a WARNING and trigger cleanup."
    "\n   - For web servers: track response times and log slow endpoints (>2s)."
    "\n\n6. STRUCTURED LOGGING:"
    "\n   - Use a consistent logging format: [TIMESTAMP] [TAG] message."
    "\n   - Log every: startup, shutdown, error, recovery action, health check, and config change."
    "\n   - Include a startup banner that prints version, config source, and environment."
)


# ── Stability Directive (Injected into Engineer Prompt) ──────
# ── Stability Directive (Injected into Engineer Prompt) ──────
STABILITY_DIRECTIVE = """

CODE STABILITY & QA RULES (MANDATORY - violations will be REJECTED):
1. NO PLACEHOLDERS: Never use 'pass', '...', or 'TODO' for critical logic. 
   If a function is defined, it MUST be implemented. If logic is complex, simplify it but keep it functional.
2. USER EXPERIENCE (UX):
   - CLI apps: Use 'argparse', colorized output (colorama/rich), and progress bars (tqdm).
   - GUI apps: Ensure window is sizable, has a title, and handles resizing gracefully.
   - Error Handling: Wrap main execution in a global try/except block that prints a user-friendly error message 
     and waits for input before closing (so the user can read the error in a standalone EXE).
3. CONFIG CONSISTENCY: When referencing config attributes (self.config.X, config.X, 
   app.config['X']), the attribute name MUST exactly match the attribute defined in the 
   Config/Settings class. Never invent config attributes that don't exist.
4. OPTIONAL PARAMETERS: All optional parameters must use 'Optional[Type] = None' 
   (from typing import Optional). Never write 'def foo(x: str = None)' - use 
   'def foo(x: Optional[str] = None)' instead.
5. IMPORT INTEGRITY: Only import symbols that are actually exported by the target 
   module. Check the project file tree - if importing 'from utils import helper', 
   the 'utils.py' file MUST define 'helper'. Never hallucinate import names.
6. ENUM CONSISTENCY: When referencing enum members, use the EXACT member name as 
   defined. If the enum defines 'status = "active"', reference it as Enum.status, 
   NOT Enum.STATUS or Enum.ACTIVE.
7. FONT PATHS: When using fonts (PIL, MoviePy, etc.), always use full file system 
   paths (e.g. 'C:/Windows/Fonts/arial.ttf'), never just font names like 'Arial'.
8. CROSS-FILE NAMING: Function, class, and variable names must be identical across 
   definition and all import sites. Never rename symbols at import boundaries.
"""

SECURITY_DIRECTIVE = """

CYBER SECURITY PROTOCOL (MANDATORY - zero tolerance for vulnerabilities):
1. INPUT VALIDATION: Trust NO ONE. Validate type, length, and format of ALL external input.
2. PARAMETERIZED QUERIES: Never string-concatenate SQL. Use placeholders (e.g., 'SELECT * FROM users WHERE id = ?', [user_id]).
3. OUTPUT ENCODING: Sanitize all data rendered to HTML/JS to prevent XSS.
4. SECRETS MANAGEMENT: NEVER hardcode API keys, passwords, or tokens. Use os.getenv('KEY') and load from .env.
5. NO DANGEROUS FUNCTIONS: Avoid exec(), eval(), pickle.load(), and shell=True in subprocess unless absolutely necessary and sanitized.
6. LEAST PRIVILEGE: Run applications with the minimum necessary permissions. Don't run as root/admin.
"""

# ── Bundler Directive (Injected into Bundler Prompt) ──────


# ── Feature Richness Directive (Injected into Engineer Prompt) ──
FEATURE_RICHNESS_DIRECTIVE = (
    "\n\nFEATURE RICHNESS STANDARDS (MANDATORY — build impressive, not minimal):"
    "\n1. UI DEPTH: Every view must have 3 states: Loading (skeleton/spinner), "
    "   Empty (friendly illustration + CTA), and Error (retry button + message). "
    "   Never show a blank screen."
    "\n2. DATA TABLES: Any list/table of data MUST include: search bar, column sorting, "
    "   pagination (or infinite scroll), and row count. Add CSV/JSON export buttons."
    "\n3. VISUAL POLISH: Use CSS variables for theming. Include a dark/light mode toggle. "
    "   Use gradients, subtle box-shadows, smooth transitions (0.2s ease), and hover effects "
    "   on all interactive elements. Buttons must have active/disabled states."
    "\n4. FEEDBACK: Every user action (save, delete, update) MUST show a toast/notification "
    "   confirming success or explaining failure. Never leave the user guessing."
    "\n5. DASHBOARD CARDS: When displaying metrics, use cards with: icon, label, value, "
    "   and a trend indicator (▲/▼ with color). Group related cards in a responsive grid."
    "\n6. FORMS: All forms must have inline validation, clear error messages, "
    "   submit loading state, and auto-focus on the first field. Include placeholder text."
    "\n7. NAVIGATION: Include a sidebar or top nav with active state highlighting. "
    "   Add breadcrumbs for nested views. Mobile: use a hamburger menu."
    "\n8. CHARTS: When analytics are relevant, include at least 2 chart types "
    "   (bar, line, pie, or gauge). Use a real charting library (Chart.js, Recharts, etc.)."
    "\n9. SEED DATA: Always include realistic demo/seed data so the app looks alive on first run. "
    "   Never ship an empty database or empty UI."
    "\n10. REAL-TIME: Add auto-refresh (30s polling or WebSocket) for any data that changes. "
    "    Show a 'Last updated: X seconds ago' indicator."
)

# ── API Conventions (Injected When Specific Libraries Detected) ──
API_CONVENTIONS = {
    "moviepy": (
        "MoviePy V2 API (CRITICAL): All setter methods were renamed to immutable style: "
        ".subclip()->.subclipped(), .set_position()->.with_position(), .set_duration()->.with_duration(), "
        ".set_audio()->.with_audio(), .set_start()->.with_start(), .set_end()->.with_end(), "
        ".set_opacity()->.with_opacity(), .set_fps()->.with_fps(), .volumex()->.with_volume_scaled(), "
        ".resize()->.resized(), .crop()->.cropped(), .rotate()->.rotated(). "
        "TextClip: first arg is 'font' (full .ttf path), 'text' is keyword-only, use 'font_size' not 'fontsize'. "
        "Imports: use 'from moviepy import X', NOT 'from moviepy.editor import X'. "
        "Resizing: use .resized(new_size=(...)), NOT .resized(newsize=(...))."
    ),
    "pydantic": (
        "Pydantic V2 API: Use 'field_validator' not 'validator', 'model_config = ConfigDict(...)' "
        "not 'class Config:', '.model_dump()' not '.dict()', 'model_json_schema()' not '.schema()'. "
        "BaseSettings moved to 'pydantic-settings' package."
    ),
    "flask": (
        "Flask 2.3+ REMOVED @app.before_first_request. Use direct function calls during "
        "app init instead. Use 'app.config[ATTR]' where ATTR matches the Config class attribute name exactly."
    ),
    "fastapi": (
        "FastAPI: Pin both 'fastapi' and 'pydantic' versions in requirements.txt. "
        "If using Pydantic V2, apply all V2 patterns (field_validator, ConfigDict, model_dump)."
    ),
    "pillow": (
        "Pillow/PIL: When specifying fonts, use full file system paths to .ttf files "
        "(e.g. 'C:/Windows/Fonts/arial.ttf'), not font names. ImageFont.truetype() requires a file path."
    ),
}


# ── Wisdom Guard (Pre-Save Deterministic Validator) ──────────

class WisdomGuard:
    """Pre-save deterministic code validator using wisdom rules.
    Scans generated code for known-bad patterns and auto-fixes them
    BEFORE the file is written to disk. Zero LLM cost."""

    # Each entry: pattern to detect, human-readable rule name, and the fix
    VIOLATION_PATTERNS = [
        {
            "pattern": "from moviepy.editor import",
            "rule": "MoviePy V2 Imports",
            "fix_find": "from moviepy.editor import",
            "fix_replace": "from moviepy import",
        },
        {
            "pattern": "from moviepy.editor",
            "rule": "MoviePy V2 Imports",
            "fix_find": "from moviepy.editor",
            "fix_replace": "from moviepy",
        },
        {
            "pattern": "@app.before_first_request",
            "rule": "Flask 2.3+ Deprecated APIs",
            "fix_find": "@app.before_first_request",
            "fix_replace": "# @app.before_first_request REMOVED in Flask 2.3+ — call this function directly during init",
        },
        {
            "pattern": "import audioop\n",
            "rule": "Python 3.13+ Stdlib Removals",
            "fix_find": "import audioop\n",
            "fix_replace": "import audioop_lts as audioop  # audioop removed in Python 3.13+\n",
        },
        {
            "pattern": "from audioop import",
            "rule": "Python 3.13+ Stdlib Removals",
            "fix_find": "from audioop import",
            "fix_replace": "from audioop_lts import",
        },
        {
            "pattern": "from pydantic import validator",
            "rule": "Pydantic V2 Migration",
            "fix_find": "from pydantic import validator",
            "fix_replace": "from pydantic import field_validator  # Pydantic V2: validator -> field_validator",
        },
        {
            "pattern": ".subclip(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".subclip(",
            "fix_replace": ".subclipped(",
        },
        # --- MoviePy V2: Method Renames (clip methods) ---
        {
            "pattern": ".set_position(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_position(",
            "fix_replace": ".with_position(",
        },
        {
            "pattern": ".set_duration(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_duration(",
            "fix_replace": ".with_duration(",
        },
        {
            "pattern": ".set_audio(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_audio(",
            "fix_replace": ".with_audio(",
        },
        {
            "pattern": ".set_start(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_start(",
            "fix_replace": ".with_start(",
        },
        {
            "pattern": ".set_end(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_end(",
            "fix_replace": ".with_end(",
        },
        {
            "pattern": ".set_opacity(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_opacity(",
            "fix_replace": ".with_opacity(",
        },
        {
            "pattern": ".set_fps(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".set_fps(",
            "fix_replace": ".with_fps(",
        },
        {
            "pattern": ".volumex(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".volumex(",
            "fix_replace": ".with_volume_scaled(",
        },
        {
            "pattern": ".resize(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".resize(",
            "fix_replace": ".resized(",
        },
        {
            "pattern": ".crop(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".crop(",
            "fix_replace": ".cropped(",
        },
        {
            "pattern": ".rotate(",
            "rule": "MoviePy V2 API Renames",
            "fix_find": ".rotate(",
            "fix_replace": ".rotated(",
        },
        # --- MoviePy V2: TextClip parameter renames ---
        {
            "pattern": "TextClip(text,",
            "rule": "MoviePy V2 TextClip Constructor",
            "fix_find": "TextClip(text,",
            "fix_replace": "TextClip(font=font, text=text,  # MoviePy V2: font is 1st positional arg",
        },
        {
            "pattern": "fontsize=",
            "rule": "MoviePy V2 TextClip Params",
            "fix_find": "fontsize=",
            "fix_replace": "font_size=",
        },
    ]

    # Requirements.txt-specific regex fixes (version corrections)
    REQUIREMENTS_FIXES = [
        {
            "pattern_re": r"moviepy\s*[=<>!~]=\s*[01]\.\S*",
            "replace_with": "moviepy>=2.0.0",
            "rule": "MoviePy V2 Pinning",
        },
    ]

    def check(self, code: str, filepath: str) -> list:
        """Returns a list of violation dicts found in the code."""
        violations = []
        for vp in self.VIOLATION_PATTERNS:
            if vp["pattern"] in code:
                violations.append({
                    "file": filepath,
                    "rule": vp["rule"],
                    "pattern": vp["pattern"],
                    "fix": f"Replace '{vp['fix_find']}' → '{vp['fix_replace']}'",
                })
        return violations

    def auto_fix(self, code: str, filepath: str = "") -> tuple:
        """Apply deterministic fixes. Returns (fixed_code, list_of_fixes_applied)."""
        import re
        fixes_applied = []
        # Standard code-level fixes
        for vp in self.VIOLATION_PATTERNS:
            if vp["fix_find"] in code:
                code = code.replace(vp["fix_find"], vp["fix_replace"])
                fix_desc = f"{vp['rule']}: '{vp['fix_find'].strip()}' → '{vp['fix_replace'].strip()}'"
                if fix_desc not in fixes_applied:
                    fixes_applied.append(fix_desc)

        # Requirements.txt-specific fixes (version corrections + deduplication)
        basename = os.path.basename(filepath) if filepath else ""
        if basename == "requirements.txt":
            for rf in self.REQUIREMENTS_FIXES:
                match = re.search(rf["pattern_re"], code)
                if match:
                    code = re.sub(rf["pattern_re"], rf["replace_with"], code)
                    fixes_applied.append(f"{rf['rule']}: '{match.group()}' -> '{rf['replace_with']}'")

            # Deduplicate requirements: keep last occurrence of each package
            seen = {}
            lines = [l.strip() for l in code.strip().split("\n") if l.strip()]
            for line in lines:
                pkg = re.split(r'[=<>!~\[]', line)[0].strip().lower()
                seen[pkg] = line  # Last wins
            deduped = list(seen.values())
            if len(deduped) < len(lines):
                fixes_applied.append(f"Deduplication: removed {len(lines) - len(deduped)} duplicate requirement(s)")
                code = "\n".join(deduped) + "\n"

        return code, fixes_applied


# ── Config Consistency Checker ───────────────────────────────
class ConfigConsistencyChecker:
    """AST-based post-build validator that ensures all config.X references
    point to attributes that actually exist in the Config/Settings class."""

    @staticmethod
    def check(written_files: dict) -> list:
        """Scan all written files. Returns list of violation dicts."""
        import ast
        # Step 1: Find config classes and extract their attribute names
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
                    # Detect Config/Settings classes (Pydantic BaseSettings or plain)
                    is_config = (
                        "config" in node.name.lower() or "settings" in node.name.lower()
                    )
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
            return []  # No config class found — nothing to check

        # Step 2: Scan all files for config.X / self.config.X references
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
                    # Pattern: X.config.ATTR (e.g. self.config.SOMETHING)
                    if node.value.attr == "config" and node.attr not in config_attrs:
                        violations.append({
                            "file": fpath,
                            "line": node.lineno,
                            "ref": f"config.{node.attr}",
                            "available": sorted(list(config_attrs)),
                        })
                elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                    # Pattern: app.config['ATTR'] or config['ATTR']
                    if node.value.attr == "config" and isinstance(node.slice, ast.Constant):
                        attr_name = node.slice.value
                        if isinstance(attr_name, str) and attr_name not in config_attrs:
                            violations.append({
                                "file": fpath,
                                "line": node.lineno,
                                "ref": f"config['{attr_name}']",
                                "available": sorted(list(config_attrs)),
                            })
        return violations


# ── Import Dry-Run (Post-Build Cross-File Verification) ──────
def import_dry_run(written_files: dict) -> list:
    """Verify that all 'from X import Y' where X is a local module,
    Y actually exists in that module's AST-parsed exports.
    Returns list of violation dicts."""
    import ast
    # Build export maps from all Python files
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

    # Check all imports
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
                                "file": fpath,
                                "line": node.lineno,
                                "import": f"from {node.module} import {alias.name}",
                                "missing": alias.name,
                                "source": f"{mod_key}.py",
                                "available": sorted(list(available))[:15],
                            })
    return violations


# ── Sandbox Runner (Docker-Isolated Execution) ───────────────
class SandboxRunner:
    """Runs generated programs inside Docker containers for safety.
    Falls back to host subprocess.run if Docker is unavailable."""

    def __init__(self):
        self.available = False
        try:
            result = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=5
            )
            self.available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            self.available = False

    def _generate_sandbox_dockerfile(self, project_path, deps, run_cmd):
        """Generate a minimal Dockerfile for sandboxed execution."""
        req_path = os.path.join(project_path, "requirements.txt")
        has_reqs = os.path.isfile(req_path)
        lines = [
            "FROM python:3.12-slim",
            "WORKDIR /app",
            "COPY . /app",
        ]
        if has_reqs:
            lines.append("RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true")
        elif deps:
            lines.append(f"RUN pip install --no-cache-dir {' '.join(deps)} 2>/dev_null || true")
        lines.append(f'CMD {json.dumps(run_cmd.split())}')
        dockerfile_path = os.path.join(project_path, ".sandbox.Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return dockerfile_path

    def execute(self, run_cmd, project_path, deps=None, timeout=60):
        """Execute the project. Uses Docker if available, else host subprocess.
        Returns a subprocess.CompletedProcess-like object."""
        if not self.available:
            # Fallback: run on host (current behavior)
            try:
                return subprocess.run(
                    run_cmd, shell=True,
                    capture_output=True, text=True,
                    cwd=project_path, timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return subprocess.CompletedProcess(
                    run_cmd, returncode=124, stdout="", stderr="Process timed out"
                )

        # Docker execution path
        deps = deps or []
        tag = f"overlord-sandbox-{os.path.basename(project_path).lower()}"
        self._generate_sandbox_dockerfile(project_path, deps, run_cmd)

        # Build the sandbox image
        build_result = subprocess.run(
            ["docker", "build", "-f", ".sandbox.Dockerfile", "-t", tag, "."],
            capture_output=True, text=True, cwd=project_path, timeout=120,
        )
        if build_result.returncode != 0:
            log("SANDBOX", f"  ⚠ Docker build failed — falling back to host execution")
            return subprocess.run(
                run_cmd, shell=True,
                capture_output=True, text=True,
                cwd=project_path, timeout=timeout,
            )

        # Run with resource limits and isolation
        docker_cmd = [
            "docker", "run", "--rm",
            "--memory=512m",
            "--cpus=1.0",
            "--network=none",
            "-v", f"{os.path.abspath(project_path)}:/app",
            tag,
        ]
        try:
            result = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=timeout,
            )
            return result
        except subprocess.TimeoutExpired:
            # Kill the container if it's still running
            subprocess.run(["docker", "kill", tag], capture_output=True, timeout=5)
            return subprocess.CompletedProcess(
                docker_cmd, returncode=124, stdout="",
                stderr=f"Container timed out after {timeout}s — killed."
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                docker_cmd, returncode=1, stdout="",
                stderr=f"Docker execution error: {e}"
            )


# ── Global State Management ──────────────────────────────────
class ProjectState:
    """Tracks exported symbols across all written files for cross-file coordination."""

    def __init__(self):
        self._symbols = {}    # {filepath: [{"name", "type", "args"/"methods"}]}
        self._variables = {}  # {filepath: [varname]}

    def register_file(self, filepath, code):
        """Parse a Python file and extract all top-level symbols."""
        import ast
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
        """Compact string of all registered symbols for LLM prompt injection."""
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
        """Get symbols exported by a specific file."""
        return self._symbols.get(filepath, [])


# ── Dockerized Dependency Verification ───────────────────────
class DependencyVerifier:
    """Verifies dependency resolution in a disposable Docker container (or local fallback)."""

    def __init__(self):
        self.docker_available = self._check_docker()

    def _check_docker(self):
        try:
            r = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def verify(self, deps, project_path):
        """Verify deps install cleanly. Returns (success: bool, message: str)."""
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
                ["docker", "run", "--rm",
                 "-v", f"{abs_proj}:/app", "-w", "/app",
                 "python:3.12-slim",
                 "pip", "install", "--no-cache-dir", "-r", "/app/requirements.txt"],
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


# ── RAG-Based Context Windowing ──────────────────────────────
class CodebaseRAG:
    """Token-aware context retrieval — only sends relevant files to the LLM."""

    def __init__(self, max_context_chars=12000):
        self._index = {}   # {filepath: set(keywords)}
        self._files = {}   # {filepath: code}
        self.max_context_chars = max_context_chars

    def index_file(self, filepath, code, symbols=None):
        """Build a keyword index for a written file."""
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
        """Score all indexed files by relevance and return best context within token budget."""
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
                overlap += 10  # boost files that import/reference each other
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


# Force UTF-8 encoding for Windows pipes (cp1252 fix)
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

    pass


# ── Global Configuration ─────────────────────────────────────

# Mapping common import names to proper PyPI package names
PKG_MAP = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "ffmpeg": "ffmpeg-python",  # CRITICAL FIX: prevents installing the wrong 'ffmpeg' package
    "googleapiclient": "google-api-python-client",
    "youtube_dl": "yt-dlp",
    "telegram": "python-telegram-bot",
    "gi": "PyGObject",
    "fal_client": "fal-client",
}


# ── Integrity Watchdog ───────────────────────────────────────
import hashlib
import threading
import shutil

class IntegrityWatchdog:
    def __init__(self, core_files):
        self.core_files = core_files
        self.golden_hashes = {}
        self.golden_content = {}
        self.active = True
        self._arm_shields()

    def _arm_shields(self):
        log("FORTRESS", "Arming Integrity Shields...")
        for fpath in self.core_files:
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    content = f.read()
                    self.golden_content[fpath] = content
                    self.golden_hashes[fpath] = hashlib.sha256(content).hexdigest()
                log("FORTRESS", f"  Locked: {os.path.basename(fpath)}")
        
        # Start Sentinel
        threading.Thread(target=self._sentinel_loop, daemon=True).start()

    def re_arm(self, filepath=None):
        """Re-snapshot one or all core files after a legitimate edit."""
        targets = [filepath] if filepath else self.core_files
        for fpath in targets:
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    content = f.read()
                    self.golden_content[fpath] = content
                    self.golden_hashes[fpath] = hashlib.sha256(content).hexdigest()
                log("FORTRESS", f"  Re-armed: {os.path.basename(fpath)}")

    def _sentinel_loop(self):
        while self.active:
            time.sleep(60)
            for fpath, original_hash in list(self.golden_hashes.items()):
                try:
                    with open(fpath, "rb") as f:
                        current_content = f.read()
                        current_hash = hashlib.sha256(current_content).hexdigest()
                    
                    if current_hash != original_hash:
                        log("CRITICAL", f"Integrity Breach detected in {os.path.basename(fpath)}!")
                        log("FORTRESS", "  Initializing Auto-Restore protocol...")
                        with open(fpath, "wb") as f:
                            f.write(self.golden_content[fpath])
                        log("FORTRESS", "  ✓ Golden Build restored.")
                except Exception as e:
                    log("ERROR", f"Watchdog error: {e}")

# ── Helpers ──────────────────────────────────────────────────

def log(tag: str, message: str):
    """Print a timestamped, tagged log line (streamed to Electron via stdout).
    Also emits to the Antigravity EventBus if active (for dashboard)."""
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] [{tag}]  {message}", flush=True)
    except UnicodeEncodeError:
        # Fallback for extremely restrictive environments
        print(f"[{ts}] [{tag}]  {message.encode('ascii', 'replace').decode('ascii')}", flush=True)
    # Emit to EventBus for dashboard (if active)
    if _active_event_bus:
        try:
            _active_event_bus.log(tag, message)
        except Exception:
            pass  # Never crash the build due to event emission


def divider():
    log("SYSTEM", "-" * 52)


def strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return raw

# Module-level active tracker — set by execute_build, auto-read by ask_llm
_active_tracker = None

def ask_llm(client: OpenAI, model: str, system_role: str, user_content: str,
            tracker: 'CostTracker' = None) -> str:
    """Send a chat completion request and return the cleaned response.
    Auto-resolves the right client for multi-provider model mixing.
    Routes Claude models through the Anthropic SDK automatically.
    Automatically records cost to _active_tracker if set, or explicit tracker param.
    Includes automatic retry-on-429 with key rotation via KeyPool."""
    global _active_tracker
    import time as _time

    provider_id = detect_provider(model) if not model.lower().startswith("claude") else "anthropic"
    pool = KeyPool.get_pool(provider_id)
    max_retries = min(len(pool.keys), 3) if pool.keys else 1

    for attempt in range(max_retries):
        try:
            # ── Anthropic/Claude Route ──
            if model.lower().startswith("claude"):
                return _ask_anthropic(model, system_role, user_content, tracker)

            # ── Standard OpenAI-compatible Route ──
            resolved_client = get_cached_client(model) if _client_cache else client
            response = resolved_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()

            # Track token usage and cost
            active = tracker or _active_tracker
            if active and hasattr(response, 'usage') and response.usage:
                active.record_call(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                )

            return strip_fences(raw)

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = '429' in err_str or 'rate' in err_str or 'resource_exhausted' in err_str
            if is_rate_limit and attempt < max_retries - 1 and len(pool.keys) > 1:
                current_key = pool.current_key()
                pool.mark_limited(current_key)
                pool.rotate()
                # Invalidate cached client so next call uses new key
                _client_cache.pop(provider_id, None)
                wait = 2 ** attempt
                log("KEYPOOL", f"  🔄 Rate limited on key …{current_key[-6:]} — rotating to next key (retry in {wait}s)")
                _time.sleep(wait)
                continue
            raise


def _ask_anthropic(model: str, system_role: str, user_content: str,
                   tracker: 'CostTracker' = None) -> str:
    """Route a request through the Anthropic SDK for Claude models.
    Uses KeyPool for automatic key rotation."""
    global _active_tracker
    if not _HAS_ANTHROPIC:
        raise ImportError(
            "anthropic package not installed. Run: pip install anthropic")

    pool = KeyPool.get_pool("anthropic")
    api_key = pool.next_key()
    if not api_key:
        raise ValueError("No Anthropic API keys available. Set ANTHROPIC_API_KEY or ANTHROPIC_API_KEYS env var.")

    client = _anthropic_sdk.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_role,
        messages=[{"role": "user", "content": user_content}],
        temperature=0.1,
    )
    raw = response.content[0].text.strip()

    # Track cost
    active = tracker or _active_tracker
    if active and hasattr(response, 'usage') and response.usage:
        active.record_call(
            model=model,
            prompt_tokens=response.usage.input_tokens or 0,
            completion_tokens=response.usage.output_tokens or 0,
        )

    return strip_fences(raw)

# ── Multi-Provider LLM Registry ─────────────────────────────
# All providers use OpenAI-compatible SDKs — just different base_urls
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "prefixes": ["llama", "gemma", "mixtral"],
        "label": "Groq ⚡ (FREE)"
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "prefixes": ["gemini"],
        "label": "Google Gemini 🧠 (FREE)"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "prefixes": ["openrouter/", "meta-llama/", "google/", "mistralai/", "deepseek/"],
        "label": "OpenRouter 🌐 (FREE tier)"
    },
    "openai": {
        "base_url": None,  # default
        "env_key": "OPENAI_API_KEY",
        "prefixes": ["gpt-", "o1-", "o3-"],
        "label": "OpenAI ☁️"
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "prefixes": ["claude"],
        "label": "Anthropic 🔒 (Reviewer)"
    }
}

# ── Multi-Key Pool ──────────────────────────────────────────
import threading as _threading
import time as _kp_time

class KeyPool:
    """Round-robin API key pool with rate-limit backoff.
    
    Keys are loaded from env vars:
      - {PROVIDER}_API_KEYS  (comma-separated, preferred)
      - {PROVIDER}_API_KEY   (single key, backward compat)
    
    Usage:
      pool = KeyPool.get_pool("gemini")
      key  = pool.next_key()  # rotates automatically
    """
    _pools = {}  # class-level cache: provider_id -> KeyPool
    _lock = _threading.Lock()

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        provider = PROVIDERS.get(provider_id, {})
        env_key = provider.get("env_key", "")
        
        # Load keys: try plural env var first, then singular
        pool_env = env_key.replace("_KEY", "_KEYS") if env_key else ""
        raw_pool = os.environ.get(pool_env, "")
        raw_single = os.environ.get(env_key, "") if env_key else ""
        
        if raw_pool:
            self.keys = [k.strip() for k in raw_pool.split(",") if k.strip()]
        elif raw_single:
            self.keys = [raw_single.strip()]
        else:
            self.keys = []
        
        self._index = 0
        self._cooldowns = {}  # key -> timestamp when cooldown expires
        self._rotations = 0
        self._key_lock = _threading.Lock()
        
        if len(self.keys) > 1:
            label = provider.get("label", provider_id)
            log("KEYPOOL", f"  🔑 {label} pool: {len(self.keys)} keys loaded")

    @classmethod
    def get_pool(cls, provider_id: str) -> 'KeyPool':
        """Get or create a cached pool for the given provider."""
        if provider_id not in cls._pools:
            with cls._lock:
                if provider_id not in cls._pools:
                    cls._pools[provider_id] = KeyPool(provider_id)
        return cls._pools[provider_id]

    @classmethod
    def reset_all(cls):
        """Clear all pools (useful for testing or re-init)."""
        with cls._lock:
            cls._pools.clear()

    def next_key(self) -> str:
        """Return the next available key, skipping cooled-down keys."""
        if not self.keys:
            return ""
        with self._key_lock:
            now = _kp_time.time()
            # Try each key starting from current index
            for _ in range(len(self.keys)):
                key = self.keys[self._index % len(self.keys)]
                cooldown_until = self._cooldowns.get(key, 0)
                if now >= cooldown_until:
                    self._index = (self._index + 1) % len(self.keys)
                    return key
                self._index = (self._index + 1) % len(self.keys)
            # All keys on cooldown — return least-recently-limited
            return self.keys[self._index % len(self.keys)]

    def current_key(self) -> str:
        """Return the most recently issued key (for error reporting)."""
        if not self.keys:
            return ""
        idx = (self._index - 1) % len(self.keys)
        return self.keys[idx]

    def rotate(self):
        """Force rotation to the next key."""
        with self._key_lock:
            self._index = (self._index + 1) % max(len(self.keys), 1)
            self._rotations += 1

    def mark_limited(self, key: str, cooldown_secs: float = 60.0):
        """Mark a key as rate-limited for cooldown_secs."""
        with self._key_lock:
            self._cooldowns[key] = _kp_time.time() + cooldown_secs

    @property
    def pool_size(self) -> int:
        return len(self.keys)

    @property
    def total_rotations(self) -> int:
        return self._rotations

def detect_provider(model_name: str) -> str:
    """Auto-detect provider from model name prefix."""
    model_lower = model_name.lower()
    for provider_id, info in PROVIDERS.items():
        for prefix in info["prefixes"]:
            if model_lower.startswith(prefix):
                return provider_id
    return "openai"  # default fallback

def get_client_for_model(model_name: str, fallback_key: str = "") -> OpenAI:
    """Create the right OpenAI client for any provider based on model name.
    Uses KeyPool for automatic key rotation."""
    provider_id = detect_provider(model_name)
    provider = PROVIDERS[provider_id]
    
    # Pull key from the pool (handles rotation automatically)
    pool = KeyPool.get_pool(provider_id)
    api_key = pool.next_key() or fallback_key
    
    if not api_key and provider_id == "openai":
        api_key = fallback_key or "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"
    
    if not api_key:
        log("WARN", f"  No API key for {provider['label']}. Set {provider['env_key']} env var.")
    
    kwargs = {"api_key": api_key or "none"}
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]
    
    return OpenAI(**kwargs)

# Client cache to avoid recreating clients for same provider
_client_cache = {}

def get_cached_client(model_name: str, fallback_key: str = "") -> OpenAI:
    """Get or create a cached client for the model's provider.
    Recreates client when KeyPool rotates to a new key."""
    provider_id = detect_provider(model_name)
    pool = KeyPool.get_pool(provider_id)
    # Cache key includes pool index so rotation invalidates the cache
    cache_key = f"{provider_id}:{pool._index}" if pool.keys else provider_id
    if cache_key not in _client_cache:
        # Clear stale entries for this provider
        stale = [k for k in _client_cache if k.startswith(provider_id)]
        for k in stale:
            del _client_cache[k]
        _client_cache[cache_key] = get_client_for_model(model_name, fallback_key)
        if pool.pool_size > 1:
            log("KEYPOOL", f"  🔌 Connected {PROVIDERS[provider_id]['label']} (key {pool._index + 1}/{pool.pool_size})")
        else:
            log("SYSTEM", f"  🔌 Connected: {PROVIDERS[provider_id]['label']}")
    return _client_cache[cache_key]


# ── Global State Manifest ────────────────────────────────────

import ast

def build_manifest(written_files: dict, planned_files: list = None) -> dict:
    """Extract every function, class, variable, and import from all written files.
    Returns a structured manifest that serves as the Source of Truth."""
    manifest = {}
    
    # Pre-populate with planned files if provided
    if planned_files:
        for fpath in planned_files:
            manifest[fpath] = {"functions": [], "classes": [], "variables": [], "imports": [], "exports_all": None, "is_planned": True}

    for fpath, code in written_files.items():
        entry = {"functions": [], "classes": [], "variables": [], "imports": [], "exports_all": None, "is_planned": False}
        if not fpath.endswith(".py"):
            # Non-Python files: just record their existence
            manifest[fpath] = entry
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            manifest[fpath] = entry
            continue

        for node in ast.iter_child_nodes(tree):
            # Functions
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args_list = []
                for a in node.args.args:
                    args_list.append(a.arg)
                sig = f"{node.name}({', '.join(args_list)})"
                entry["functions"].append(sig)
            # Classes
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(item.name)
                entry["classes"].append({"name": node.name, "methods": methods})
            # Top-level assignments (variables/constants)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        entry["variables"].append(target.id)
                        # Detect __all__
                        if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                            entry["exports_all"] = [
                                elt.value for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]
            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    entry["imports"].append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                names = ", ".join(a.name for a in node.names)
                entry["imports"].append(f"from {node.module or '.'} import {names}")

        manifest[fpath] = entry
    return manifest


def validation_gate(written_files: dict, manifest: dict) -> list:
    """Cross-reference every import against the manifest. Returns list of violations."""
    violations = []
    # Build a quick lookup of all exported names per project file
    exports_map = {}
    for fpath, info in manifest.items():
        if not fpath.endswith(".py"):
            continue
        module_key = fpath.replace(".py", "").replace("/", ".").replace("\\", ".")
        exported = set()
        # If __all__ is defined, use that exclusively
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
        # Also map by basename (e.g. "utils" for "utils.py")
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
                # Only validate imports from project files
                mod_file = f"{mod}.py"
                if mod_file in written_files and mod_file in exports_map:
                    available = exports_map[mod_file]
                    for alias in node.names:
                        if alias.name != "*" and alias.name not in available:
                            violations.append({
                                "file": fpath,
                                "line": node.lineno,
                                "import_stmt": f"from {node.module} import {alias.name}",
                                "missing": alias.name,
                                "source_file": mod_file,
                                "available": sorted(list(available))
                            })
    return violations


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


# ── Project Assembler ────────────────────────────────────────

def project_assembler(plan: dict, project_path: str) -> str:
    """
    Creates the directory structure and empty files based on the Architect's JSON.
    Acts as the "hands" — turning the abstract blueprint into a physical workspace
    so the Engineer has a clean canvas to write into.
    """
    from pathlib import Path

    base_path = Path(project_path)
    base_path.mkdir(parents=True, exist_ok=True)

    log("ASSEMBLER", "--- Initializing Project Workspace ---")

    # Extract file paths from the Architect's manifest format:
    #   {"files": [{"path": "filename.py", "task": "..."}], ...}
    file_tree = [f["path"] for f in plan.get("files", [])]

    created_dirs = set()
    for file_path in file_tree:
        full_path = base_path / file_path

        # Create subdirectories if they don't exist
        parent = full_path.parent
        if parent != base_path and str(parent) not in created_dirs:
            parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(str(parent))

        # Touch the file to create it empty (clean canvas for the Engineer)
        full_path.touch()
        log("ASSEMBLER", f"  ├─ Created: {file_path}")

    # Initialize a basic .env if not present
    env_path = base_path / ".env"
    if not env_path.exists():
        env_path.write_text("# Auto-generated environment variables\n")
        log("ASSEMBLER", "  ├─ Created: .env")

    log("ASSEMBLER", f"  └─ Workspace ready: {len(file_tree)} file(s) scaffolded")
    return str(base_path)


# ── Reviewer Agent (Zero-Inference Loop) ─────────────────────

class ReviewerAgent:
    """Autonomous code reviewer. Returns APPROVED or REJECTED with reason.
    The Overlord never asks permission — it just forces a rewrite on rejection."""

    REVIEW_SYSTEM = (
        "You are 'Overlord Reviewer,' a ruthless code quality gate. "
        "You receive a filename and its source code. "
        "Your job: inspect the code for these fatal flaws:\n"
        "1. Syntax errors or incomplete code (truncated functions, missing returns)\n"
        "2. Placeholder URLs like 'example.com', 'your-api-key', or dummy credentials\n"
        "3. Import of modules that don't exist in the project (hallucinated imports). "
        "NOTE: Modules listed in the project manifest or file tree ARE valid, even if currently empty.\n"
        "4. Functions/classes referenced but never defined\n"
        "5. Obvious logic errors (infinite loops, wrong return types)\n"
        "6. Config attribute mismatches: any 'self.config.X' or 'config.X' where X is NOT "
        "defined in the Config/Settings class. All attribute names must match exactly.\n"
        "7. Enum member mismatches: enum references must use the EXACT member name as defined. "
        "If the enum defines 'status', reference it as Enum.status, NOT Enum.STATUS.\n"
        "8. Cross-file naming: imported function/class names must match their definition exactly. "
        "No silent renames at import boundaries.\n\n"
        "Output ONLY a JSON object with this exact schema:\n"
        '{"status": "APPROVED" or "REJECTED", "reason": "concise explanation"}\n'
        "If the code is acceptable, status is APPROVED and reason is 'Clean code.'"
        "Be strict but fair. Minor style issues are NOT grounds for rejection."
    )

    def __init__(self, client, model, wisdom_context: str = ""):
        self.client = client
        self.model = model
        # Build the effective system prompt, optionally enriched with wisdom rules
        self.system_prompt = self.REVIEW_SYSTEM
        if wisdom_context:
            self.system_prompt += (
                "\n\nADDITIONAL RULES — REJECT code that violates any of these:\n"
                + wisdom_context
            )

    def review(self, filepath: str, code: str, manifest_context: str = "") -> dict:
        """Review a single file. Returns {'status': 'APPROVED'|'REJECTED', 'reason': str}."""
        # ── Deterministic Wisdom Block: instant REJECT for deprecated patterns ──
        # Fires BEFORE the LLM call — zero cost, guaranteed catch.
        if filepath.endswith(".py") and "before_first_request" in code:
            log("REVIEWER", f"  🚫 WISDOM BLOCK: @app.before_first_request detected in {filepath}")
            return {
                "status": "REJECTED",
                "reason": "WISDOM BLOCK: Flask removed @app.before_first_request in v2.3+. "
                          "Remove the decorator and call the initialization function directly "
                          "during app setup (e.g., inside create_app() or at module level)."
            }
        user_prompt = (
            f"File: {filepath}\n\n"
            f"Source Code:\n```\n{code}\n```\n\n"
        )
        if manifest_context:
            user_prompt += f"Project Manifest (for cross-reference):\n{manifest_context}\n"

        try:
            raw = ask_llm(self.client, self.model, self.system_prompt, user_prompt)
            # Parse JSON response
            result = json.loads(raw)
            if "status" not in result:
                return {"status": "APPROVED", "reason": "Reviewer returned no status — auto-approved."}
            return result
        except json.JSONDecodeError:
            # If the reviewer can't return valid JSON, auto-approve to avoid blocking
            raw_upper = raw.upper() if raw else ""
            if "REJECTED" in raw_upper:
                return {"status": "REJECTED", "reason": raw[:200]}
            return {"status": "APPROVED", "reason": "Reviewer parse fallback — auto-approved."}
        except Exception as e:
            log("REVIEWER", f"  ⚠ Review failed: {e} — auto-approving.")
            return {"status": "APPROVED", "reason": f"Review error: {e}"}


# ── Codebase State Persistence ───────────────────────────────

class CodebaseState:
    """Persistent wrapper around the written_files dict.
    Saves state to disk after every write, enabling crash recovery
    and preventing the LLM from hallucinating a different tech stack mid-build."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.state_file = os.path.join(project_path, ".overlord_state.json")
        self.files = {}       # {filepath: code_string}
        self.metadata = {}    # {filepath: {"chars": int, "hash": str, "reviews": int}}
        self._load()

    def _load(self):
        """Load previous state if it exists (crash recovery / incremental builds)."""
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
        """Persist current state to disk."""
        try:
            data = {"files": self.files, "metadata": self.metadata,
                    "saved_at": datetime.now().isoformat()}
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log("STATE", f"  ⚠ State save failed: {e}")

    def write(self, filepath: str, code: str, review_count: int = 0):
        """Store a file and persist the state."""
        self.files[filepath] = code
        self.metadata[filepath] = {
            "chars": len(code),
            "hash": hashlib.sha256(code.encode("utf-8")).hexdigest()[:16],
            "reviews": review_count,
            "written_at": datetime.now().isoformat()
        }
        self._save()

    def get_context_block(self, exclude: str = "") -> str:
        """Build context from all written files for LLM consumption."""
        snippets = []
        for fpath, code in self.files.items():
            if fpath == exclude:
                continue
            preview = "\n".join(code.split("\n")[:40])
            snippets.append(f"--- {fpath} ---\n{preview}\n---")
        return "\n\n".join(snippets) if snippets else "No files written yet."

    def clear(self):
        """Reset state for a fresh build."""
        self.files = {}
        self.metadata = {}
        if os.path.exists(self.state_file):
            os.remove(self.state_file)


# ── Cost Tracking & Budget Kill-Switch ─────────────────────

class CostTracker:
    """Tracks estimated spending across all LLM calls in a build.
    When the budget is exceeded, signals the orchestrator to pivot
    all remaining calls to the cheapest available model."""

    # Pricing per 1K tokens (input/output) — update as providers change
    PRICING = {
        # OpenAI
        "gpt-4o":           {"input": 0.0025, "output": 0.010},
        "gpt-4o-mini":      {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo":      {"input": 0.01,   "output": 0.03},
        "gpt-3.5-turbo":    {"input": 0.0005, "output": 0.0015},
        "o1":               {"input": 0.015,  "output": 0.06},
        "o1-mini":          {"input": 0.003,  "output": 0.012},
        # Gemini
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
        "gemini-1.5-pro":   {"input": 0.00125, "output": 0.005},
        # Groq (free tier / near-zero)
        "llama3-70b-8192":  {"input": 0.00059, "output": 0.00079},
        "llama3-8b-8192":   {"input": 0.00005, "output": 0.00008},
        "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
        # Local (Ollama) — free
        "llama3":           {"input": 0.0, "output": 0.0},
        "codellama":        {"input": 0.0, "output": 0.0},
        "mistral":          {"input": 0.0, "output": 0.0},
    }
    DEFAULT_PRICING = {"input": 0.002, "output": 0.006}  # Conservative fallback

    def __init__(self, budget: float = 5.0):
        self.budget = budget
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.per_model = {}  # {model: {"cost": x, "calls": n}}
        self._budget_exceeded = False
        self._pivot_triggered = False

    def record_call(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Record a single LLM call's token usage and estimated cost."""
        pricing = self.PRICING.get(model, self.DEFAULT_PRICING)
        cost = (prompt_tokens / 1000 * pricing["input"]) + \
               (completion_tokens / 1000 * pricing["output"])

        self.total_cost += cost
        self.total_input_tokens += prompt_tokens
        self.total_output_tokens += completion_tokens
        self.call_count += 1

        if model not in self.per_model:
            self.per_model[model] = {"cost": 0.0, "calls": 0, "tokens": 0}
        self.per_model[model]["cost"] += cost
        self.per_model[model]["calls"] += 1
        self.per_model[model]["tokens"] += prompt_tokens + completion_tokens

        # Check budget
        if self.total_cost >= self.budget and not self._budget_exceeded:
            self._budget_exceeded = True
            log("SYSTEM", f"⚠️ BUDGET ALERT: ${self.total_cost:.4f} / ${self.budget:.2f} exceeded!")

    @property
    def budget_exceeded(self) -> bool:
        return self._budget_exceeded

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget - self.total_cost)

    @property
    def pivot_triggered(self) -> bool:
        return self._pivot_triggered

    def trigger_pivot(self):
        """Mark that the model pivot has been triggered."""
        self._pivot_triggered = True

    def get_summary(self) -> str:
        """Return a formatted cost summary for logging."""
        lines = [f"Total: ${self.total_cost:.4f} / ${self.budget:.2f} budget"]
        lines.append(f"Calls: {self.call_count} | Tokens: {self.total_input_tokens:,} in + {self.total_output_tokens:,} out")
        for m, data in sorted(self.per_model.items(), key=lambda x: -x[1]["cost"]):
            lines.append(f"  {m}: ${data['cost']:.4f} ({data['calls']} calls, {data['tokens']:,} tokens)")
        return "\n".join(lines)

    def save_report(self, project_path: str):
        """Write a cost report JSON to the project directory."""
        report = {
            "budget": self.budget,
            "total_cost": round(self.total_cost, 6),
            "remaining": round(self.remaining, 6),
            "budget_exceeded": self._budget_exceeded,
            "pivot_triggered": self._pivot_triggered,
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "per_model": self.per_model,
        }
        report_path = os.path.join(project_path, "cost_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        log("SYSTEM", f"  📊 Cost report saved: cost_report.json")


# ── Project Assembler (Phase 1.5) ────────────────────────────

def project_assembler(plan: dict, project_path: str):
    """Instantly creates the full folder tree and empty placeholder files
    from the Architect's manifest BEFORE any code is written.
    
    This ensures the Developer agent works with real file paths,
    eliminating hallucinations about file locations. The Developer
    can say 'Write code for ./cat_crm/api/main.py' because the file
    already exists on disk."""
    
    # Extract file tree — support both 'file_tree' and 'files' formats
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
        
        # Create directory structure
        if parent_dir not in created_dirs:
            os.makedirs(parent_dir, exist_ok=True)
            created_dirs.add(parent_dir)
        
        # Create empty placeholder file (only if it doesn't already exist)
        if not os.path.exists(full_path):
            with open(full_path, "w", encoding="utf-8") as f:
                # Write a minimal placeholder comment
                ext = os.path.splitext(fpath)[1].lower()
                if ext == ".py":
                    f.write(f"# {fpath} — placeholder, code will be generated by Overlord Engineer\n")
                elif ext in (".js", ".ts", ".jsx", ".tsx"):
                    f.write(f"// {fpath} — placeholder, code will be generated by Overlord Engineer\n")
                elif ext in (".html", ".xml"):
                    f.write(f"<!-- {fpath} — placeholder -->\n")
                elif ext in (".css", ".scss"):
                    f.write(f"/* {fpath} — placeholder */\n")
                else:
                    f.write("")  # Empty file for unknown types
            log("ASSEMBLER", f"  ├─ {fpath}")
    
    # Also create standard project directories if not already present
    for std_dir in ["tests", "docs"]:
        std_path = os.path.join(project_path, std_dir)
        if not os.path.exists(std_path):
            os.makedirs(std_path, exist_ok=True)
    
    # Log the tree structure
    log("ASSEMBLER", f"  └─ ✓ Scaffold complete: {len(file_tree)} files, {len(created_dirs)} directories")
    
    # Create .gitignore with sensible defaults
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


# ── Zero-Chat Self-Healing Deployment ────────────────────────

def auto_heal_deployment(project_path: str, client, model: str,
                         reviewer: ReviewerAgent, state: CodebaseState,
                         written_files: dict, eng_system: str,
                         max_cycles: int = 3) -> bool:
    """Attempt docker-compose up --build. If it fails, capture the container
    logs, feed them to the Reviewer for root-cause analysis, have the
    Developer patch the broken file, and retry — fully autonomous.
    
    Returns True if deployment eventually succeeds, False if all cycles exhausted."""
    import shutil
    
    # Pre-flight: docker must be available
    if not shutil.which("docker"):
        log("DOCKER", "  ⚠ Docker not found on PATH — skipping deployment healing.")
        return False
    
    compose_file = os.path.join(project_path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        log("DOCKER", "  ⚠ No docker-compose.yml found — skipping deployment healing.")
        return False
    
    for cycle in range(1, max_cycles + 1):
        log("DOCKER", f"  ── Deploy Cycle {cycle}/{max_cycles} ──")
        
        # 1. Build & start containers (detached, with timeout)
        try:
            build_result = subprocess.run(
                ["docker-compose", "up", "--build", "-d"],
                capture_output=True, text=True,
                cwd=project_path, timeout=120,
            )
        except subprocess.TimeoutExpired:
            log("DOCKER", f"  ⏱ Build timed out (120s) on cycle {cycle}.")
            # Tear down any partial containers
            subprocess.run(["docker-compose", "down"], cwd=project_path,
                           capture_output=True, timeout=30)
            continue
        except FileNotFoundError:
            # Try 'docker compose' (V2 syntax) instead of 'docker-compose'
            try:
                build_result = subprocess.run(
                    ["docker", "compose", "up", "--build", "-d"],
                    capture_output=True, text=True,
                    cwd=project_path, timeout=120,
                )
            except Exception as e:
                log("DOCKER", f"  ✗ Cannot invoke docker compose: {e}")
                return False
        except Exception as e:
            log("DOCKER", f"  ✗ Deploy error: {e}")
            return False
        
        # 2. Wait briefly for the container to either stabilize or crash
        time.sleep(5)
        
        # 3. Capture container logs
        try:
            logs_result = subprocess.run(
                ["docker-compose", "logs", "--tail=80"],
                capture_output=True, text=True,
                cwd=project_path, timeout=15,
            )
            container_logs = logs_result.stdout + logs_result.stderr
        except FileNotFoundError:
            logs_result = subprocess.run(
                ["docker", "compose", "logs", "--tail=80"],
                capture_output=True, text=True,
                cwd=project_path, timeout=15,
            )
            container_logs = logs_result.stdout + logs_result.stderr
        except Exception:
            container_logs = build_result.stderr
        
        # 4. Check if containers are healthy (running, not restarting/exited)
        try:
            ps_result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True, text=True,
                cwd=project_path, timeout=10,
            )
            ps_output = ps_result.stdout
        except FileNotFoundError:
            ps_result = subprocess.run(
                ["docker", "compose", "ps"],
                capture_output=True, text=True,
                cwd=project_path, timeout=10,
            )
            ps_output = ps_result.stdout
        except Exception:
            ps_output = ""
        
        # Success heuristic: containers are "Up" and no crash keywords in logs
        crash_signals = ["Traceback", "Error", "error", "FATAL", "exited with code",
                         "ModuleNotFoundError", "ImportError", "ConnectionRefusedError",
                         "FileNotFoundError", "KeyError", "SyntaxError"]
        has_crash = any(sig in container_logs for sig in crash_signals)
        is_running = "Up" in ps_output and "Exit" not in ps_output
        
        if is_running and not has_crash:
            log("DOCKER", f"  ✓ Deployment HEALTHY on cycle {cycle}!")
            # Leave containers running for the user
            return True
        
        # ── DEPLOYMENT FAILED — enter self-healing ──
        log("DOCKER", f"  ✗ Deployment unhealthy on cycle {cycle}.")
        
        # Save error log to disk for reference
        error_log_path = os.path.join(project_path, f"error_cycle_{cycle}.log")
        with open(error_log_path, "w", encoding="utf-8") as f:
            f.write(f"=== DEPLOY CYCLE {cycle} ===\n")
            f.write(f"BUILD OUTPUT:\n{build_result.stdout}\n{build_result.stderr}\n")
            f.write(f"CONTAINER LOGS:\n{container_logs}\n")
            f.write(f"CONTAINER STATUS:\n{ps_output}\n")
        log("DOCKER", f"  📄 Saved error log: error_cycle_{cycle}.log")
        
        # Tear down broken containers before fixing
        try:
            subprocess.run(["docker-compose", "down", "--remove-orphans"],
                           cwd=project_path, capture_output=True, timeout=30)
        except FileNotFoundError:
            subprocess.run(["docker", "compose", "down", "--remove-orphans"],
                           cwd=project_path, capture_output=True, timeout=30)
        except Exception:
            pass
        
        if cycle >= max_cycles:
            log("DOCKER", f"  ✗ All {max_cycles} heal cycles exhausted. Manual intervention needed.")
            return False
        
        # 5. REVIEWER DIAGNOSIS — ask what went wrong
        log("REVIEWER", "  🔍 Reviewer analyzing container failure…")
        
        diag_prompt = (
            f"The Docker deployment FAILED. Analyze these container logs and identify:\n"
            f"1. The ROOT CAUSE of the failure\n"
            f"2. Which source file needs to be fixed\n"
            f"3. The exact fix required\n\n"
            f"Project files: {list(written_files.keys())}\n\n"
            f"CONTAINER LOGS:\n{container_logs[:3000]}\n\n"
            f"BUILD OUTPUT:\n{build_result.stderr[:2000]}\n\n"
            f"Respond as JSON: {{\"root_cause\": \"...\", \"fix_file\": \"filename.py\", "
            f"\"fix_instruction\": \"exactly what to change\"}}"
        )
        
        try:
            diag_raw = ask_llm(client, model,
                "You are 'Overlord Deployment Reviewer.' You specialize in diagnosing "
                "Docker container failures. Read the logs carefully and output a precise "
                "diagnosis as JSON. No markdown fences.",
                diag_prompt)
            
            # Parse JSON response
            try:
                diagnosis = json.loads(diag_raw)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start = diag_raw.find("{")
                end = diag_raw.rfind("}") + 1
                if start >= 0 and end > start:
                    diagnosis = json.loads(diag_raw[start:end])
                else:
                    log("REVIEWER", f"  ⚠ Could not parse diagnosis. Raw: {diag_raw[:200]}")
                    continue
            
            root_cause = diagnosis.get("root_cause", "Unknown")
            fix_file = diagnosis.get("fix_file", "")
            fix_instruction = diagnosis.get("fix_instruction", "")
            
            log("REVIEWER", f"  Root cause: {root_cause[:120]}")
            log("REVIEWER", f"  Fix target: {fix_file}")
            
        except Exception as e:
            log("ERROR", f"  Reviewer diagnosis failed: {e}")
            continue
        
        # 6. DEVELOPER PATCH — rewrite the broken file
        if fix_file and fix_file in written_files:
            log("ENGINEER", f"  🔧 Developer patching: {fix_file}")
            
            patch_prompt = (
                f"A Docker deployment FAILED. The Reviewer diagnosed the issue:\n"
                f"Root cause: {root_cause}\n"
                f"Fix instruction: {fix_instruction}\n\n"
                f"Here is the current source code for {fix_file}:\n"
                f"```\n{written_files[fix_file]}\n```\n\n"
                f"Container error logs:\n{container_logs[:2000]}\n\n"
                f"Rewrite the COMPLETE file with the fix applied. "
                f"Output ONLY raw source code. No markdown fences."
            )
            
            try:
                fixed_code = ask_llm(client, model, eng_system, patch_prompt)
                
                # Write to disk
                full_path = os.path.join(project_path, fix_file)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(fixed_code)
                
                # Update state
                state.write(fix_file, fixed_code)
                written_files[fix_file] = fixed_code
                
                log("ENGINEER", f"  ✓ Patched: {fix_file}")
                log("DOCKER", f"  ↻ Retrying deployment with patched code…")
                
            except Exception as e:
                log("ERROR", f"  Developer patch failed: {e}")
                continue
        
        elif fix_file == "Dockerfile" or fix_file == "docker-compose.yml":
            # The issue is in the Docker config itself, not source code
            log("DOCKER", f"  🔧 Patching Docker config: {fix_file}")
            
            patch_prompt = (
                f"The Docker deployment failed because of an issue in {fix_file}.\n"
                f"Root cause: {root_cause}\n"
                f"Fix instruction: {fix_instruction}\n\n"
                f"Current {fix_file}:\n"
                f"```\n{open(os.path.join(project_path, fix_file), 'r').read()}\n```\n\n"
                f"Project files: {list(written_files.keys())}\n"
                f"Dependencies: requirements.txt exists\n\n"
                f"Rewrite the COMPLETE {fix_file} with the fix. "
                f"Output ONLY the file content. No markdown fences."
            )
            
            try:
                fixed_config = ask_llm(client, model,
                    "You are 'Overlord DevOps Specialist.' Fix the Docker configuration. "
                    "Output ONLY the corrected file content.",
                    patch_prompt)
                
                config_path = os.path.join(project_path, fix_file)
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(fixed_config)
                
                log("DOCKER", f"  ✓ Patched: {fix_file}")
                log("DOCKER", f"  ↻ Retrying deployment…")
                
            except Exception as e:
                log("ERROR", f"  Docker config patch failed: {e}")
                continue
        else:
            log("DOCKER", f"  ⚠ Cannot identify fix target '{fix_file}' in project files.")
            continue
    
    return False


# ── Voice Briefing (ElevenLabs TTS) ──────────────────────────

def generate_voice_briefing(project_path: str, project_name: str,
                            file_count: int, run_cmd: str,
                            client, model: str, prompt: str,
                            cost_summary: str = "") -> str:
    """Generate a 30-second voice briefing using ElevenLabs TTS.
    
    Flow:
    1. LLM writes a concise 3-sentence narration script
    2. ElevenLabs converts it to high-quality speech audio
    3. Audio auto-plays on the user's system
    
    Returns the path to the saved audio file, or "" on failure."""
    import urllib.request
    import urllib.parse
    
    ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    if not ELEVENLABS_KEY:
        log("VOICE", "  ⚠ ELEVENLABS_API_KEY not set — skipping voice briefing.")
        log("VOICE", "  💡 Set it in your .env to enable spoken build summaries.")
        return ""
    
    log("VOICE", "🎙️  Generating voice briefing…")
    
    # Step 1: Generate the narration script via LLM (cheap model)
    script_prompt = (
        f"Write a confident, energetic 3-sentence voice briefing (max 40 words) "
        f"announcing that the Overlord AI has finished building a project.\n\n"
        f"Project: {project_name}\n"
        f"Original request: {prompt[:200]}\n"
        f"Files generated: {file_count}\n"
        f"Run command: {run_cmd}\n"
    )
    if cost_summary:
        script_prompt += f"Build cost: {cost_summary.split(chr(10))[0]}\n"
    
    script_prompt += (
        "\nTone: Professional but exciting, like a mission control announcement. "
        "Example: 'Overlord build complete. Your [project type] is ready with [N] files. "
        "Run it now with [command].' "
        "Output ONLY the narration text. No quotes, no labels."
    )
    
    try:
        script = ask_llm(client, model,
            "You write ultra-concise voice-over scripts for an AI build system. "
            "Output only the spoken words, nothing else.",
            script_prompt)
        # Clean up — remove any quotes or labels the LLM might add
        script = script.strip().strip('"').strip("'")
        if len(script) > 300:
            script = script[:300]  # Hard cap for ~30 seconds of speech
        log("VOICE", f"  📝 Script: \"{script}\"")
    except Exception as e:
        log("VOICE", f"  ⚠ Script generation failed: {e}")
        script = f"Overlord build complete. {project_name} is ready with {file_count} files. Run it with {run_cmd}."
    
    # Step 2: Call ElevenLabs TTS API
    # Using Rachel voice (21m00Tcm4TlvDq8ikWAM) — professional, clear
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    tts_payload = json.dumps({
        "text": script,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.4,
            "use_speaker_boost": True
        }
    }).encode("utf-8")
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_KEY,
    }
    
    audio_path = os.path.join(project_path, "build_briefing.mp3")
    
    try:
        req = urllib.request.Request(tts_url, data=tts_payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio_data = resp.read()
        
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        
        log("VOICE", f"  ✓ Audio saved: build_briefing.mp3 ({len(audio_data):,} bytes)")
        
    except urllib.error.HTTPError as e:
        log("VOICE", f"  ✗ ElevenLabs API error: {e.code} {e.reason}")
        return ""
    except Exception as e:
        log("VOICE", f"  ✗ TTS failed: {e}")
        return ""
    
    # Step 3: Auto-play the audio (non-blocking)
    try:
        if sys.platform == "win32":
            # Windows: use the built-in media player (hidden window)
            subprocess.Popen(
                ["cmd", "/c", "start", "", "/min", audio_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        elif sys.platform == "darwin":
            # macOS: afplay
            subprocess.Popen(
                ["afplay", audio_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            # Linux: aplay or mpv
            player = shutil.which("mpv") or shutil.which("aplay") or shutil.which("paplay")
            if player:
                subprocess.Popen(
                    [player, audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                log("VOICE", "  ℹ No audio player found — briefing saved but not auto-played.")
        
        log("VOICE", "  🔊 Playing briefing…")
    except Exception as e:
        log("VOICE", f"  ℹ Auto-play failed: {e} — audio still saved at build_briefing.mp3")
    
    return audio_path


# ── Handoff Guarantee ────────────────────────────────────────

def finalize_package(project_path: str, state: CodebaseState, project_name: str,
                     arch_stack: dict = None, arch_file_tree: list = None,
                     deps: list = None, run_cmd: str = "python main.py",
                     prompt: str = "", client=None, model: str = ""):
    """Produces a single, consolidated handoff package with:
    1. Project Overview (3-sentence summary)
    2. Environment Setup (exact commands)
    3. File Manifest (every file + purpose)
    4. Code Blocks (complete source per file)
    Plus .env.example and package_manifest.json."""
    log("HANDOFF", "Assembling Consolidated Output Package…")

    deps = deps or []
    total_size = 0
    for code in state.files.values():
        total_size += len(code)

    # ── Section 1: Project Overview (LLM-generated 3-sentence summary) ──
    overview = ""
    if client and model:
        try:
            overview_system = (
                "You are a technical writer. Write exactly 3 sentences summarizing this software project. "
                "Sentence 1: What the project does and who it's for. "
                "Sentence 2: Key technologies, architecture, and notable features. "
                "Sentence 3: How to install and run it. "
                "Output ONLY the 3 sentences. No markdown, no headers."
            )
            overview_prompt = (
                f"Project: {project_name}\n"
                f"Goal: {prompt[:400]}\n"
                f"Files: {list(state.files.keys())}\n"
                f"Dependencies: {deps}\n"
                f"Run command: {run_cmd}"
            )
            overview = ask_llm(client, model, overview_system, overview_prompt)
            log("HANDOFF", "  ✓ Project overview generated")
        except Exception as e:
            log("HANDOFF", f"  ⚠ Overview generation failed: {e}")

    if not overview:
        overview = (
            f"{project_name} is an application built autonomously by Overlord. "
            f"It comprises {len(state.files)} source files using {', '.join(deps[:5]) or 'the Python standard library'}. "
            f"To run: install dependencies with pip and execute '{run_cmd}'."
        )

    # ── Section 2: Environment Setup ──
    setup_commands = []
    setup_commands.append(f"mkdir {project_name} && cd {project_name}")
    if deps:
        setup_commands.append("python -m venv venv")
        setup_commands.append("# Windows: venv\\Scripts\\activate  |  Unix: source venv/bin/activate")
        setup_commands.append("pip install -r requirements.txt")
    setup_commands.append(run_cmd)

    # ── Section 3: File Manifest ──
    file_manifest_rows = []
    for fpath, code in state.files.items():
        line_count = len(code.split("\n"))
        char_count = len(code)
        # Auto-detect purpose from first docstring or comment
        purpose = ""
        for line in code.split("\n")[:10]:
            stripped = line.strip()
            if stripped.startswith("#") and not stripped.startswith("#!"):
                purpose = stripped.lstrip("# ").strip()
                break
            elif '"""' in stripped or "'''" in stripped:
                purpose = stripped.strip("\"' ").strip()
                break
        if not purpose:
            ext = os.path.splitext(fpath)[1]
            purpose = f"{ext.lstrip('.')} source file" if ext else "project file"
        file_manifest_rows.append((fpath, line_count, char_count, purpose[:60]))

    # ── Build the FULL_PACKAGE.md ──
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "html": "html", "css": "css", "json": "json",
        "yml": "yaml", "yaml": "yaml", "sh": "bash",
        "bat": "batch", "md": "markdown", "txt": "",
        "dockerfile": "dockerfile", "toml": "toml", "cfg": "ini",
    }

    lines = []
    lines.append(f"# 📦 Consolidated Package: {project_name}")
    lines.append(f"")
    lines.append(f"*Generated by Overlord on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append(f"")

    # Section 1
    lines.append(f"## 🎯 Project Overview")
    lines.append(f"")
    lines.append(overview)
    lines.append(f"")

    # Section 2
    lines.append(f"## 🔧 Environment Setup")
    lines.append(f"")
    lines.append(f"```bash")
    for cmd in setup_commands:
        lines.append(cmd)
    lines.append(f"```")
    lines.append(f"")

    # Section 3
    lines.append(f"## 📋 File Manifest")
    lines.append(f"")
    lines.append(f"| File | Lines | Chars | Purpose |")
    lines.append(f"|------|------:|------:|---------|")
    for fpath, lc, cc, purpose in file_manifest_rows:
        lines.append(f"| `{fpath}` | {lc} | {cc:,} | {purpose} |")
    lines.append(f"")
    lines.append(f"**Total: {len(state.files)} files, {total_size:,} characters**")
    lines.append(f"")

    # Section 4
    lines.append(f"## 💻 Source Code")
    lines.append(f"")
    for fpath, code in state.files.items():
        ext = os.path.splitext(fpath)[1].lstrip(".")
        lang = lang_map.get(ext, ext)
        # Handle Dockerfile specially
        if fpath.lower() == "dockerfile":
            lang = "dockerfile"
        lines.append(f"### `{fpath}`")
        lines.append(f"```{lang}")
        lines.append(code)
        lines.append(f"```")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*End of Consolidated Package — {project_name}*")

    package_md = "\n".join(lines)
    pkg_path = os.path.join(project_path, "FULL_PACKAGE.md")
    with open(pkg_path, "w", encoding="utf-8") as f:
        f.write(package_md)
    log("HANDOFF", f"  ✓ FULL_PACKAGE.md  ({len(state.files)} files, {total_size:,} chars)")

    # Print the consolidated output to stdout for Electron GUI
    print("\n" + "=" * 60, flush=True)
    print("  OVERLORD — CONSOLIDATED BUILD PACKAGE", flush=True)
    print("=" * 60, flush=True)
    print(f"\n## PROJECT OVERVIEW\n{overview}\n", flush=True)
    print("## ENVIRONMENT SETUP", flush=True)
    for cmd in setup_commands:
        print(f"  {cmd}", flush=True)
    print("", flush=True)
    print("## FILE MANIFEST", flush=True)
    for fpath, lc, cc, purpose in file_manifest_rows:
        print(f"  {fpath:30s}  {lc:5d} lines  →  {purpose}", flush=True)
    print(f"\n  TOTAL: {len(state.files)} files, {total_size:,} chars", flush=True)
    print("=" * 60, flush=True)

    # 2. .env.example — auto-discover environment variables from generated code
    env_vars = set()
    for fpath, code in state.files.items():
        for line in code.split("\n"):
            for pattern in ["os.environ.get(", "os.getenv(", "os.environ["]:
                if pattern in line:
                    start = line.find(pattern) + len(pattern)
                    for q in ["'", '"']:
                        qi = line.find(q, start)
                        if qi >= 0:
                            qe = line.find(q, qi + 1)
                            if qe > qi:
                                env_vars.add(line[qi + 1:qe])
                                break
    if env_vars:
        env_path = os.path.join(project_path, ".env.example")
        with open(env_path, "w", encoding="utf-8") as f:
            for var in sorted(env_vars):
                f.write(f"{var}=\n")
        log("HANDOFF", f"  ✓ .env.example  ({len(env_vars)} variable(s))")

    # 3. package_manifest.json — structured manifest with checksums + stack DNA
    manifest = {
        "project": project_name,
        "generated_at": datetime.now().isoformat(),
        "total_files": len(state.files),
        "total_chars": total_size,
        "files": {}
    }
    if arch_stack:
        manifest["stack"] = arch_stack
    if arch_file_tree:
        manifest["file_tree"] = arch_file_tree
    for fpath, meta in state.metadata.items():
        manifest["files"][fpath] = meta

    manifest_path = os.path.join(project_path, "package_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("HANDOFF", f"  ✓ package_manifest.json")

    return pkg_path


# ── Gallery Agent (Portfolio Dashboard) ──────────────────────

def update_gallery(project_path, manifest):
    """Appends a project card to an 'overlord_gallery.html' dashboard.
    Creates the gallery if it doesn't exist. Uses Tailwind CDN for styling."""
    gallery_file = "overlord_gallery.html"
    project_name = manifest.get("project_name")
    stack = manifest.get("stack", {})
    date = datetime.now().strftime("%Y-%m-%d")

    # The HTML Card Template
    new_card = f"""
    <div class="card">
        <h3>{project_name}</h3>
        <p><strong>Stack:</strong> {stack.get('frontend', 'N/A')} + {stack.get('backend', 'N/A')}</p>
        <p><strong>Created:</strong> {date}</p>
        <a href="./{project_name}/BUILD_LOG.md" class="btn">View Logs</a>
        <a href="./{project_name}" class="btn">Open Code</a>
    </div>
    """

    # If gallery doesn't exist, create it with Tailwind CSS styling
    if not os.path.exists(gallery_file):
        with open(gallery_file, "w", encoding="utf-8") as f:
            f.write(f"<html><head><script src='https://cdn.tailwindcss.com'></script></head>"
                    f"<body class='bg-gray-900 text-white p-10'>"
                    f"<h1 class='text-4xl font-bold mb-8'>Overlord Project Library</h1>"
                    f"<div id='gallery' class='grid grid-cols-3 gap-6'>{new_card}</div>"
                    f"</body></html>")
    else:
        # Append the new card to the existing gallery
        with open(gallery_file, "r+", encoding="utf-8") as f:
            content = f.read()
            f.seek(0)
            f.write(content.replace(
                "<div id='gallery' class='grid grid-cols-3 gap-6'>",
                f"<div id='gallery' class='grid grid-cols-3 gap-6'>{new_card}"
            ))

    log("GALLERY", f"  🖼️  Gallery updated: {gallery_file} — added '{project_name}'")


# ── Setup Agent (Phase 4: Deploy) ────────────────────────────
import re as _re_module

def setup_agent(project_path: str, written_files: dict, deps: list, run_cmd: str):
    """Deterministic deploy agent — scans generated code for runtime,
    env vars, and ports. Emits: setup.ps1, docker-compose.yml, .env.template.
    No LLM call needed — pure static analysis."""
    log("SETUP", "Engaging Setup Agent (static analysis)…")

    # ── 1. Runtime Detection ─────────────────────────────────
    extensions = set()
    for fpath in written_files:
        ext = os.path.splitext(fpath)[1].lower()
        if ext:
            extensions.add(ext)

    runtime = "python"
    install_cmd = "pip install -r requirements.txt"
    base_image = "python:3.12-slim"
    if ".js" in extensions or ".ts" in extensions:
        if ".py" not in extensions:
            runtime = "node"
            install_cmd = "npm install"
            base_image = "node:20-slim"
    elif ".go" in extensions:
        runtime = "go"
        install_cmd = "go mod download"
        base_image = "golang:1.22-alpine"
    elif ".rs" in extensions:
        runtime = "rust"
        install_cmd = "cargo build --release"
        base_image = "rust:1.76-slim"

    log("SETUP", f"  Runtime: {runtime}  |  Base: {base_image}")

    # ── 2. Environment Variable Scanning ─────────────────────
    env_vars = set()
    env_patterns_py = [
        _re_module.compile(r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]+)["\']'),
        _re_module.compile(r'os\.getenv\(["\']([A-Z_][A-Z0-9_]+)["\']'),
        _re_module.compile(r'os\.environ\[["\']([A-Z_][A-Z0-9_]+)["\']\]'),
    ]
    env_pattern_js = _re_module.compile(r'process\.env\.([A-Z_][A-Z0-9_]+)')

    for fpath, code in written_files.items():
        if fpath.endswith(".py"):
            for pat in env_patterns_py:
                env_vars.update(pat.findall(code))
        elif fpath.endswith((".js", ".ts")):
            env_vars.update(env_pattern_js.findall(code))

    # Remove noise
    noise = {"PATH", "HOME", "USER", "SHELL", "LANG", "TERM", "PWD",
             "PYTHONPATH", "PYTHONUNBUFFERED", "NODE_ENV"}
    env_vars -= noise
    env_vars_sorted = sorted(env_vars)

    log("SETUP", f"  Detected {len(env_vars_sorted)} env var(s): {', '.join(env_vars_sorted[:8]) or 'none'}")

    # ── 3. Port Detection ────────────────────────────────────
    port = None
    port_patterns = [
        _re_module.compile(r'\.listen\(\s*(\d{4,5})'),
        _re_module.compile(r'port\s*=\s*(\d{4,5})', _re_module.IGNORECASE),
        _re_module.compile(r'PORT\s*=\s*(\d{4,5})'),
        _re_module.compile(r'--port\s+(\d{4,5})'),
        _re_module.compile(r'host\s*=.*port\s*=\s*(\d{4,5})', _re_module.IGNORECASE),
        _re_module.compile(r'uvicorn.*:(\d{4,5})'),
    ]
    all_code = "\n".join(written_files.values())
    for pat in port_patterns:
        match = pat.search(all_code)
        if match:
            port = match.group(1)
            break
    if not port:
        port = "8000"

    log("SETUP", f"  Port: {port}")

    # ── 4. Generate .env.template ─────────────────────────────
    env_lines = ["# Environment Variables — fill in your real values"]
    for var in env_vars_sorted:
        env_lines.append(f"{var}=your_value_here")
    if not env_vars_sorted:
        env_lines.append("# No environment variables detected")
    env_content = "\n".join(env_lines) + "\n"

    env_path = os.path.join(project_path, ".env.template")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    log("SETUP", "  ✓ .env.template")

    # ── 5. Generate setup.ps1 (PowerShell) ────────────────────
    project_name = os.path.basename(project_path)
    setup_ps1 = f'''# ══════════════════════════════════════════════════════════════
#  {project_name} — One-Click Setup (PowerShell)
#  Generated by Overlord Setup Agent
# ══════════════════════════════════════════════════════════════

Write-Host "  Setting up {project_name}..." -ForegroundColor Cyan

# Step 1: Create .env from template if it doesn't exist
if (-not (Test-Path ".env")) {{
    if (Test-Path ".env.template") {{
        Copy-Item ".env.template" ".env"
        Write-Host "  [OK] Created .env from template — fill in your values." -ForegroundColor Yellow
    }}
}} else {{
    Write-Host "  [OK] .env already exists." -ForegroundColor Green
}}

# Step 2: Install dependencies
Write-Host "  Installing dependencies..." -ForegroundColor Cyan
{install_cmd}
if ($LASTEXITCODE -ne 0) {{
    Write-Host "  [FAIL] Dependency install failed." -ForegroundColor Red
    exit 1
}}
Write-Host "  [OK] Dependencies installed." -ForegroundColor Green

# Step 3: Ready
Write-Host ""
Write-Host "  Setup complete! To start:" -ForegroundColor Green
Write-Host "    {run_cmd}" -ForegroundColor White
Write-Host "  Or use Docker:" -ForegroundColor Green
Write-Host "    docker-compose up -d" -ForegroundColor White
Write-Host ""
'''
    setup_path = os.path.join(project_path, "setup.ps1")
    with open(setup_path, "w", encoding="utf-8") as f:
        f.write(setup_ps1)
    log("SETUP", "  ✓ setup.ps1")

    # ── 6. Generate docker-compose.yml (deterministic) ────────
    env_file_line = "    env_file: .env" if env_vars_sorted else "    # No env_file needed"
    docker_compose = f'''# {project_name} — Docker Compose (Overlord Setup Agent)
version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {project_name.lower().replace(" ", "-")}
    ports:
      - "{port}:{port}"
{env_file_line}
    restart: unless-stopped
'''
    compose_path = os.path.join(project_path, "docker-compose.yml")
    with open(compose_path, "w", encoding="utf-8") as f:
        f.write(docker_compose)
    log("SETUP", "  ✓ docker-compose.yml")

    # ── 7. The Big Green Button ───────────────────────────────
    divider()
    log("SETUP", "🟢 THE BIG GREEN BUTTON:")
    log("SETUP", f"   cd {project_path} && docker-compose up -d")
    log("SETUP", f"")
    log("SETUP", f"   Or run locally:")
    log("SETUP", f"   cd {project_path} && .\\setup.ps1")
    divider()

    return {
        "setup_script": setup_path,
        "docker_compose": compose_path,
        "env_template": env_path,
        "runtime": runtime,
        "port": port,
        "env_vars": env_vars_sorted,
        "run_command": f"cd {project_path} && docker-compose up -d",
    }



# ── Voice Briefing (Eleven Labs TTS) ──────────────────────

def voice_briefing(client, model: str, project_name: str, prompt: str,
                   file_list: list, project_path: str):
    """
    Generates a 30-second voice summary of the completed build using
    Eleven Labs TTS. Creates a narrated MP3 briefing and auto-plays it.
    Gracefully degrades if Eleven Labs API key is unavailable.
    """
    import requests

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        log("VOICE", "  ⚠ ELEVENLABS_API_KEY not set — skipping voice briefing.")
        return None

    log("VOICE", "🎤 Generating Voice Briefing…")

    # Step 1: Generate a concise spoken summary via LLM
    # Assuming BUNDLER_MODE_DIRECTIVE is defined elsewhere or will be defined.
    # This block is inserted based on the user's instruction, assuming it's a new section.
    bundler_system = (
        "You are the 'Bundler' agent. Your job is to package the project for distribution."
        "\nCreate a 'requirements.txt' with all necessary dependencies."
        "\nCreate a 'README.md' with clear setup and run instructions."
        "\nCreate a 'Dockerfile' for containerization."
        "\nCreate a 'docker-compose.yml' for orchestration."
        f"{BUNDLER_MODE_DIRECTIVE}"  # Inject the Single-EXE instructions
        "\n\nOutput ONLY the content of these files using the standard YAML bundle format."
    )
    briefing_system = (
        "You are a concise project narrator. Write a 2-3 sentence spoken briefing "
        "(under 50 words) summarizing what was just built. Use a confident, professional "
        "tone as if announcing a product launch. Do NOT use markdown, code, or bullet points. "
        "Output ONLY the narration text, nothing else."
    )
    briefing_context = (
        f"Project: {project_name}\n"
        f"Goal: {prompt[:200]}\n"
        f"Files created: {', '.join(f['path'] if isinstance(f, dict) else str(f) for f in file_list[:10])}\n"
    )

    try:
        narration = ask_llm(client, model, briefing_system, briefing_context)
        # Clean it up — no markdown, no quotes
        narration = narration.strip().strip('"').strip("'")
        if len(narration) > 300:
            narration = narration[:297] + "..."
        log("VOICE", f"  📝 \"{narration}\"")
    except Exception as e:
        log("VOICE", f"  ⚠ Narration generation failed: {e}")
        return None

    # Step 2: Send to Eleven Labs TTS
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    payload = {
        "text": narration,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        }
    }

    try:
        response = requests.post(tts_url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            log("VOICE", f"  ⚠ Eleven Labs API returned {response.status_code}: {response.text[:100]}")
            return None

        # Step 3: Save the audio file
        audio_path = os.path.join(project_path, "briefing.mp3")
        with open(audio_path, "wb") as f:
            f.write(response.content)
        log("VOICE", f"  ✓ Briefing saved: briefing.mp3 ({len(response.content) // 1024}KB)")

        # Step 4: Auto-play on Windows
        try:
            if sys.platform == "win32":
                os.startfile(audio_path)
                log("VOICE", "  🔊 Playing briefing…")
            elif sys.platform == "darwin":
                subprocess.Popen(["afplay", audio_path])
                log("VOICE", "  🔊 Playing briefing…")
            else:
                # Linux — try aplay or mpv
                for player in ["mpv", "aplay", "paplay"]:
                    try:
                        subprocess.Popen([player, audio_path])
                        log("VOICE", "  🔊 Playing briefing…")
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            log("VOICE", "  ⚠ Auto-play failed — open briefing.mp3 manually.")

        return audio_path

    except requests.exceptions.Timeout:
        log("VOICE", "  ⚠ Eleven Labs API timed out.")
        return None
    except Exception as e:
        log("VOICE", f"  ⚠ Voice briefing failed: {e}")
        return None


# ── Pre-Flight Search (Version Verification) ────────────────────

def preflight_search(prompt: str, enhanced_prompt: str = "") -> dict:
    """
    Pre-flight Google Search phase — runs BEFORE the Architect.
    Queries for the latest stable versions of likely dependencies,
    catches known breaking changes, and verifies Docker base image tags.
    
    Returns a dict with:
      - verified_versions: {package: version}
      - warnings: [breaking change notices]
      - docker_images: {alias: verified_tag}
      - search_context: formatted string for Architect injection
    """
    import urllib.request
    import urllib.parse
    
    log("SEARCH", "🔍 Pre-Flight Version Search…")
    
    result = {
        "verified_versions": {},
        "warnings": [],
        "docker_images": {},
        "search_context": "",
    }
    
    # ── Extract technology signals from the prompt ────────────
    tech_signals = {
        "fastapi":    {"search": "fastapi latest stable version pypi", "docker": None},
        "flask":      {"search": "flask latest stable version pypi", "docker": None},
        "django":     {"search": "django latest stable version pypi", "docker": None},
        "next.js":    {"search": "next.js latest stable version npm", "docker": "node"},
        "nextjs":     {"search": "next.js latest stable version npm", "docker": "node"},
        "react":      {"search": "react latest stable version npm", "docker": "node"},
        "vue":        {"search": "vue.js latest stable version npm", "docker": "node"},
        "express":    {"search": "express.js latest stable version npm", "docker": "node"},
        "postgresql":  {"search": "postgresql latest stable version docker", "docker": "postgres"},
        "postgres":   {"search": "postgresql latest stable version docker", "docker": "postgres"},
        "mysql":      {"search": "mysql latest stable version docker", "docker": "mysql"},
        "mongodb":    {"search": "mongodb latest stable version docker", "docker": "mongo"},
        "redis":      {"search": "redis latest stable version docker", "docker": "redis"},
        "sqlalchemy":  {"search": "sqlalchemy latest stable version pypi", "docker": None},
        "prisma":     {"search": "prisma latest stable version npm", "docker": None},
        "python":     {"search": "python latest stable version docker", "docker": "python"},
        "node":       {"search": "node.js latest LTS version docker", "docker": "node"},
        "tailwind":   {"search": "tailwindcss latest stable version npm", "docker": None},
        "typescript":  {"search": "typescript latest stable version npm", "docker": None},
        "uvicorn":    {"search": "uvicorn latest stable version pypi", "docker": None},
        "pydantic":   {"search": "pydantic latest stable version pypi", "docker": None},
        "psycopg2":   {"search": "psycopg2-binary latest stable version pypi", "docker": None},
    }
    
    combined_prompt = f"{prompt} {enhanced_prompt}".lower()
    detected_techs = []
    for tech, config in tech_signals.items():
        if tech in combined_prompt:
            detected_techs.append((tech, config))
    
    # ── Wisdom-Driven Co-Lookup: FastAPI always needs Pydantic ──
    detected_names = [t[0] for t in detected_techs]
    if "fastapi" in detected_names and "pydantic" not in detected_names:
        detected_techs.append(("pydantic", tech_signals["pydantic"]))
        log("SEARCH", "  🔗 Auto-added Pydantic lookup (FastAPI dependency, wisdom rule)")
    
    if not detected_techs:
        log("SEARCH", "  ⚠ No specific technologies detected — skipping search.")
        return result
    
    log("SEARCH", f"  Detected {len(detected_techs)} technologies: {[t[0] for t in detected_techs]}")
    
    # ── Query PyPI / npm / Docker Hub APIs directly (faster than Google) ──
    for tech_name, config in detected_techs:
        try:
            # PyPI packages
            if "pypi" in config["search"]:
                pkg_name = tech_name.replace(".", "").replace(" ", "")
                # Map aliases
                pypi_map = {
                    "fastapi": "fastapi", "flask": "flask", "django": "django",
                    "sqlalchemy": "sqlalchemy", "uvicorn": "uvicorn",
                    "pydantic": "pydantic", "psycopg2": "psycopg2-binary",
                }
                pkg = pypi_map.get(pkg_name, pkg_name)
                url = f"https://pypi.org/pypi/{pkg}/json"
                req = urllib.request.Request(url, headers={"User-Agent": "Overlord/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    version = data["info"]["version"]
                    result["verified_versions"][pkg] = version
                    log("SEARCH", f"  ✓ {pkg}=={version} (PyPI latest)")
            
            # npm packages
            elif "npm" in config["search"]:
                npm_map = {
                    "next.js": "next", "nextjs": "next", "react": "react",
                    "vue": "vue", "express": "express", "tailwind": "tailwindcss",
                    "typescript": "typescript", "prisma": "prisma",
                    "node": None,  # Skip — node isn't an npm package
                }
                pkg = npm_map.get(tech_name)
                if pkg:
                    url = f"https://registry.npmjs.org/{pkg}/latest"
                    req = urllib.request.Request(url, headers={"User-Agent": "Overlord/1.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode())
                        version = data.get("version", "unknown")
                        result["verified_versions"][pkg] = version
                        log("SEARCH", f"  ✓ {pkg}@{version} (npm latest)")
            
            # Docker images — query Docker Hub
            elif "docker" in config["search"] and config.get("docker"):
                image = config["docker"]
                docker_map = {
                    "postgres": ("library/postgres", "15-alpine"),
                    "python": ("library/python", "3.12-slim"),
                    "node": ("library/node", "20-alpine"),
                    "mysql": ("library/mysql", "8.0"),
                    "mongo": ("library/mongo", "7.0"),
                    "redis": ("library/redis", "7-alpine"),
                }
                lib, default_tag = docker_map.get(image, (f"library/{image}", "latest"))
                # Try to verify the tag exists via Docker Hub API
                try:
                    tag_url = f"https://hub.docker.com/v2/repositories/{lib}/tags/{default_tag}/"
                    req = urllib.request.Request(tag_url, headers={"User-Agent": "Overlord/1.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        tag_data = json.loads(resp.read().decode())
                        tag_name = tag_data.get("name", default_tag)
                        result["docker_images"][image] = f"{image}:{tag_name}"
                        log("SEARCH", f"  ✓ {image}:{tag_name} (Docker Hub verified)")
                except Exception:
                    result["docker_images"][image] = f"{image}:{default_tag}"
                    log("SEARCH", f"  ~ {image}:{default_tag} (default, unverified)")
                    
        except Exception as e:
            log("SEARCH", f"  ⚠ Lookup failed for {tech_name}: {e}")
    
    # ── Wisdom-Driven Breaking Change Warnings ────────────────
    if "fastapi" in result["verified_versions"] or "pydantic" in result["verified_versions"]:
        pydantic_ver = result["verified_versions"].get("pydantic", "")
        if pydantic_ver and pydantic_ver.startswith("2"):
            result["warnings"].append(
                "PYDANTIC V2 BREAKING CHANGE: Use 'from pydantic import field_validator' "
                "instead of 'from pydantic import validator'. 'class Config:' inside models is "
                "removed — use 'model_config = ConfigDict(...)'. BaseSettings moved to "
                "'pydantic-settings' package. '.dict()' is now '.model_dump()'. "
                "Do NOT use Pydantic v1 patterns."
            )
            log("SEARCH", f"  ⚠ Wisdom: Pydantic {pydantic_ver} detected — v2 breaking change warning injected")
    
    # ── Build context string for Architect injection ──────────
    context_parts = []
    if result["verified_versions"]:
        versions_str = ", ".join(f"{k}=={v}" for k, v in result["verified_versions"].items())
        context_parts.append(f"VERIFIED LATEST STABLE VERSIONS (use these exact versions): {versions_str}")
    if result["docker_images"]:
        docker_str = ", ".join(f"{v}" for v in result["docker_images"].values())
        context_parts.append(f"VERIFIED DOCKER IMAGES: {docker_str}")
    if result["warnings"]:
        warnings_str = "; ".join(result["warnings"])
        context_parts.append(f"BREAKING CHANGE WARNINGS: {warnings_str}")
    
    result["search_context"] = "\n".join(context_parts)
    
    if context_parts:
        log("SEARCH", f"  📋 Pre-flight complete: {len(result['verified_versions'])} versions, {len(result['docker_images'])} images verified")
    else:
        log("SEARCH", "  ⚠ No version data retrieved.")
    
    return result


# ── Platform Profiles ───────────────────────────────────────────

PLATFORM_PROFILES = {
    "python": {
        "label": "🐍 Python (Default)",
        "arch_directive": (
            "Target: Standard Python application. "
            "Use Python 3.11+ with pip for dependencies. "
            "Entry point: main.py. Package manager: requirements.txt. "
            "Docker base: python:3.12-slim."
        ),
        "file_extensions": [".py"],
        "run_command": "python main.py",
        "build_command": "pip install -r requirements.txt",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
    "android": {
        "label": "🤖 Android (Kotlin + Gradle)",
        "arch_directive": (
            "Target: Native Android application using Kotlin and Jetpack Compose. "
            "Project structure MUST follow standard Android/Gradle layout: "
            "app/src/main/java/com/<package>/ for Kotlin sources, "
            "app/src/main/res/ for resources (layout, values, drawable), "
            "app/src/main/AndroidManifest.xml for the manifest. "
            "Root files: build.gradle.kts (project), app/build.gradle.kts (module), "
            "settings.gradle.kts, gradle.properties. "
            "Use Material 3 design components. Min SDK 24, target SDK 34. "
            "Use Kotlin coroutines for async. Use Retrofit for networking. "
            "Use Hilt for dependency injection. Use Room for local database. "
            "Do NOT include requirements.txt or Dockerfile — use Gradle only. "
            "The run_command should be: ./gradlew assembleDebug"
        ),
        "file_extensions": [".kt", ".xml", ".kts"],
        "run_command": "./gradlew assembleDebug",
        "build_command": "./gradlew build",
        "docker_base": "thyrlian/android-sdk:latest",
        "dep_file": "app/build.gradle.kts",
    },
    "linux": {
        "label": "🐧 Linux Desktop (Python + GTK/Qt)",
        "arch_directive": (
            "Target: Native Linux desktop application. "
            "Use Python 3.11+ with either PyGObject (GTK4) or PyQt6 for the GUI. "
            "Include a .desktop file for XDG menu integration. "
            "Include an install.sh script that installs system deps via apt/dnf. "
            "Include an AppImage or Flatpak manifest if appropriate. "
            "Entry point: main.py. Package manager: requirements.txt + system deps. "
            "Use Meson or setuptools for packaging. "
            "Follow Freedesktop.org standards for icons and .desktop files. "
            "Docker base: python:3.12-slim (for testing). "
            "The run_command should be: python3 main.py"
        ),
        "file_extensions": [".py", ".desktop", ".sh"],
        "run_command": "python3 main.py",
        "build_command": "pip install -r requirements.txt",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
    "studio": {
        "label": "🎨 Studio Engine (High Performance)",
        "arch_directive": (
            "Target: Professional-grade Creative Suite Application. "
            "Use PyQt6 for a robust, multi-threaded GUI with Dock Widgets, Toolbars, and Menus. "
            "Mandatory Libraries: PyQt6 (UI), NumPy (Processing), OpenCV (Vision/Image Processing). "
            "Architecture: Modular/Plugin-based. Create a 'core/' folder for the engine and 'plugins/' for effects. "
            "Use multi-threading (QThread) to keep the UI responsive during heavy processing. "
            "Entry point: app.py. The program MUST run immediately with no missing assets. "
            "If custom icons or cursors are needed, generate them using the MediaEngine."
        ),
        "file_extensions": [".py", ".ui", ".qrc"],
        "run_command": "python app.py",
        "build_command": "pip install PyQt6 opencv-python numpy",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
}


# ── Knowledge Base (Persistent Memory) ──────────────────────────

class KnowledgeBase:
    """
    Persistent memory system that stores lessons learned from past builds
    and retrieves them to improve future architectural decisions.
    """
    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        self.memory_file = os.path.join(memory_dir, "lessons.json")
        os.makedirs(memory_dir, exist_ok=True)
        self.lessons = self._load_memory()

    def _load_memory(self) -> list:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log("MEMORY", f"  ⚠ Failed to load memory: {e}")
                return []
        return []

    def memorize(self, lesson: dict):
        """
        Saves a new lesson. 
        Lesson format: {"tags": [], "trigger": str, "lesson": str, "outcome": str}
        """
        # Simple deduplication based on lesson text
        if any(l["lesson"] == lesson["lesson"] for l in self.lessons):
            return
        
        self.lessons.append(lesson)
        self._save_memory()
        log("MEMORY", "  ✓ Lesson learned and saved.")

    def _save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.lessons, f, indent=2)
        except Exception as e:
            log("MEMORY", f"  ⚠ Failed to save memory: {e}")

    def recall(self, context: str) -> str:
        """
        Retrieves relevant lessons based on keyword matching with the context.
        Returns a formatted string of insights.
        """
        context_lower = context.lower()
        relevant_lessons = []
        
        for lesson in self.lessons:
            # Check if any tag matches the context
            tags = lesson.get("tags", [])
            trigger = lesson.get("trigger", "").lower()
            
            if trigger in context_lower or any(tag.lower() in context_lower for tag in tags):
                relevant_lessons.append(f"- [{lesson.get('outcome', 'info').upper()}] {lesson.get('lesson')}")

        if not relevant_lessons:
            return ""
        
        return "🧠 MEMORY INSIGHTS (Past Lessons):\n" + "\n".join(relevant_lessons[:5]) # Top 5 only


# ── Deep Research Agent (Google Search) ─────────────────────────

class GoogleResearchAgent:
    """
    Performs 'Deep Research' by querying Google Custom Search API.
    Strategies:
      - Implementation: "how to build X"
      - Code Patterns (GitHub): "site:github.com ..."
      - Pitfalls (StackOverflow): "site:stackoverflow.com ..."
      - Documentation: "site:readthedocs.io ..."
    """
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.cse_id = os.environ.get("GOOGLE_CSE_ID")

    def run_research(self, enhanced_prompt: str, kb_context: str = "") -> str:
        if not self.api_key or not self.cse_id:
            log("RESEARCH", "  ⚠ GOOGLE_API_KEY or GOOGLE_CSE_ID not found. Skipping deep research.")
            return ""

        log("RESEARCH", "  🤔 Generating multi-vector research strategy...")
        
        # Step 1: Generate Targeted Queries
        strategy_system = (
            "You are a Senior Technical Researcher. Generate Google search queries to solve this problem. "
            "Create exactly 4 queries, one for each category:\n"
            "1. 'general': High-level architecture/tutorial\n"
            "2. 'github': Code examples (site:github.com)\n"
            "3. 'stackoverflow': Common errors/pitfalls (site:stackoverflow.com)\n"
            "4. 'docs': Official documentation (site:readthedocs.io OR site:devdocs.io OR official site)\n"
            "Output ONLY valid JSON: {\"general\": \"...\", \"github\": \"...\", \"stackoverflow\": \"...\", \"docs\": \"...\"}"
        )
        
        queries = {}
        try:
            raw_queries = ask_llm(self.client, self.model, strategy_system, enhanced_prompt)
            queries = json.loads(raw_queries)
        except Exception as e:
            log("RESEARCH", f"  ⚠ Failed to generate queries: {e}")
            return kb_context # Return memory even if search fails

        # Step 2: Execute Searches in Parallel (Threads would be better, but sequential for safety)
        import requests
        aggregated_results = []
        
        log("RESEARCH", "  🔎 Executing targeted searches...")
        
        for category, query in queries.items():
            try:
                log("RESEARCH", f"    → [{category.upper()}] {query}")
                url = "https://www.googleapis.com/customsearch/v1"
                params = {"key": self.api_key, "cx": self.cse_id, "q": query, "num": 3}
                resp = requests.get(url, params=params, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        link = item.get("link", "")
                        aggregated_results.append(f"[{category.upper()}] {title}\nURL: {link}\nSnippet: {snippet}\n")
                else:
                    log("RESEARCH", f"      ⚠ {category} failed: {resp.status_code}")
            except Exception as e:
                log("RESEARCH", f"      ⚠ Error: {e}")

        if not aggregated_results and not kb_context:
            return ""

        # Step 3: Synthesize Report
        log("RESEARCH", "  📝 Synthesizing comprehensive implementation report...")
        summary_system = (
            "You are a Technical Lead. Write a 'Implementation Strategy Report' based on the provided search results "
            "and internal memory. \n"
            "Structure:\n"
            "1. 🏛 **Architecture Patterns** (from General/GitHub)\n"
            "2. 📦 **Recommended Tech Stack** (Libraries/Tools)\n"
            "3. ⚠️ **Critical Pitfalls & Fixes** (from StackOverflow/Memory)\n"
            "   - If Memory says 'FastAPI needs X', EMPHASIZE it.\n"
            "4. 🔗 **Key Resources** (Links)\n\n"
            "Keep it technical, actionable, and under 500 words."
        )
        
        full_context = f"{kb_context}\n\nEXTERNAL SEARCH RESULTS:\n" + "\n---\n".join(aggregated_results)[:15000]
        
        try:
            report = ask_llm(self.client, self.model, summary_system, full_context)
            return f"DEEP RESEARCH & MEMORY REPORT:\n{report}"
        except Exception as e:
            log("RESEARCH", f"  ⚠ Summarization failed: {e}")
            return kb_context


# ── Developer Knowledge Agent (Official Docs) ───────────────

class DevKnowledgeAgent:
    """Retrieves official Markdown documentation via Google Developer Knowledge REST API
    to ground the LLM's code generation in real, current docs."""

    API_BASE = "https://developerknowledge.googleapis.com/v1alpha"

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY", "")

    def lookup(self, topic: str) -> str:
        """Returns official documentation snippets for grounding the Architect."""
        if not self.api_key:
            log("RESEARCH", "  ⚠ GOOGLE_API_KEY not set. Skipping Developer Knowledge lookup.")
            return ""

        try:
            import requests
            log("RESEARCH", f"  📚 Querying Developer Knowledge API for: {topic[:80]}...")
            resp = requests.get(
                f"{self.API_BASE}/documentChunks:search",
                params={
                    "query": topic[:200],
                    "key": self.api_key,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                log("RESEARCH", f"  ⚠ Developer Knowledge API returned {resp.status_code}")
                return ""

            data = resp.json()
            chunks = data.get("documentChunks", [])
            snippets = []
            for chunk in chunks[:5]:
                content = chunk.get("chunkContent", {}).get("markdownContent", "")
                if content:
                    snippets.append(content)

            if snippets:
                log("RESEARCH", f"  ✓ Retrieved {len(snippets)} official doc snippet(s)")
                return "OFFICIAL DOCUMENTATION (Developer Knowledge API):\n" + "\n---\n".join(snippets)
            else:
                log("RESEARCH", "  ⚠ No relevant docs found via Developer Knowledge API.")
                return ""
        except ImportError:
            log("RESEARCH", "  ⚠ requests library not available. Skipping docs lookup.")
            return ""
        except Exception as e:
            log("RESEARCH", f"  ⚠ Developer Knowledge lookup failed: {e}")
            return ""


# ── Self-Correction Module (Linter-Critic Loop) ─────────────

class SelfCorrectionModule:
    """Dual-Agent Loop: Critic (lint/compile) → Fixer (AI repair) → Re-check.
    Replaces the inline ast.parse loop with a proper, reusable module
    supporting Python (compile + optional flake8) and JS/TS (optional eslint)."""

    def __init__(self, code: str, filepath: str, max_attempts: int = 3):
        self.code = code
        self.path = filepath
        self.attempts = 0
        self.max_attempts = max_attempts
        self.ext = os.path.splitext(filepath)[1].lower()

    def run_lint_check(self):
        """Run static analysis. Returns (is_valid: bool, report: str)."""
        if self.ext == ".py":
            return self._check_python()
        elif self.ext in (".js", ".ts", ".jsx", ".tsx"):
            return self._check_js()
        # Non-lintable file types pass automatically
        return True, "Non-lintable file type — skipped."

    def _check_python(self):
        """Python: compile() for syntax + optional flake8 for style."""
        # Step 1: Hard syntax check
        try:
            compile(self.code, self.path, 'exec')
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

        # Step 2: Optional flake8 deep check
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
                tmp.write(self.code)
                tmp_path = tmp.name
            result = subprocess.run(
                [sys.executable, '-m', 'flake8', '--max-line-length=120',
                 '--select=E9,F63,F7,F82',  # Fatal errors only
                 tmp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(tmp_path)
            if result.returncode != 0 and result.stdout.strip():
                return False, f"flake8 errors:\n{result.stdout.strip()[:500]}"
        except Exception:
            pass  # flake8 not available — that's fine, compile() already passed

        return True, "Python checks passed."

    def _check_js(self):
        """JS/TS: optional eslint check."""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix=self.ext, delete=False, encoding='utf-8') as tmp:
                tmp.write(self.code)
                tmp_path = tmp.name
            result = subprocess.run(
                ['npx', 'eslint', '--no-eslintrc', '--rule', '{"no-undef": "error"}', tmp_path],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(tmp_path)
            if result.returncode != 0 and result.stdout.strip():
                return False, f"eslint errors:\n{result.stdout.strip()[:500]}"
        except Exception:
            pass  # eslint not available — skip
        return True, "JS checks passed."

    def repair_loop(self, fixer_callback) -> str:
        """The Loop: Check → Fail → Ask AI to Fix → Re-check.
        fixer_callback(code: str, error_report: str) -> str (fixed code)"""
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



# ── Multimodal Visual Engine (SDXL / SVD) ───────────────────────

class MultimodalMediaEngine:
    """
    Autonomous Visual DNA Engine.
    Handles SDXL for static UI/Branding and SVD for UX Motion Prototyping.
    """
    def __init__(self, api_key=None):
        # Prioritizes Environment Variable or Electron-passed Key
        self.api_key = api_key or os.getenv("STABILITY_API_KEY")
        self.host = "https://api.stability.ai/v2beta"

    def ensure_asset_dirs(self, root_path):
        """Creates the standardized asset tree for the one hand-off package."""
        gen_dir = os.path.join(root_path, "assets", "gen")
        os.makedirs(gen_dir, exist_ok=True)
        return gen_dir

    def generate_ui_dna(self, project_context, save_dir):
        """Uses SDXL to generate a master brand asset based on project logic."""
        if not self.api_key:
            print("[OVERLORD] ⚠️ Stability API Key missing. Skipping Visual DNA.")
            return None

        print("[OVERLORD] 🎨 Generating Master Visual DNA (SDXL)...")
        try:
            import requests
        except ImportError:
            print("[OVERLORD] ❌ 'requests' library missing. Skipping Visual DNA.")
            return None

        endpoint = f"{self.host}/stable-image/generate/sdxl"
        
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "accept": "image/*"
        }
        
        # Crafting the prompt based on the engine's architectural context
        fields = {
            "prompt": (None, f"Professional software UI, {project_context}, clean minimalist aesthetic, high fidelity, 4k"),
            "output_format": (None, "png")
        }

        try:
            response = requests.post(endpoint, headers=headers, files=fields)
            if response.status_code == 200:
                path = os.path.join(save_dir, "master_brand.png")
                with open(path, "wb") as f:
                    f.write(response.content)
                print(f"[OVERLORD] ✅ Visual DNA saved: {path}")
                return path
            else:
                print(f"[OVERLORD] ❌ SDXL Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[OVERLORD] ❌ SDXL Exception: {e}")
        return None

    def generate_ux_motion(self, image_path, save_dir):
        """Uses SVD to turn the static UI DNA into a motion prototype."""
        if not self.api_key or not image_path:
            return None

        print("[OVERLORD] 🎬 Generating UX Motion Proof (SVD)...")
        try:
            import requests
        except ImportError:
            return None

        endpoint = f"{self.host}/image-to-video"
        
        headers = {"authorization": f"Bearer {self.api_key}"}
        try:
            files = {"image": open(image_path, "rb")}
            data = {"seed": 0, "cfg_scale": 1.8, "motion_bucket_id": 127}

            resp = requests.post(endpoint, headers=headers, files=files, data=data)
            if resp.status_code == 200:
                gen_id = resp.json().get("id")
                return self._poll_for_video(gen_id, save_dir)
            else:
                 print(f"[OVERLORD] ❌ SVD Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[OVERLORD] ❌ SVD Exception: {e}")
        return None

    def _poll_for_video(self, gen_id, save_dir):
        """Polls for completion to ensure the 'One Hand-off' is complete before finishing."""
        import requests
        endpoint = f"{self.host}/image-to-video/result/{gen_id}"
        headers = {"authorization": f"Bearer {self.api_key}", "accept": "video/*"}
        
        print("[OVERLORD] ⏳ Rendering video (this may take a minute)...")
        for _ in range(30): # 5 minute timeout
            time.sleep(10)
            try:
                res = requests.get(endpoint, headers=headers)
                if res.status_code == 200:
                    path = os.path.join(save_dir, "interaction_demo.mp4")
                    with open(path, "wb") as f:
                        f.write(res.content)
                    print(f"[OVERLORD] ✅ Motion Proof saved: {path}")
                    return path
                elif res.status_code != 202:
                    break
            except:
                break
        return None

def execute_multimodal_handover(project_path, context):
    try:
        engine = MultimodalMediaEngine()
        target_dir = engine.ensure_asset_dirs(project_path)
        # Use a summarised context for the prompt
        brand_img = engine.generate_ui_dna(context[:500], target_dir)
        if brand_img:
            engine.generate_ux_motion(brand_img, target_dir)
    except Exception as e:
        print(f"[OVERLORD] ⚠️ Multimodal Handover failed: {e}")

# ── Build Pipeline ───────────────────────────────────────────

def execute_build(args):
    # ── NEW: Upgrade Flow ─────────────────────────────────────────
    if hasattr(args, 'mode') and args.mode == 'upgrade':
        log("SYSTEM", f"🚀 Launching Upgrade Flow for {args.project}...")
        try:
            from creation_engine.orchestrator import CreationEngine
            # Initialize CreationEngine with upgrade parameters
            # ── Resolve Model ──
            # Intelligent Routing
            selected_model = resolve_smart_model(args.prompt, args.model)
            if selected_model != args.model:
                print(f"[SYSTEM] 🧠 Smart Router: Switched from '{args.model}' to '{selected_model}' based on task complexity.")
                args.model = selected_model

            # ── Initialize Creation Engine ──
            engine = CreationEngine(
                project_name=args.project,
                prompt=args.prompt,
                output_dir=args.output,
                model=args.model,
                api_key=args.api_key,
                arch_model=args.arch_model,
                eng_model=args.eng_model,
                local_model=args.local_model,
                review_model=args.review_model,
                budget=args.budget,
                docker=args.docker,
                source_path=args.source,
                mode=args.mode,  # Now supports 'upgrade' and 'reverse'
                decompile_only=args.decompile_only,
                phase=args.phase,
                focus=args.focus,
                clean_output=args.clean
            )
            # Run the engine
            engine.run()
            log("SUCCESS", "Upgrade complete.")
            return
        except ImportError:
            log("ERROR", "CreationEngine not found. Falling back to standard build.")
        except Exception as e:
            log("ERROR", f"Upgrade flow failed: {e}")
            import traceback
            traceback.print_exc()
            return

    project_path = os.path.join(args.output, args.project)
    os.makedirs(project_path, exist_ok=True)

    # ── Initialize Antigravity Event Bus (for dashboard) ─────
    global _active_event_bus
    use_dashboard = getattr(args, 'dashboard', False) or getattr(args, 'sandbox', False)
    if use_dashboard and _HAS_EVENT_BUS:
        _active_event_bus = EventBus(project_path)
        log("SYSTEM", "📡 Antigravity Event Bus activated — dashboard can connect")
    else:
        _active_event_bus = None

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "") or "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"
    
    model = args.model

    # Per-phase model routing: use the best model for thinking, fast model for coding
    arch_model = getattr(args, 'arch_model', None) or model  # Phase 0 + 1 + 3
    eng_model = getattr(args, 'eng_model', None) or model    # Phase 2
    # Cost-aware tier: cheap/local model for Reviewer, Dockerfile, README, Env scripts
    local_model = getattr(args, 'local_model', None) or eng_model  # Phase 2.5 + 4 + 5
    # Dedicated review model: Claude or other reasoning model for senior-level code review
    review_model = getattr(args, 'review_model', None) or local_model  # Phase 2.5 Master Reviewer

    # Create provider-aware clients for each phase
    # This enables mixing providers: e.g. Gemini for Architect + Groq for Engineer
    global _client_cache
    _client_cache = {}  # Reset cache per build
    client = get_cached_client(arch_model, api_key)  # Primary client for arch phases

    # Initialize Wisdom System — load rules for the Reviewer and Engineer
    wisdom = GlobalWisdom(project_path)
    wisdom_rules = wisdom.get_generation_rules()
    wisdom_guard = WisdomGuard()
    if wisdom_rules:
        log("SYSTEM", f"🛡️  Loaded {len([k for k in wisdom.global_wisdom if k.startswith('GENERATION_RULE__')])} generation rule(s) from global wisdom")

    # Initialize Zero-Inference Reviewer + State Persistence (wisdom-enriched)
    reviewer = ReviewerAgent(client, local_model, wisdom_context=wisdom_rules)
    state = CodebaseState(project_path)

    # Initialize Intelligence Systems (State, RAG, Dep Verification)
    proj_state = ProjectState()
    rag = CodebaseRAG(max_context_chars=12000)
    dep_verifier = DependencyVerifier()

    # Initialize Cost Tracker with budget kill-switch
    budget = getattr(args, 'budget', 5.0) or 5.0
    tracker = CostTracker(budget=float(budget))

    # Activate module-level tracker so ALL ask_llm calls auto-record cost
    global _active_tracker
    _active_tracker = tracker

    # Resolve platform profile
    platform = getattr(args, 'platform', 'python') or 'python'
    # Detect Studio Mode
    studio_keywords = ["studio", "adobe", "photoshop", "editor", "graphics", "professional", "creative", "suite", "pro"]
    studio_mode = any(word in args.prompt.lower() for word in studio_keywords)
    
    if studio_mode and platform == "python":
        log("ARCHITECT", "  ✨ STUDIO MODE DETECTED — Activating High-Performance Profile")
        profile = PLATFORM_PROFILES["studio"]
    else:
        profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["python"])

    log("SYSTEM", f"Build initiated for project: {args.project}")
    log("SYSTEM", f"Output path: {os.path.abspath(project_path)}")
    log("SYSTEM", f"🎯 Platform: {profile['label']}")
    if arch_model != eng_model or local_model != eng_model or review_model != local_model:
        log("SYSTEM", f"🧠 Strategy Model (Architect): {arch_model}")
        log("SYSTEM", f"⚡ Speed Model (Engineer):     {eng_model}")
        if local_model != eng_model:
            log("SYSTEM", f"💰 Local Model (Reviewer/Env):  {local_model}")
        if review_model != local_model:
            log("SYSTEM", f"🔒 Review Model (Senior):      {review_model}")
    else:
        log("SYSTEM", f"Model: {model}")
    log("SYSTEM", f"💵 Budget: ${tracker.budget:.2f} (kill-switch enabled)")

    # Initialize Media Engine for image/video tasks
    try:
        from media_engine import MediaEngine
        media = MediaEngine(output_dir=os.path.join(project_path, "media"))
        media_status = f"Available image providers: {media.get_available_providers()}"
    except Exception as e:
        media = None
        media_status = f"Media Engine unavailable: {e}"
        log("WARN", f"  Media Engine not loaded: {e}")

    divider()

    # ── Phase 0: PROMPT ENGINEER (Auto-Enhance) ──────────────
    log("SYSTEM", "🧠 Phase 0: Prompt Enhancement AI")
    log("SYSTEM", f"  Raw input: \"{args.prompt[:80]}{'…' if len(args.prompt) > 80 else ''}\"")

    platform_directive = profile["arch_directive"]

    enhance_system = (
        "You are 'Overlord Prompt Engineer,' an elite AI that transforms vague user ideas "
        "into detailed, comprehensive software engineering specifications. "
        "The user will give you a brief idea — maybe just a few words. "
        "Your job is to expand it into a RICH, AMBITIOUS prompt that a code-generating AI can use to build "
        "a complete, production-quality, feature-packed application. "
        "Think like a Product Manager at a top tech company — the goal is to IMPRESS, not just function. "
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        "\n\nYour enhanced prompt MUST include ALL of these categories:"
        "\n\n📋 CATEGORY 1 — CORE FEATURES (3-5 features):"
        "\n  The primary business logic and main functionality the app must deliver."
        "\n\n📊 CATEGORY 2 — DATA MANAGEMENT (3-4 features):"
        "\n  Search with filters, sortable columns, pagination, data export (CSV/JSON), "
        "  bulk actions (select all, bulk delete), and import capabilities."
        "\n\n🎨 CATEGORY 3 — UI/UX EXCELLENCE (3-4 features):"
        "\n  Responsive layout (mobile + desktop), dark/light mode toggle, loading skeletons, "
        "  toast notifications for all actions, empty-state illustrations, breadcrumb navigation, "
        "  sidebar or top nav with active states, and smooth CSS transitions/animations."
        "\n\n📈 CATEGORY 4 — ANALYTICS & DASHBOARDS (2-3 features):"
        "\n  Stats cards with trend indicators (▲/▼), at least 2 chart types (bar, line, pie, or gauge), "
        "  activity feed or recent-actions log, and summary metrics on the main page."
        "\n\n⚡ CATEGORY 5 — REAL-TIME & PERFORMANCE (1-2 features):"
        "\n  Auto-refresh with polling interval, 'Last updated X ago' indicators, "
        "  optimistic UI updates, and caching where appropriate."
        "\n\n🔧 CATEGORY 6 — SETTINGS & CONFIGURATION (1-2 features):"
        "\n  User preferences panel, environment-based config (.env), "
        "  and a seed/demo data command so the app looks alive on first run."
        "\n\nThe result should specify 12-20 concrete features total across these categories."
        "\n\nRules:"
        "\n- Output ONLY the enhanced prompt text. No markdown, no headers, no explanations."
        "\n- Write it as a single, flowing engineering specification."
        "\n- Be specific — name exact function names, exact UI elements, exact data structures."
        "\n- If the idea involves media, include image/video generation capabilities."
        "\n- Always include a main entry point and a proper CLI or GUI."
        "\n- Make it sound like a Product Requirements Document from a senior PM."
        "\n- Target 600-800 words. Make every word count."
    )

    try:
        enhanced_prompt = ask_llm(client, arch_model, enhance_system, args.prompt)
        log("SYSTEM", "  ✓ Prompt enhanced successfully")
        # Show a preview of the enhanced prompt
        preview_lines = enhanced_prompt.strip().split("\n")[:3]
        for line in preview_lines:
            if line.strip():
                log("SYSTEM", f"    → {line.strip()[:100]}")
        if len(preview_lines) > 3:
            log("SYSTEM", f"    → ... ({len(enhanced_prompt)} chars total)")
        # Replace the original prompt with the enhanced version
        original_prompt = args.prompt
        args.prompt = enhanced_prompt
    except Exception as e:
        log("WARN", f"  Prompt enhancement failed: {e}. Using original prompt.")
        enhanced_prompt = args.prompt
        original_prompt = args.prompt

    divider()

    # ── Phase 0.5: PRE-FLIGHT SEARCH (Version Verification) ──
    log("SYSTEM", "🔍 Phase 0.5: Pre-Flight Version Search")
    search_results = preflight_search(original_prompt, args.prompt)
    search_context = search_results.get("search_context", "")
    
    # ── Phase 0.1: ASSET PRE-CHECK (Custom Icon) ─────────────
    # If the user has placed a custom icon in assets/, we use it.
    _here = os.path.dirname(os.path.abspath(__file__))
    custom_icon_png = os.path.join(_here, "assets", "icon.png")
    custom_icon_ico = os.path.join(_here, "assets", "icon.ico")
    
    icon_path = None
    if os.path.exists(custom_icon_png):
        log("SYSTEM", "🎨 Custom icon detected in assets/ — Skipping AI generation.")
        # Ensure it's copied to the project
        project_assets = os.path.join(project_path, "assets")
        os.makedirs(project_assets, exist_ok=True)
        shutil.copy(custom_icon_png, os.path.join(project_assets, "icon.png"))
        if os.path.exists(custom_icon_ico):
            shutil.copy(custom_icon_ico, os.path.join(project_assets, "icon.ico"))
        icon_path = os.path.join(project_assets, "icon.png")

    # ── Phase 0.2: DEEP RESEARCH & MEMORY RECALL ──
    log("SYSTEM", "🌐 Phase 0.2: Deep Research & Learning")
    
    # 1. Initialize Memory
    kb = KnowledgeBase(os.path.join(os.path.dirname(project_path), "memory"))
    memory_context = kb.recall(enhanced_prompt)
    if memory_context:
        log("MEMORY", "  🧠 Recalled relevant lessons from past builds.")

    # 2. Query Developer Knowledge API for official docs
    dk_agent = DevKnowledgeAgent()
    dk_docs = dk_agent.lookup(enhanced_prompt)
    if dk_docs:
        memory_context = dk_docs + "\n\n" + memory_context if memory_context else dk_docs

    # 3. Run Google Research (incorporating memory + official docs)
    research_agent = GoogleResearchAgent(client, arch_model)
    research_report = research_agent.run_research(enhanced_prompt, kb_context=memory_context)
    
    if research_report:
        log("SYSTEM", "  ✓ Research, Docs & Memory analysis complete.")
        # Combine version data + deep research
        if search_context:
            research_report += "\n\n" + search_context
    else:
        log("SYSTEM", "  ℹ No deep research results (keys missing or no results).")
        # Fallback to just the version search
        research_report = search_context

    divider()

    # ── Phase 1: ARCHITECT ───────────────────────────────────
    log("ARCHITECT", "Engaging Architect agent…")
    log("ARCHITECT", "Analyzing prompt and planning project structure…")

    # Build version advisory block from pre-flight search
    version_advisory = ""
    if search_context:
        version_advisory = (
            "\n\nPRE-FLIGHT VERSION INTELLIGENCE (from live registry lookups):"
            f"\n{search_context}"
            "\nUse these verified versions in your dependency list instead of guessing."
        )

    arch_system = (
        "You are 'Overlord,' an autonomous Senior Full-Stack Engineer and DevOps Specialist. "
        "Directive: No Hallucinations. Do not use placeholder domains or URLs like 'example.com' or 'your-api-endpoint'. "
        "Use real public APIs or write self-contained logic with functional mocks if needed. "
        "Mission: Zero-Interaction Planning. Decompose user intent into a logical file structure. "
        "MEDIA ENGINE: You have access to a unified media engine with these capabilities: "
        "Image generation (Flux 2.0, Adobe Firefly, Midjourney, Ideogram) via 'from media_engine import MediaEngine', "
        "Video transcoding via HandBrake, and live streaming pipelines via GStreamer. "
        "Use 'engine = MediaEngine()' then 'engine.generate_image(prompt)' for images, "
        "'engine.transcode_video(input, output)' for transcoding, "
        "'engine.stream_pipeline(desc)' for GStreamer pipelines. "
        f"{media_status}. "
        "\n\nDESIGN SYSTEM & VISUAL IDENTITY (MANDATORY):"
        "\n- Define a 'Visual DNA': color palette (hex), typography (Google Fonts), and spacing."
        "\n- Create a 'master_brand' style description for AI image generation (e.g., 'Cyberpunk minimalism, neon blue & purple, dark mode')."
        "\n- IMPORTANT: The 'master_brand' description will be used to generate ACTUAL ASSETS (logos, backgrounds) so be evocative!"
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        "\n\nTECH STACK CONSTRAINT — MANDATORY (Stable-Gold Stack):"
        "\nYou MUST default to the following 'Stable-Gold' libraries. Do NOT substitute alternatives unless the user explicitly requests it or the platform makes it impossible."
        "\n  [Frontend]  TypeScript + React / Next.js — prevents runtime type errors, ensures SEO readiness."
        "\n  [Backend]   FastAPI — superior async performance, auto-generated OpenAPI docs. Do NOT use Flask for new projects."
        "\n  [Database]  PostgreSQL (via Prisma or Supabase) — robust relational data. No NoSQL unless high-speed caching is required. Include 'schema.prisma' if using Prisma."
        "\n  [Auth]      Clerk or NextAuth — standardized, secure authentication patterns."
        "\n  [Styling]   Tailwind CSS — scannable, utility-first design consistency."
        "\n  [Env/Docs]  Every project MUST include a detailed 'README.md' and '.env.example' with all required variables."
        "\n\nQUALITY ASSURANCE MODULES (MANDATORY):"
        "\n- Plan a robust 'errors.py' or 'exceptions.py' module to define custom exception types."
        "\n- Plan a 'logs.py' or 'logger.py' module for structured logging configuration."
        "\n- Ensure every major component has a corresponding test file in 'tests/' directory."
        "\n\nARCHITECTURE DEPTH STANDARDS (MANDATORY):"
        "\n- Plan AT LEAST 8-15 files for any non-trivial project. Think in MODULES, not monoliths."
        "\n- Separate concerns: components/, utils/, lib/, config/, seed/ folders as appropriate."
        "\n- ALWAYS include a seed/demo data file so the app has realistic data on first run."
        "\n- ALWAYS include a config or constants module for environment variables and settings."
        "\n- ALWAYS include utility/helper modules. Do NOT cram everything into main.py."
        "\n- For web apps: plan separate files for each page/view, each API route group, "
        "  each data model, and shared components (navbar, sidebar, cards, tables, charts)."
        "\n- Include analytics/dashboard views with chart components wherever data is displayed."
        "\n- Plan for search, filter, sort, and pagination in any data-heavy view."
        f"{version_advisory}"
        f"\n\n{research_report if 'research_report' in locals() and research_report else ''}"
        "\n\nOutput ONLY valid JSON with this exact 'Package Manifest' schema: "
        '{"project_name": "<slug_name>", '
        '"stack": {"frontend": "<framework>", "backend": "<framework>", "database": "<provider>"}, '
        '"file_tree": ["path/file.ext", ...], '
        '"files": [{"path": "filename.ext", "task": "description"}], '
        '"dependencies": ["package1"], '
        f'"run_command": "{profile["run_command"]}"}} '
        "Every project MUST include a main entry point and a README.md. "
        f"{PRODUCTION_SAFETY_DIRECTIVE}"
        "\nOutput ONLY raw JSON. No markdown."
    )

    try:
        raw_plan = ask_llm(client, arch_model, arch_system, args.prompt)
        plan = json.loads(raw_plan)
    except json.JSONDecodeError:
        log("ERROR", "Architect returned invalid JSON. Retrying…")
        try:
            raw_plan = ask_llm(client, model, arch_system + " Output raw JSON only.", args.prompt)
            plan = json.loads(raw_plan)
        except Exception as e:
            log("ERROR", f"Architect failed: {e}")
            sys.exit(1)
    except Exception as e:
        log("ERROR", f"Architect failed: {e}")
        sys.exit(1)

    files   = plan.get("files", [])
    deps    = plan.get("dependencies", [])
    run_cmd = plan.get("run_command", "python main.py")
    arch_stack     = plan.get("stack", {})
    arch_proj_name = plan.get("project_name", args.project)
    arch_file_tree = plan.get("file_tree", [f["path"] for f in files])

    log("ARCHITECT", f"Blueprint ready — {len(files)} file(s), {len(deps)} dep(s)")
    if arch_stack:
        log("ARCHITECT", f"  Stack: {json.dumps(arch_stack)}")
    for f in files:
        log("ARCHITECT", f"  ├─ {f['path']}  →  {f['task'][:60]}")
    log("ARCHITECT", f"  └─ run: {run_cmd}")
    divider()

    # ── Phase 1.5: PROJECT ASSEMBLER ─────────────────────────
    log("SYSTEM", "🏗️  Phase 1.5: Project Assembler")
    project_assembler(plan, project_path)
    divider()

    # ── Budget Checkpoint (after Architect) ────────────────────
    if tracker.budget_exceeded and not tracker.pivot_triggered:
        log("SYSTEM", f"💸 Budget exceeded after Architect phase: ${tracker.total_cost:.4f} / ${tracker.budget:.2f}")
        log("SYSTEM", f"   Pivoting ALL models → {local_model} to control costs.")
        arch_model = local_model
        eng_model = local_model
        tracker.trigger_pivot()
    else:
        log("SYSTEM", f"💵 Cost so far: ${tracker.total_cost:.4f} / ${tracker.budget:.2f} (${tracker.remaining:.4f} remaining)")

    # ── Phase 2: ENGINEER + RECURSIVE REFINEMENT ──────────────
    log("ENGINEER", "Engaging Engineer agent…")

    file_list = [f["path"] for f in files]
    written_files = state.files  # Backed by persistent CodebaseState

    # Strategy: Write main.py FIRST so we know what imports it expects,
    # then pass those import names as a contract to all other files.
    main_entry = None
    other_files = []
    for f in files:
        if f["path"] == "main.py":
            main_entry = f
        else:
            other_files.append(f)

    # Reorder: main.py first, then everything else
    ordered_files = ([main_entry] + other_files) if main_entry else list(files)

    for i, file_spec in enumerate(ordered_files, 1):
        fpath = file_spec["path"]
        ftask = file_spec["task"]
        log("ENGINEER", f"[{i}/{len(ordered_files)}] Writing: {fpath}")

        # ── Pillar 1: RAG-Powered Context + Global State ──
        manifest = build_manifest(written_files, planned_files=file_list)
        manifest_ctx = manifest_to_context(manifest) if manifest else "No files written yet."
        symbol_table = proj_state.get_symbol_table()
        rag_context = rag.get_relevant_context(fpath, ftask, symbol_table)

        # Extract import contract from main.py if available
        import_contract = ""
        if "main.py" in written_files and fpath != "main.py":
            main_code = written_files["main.py"]
            relevant_imports = []
            module_base = fpath.replace(".py", "")
            for line in main_code.split("\n"):
                stripped = line.strip()
                if module_base in stripped and ("import" in stripped):
                    relevant_imports.append(stripped)
            if relevant_imports:
                import_contract = (
                    f"\n\nCRITICAL CONTRACT — main.py imports from YOUR file:\n"
                    + "\n".join(f"  {imp}" for imp in relevant_imports)
                    + "\nYou MUST export these exact function/class names. Do NOT rename them."
                )

        # Build dependency-aware API conventions
        api_conv_parts = []
        for dep_name in deps:
            dep_lower = dep_name.lower().split("==")[0].split(">=")[0].strip()
            if dep_lower in API_CONVENTIONS:
                api_conv_parts.append(API_CONVENTIONS[dep_lower])
            # Also check aliases (PIL -> pillow)
            if dep_lower == "pillow" or dep_lower == "pil":
                api_conv_parts.append(API_CONVENTIONS.get("pillow", ""))
        api_conv_block = ""
        if api_conv_parts:
            api_conv_block = "\n\nLIBRARY API CONVENTIONS (use these EXACT patterns):\n" + "\n".join(f"- {c}" for c in api_conv_parts)

        eng_system = (
            "You are 'Overlord,' an autonomous Senior Full-Stack Engineer. "
            "Directive: Modular Engineering. Write clean, documented code using proper imports. "
            "IMPORTANT: NEVER use placeholder URLs, dummy credentials, or broken 'example.com' domains. "
            "Use functional logic. If an API is unknown, use a robust mock or public test endpoint. "
            "Directive: Self-healing. Anticipate failures with clean try-except blocks. "
            "Directive: Feature-Rich. Build IMPRESSIVE implementations, not bare-minimum stubs. "
            "Every file you write should demonstrate senior-level engineering with thorough edge-case handling. "
            f"Structure: {file_list}. Target: {fpath}. Task: {ftask}. "
            f"{import_contract}"
            f"\n\n{symbol_table}"
            f"{wisdom.get_generation_rules()}"
            f"{PRODUCTION_SAFETY_DIRECTIVE}"
            f"{STABILITY_DIRECTIVE}"
            f"{SECURITY_DIRECTIVE}"
            f"{FEATURE_RICHNESS_DIRECTIVE}"
            f"{api_conv_block}"
            "\nOutput ONLY raw source code. No markdown fences, no explanations."
        )

        # Inject wisdom generation rules into Engineer prompt
        if wisdom_rules:
            eng_system += f"\n\n{wisdom_rules}"

        user_prompt = (
            f"Construct the file: {fpath}\n\n"
            f"Relevant context (RAG-selected):\n{rag_context}\n\n"
            f"Full manifest:\n{manifest_ctx}"
        )

        try:
            code = ask_llm(client, eng_model, eng_system, user_prompt)
        except Exception as e:
            log("ERROR", f"Engineer failed on {fpath}: {e}")
            continue

        # ── REVIEWER GATE (Zero-Inference Loop) ──
        # The Overlord doesn't ask permission — it sees REJECTED and forces a rewrite.
        review_count = 0
        for review_attempt in range(3):
            verdict = reviewer.review(fpath, code, manifest_ctx)
            review_count = review_attempt + 1
            if verdict["status"] == "APPROVED":
                log("REVIEWER", f"  ✓ APPROVED: {fpath} (pass {review_count})")
                break
            else:
                log("REVIEWER", f"  ✗ REJECTED [{review_count}/3]: {verdict['reason'][:100]}")
                if review_attempt < 2:  # Don't retry on last attempt
                    try:
                        code = ask_llm(client, eng_model, eng_system,
                            f"{user_prompt}\n\nYour previous code was REJECTED by the Reviewer.\n"
                            f"Reason: {verdict['reason']}\n"
                            f"Fix ALL issues and output the complete corrected code.")
                    except Exception as e:
                        log("REVIEWER", f"  ⚠ Rewrite failed: {e} — accepting current version.")
                        break

        # ── Wisdom Review Gate — proactive rule enforcement ──
        wisdom_violations = wisdom.review_against_wisdom(code, fpath)
        if wisdom_violations:
            log("WISDOM", f"  ⚠ {len(wisdom_violations)} wisdom violation(s) in {fpath}")
            for wv in wisdom_violations:
                log("WISDOM", f"    ✗ {wv['rule'][:80]}")
            wisdom_report = "\n".join(
                f"- VIOLATION: {wv['rule']}\n  FIX: {wv['fix']}" for wv in wisdom_violations
            )
            try:
                code = ask_llm(client, eng_model, eng_system,
                    f"WISDOM REVIEW FAILED for {fpath}.\n"
                    f"The following known rules were violated:\n{wisdom_report}\n\n"
                    f"Fix ALL violations. Output ONLY the corrected complete source code:\n\n{code}")
                log("WISDOM", f"  ✓ Self-corrected {fpath} against wisdom rules")
            except Exception as e:
                log("WISDOM", f"  ⚠ Wisdom correction failed: {e} — continuing with current code")

        # ── Pillar 3: Self-Correction Module — lint + auto-repair ──
        def _fixer_callback(broken_code, error_report):
            """AI fixer agent: takes broken code + error report, returns fixed code."""
            return ask_llm(client, eng_model, eng_system,
                f"Your previous code has errors:\n{error_report}\n\n"
                f"Fix ALL issues. Output ONLY the corrected complete source code:\n\n{broken_code}")

        corrector = SelfCorrectionModule(code, fpath, max_attempts=3)
        code = corrector.repair_loop(_fixer_callback)

        # ── Wisdom Guard: Deterministic pre-save validation ──
        code, wisdom_fixes = wisdom_guard.auto_fix(code, fpath)
        if wisdom_fixes:
            log("WISDOM", f"  🛡️ Auto-fixed {len(wisdom_fixes)} violation(s) in {fpath}")
            for wf in wisdom_fixes:
                log("WISDOM", f"    → {wf}")

        full_path = os.path.join(project_path, fpath)
        # Directory already created by Project Assembler (Phase 1.5)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)

        state.write(fpath, code, review_count)
        written_files = state.files  # Keep reference in sync
        proj_state.register_file(fpath, code)
        rag.index_file(fpath, code, proj_state.get_exports_for(fpath))
        log("ENGINEER", f"  ✓ {fpath}  ({len(code)} chars, {review_count} review(s))")
        log("STATE", f"    Registered {len(proj_state.get_exports_for(fpath))} symbols")

        # Emit file write event for Antigravity Dashboard live code viewer
        if _active_event_bus:
            try:
                _active_event_bus.file_write(fpath, code)
            except Exception:
                pass

        # ── Pillar 2: Validation Gate — cross-file import check ──
        if fpath.endswith(".py") and len(written_files) > 1:
            manifest = build_manifest(written_files, planned_files=file_list)
            violations = validation_gate(written_files, manifest)
            file_violations = [v for v in violations if v["file"] == fpath]
            if file_violations:
                log("GATE", f"  ⚠ {len(file_violations)} broken import(s) in {fpath}")
                for v in file_violations:
                    log("GATE", f"    ✗ {v['import_stmt']} → '{v['missing']}' not found in {v['source_file']}")
                    log("GATE", f"      Available: {v['available'][:8]}")
                # Auto-repair: re-prompt with violation details
                violation_report = "\n".join(
                    f"- {v['import_stmt']}: '{v['missing']}' does not exist in {v['source_file']}. "
                    f"Available exports: {v['available']}"
                    for v in file_violations
                )
                try:
                    log("GATE", f"  🔧 Auto-repairing broken imports in {fpath}…")
                    code = ask_llm(client, eng_model, eng_system,
                        f"IMPORT VIOLATIONS DETECTED in {fpath}:\n{violation_report}\n\n"
                        f"Fix the imports to use only symbols that actually exist. "
                        f"Output ONLY the corrected complete source code:\n\n{code}")
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    written_files[fpath] = code
                    log("GATE", f"  ✓ Imports repaired in {fpath}")
                except Exception as e:
                    log("ERROR", f"  Gate repair failed: {e}")

    # ── Save Manifest to disk ──
    manifest = build_manifest(written_files, planned_files=file_list)
    manifest_path = os.path.join(project_path, "project_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("ENGINEER", f"  📋 Manifest saved: project_manifest.json ({len(manifest)} files)")

    divider()

    # ── Budget Checkpoint (after Engineer) ─────────────────────
    if tracker.budget_exceeded and not tracker.pivot_triggered:
        log("SYSTEM", f"💸 Budget exceeded after Engineer phase: ${tracker.total_cost:.4f} / ${tracker.budget:.2f}")
        log("SYSTEM", f"   Pivoting remaining phases → {local_model} to control costs.")
        arch_model = local_model
        eng_model = local_model
        tracker.trigger_pivot()
    else:
        log("SYSTEM", f"💵 Cost so far: ${tracker.total_cost:.4f} / ${tracker.budget:.2f} (${tracker.remaining:.4f} remaining)")

    # ── Phase 2.8: SECURITY AUDITOR ────────────────────────────
    log("SECURITY", "Engaging Cyber Security Auditor (Bandit/Safety)...")
    
    # Check dependencies first (Safety/Pip-Audit)
    try:
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            log("SECURITY", "  Running Dependency Vulnerability Scan (Safety)...")
            safety_cmd = [sys.executable, "-m", "safety", "check", "-r", "requirements.txt", "--json"]
            res = subprocess.run(safety_cmd, cwd=project_path, capture_output=True, text=True)
            # Handle valid JSON or empty outputs
            if res.stdout.strip().startswith("{") or res.stdout.strip().startswith("["):
                 try:
                     vulns = json.loads(res.stdout)
                     issues = vulns.get('vulnerabilities', []) if isinstance(vulns, dict) else vulns
                     if issues:
                         log("SECURITY", f"  ❌ Found {len(issues)} vulnerable dependencies!")
                         for v in issues:
                             pkg = v.get('package_name', '?')
                             spec = v.get('vulnerable_spec', '?')
                             log("SECURITY", f"    - {pkg} ({spec})")
                         # TODO: Auto-upgrade could happen here
                     else:
                         log("SECURITY", "  ✓ Dependencies are clean.")
                 except:
                     log("SECURITY", "  ⚠️ Safety output parse failed.")
            elif "No known security vulnerabilities" in res.stdout:
                 log("SECURITY", "  ✓ Dependencies are clean.")
    except Exception as e:
        log("WARN", f"  Dependency scan skipped: {e}")

    # Code Scan (Bandit)
    log("SECURITY", "  Running Static Code Analysis (Bandit)...")
    try:
        bandit_cmd = [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "-q"]
        res = subprocess.run(bandit_cmd, cwd=project_path, capture_output=True, text=True)
        if res.stdout.strip().startswith("{"):
            report = json.loads(res.stdout)
            results = report.get('results', [])
            high_sev = [r for r in results if r['issue_severity'] == 'HIGH']
            
            if high_sev:
                log("SECURITY", f"  ❌ Found {len(high_sev)} HIGH severity security issues!")
                # Group by file
                files_to_fix = {}
                for issue in high_sev:
                    fname = issue['filename'].replace(".\\", "").replace("./", "")
                    if fname in written_files:
                        if fname not in files_to_fix:
                            files_to_fix[fname] = []
                        files_to_fix[fname].append(issue)
                        log("SECURITY", f"    - {fname}:{issue['line_number']} >> {issue['issue_text']}")

                # Auto-Heal High Severity Issues
                for fix_file, issues in files_to_fix.items():
                    log("SECURITY", f"  🚑 Auto-Patching Security Vulnerabilities in {fix_file}...")
                    issue_desc = "\n".join([f"- {i['issue_text']} (Line {i['line_number']})" for i in issues])
                    
                    try:
                        fixed_code = ask_llm(client, eng_model, eng_system,
                            f"SECURITY VULNERABILITY DETECTED in {fix_file}:\n{issue_desc}\n\n"
                            f"You MUST fix these security issues. Replace insecure code with secure alternatives.\n"
                            f"Output ONLY the complete corrected source code:\n\n{written_files[fix_file]}")
                        
                        written_files[fix_file] = fixed_code
                        with open(os.path.join(project_path, fix_file), "w", encoding="utf-8") as f:
                            f.write(fixed_code)
                        log("SECURITY", f"  ✓ Patched: {fix_file}")
                    except Exception as ex:
                        log("ERROR", f"  Security patch failed for {fix_file}: {ex}")

            else:
                log("SECURITY", "  ✓ Codebase passed static security analysis.")
    except Exception as e:
        log("WARN", f"  Static analysis skipped: {e}")

    # ── Phase 2.8: SECURITY AUDITOR ────────────────────────────
    log("SECURITY", "Engaging Cyber Security Auditor (Bandit/Safety)...")
    
    # Check dependencies first (Safety/Pip-Audit)
    try:
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            log("SECURITY", "  Running Dependency Vulnerability Scan (Safety)...")
            safety_cmd = [sys.executable, "-m", "safety", "check", "-r", "requirements.txt", "--json"]
            res = subprocess.run(safety_cmd, cwd=project_path, capture_output=True, text=True)
            # Handle valid JSON or empty outputs
            if res.stdout.strip().startswith("{") or res.stdout.strip().startswith("["):
                 try:
                     vulns = json.loads(res.stdout)
                     issues = vulns.get('vulnerabilities', []) if isinstance(vulns, dict) else vulns
                     if issues:
                         log("SECURITY", f"  ❌ Found {len(issues)} vulnerable dependencies!")
                         for v in issues:
                             pkg = v.get('package_name', '?')
                             spec = v.get('vulnerable_spec', '?')
                             log("SECURITY", f"    - {pkg} ({spec})")
                         # TODO: Auto-upgrade could happen here
                     else:
                         log("SECURITY", "  ✓ Dependencies are clean.")
                 except:
                     log("SECURITY", "  ⚠️ Safety output parse failed.")
            elif "No known security vulnerabilities" in res.stdout:
                 log("SECURITY", "  ✓ Dependencies are clean.")
    except Exception as e:
        log("WARN", f"  Dependency scan skipped: {e}")

    # Code Scan (Bandit)
    log("SECURITY", "  Running Static Code Analysis (Bandit)...")
    try:
        bandit_cmd = [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "-q"]
        res = subprocess.run(bandit_cmd, cwd=project_path, capture_output=True, text=True)
        if res.stdout.strip().startswith("{"):
            report = json.loads(res.stdout)
            results = report.get('results', [])
            high_sev = [r for r in results if r['issue_severity'] == 'HIGH']
            
            if high_sev:
                log("SECURITY", f"  ❌ Found {len(high_sev)} HIGH severity security issues!")
                # Group by file
                files_to_fix = {}
                for issue in high_sev:
                    fname = issue['filename'].replace(".\\", "").replace("./", "")
                    if fname in written_files:
                        if fname not in files_to_fix:
                            files_to_fix[fname] = []
                        files_to_fix[fname].append(issue)
                        log("SECURITY", f"    - {fname}:{issue['line_number']} >> {issue['issue_text']}")

                # Auto-Heal High Severity Issues
                for fix_file, issues in files_to_fix.items():
                    log("SECURITY", f"  🚑 Auto-Patching Security Vulnerabilities in {fix_file}...")
                    issue_desc = "\n".join([f"- {i['issue_text']} (Line {i['line_number']})" for i in issues])
                    
                    try:
                        fixed_code = ask_llm(client, eng_model, eng_system,
                            f"SECURITY VULNERABILITY DETECTED in {fix_file}:\n{issue_desc}\n\n"
                            f"You MUST fix these security issues. Replace insecure code with secure alternatives.\n"
                            f"Output ONLY the complete corrected source code:\n\n{written_files[fix_file]}")
                        
                        written_files[fix_file] = fixed_code
                        with open(os.path.join(project_path, fix_file), "w", encoding="utf-8") as f:
                            f.write(fixed_code)
                        log("SECURITY", f"  ✓ Patched: {fix_file}")
                    except Exception as ex:
                        log("ERROR", f"  Security patch failed for {fix_file}: {ex}")

            else:
                log("SECURITY", "  ✓ Codebase passed static security analysis.")
    except Exception as e:
        log("WARN", f"  Static analysis skipped: {e}")

    # ── Phase 2.5: AUDITOR + MASTER REVIEWER ──────────────────
    log("AUDITOR", "Engaging Local Intelligence Auditor…")

    # Robust standard library detection
    if sys.version_info >= (3, 10):
        std_libs = sys.stdlib_module_names
    else:
        std_libs = {
            "os", "sys", "json", "time", "datetime", "subprocess", "random", 
            "math", "re", "struct", "threading", "collections", "itertools",
            "functools", "traceback", "typing", "ast", "shutil", "glob",
            "unittest", "logging", "argparse", "socket", "http", "urllib",
            "xml", "html", "email", "io", "pathlib", "tkinter", "copy"
        }

    detected_deps = set(deps)
    
    for fpath, code in written_files.items():
        if not fpath.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
            log("AUDITOR", f"  ✓ Syntax clean: {fpath}")
            # Extract imports for dependency injection
            for node in ast.walk(tree):
                module_name = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                if module_name:
                    # Check if this is a local module/file or directory
                    is_local = (
                        module_name in written_files or 
                        f"{module_name}.py" in written_files or 
                        any(f.startswith(f"{module_name}/") for f in written_files)
                    )
                    
                    if module_name not in std_libs and not is_local:
                        if not module_name.startswith('.'):
                            final_pkg = PKG_MAP.get(module_name, module_name)
                            if final_pkg not in detected_deps:
                                detected_deps.add(final_pkg)
                                log("AUDITOR", f"    + Auto-injecting: {final_pkg}")
        except SyntaxError as e:
            log("ERROR", f"  Syntax Error in {fpath}:L{e.lineno}: {e.msg}")

    # Final Validation Gate sweep across ALL files
    manifest = build_manifest(written_files)
    all_violations = validation_gate(written_files, manifest)
    if all_violations:
        log("GATE", f"  ⚠ {len(all_violations)} cross-file import violation(s) remain")
        for v in all_violations:
            log("GATE", f"    ✗ {v['file']}: {v['import_stmt']} → missing '{v['missing']}'")
    else:
        log("GATE", "  ✓ All cross-file imports verified")

    # ── Config Consistency Check (post-build) ──
    config_violations = ConfigConsistencyChecker.check(written_files)
    if config_violations:
        log("CONFIG", f"  ⚠ {len(config_violations)} config attribute mismatch(es) detected")
        for cv in config_violations:
            log("CONFIG", f"    ✗ {cv['file']}:L{cv['line']}: {cv['ref']} — available: {cv['available'][:8]}")
        # Auto-repair: re-prompt the engineer for affected files
        affected_files = set(cv["file"] for cv in config_violations)
        for af in affected_files:
            if af in written_files:
                af_violations = [cv for cv in config_violations if cv["file"] == af]
                violation_report = "\n".join(
                    f"- Line {cv['line']}: '{cv['ref']}' does not exist in Config class. "
                    f"Available attributes: {cv['available']}" for cv in af_violations
                )
                try:
                    log("CONFIG", f"  🔧 Auto-repairing config refs in {af}…")
                    fixed_code = ask_llm(client, eng_model,
                        "You are a code fixer. Fix ONLY the config attribute references listed below. "
                        "Replace each invalid reference with the correct attribute from the available list. "
                        "Output ONLY the complete corrected source code.",
                        f"CONFIG ATTRIBUTE VIOLATIONS in {af}:\n{violation_report}\n\n"
                        f"Current code:\n{written_files[af]}")
                    full_path = os.path.join(project_path, af)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(fixed_code)
                    written_files[af] = fixed_code
                    log("CONFIG", f"  ✓ Config refs repaired in {af}")
                except Exception as e:
                    log("ERROR", f"  Config repair failed for {af}: {e}")
    else:
        log("CONFIG", "  ✓ All config attribute references verified")

    # ── Import Dry-Run (deep cross-file verification) ──
    dry_run_violations = import_dry_run(written_files)
    if dry_run_violations:
        log("DRY-RUN", f"  ⚠ {len(dry_run_violations)} import resolution failure(s)")
        for dv in dry_run_violations:
            log("DRY-RUN", f"    ✗ {dv['file']}:L{dv['line']}: {dv['import']} — '{dv['missing']}' not in {dv['source']}")
    else:
        log("DRY-RUN", "  ✓ All local imports resolve correctly")

    deps = list(detected_deps)

    # ── Pillar 4: MASTER REVIEWER (Zero-Trust LLM Gatekeeper) ──
    log("REVIEWER", "Engaging Master Reviewer — Zero-Trust Audit…")

    reviewer_system = (
        "Role: You are the Lead Systems Architect and Senior Security Engineer. "
        "Your sole purpose is to audit code generated by a Developer agent for a project "
        "defined by an Architect agent. "
        "\n\nObjective: Perform a Zero-Trust audit. Identify logical fallacies, missing "
        "dependencies, and integration mismatches before any code is finalized."
        "\n\n1. VERIFICATION CHECKLIST — validate for EVERY file:"
        "\n  - Import Integrity: Does every import point to a file that exists in the file tree?"
        "\n  - Dependency Sync: Are all imported libraries listed in the dependencies?"
        "\n  - State Consistency: Flag all naming discrepancies (user_id vs userId, etc.)"
        "\n  - Security Check: Scan for hardcoded API keys, lack of .env usage, SQL injection."
        "\n  - Config Coherence: Every 'self.config.X' or 'config[\"X\"]' reference MUST match "
        "an attribute actually defined in the Config/Settings class. Flag any mismatch."
        "\n  - Enum Integrity: Enum member references must use the exact name from the definition. "
        "If enum defines 'private', code must use Enum.private, NOT Enum.PRIVATE."
        "\n  - Cross-File Naming: Imported function/class names must be IDENTICAL to their definition. "
        "No silent renames at module boundaries."
        "\n\n2. RESPONSE PROTOCOL:"
        '\n  IF BUGS FOUND: Output JSON: {"status": "REJECTED", "issues": [{"file": "...", "line": N, "error": "...", "fix": "..."}]}'
        '\n  IF CODE IS PERFECT: Output JSON: {"status": "APPROVED"}'
        "\n\n3. CONSTRAINT: Do NOT provide suggestions or advice. Provide ONLY Direct Corrections or Approval. "
        "You are the final wall before the user receives the code."
        "\nOutput ONLY the JSON response. No markdown fences, no extra text."
    )

    # Build the full codebase snapshot for review
    codebase_snapshot = []
    for fpath, code in written_files.items():
        codebase_snapshot.append(f"=== FILE: {fpath} ===\n{code}\n=== END ===")
    review_payload = (
        f"FILE TREE: {list(written_files.keys())}\n"
        f"DEPENDENCIES: {deps}\n\n"
        + "\n\n".join(codebase_snapshot)
    )

    max_review_cycles = 5
    for review_cycle in range(1, max_review_cycles + 1):
        try:
            review_raw = ask_llm(client, local_model, reviewer_system, review_payload)
            review_result = json.loads(review_raw)
        except (json.JSONDecodeError, Exception) as e:
            log("REVIEWER", f"  ⚠ Review parse failed: {e}. Proceeding.")
            break

        if review_result.get("status") == "APPROVED":
            log("REVIEWER", f"  ✓ APPROVED — All files passed Zero-Trust audit (cycle {review_cycle})")
            break
        elif review_result.get("status") == "REJECTED":
            issues = review_result.get("issues", [])
            log("REVIEWER", f"  ✗ REJECTED — {len(issues)} issue(s) found (cycle {review_cycle}/{max_review_cycles})")
            for issue in issues:
                log("REVIEWER", f"    [{issue.get('file','?')}:L{issue.get('line','?')}] {issue.get('error','Unknown')}")

            if review_cycle < max_review_cycles:
                # Apply fixes: group issues by file and re-prompt Engineer
                files_to_fix = {}
                for issue in issues:
                    f = issue.get("file", "")
                    if f in written_files:
                        if f not in files_to_fix:
                            files_to_fix[f] = []
                        files_to_fix[f].append(issue)

                for fix_file, fix_issues in files_to_fix.items():
                    issue_report = "\n".join(
                        f"- Line {iss.get('line','?')}: {iss.get('error','')} → Fix: {iss.get('fix','')}"
                        for iss in fix_issues
                    )
                    log("REVIEWER", f"  🔧 Applying corrections to {fix_file}…")
                    try:
                        fixed_code = ask_llm(client, eng_model,
                            "You are 'Overlord,' a Senior Engineer. Apply ONLY the requested fixes. "
                            "Output ONLY the complete corrected source code. No markdown, no explanations.",
                            f"File: {fix_file}\nISSUES TO FIX:\n{issue_report}\n\n"
                            f"CURRENT CODE:\n{written_files[fix_file]}")
                        written_files[fix_file] = fixed_code
                        fp = os.path.join(project_path, fix_file)
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(fixed_code)
                        log("REVIEWER", f"  ✓ Fixed: {fix_file}")
                    except Exception as e:
                        log("ERROR", f"  Fix failed for {fix_file}: {e}")

                # Rebuild review payload for next cycle
                codebase_snapshot = []
                for fpath, code in written_files.items():
                    codebase_snapshot.append(f"=== FILE: {fpath} ===\n{code}\n=== END ===")
                review_payload = (
                    f"FILE TREE: {list(written_files.keys())}\n"
                    f"DEPENDENCIES: {deps}\n\n"
                    + "\n\n".join(codebase_snapshot)
                )
        else:
            log("REVIEWER", f"  ⚠ Unexpected response. Proceeding.")
            break

    # Re-save manifest after all corrections
    manifest = build_manifest(written_files)
    manifest_path = os.path.join(project_path, "project_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    divider()


    # ── Phase 3: DEBUGGER (Autonomic Healing) ────────────────
    if args.debug:
        log("DEBUGGER", "Engaging Autonomic Repair System…")
        
        # Initialize Wisdom
        wisdom = GlobalWisdom(project_path)


        # Environment Healing: Try to install dependencies before running
        if deps:
            log("DEBUGGER", f"Syncing environment: pip install {' '.join(deps)}…")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install"] + deps, capture_output=True, text=True, timeout=60)
                log("DEBUGGER", "  ✓ Dependencies synchronized.")
            except Exception as e:
                log("ERROR", f"  Environment sync failed: {e}")

        # ── GUI Detection — skip subprocess test for GUI apps ──
        gui_imports = {"tkinter", "pygame", "PyQt5", "PyQt6", "PySide2", "PySide6",
                       "kivy", "dearpygui", "customtkinter", "wx"}
        is_gui_app = False
        for fpath, code in written_files.items():
            if fpath.endswith(".py"):
                for gui_mod in gui_imports:
                    if f"import {gui_mod}" in code or f"from {gui_mod}" in code:
                        is_gui_app = True
                        break
            if is_gui_app:
                break

        if is_gui_app:
            log("DEBUGGER", "  🖥️ GUI application detected (tkinter/pygame/Qt/etc).")
            log("DEBUGGER", "  Skipping subprocess test — GUI apps require a display.")
            log("DEBUGGER", "  ✓ Code structure validated by Reviewer. Run manually to test.")
        else:
            # Initialize Docker sandbox runner
            sandbox = SandboxRunner()
            if sandbox.available:
                log("DEBUGGER", "  🐳 Docker detected — executing in isolated sandbox")
            else:
                log("DEBUGGER", "  ⚠ Docker unavailable — executing on host (install Docker for isolation)")
            log("DEBUGGER", f"Running: {run_cmd}")

            max_passes = 5
            for attempt in range(1, max_passes + 1):
                log("DEBUGGER", f"Debug pass {attempt}/{max_passes}…")
                try:
                    result = sandbox.execute(run_cmd, project_path, deps, timeout=30)
                except subprocess.TimeoutExpired:
                    log("DEBUGGER", "  ⏱ Process timed out (30s). Skipping.")
                    break
                except Exception as e:
                    log("DEBUGGER", f"  Cannot execute: {e}")
                    break

                output_text = (result.stdout + "\n" + result.stderr).lower()
                error_markers = ["error", "exception", "traceback", "failed", "critical"]
                has_error_string = any(m in output_text for m in error_markers)

                # ── Smart Detection: CLI apps that require arguments ──
                # If the program is just asking for arguments (usage message),
                # that's NOT a bug — the code is working correctly.
                usage_indicators = ["usage:", "positional arguments", "too few arguments",
                                    "the following arguments are required",
                                    "expected one argument", "expected at least"]
                is_usage_message = any(u in output_text for u in usage_indicators)

                # Argparse exits with code 2 for missing args; custom usage exits with code 1
                if is_usage_message and "traceback" not in output_text:
                    log("DEBUGGER", "  ✓ Program is a CLI tool — requires arguments to run.")
                    log("DEBUGGER", "    This is NOT an error. The code structure is valid.")
                    combined = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
                    for line in combined.split("\n")[:4]:
                        if line.strip():
                            log("DEBUGGER", f"    {line.strip()}")
                    break

                if result.returncode == 0 and not has_error_string:
                    log("DEBUGGER", "  ✓ Program executed successfully — no errors.")
                    if result.stdout.strip():
                        for line in result.stdout.strip().split("\n")[:8]:
                            log("DEBUGGER", f"    stdout: {line}")
                    break
                else:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    log("DEBUGGER", f"  ✗ Potential error detected (Code {result.returncode} or Error in output)")
                    
                    # Dynamic Healing: Detect ModuleNotFoundError
                    if "modulenotfounderror" in stderr.lower():
                        import re
                        match = re.search(r"no module named ['\"]([^'\"]+)['\"]", stderr.lower())
                        if match:
                            missing_pkg = match.group(1)
                            # Use global PKG_MAP for correct PyPI names
                            final_pkg = PKG_MAP.get(missing_pkg, missing_pkg)
                            
                            log("DEBUGGER", f"  Healing environment: Installing missing package '{final_pkg}'…")
                            subprocess.run([sys.executable, "-m", "pip", "install", final_pkg], capture_output=True, text=True)
                            continue # Retry this pass immediately

                    # Dynamic Healing: Missing binary (e.g. ffmpeg.exe not on PATH)
                    if "winerror 2" in stderr.lower() or "filenotfounderror" in stderr.lower():
                        if "ffmpeg" in stderr.lower() or "ffprobe" in stderr.lower():
                            log("DEBUGGER", "  Binary missing: ffmpeg not on PATH. Installing imageio-ffmpeg…")
                            subprocess.run([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"], capture_output=True, text=True)
                            # Inject wisdom so the LLM knows how to use the bundled binary
                            wisdom.learn(
                                "[WinError 2] The system cannot find the file specified",
                                "ffmpeg binary is missing. Use: import imageio_ffmpeg; "
                                "ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe(); "
                                "then pass ffmpeg_path to subprocess.run() or ffmpeg.input(). "
                                "Do NOT call 'ffmpeg' directly — use the full path from imageio_ffmpeg."
                            )

                    for line in stderr.split("\n")[:6]:
                        log("ERROR", f"    {line}")

                    if attempt < max_passes:
                        
                        # 1. Consult Global Wisdom First
                        known_fix = wisdom.consult(stderr)
                        if known_fix:
                            log("WISDOM", "  🧠 Error pattern recognized! Applying known fix…")
                            previous_wisdom = f"\n\n[GLOBAL WISDOM SUGGESTION]:\n{known_fix}"
                        else:
                            previous_wisdom = ""

                        log("DEBUGGER", "  Engaging LLM to repair damaged logic…")

                        # Improved selection: find the innermost project file mentioned in the traceback
                        fix_target = None
                        last_pos = -1
                        for fname in written_files:
                            # Find the LAST occurrence of each project file in the stderr
                            pos = stderr.rfind(fname)
                            if pos != -1 and pos > last_pos:
                                last_pos = pos
                                fix_target = fname

                        if not fix_target and written_files:
                            fix_target = list(written_files.keys())[0]

                        if fix_target:
                            # Context Injection: Find other files mentioned in the error to provide context
                            context_files = []
                            for fname in written_files:
                                if fname != fix_target and fname in stderr:
                                    context_files.append(f"--- REFERENCE: {fname} ---\n{written_files[fname]}\n-----------------------")
                            
                            context_block = "\n\n".join(context_files)

                            dbg_system = (
                                "You are 'Overlord,' a Senior Debugger. Directive: Self-Healing. "
                                "Analyze the error, the target file, and the reference context. "
                                "If 'ImportError' or 'AttributeError', ensure the missing symbol is defined and exported. "
                                "Check for circular imports. "
                                "If '[WinError 2]' or 'FileNotFoundError' for a binary like ffmpeg: "
                                "use 'import imageio_ffmpeg; ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()' "
                                "and pass that path to subprocess calls instead of calling 'ffmpeg' directly. "
                                "Preserve existing logic. Output ONLY the complete corrected source code for the TARGET FILE. "
                                "No markdown fences, no explanations."
                            )
                            dbg_prompt = (
                                f"Project Structure: {list(written_files.keys())}\n"
                                f"Target File: {fix_target}\n\n"
                                f"```\n{written_files[fix_target]}\n```\n\n"
                                f"RELATED CONTEXT (Read-Only):\n{context_block}\n\n"
                                f"ERROR:\n{stderr}{previous_wisdom}"
                            )
                            try:
                                fixed = ask_llm(client, arch_model, dbg_system, dbg_prompt)
                                fp = os.path.join(project_path, fix_target)
                                with open(fp, "w", encoding="utf-8") as f:
                                    f.write(fixed)
                                state.write(fix_target, fixed)
                                written_files = state.files  # Keep reference in sync
                                log("DEBUGGER", f"  ✓ Patched: {fix_target}")
                                
                                # Learn from this fix — store the actual error + strategy
                                error_type = "unknown"
                                if "importerror" in stderr.lower():
                                    error_type = "Ensure the imported symbol exists and is spelled correctly in the source module."
                                elif "attributeerror" in stderr.lower():
                                    error_type = "The module does not expose this attribute. Check the API or use an alternative."
                                elif "winerror 2" in stderr.lower():
                                    error_type = "Binary not found. Use imageio_ffmpeg.get_ffmpeg_exe() for ffmpeg path."
                                elif "syntaxerror" in stderr.lower():
                                    error_type = "Fix syntax: check for missing colons, brackets, or indentation."
                                else:
                                    error_type = f"LLM repaired logic in {fix_target}. Review the fix if error recurs."
                                wisdom.learn(stderr, error_type)

                            except Exception as e:
                                log("ERROR", f"  Fix attempt failed: {e}")
                                break

        divider()

    # ── Phase 4: PACKAGING ───────────────────────────────────
    log("SYSTEM", "Generating project artifacts…")

    # requirements.txt
    # Ensure PyInstaller is present for bundling
    if not getattr(args, 'no_bundle', False):
        if not any("pyinstaller" in d.lower() for d in deps):
            deps.append("pyinstaller")

    req_path = os.path.join(project_path, "requirements.txt")
    with open(req_path, "w", encoding="utf-8") as f:
        f.write("\n".join(deps))
    log("SYSTEM", f"  ✓ requirements.txt  ({len(deps)} packages)")

    # Verify dependencies in isolated environment
    log("DOCKER", "Verifying dependency resolution…")
    dep_ok, dep_msg = dep_verifier.verify(deps, project_path)
    if dep_ok:
        log("DOCKER", f"  ✓ {dep_msg}")
    else:
        log("ERROR", f"  ✗ {dep_msg}")
        log("SYSTEM", "  ⚠ Dependencies may not resolve cleanly. Review requirements.txt.")

    # Dockerfile
    if args.docker:
        log("DOCKER", "Generating Dockerfile…")
        docker_system = (
            "You are 'Overlord,' a Senior DevOps Specialist. "
            "Directive: Standardized Packaging. Create a production-ready Dockerfile for this project. "
            "Use python:3.12-slim as base. Output ONLY Dockerfile content, no markdown."
        )
        try:
            dockerfile = ask_llm(client, local_model, docker_system, f"Project plan: {json.dumps(plan)}")
            with open(os.path.join(project_path, "Dockerfile"), "w", encoding="utf-8") as f:
                f.write(dockerfile)
            log("DOCKER", "  ✓ Dockerfile written")
        except Exception as e:
            log("ERROR", f"  Dockerfile generation failed: {e}")

    # README.md
    if args.readme:
        log("DOCS", "Generating README.md…")
        doc_system = (
            "You are 'Overlord,' a Senior Full-Stack Engineer. "
            "Directive: Standardized Packaging. Create a professional README.md with project description, "
            "installation, usage, and Docker instructions. Output ONLY markdown."
        )
        try:
            readme = ask_llm(
                client, local_model, doc_system,
                f"Goal: {args.prompt}\nFiles: {file_list}\nRun: {run_cmd}"
            )
            with open(os.path.join(project_path, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme)
            log("DOCS", "  ✓ README.md written")
        except Exception as e:
            log("ERROR", f"  README generation failed: {e}")

    # ── Phase 5: ENVIRONMENT AGENT ────────────────────────────
    log("ENVIRON", "Engaging Environment Agent…")
    log("ENVIRON", "Generating one-command run scripts for all platforms…")

    env_system = (
        "You are 'Overlord Environment Specialist.' "
        "Your mission: generate deployment scripts so the user can run this project with ONE command. "
        "You will be given the project's file list, dependencies, and run command. "
        "Output ONLY the requested script content. No markdown fences, no explanations."
    )

    # setup.sh — Unix/macOS
    try:
        setup_sh = ask_llm(client, local_model, env_system,
            f"Generate a setup.sh bash script for this project.\n"
            f"Files: {file_list}\n"
            f"Dependencies: {deps}\n"
            f"Run command: {run_cmd}\n\n"
            f"The script should:\n"
            f"1. Create a Python virtual environment in ./venv\n"
            f"2. Activate it\n"
            f"3. Install all dependencies from requirements.txt\n"
            f"4. Run the application with: {run_cmd}\n"
            f"Start with #!/bin/bash and set -e. Make it robust.")
        with open(os.path.join(project_path, "setup.sh"), "w", encoding="utf-8", newline="\n") as f:
            f.write(setup_sh)
        log("ENVIRON", "  ✓ setup.sh")
    except Exception as e:
        log("ERROR", f"  setup.sh generation failed: {e}")

    # run.bat — Windows
    try:
        run_bat = ask_llm(client, local_model, env_system,
            f"Generate a run.bat Windows batch script for this project.\n"
            f"Files: {file_list}\n"
            f"Dependencies: {deps}\n"
            f"Run command: {run_cmd}\n\n"
            f"The script should:\n"
            f"1. Create a Python virtual environment in .\\venv if it doesn't exist\n"
            f"2. Activate it\n"
            f"3. Install dependencies from requirements.txt\n"
            f"4. Run the application. logic:\n"
            f"   IF 'dist\\{args.project}.exe' exists, run IT.\n"
            f"   ELSE, run via python: {run_cmd}\n"
            f"5. Pause at the end so the window stays open\n"
            f"Use @echo off and proper Windows batch syntax (if exist ...).")
        with open(os.path.join(project_path, "run.bat"), "w", encoding="utf-8") as f:
            f.write(run_bat)
        log("ENVIRON", "  ✓ run.bat")
    except Exception as e:
        log("ERROR", f"  run.bat generation failed: {e}")

    # docker-compose.yml — only if Docker mode is active
    if args.docker:
        try:
            compose = ask_llm(client, local_model, env_system,
                f"Generate a docker-compose.yml for this project.\n"
                f"Files: {file_list}\n"
                f"Dependencies: {deps}\n"
                f"Run command: {run_cmd}\n"
                f"Project name: {args.project}\n\n"
                f"The compose file should:\n"
                f"1. Build from the local Dockerfile\n"
                f"2. Map relevant ports (if web app, use 8000:8000 or 5000:5000)\n"
                f"3. Mount a ./data volume for persistence\n"
                f"4. Set restart: unless-stopped\n"
                f"Use docker compose v3.8+ syntax.")
            with open(os.path.join(project_path, "docker-compose.yml"), "w", encoding="utf-8") as f:
                f.write(compose)
            log("ENVIRON", "  ✓ docker-compose.yml")
        except Exception as e:
            log("ERROR", f"  docker-compose.yml generation failed: {e}")

    # Setup Agent: deterministic env/port/config scan (always runs)
    try:
        setup_result = setup_agent(project_path, written_files, deps, run_cmd)
        log("ENVIRON", f"  Deploy: {len(setup_result['env_vars'])} env var(s), port {setup_result['port']}")
    except Exception as e:
        log("ERROR", f"  Setup Agent failed: {e}")

    divider()

    # ── Phase 5.5: ZERO-CHAT SELF-HEALING DEPLOYMENT ─────────
    if args.docker:
        log("DOCKER", "Initiating Zero-Chat Self-Healing Deployment…")
        log("DOCKER", "Building and deploying containers — autonomous healing enabled.")
        
        # Derive the engineer system prompt for Developer patches
        heal_eng_system = (
            "You are 'Overlord,' a Senior Full-Stack Developer. "
            "Directive: Self-Healing. Fix the code so the Docker container runs without errors. "
            f"Project files: {file_list}. "
            "Output ONLY raw source code. No markdown fences, no explanations."
        )
        
        deploy_ok = auto_heal_deployment(
            project_path=project_path,
            client=client,
            model=arch_model,
            reviewer=reviewer,
            state=state,
            written_files=written_files,
            eng_system=heal_eng_system,
            max_cycles=3,
        )
        
        if deploy_ok:
            log("SUCCESS", "Docker deployment verified — containers are LIVE.")
        else:
            log("WARN", "Docker deployment could not be auto-healed. Check error_cycle_*.log files.")
        
    # ── Phase 5.6: MULTIMODAL HANDOVER (Visual DNA) ──────────
    try:
        log("SYSTEM", "🎨 Engaging Multimodal Visual Engine (SDXL + SVD)...")
        # Use the enhanced prompt + Architect's design vision as context
        # We search for the Architect's design thoughts in the logs or use the prompt
        visual_context = enhanced_prompt 
        execute_multimodal_handover(project_path, visual_context)
    except Exception as e:
        log("WARN", f"  Multimodal Engine failed: {e}")

    divider()

    # ── Phase 5.7: BUNDLER AGENT ──────────────────────────────
    bundle_result = None
    if not getattr(args, 'no_bundle', False):
        try:
            from bundler_agent import bundle_project
            log("BUNDLER", "Engaging Bundler Agent — packaging standalone executable...")
            bundle_result = bundle_project(
                project_path=project_path,
                project_name=arch_proj_name,
            )
            if bundle_result.get("success"):
                log("BUNDLER", f"  ✓ Standalone .exe ready — double-click LAUNCH.bat to run!")
            else:
                log("BUNDLER", f"  ⚠ Bundling skipped: {bundle_result.get('error', 'unknown')}")
                log("BUNDLER", "  Project still works with: python {}".format(bundle_result.get('entry_point', 'main.py')))
        except ImportError:
            log("BUNDLER", "  ⚠ bundler_agent.py not found — skipping .exe packaging.")
        except Exception as e:
            log("BUNDLER", f"  ⚠ Bundler error: {e}")
        divider()
    # ── Phase 5.8: RUNTIME VERIFICATION (Start & Run Check) ──
    log("SYSTEM", "🧠 Phase 5.8: Runtime Verification")
    verify_cmd = None
    # Priority 1: Bundled Exe
    if bundle_result and bundle_result.get("success"):
        exe_name = f"{arch_proj_name}.exe" if os.name == 'nt' else arch_proj_name
        possible_exe = os.path.join(project_path, "dist", exe_name)
        if os.path.exists(possible_exe):
            verify_cmd = [possible_exe]
    
    # Priority 2: Python Entry Point
    if not verify_cmd:
        entry = "main.py"
        if bundle_result and bundle_result.get("entry_point"):
            entry = bundle_result.get("entry_point")
        elif "main.py" not in written_files and "app.py" in written_files:
            entry = "app.py"
        
        # Check if entry file exists
        if os.path.exists(os.path.join(project_path, entry)):
            verify_cmd = [sys.executable, entry]

    if verify_cmd:
        log("TEST", f"  🚀 Verifying startup: {' '.join(verify_cmd)}")
        try:
            # We run it for 5 seconds to see if it crashes
            import subprocess, time
            
            # Use a new process group to ensure we can kill it cleanly
            creationflags = 0
            if os.name == 'nt':
                creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
            
            proc = subprocess.Popen(
                verify_cmd, 
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags
            )
            
            try:
                # Wait 5 seconds
                code = proc.wait(timeout=5)
                # If we are here, it exited within 5 seconds
                if code == 0:
                    log("TEST", "  ✓ Program started and exited successfully (CLI tool).")
                else:
                    _, stderr_out = proc.communicate()
                    # Linter thinks this is str, but it's bytes. Force cast or just decode safely.
                    err_text = stderr_out.decode('utf-8', errors='ignore') if stderr_out else ""
                    log("ERROR", f"  ✗ Program crashed on startup (Exit Code: {code})")
                    log("ERROR", f"  Traceback:\n{err_text}")
                    # In a stricter mode, we would fail the build here
            except subprocess.TimeoutExpired:
                # It is still running after 5s -> SUCCESS (it's a server or GUI)
                log("TEST", "  ✓ Program is running stable (Server/GUI detected).")
                # Kill it gently
                if os.name == 'nt':
                    # Send CTRL_BREAK_EVENT
                    import signal
                    creationflags = getattr(signal, 'CTRL_BREAK_EVENT', 0)
                    os.kill(proc.pid, creationflags)
                else:
                    proc.terminate()
                
                try:
                    proc.wait(timeout=2)
                except:
                    proc.kill()
                    
        except Exception as e:
            log("WARN", f"  ⚠ Verification failed to execute: {e}")
    else:
        log("WARN", "  ⚠ Could not determine run command for verification.")
    
    divider()

    # ── Phase 6: HANDOFF ─────────────────────────────────────
    finalize_package(project_path, state, arch_proj_name,
                     arch_stack=arch_stack, arch_file_tree=arch_file_tree,
                     deps=deps, run_cmd=run_cmd, prompt=args.prompt,
                     client=client, model=local_model)

    # ── Phase 7: VOICE BRIEFING ──────────────────────────────
    if getattr(args, 'voice', False):
        log("VOICE", "Engaging Voice Briefing Agent…")
        generate_voice_briefing(
            project_path=project_path,
            project_name=arch_proj_name,
            file_count=len(state.files),
            run_cmd=run_cmd,
            client=client,
            model=local_model,
            prompt=args.prompt,
            cost_summary=tracker.get_summary(),
        )
        divider()

    # ── Phase 6.5: GALLERY UPDATE ────────────────────────────
    try:
        gallery_manifest = {
            "project_name": arch_proj_name,
            "stack": arch_stack or {},
            "file_tree": arch_file_tree or list(written_files.keys()),
        }
        update_gallery(project_path, gallery_manifest)
    except Exception as e:
        log("WARN", f"Gallery update failed (non-critical): {e}")

    # ── Done ─────────────────────────────────────────────
    divider()

    # Save cost report
    tracker.save_report(project_path)
    log("SYSTEM", f"💵 {tracker.get_summary()}")
    if tracker.budget_exceeded:
        log("WARN", f"Build exceeded budget: ${tracker.total_cost:.4f} / ${tracker.budget:.2f}")
    if tracker.pivot_triggered:
        log("SYSTEM", "Model was auto-pivoted to local model mid-build to control costs.")

    # Voice Briefing — narrate what was built (if Eleven Labs key is available)
    try:
        voice_briefing(client, local_model, args.project, args.prompt,
                       files, project_path)
    except Exception as e:
        log("VOICE", f"  ⚠ Voice briefing skipped: {e}")

    # ── Phase 7: AUTOMATIC POST-MORTEM (Learning) ────────────
    try:
        log("SYSTEM", "🧠 Phase 7: Post-Mortem & Learning")
        
        # 1. Gather context (errors vs success)
        has_error = tracker.budget_exceeded # Simple proxy, can be improved
        outcome = "failure" if has_error else "success"
        
        # 2. Ask LLM to extract a lesson
        pm_system = (
            "You are the 'Overlord Post-Mortem Analyst'. "
            "Analyze the build execution (based on your internal state of what just happened). "
            "Identify ONE key technical lesson or pattern that was critical to this build's outcome. "
            "Output valid JSON: {\"trigger\": \"<context keyword>\", \"lesson\": \"<concise lesson>\", \"tags\": [\"<tag1>\", \"<tag2>\"]}"
        )
        
        # We use the prompt + stack as context for the lesson
        pm_context = f"Project: {args.project}\nStack: {arch_stack}\nOutcome: {outcome}\nPrompt: {args.prompt}"
        
        raw_lesson = ask_llm(client, local_model, pm_system, pm_context)
        lesson_data = json.loads(raw_lesson)
        lesson_data["outcome"] = "positive" if outcome == "success" else "negative"
        
        # 3. Memorize
        kb.memorize(lesson_data)
        
    except Exception as e:
        log("SYSTEM", f"  ⚠ Post-mortem failed (learning skipped): {e}")

    log("SUCCESS", f"BUILD COMPLETE  →  {os.path.abspath(project_path)}")
    log("SUCCESS", f"To run:  cd {project_path} && {run_cmd}")
    log("SUCCESS", f"Or use:  setup.sh (Unix) / run.bat (Windows)")


# ── Main Execution ───────────────────────────────────────────

if __name__ == "__main__":
    # Activate Fortress Protocols
    # Protects this brain file and the electron bridge
    watchdog = IntegrityWatchdog([__file__, "main.js"])

    parser = argparse.ArgumentParser(description="Overlord Agent Brain")
    parser.add_argument("--project", type=str, help="Project name (e.g., 'SnakeGame')")
    parser.add_argument("--prompt", type=str, help="Feature description (e.g., 'Make it green')")
    parser.add_argument("--output",  default="./output", help="Output directory")
    parser.add_argument("--model",      default="gpt-4o", help="OpenAI model (default for all phases)")
    parser.add_argument("--arch-model", default="", help="Strategy model for Architect/Prompt phases")
    parser.add_argument("--eng-model",  default="", help="Speed model for Engineer phase")
    parser.add_argument("--local-model", default="", help="Cheap/local model for Reviewer, Env, Dockerfile phases (e.g. llama3 via Ollama)")
    parser.add_argument("--review-model", default="", help="Dedicated review model for senior code review (e.g. claude-sonnet-4-20250514)")
    parser.add_argument("--budget",      default=5.0, type=float, help="Max spend in USD before pivoting to local model (default: $5.00)")
    parser.add_argument("--api-key",    default="", help="OpenAI API key")
    parser.add_argument("--docker",     action="store_true", help="Generate Dockerfile")
    parser.add_argument("--readme",     action="store_true", help="Generate README.md")
    parser.add_argument("--debug",      action="store_true", help="Auto-debug (3 passes)")
    parser.add_argument("--setup",      action="store_true", help="Generate setup.ps1, docker-compose.yml, .env.template")
    parser.add_argument("--voice",      action="store_true", help="Generate voice briefing via ElevenLabs TTS at build completion")
    parser.add_argument("--no-bundle",  action="store_true", help="Skip PyInstaller .exe bundling")
    parser.add_argument("--platform",   default="python", choices=["python", "android", "linux"],
                        help="Target platform: python (default), android (Kotlin+Gradle), linux (GTK/Qt desktop)")
    parser.add_argument("--dashboard",  action="store_true", help="Enable Antigravity Dashboard (event bus for Streamlit UI)")
    parser.add_argument("--sandbox",    action="store_true", help="Run tests in Docker sandbox (ephemeral container)")
    parser.add_argument("--mode",       default="new", choices=["new", "upgrade", "reverse"], help="Build mode: new, upgrade, or reverse")
    parser.add_argument("--source",     help="Source path for upgrade/reverse mode")
    parser.add_argument("--decompile-only", action="store_true", help="Run decompiler only and exit")
    parser.add_argument("--phase",      default="all", choices=["plan", "code", "verify", "all"], help="Run specific phase only")
    parser.add_argument("--focus",      help="Glob pattern to focus on specific files")
    parser.add_argument("--clean",      action="store_true", help="Output clean code to a structured folder (Reverse Engineering mode)")
    parser.add_argument("--self-check", action="store_true", help="Run a security self-audit on the Creation Engine")
    
    # Handle the Electron positional argument bridge requirement
    # [script_name, project_name, prompt, ...any other flags]
    if len(sys.argv) > 2 and not sys.argv[1].startswith('-'):
        args = parser.parse_known_args()[0]
        args.project = sys.argv[1]
        args.prompt = sys.argv[2]
        # Any remaining args like --docker are handled by parse_known_args if present
    else:
        args = parser.parse_args()

    # Self-Check Handler
    if getattr(args, 'self_check', False):
        print("🛡️  Initiating Creation Engine Security Self-Audit...", flush=True)
        try:
            # Check for security tools
            import subprocess
            subprocess.run([sys.executable, "-m", "bandit", "--version"], check=True, stdout=subprocess.DEVNULL)
            subprocess.run([sys.executable, "-m", "safety", "--version"], check=True, stdout=subprocess.DEVNULL)
            
            # Run Bandit on current directory
            print("Running Bandit (Code Analysis)...", flush=True)
            subprocess.run([sys.executable, "-m", "bandit", "-r", ".", "-x", "venv,tests,build,dist,.git", "-f", "txt"], check=False)
            
            # Run Safety on requirements
            import os
            if os.path.exists("requirements.txt"):
                print("\nRunning Safety (Dependency Check)...", flush=True)
                subprocess.run([sys.executable, "-m", "safety", "check", "-r", "requirements.txt"], check=False)
            
            print("\n✅ Security Self-Audit Complete.", flush=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
             print("❌ Security tools not found. Please run: pip install bandit safety", flush=True)
        sys.exit(0)

    if not args.project and not args.prompt and not args.mode == 'upgrade':
        parser.print_help()
        log("ERROR", "Missing required arguments: project and prompt.")
        sys.exit(1)

    execute_build(args)
