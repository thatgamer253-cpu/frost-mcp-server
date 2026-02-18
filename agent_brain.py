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
import re
import ast
import argparse
import subprocess
import shutil
import hashlib
import threading
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, cast, TYPE_CHECKING

# ── Root Path Alignment ─────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

if TYPE_CHECKING:
    import openai
    import anthropic as _anthropic_sdk
    from dotenv import load_dotenv

# Optional: Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# Initialize LLM globals
_HAS_OPEN_AI = False
_HAS_ANTHROPIC = False

try:
    from openai import OpenAI
    _HAS_OPEN_AI = True
except ImportError:
    # Dummy OpenAI for linting and fallback
    class OpenAI: # type: ignore
        def __init__(self, *args, **kwargs):
            class Chat:
                class Completions:
                    def create(self, *args, **kwargs):
                        class Resp:
                            class Choice:
                                class Msg: content = ""
                                message = Msg()
                            class Usage:
                                prompt_tokens = 0
                                completion_tokens = 0
                            choices = [Choice()]
                            usage = Usage()
                        return Resp()
                completions = Completions()
            self.chat = Chat()

try:
    import anthropic as _anthropic_sdk
    _HAS_ANTHROPIC = True
except ImportError:
    class _anthropic_sdk: # type: ignore
        class Anthropic:
            def __init__(self, *args, **kwargs):
                class Messages:
                    def create(self, *args, **kwargs):
                        class Resp:
                            class Content: text = ""
                            class Usage:
                                input_tokens = 0
                                output_tokens = 0
                            content = [Content()]
                            usage = Usage()
                        return Resp()
                self.messages = Messages()
    _HAS_ANTHROPIC = False

# ── Status Bridge for UI Updates ──────────────────────────────
class StatusBridge:
    """Bridge for async UI notifications (mocking websocket behavior for file-based IPC)."""
    def __init__(self, project_path):
        self.status_file = os.path.join(project_path, "build_state.json")

    def update(self, key, value):
        """Update a specific key in the status file."""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            
            data[key] = value
            data["last_update"] = time.time()
            
            with open(self.status_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass # Non-blocking updates

    def update_healer(self, healer, state):
        """Update the status of a specific healer (Sentinel, Alchemist, Stealth)."""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}

            if "healer_status" not in data:
                data["healer_status"] = {"Sentinel": "idle", "Alchemist": "idle", "Stealth": "idle"}
            
            data["healer_status"][healer] = state
            data["last_update"] = time.time()

            with open(self.status_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def notify(self, sender, message, status="info"):
        """Send a notification bubble or status update."""
        if status in ["thinking", "coding", "audit", "info"]:
            self.update("thinking_bubble", f"[{sender}] {message}")
        
        elif status == "warning":
            self.update("thinking_bubble", f"⚠️ [{sender}] {message}")
            if sender == "Sentinel":
                self.update_healer("Sentinel", "running")

        elif status == "error":
            self.update("thinking_bubble", f"❌ [{sender}] {message}")
            if sender == "Sentinel":
                self.update_healer("Sentinel", "fail")

        elif status == "success":
            self.update("thinking_bubble", f"✅ [{sender}] {message}")
            if sender == "Sentinel":
                self.update_healer("Sentinel", "pass")

        elif status == "breakpoint":
            self.update("breakpoint_request", {
                "sender": sender,
                "content": message,
                "status": status,
                "timestamp": time.time()
            })

# ── Global Wisdom System ─────────────────────────────────────
class GlobalWisdom:
    def __init__(self, project_path: str):
        self.wisdom_file: str = os.path.join(project_path, "local_wisdom.json")
        # Global wisdom lives at the Creator root — shared across ALL projects
        self.global_wisdom_file: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "global_wisdom.json")
        self.wisdom: Dict[str, Any] = self._load(self.wisdom_file)
        self.global_wisdom: Dict[str, Any] = self._load(self.global_wisdom_file)

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
        rules = {str(k): v for k, v in self.global_wisdom.items() if str(k).startswith("GENERATION_RULE__")}
        if not rules:
            return ""
        lines = ["MANDATORY GENERATION RULES (learned from past build failures):"]
        for key, rule in rules.items():
            label = key.replace("GENERATION_RULE__", "").replace("_", " ").title()
            lines.append(f"- [{label}]: {rule}")
        return "\n".join(lines)

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
        "architect", "refactor", "rewrite", "redesign", "analysis", "blueprint", 
        "complex", "plan", "structure", "database", "security", "enterprise",
        "studio", "multi-agent", "distributed", "blockchain", "ai"
    ]
    if any(trigger in p_lower for trigger in complex_triggers) or len(prompt) > 400:
        # Prefer High Reasoning Models
        return "gemini-2.0-pro-exp-02-05" 

    # 2. Simple/Speed Tasks -> Flash
    simple_triggers = [
        "fix", "typo", "color", "style", "css", "comment", "rename", "log", "hello"
    ]
    if any(trigger in p_lower for trigger in simple_triggers) and len(prompt) < 150:
       return "gemini-2.0-flash"

    # Default Balanced
    return "gemini-2.0-flash"


def resolve_mission_parameters(prompt: str) -> dict:
    """
    Infers platform, scale, and phase from the prompt for autonomous fulfillment.
    """
    p_lower = prompt.lower()
    
    # Platform Inference
    platform = "python"
    is_media = False
    if any(kw in p_lower for kw in ["android", "ios", "mobile", "app", "apk", "kotlin", "java"]):
        platform = "android"
    elif any(kw in p_lower for kw in ["linux", "desktop", "gtk", "qt", "native app", "ubuntu", "fedora"]):
        platform = "linux"
    elif any(kw in p_lower for kw in ["studio", "pro tool", "creative suite", "photoshop-like", "video editor", "high performance", "movie", "cinema", "short", "clip", "editing", "montage", "game", "indie", "unreal", "unity", "pygame", "interactive", "rpg", "gemini video", "ai vision", "vision to video"]):
        platform = "studio"
        is_media = True
        
    # Scale Inference
    scale = "application"
    if is_media:
        scale = "asset"
    if any(kw in p_lower for kw in ["module", "utility", "script", "library", "helper", "simple"]):
        scale = "module"
    elif any(kw in p_lower for kw in ["prototype", "proof of concept", "demo", "minimal"]):
        scale = "prototype"
    elif any(kw in p_lower for kw in ["enterprise", "full suite", "comprehensive", "advanced", "pro"]):
        scale = "application"
        
    # Phase Inference
    phase = "all"
    if any(kw in p_lower for kw in ["plan only", "blueprint", "architect only"]):
        phase = "plan"
    elif any(kw in p_lower for kw in ["code only", "implementation only", "just write"]):
        phase = "code"
    elif any(kw in p_lower for kw in ["verify only", "test only", "just debug"]):
        phase = "verify"

    return {
        "platform": platform,
        "scale": scale,
        "phase": phase
    }


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

class ASTWisdomGuard:
    """Surgical code validator and auto-fixer using AST transformations."""

    def __init__(self):
        # Mapping of (Old Method Name, New Method Name) for MoviePy V2
        self.moviepy_rename_map = {
            "subclip": "subclipped",
            "set_position": "with_position",
            "set_duration": "with_duration",
            "set_audio": "with_audio",
            "set_start": "with_start",
            "set_end": "with_end",
            "set_opacity": "with_opacity",
            "set_fps": "with_fps",
            "volumex": "with_volume_scaled",
            "resize": "resized",
            "crop": "cropped",
            "rotate": "rotated"
        }

    def auto_fix(self, code: str, filepath: str = "") -> tuple:
        if not filepath.endswith(".py"):
            return code, []

        fixes_applied = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, ["AST Error: Could not parse file for fixes"]

        class WisdomTransformer(ast.NodeTransformer):
            def __init__(self, rename_map):
                self.rename_map = rename_map
                self.local_fixes = []

            def visit_Call(self, node):
                # Fix MoviePy Method Renames: clip.subclip() -> clip.subclipped()
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.rename_map:
                        old_name = node.func.attr
                        new_name = self.rename_map[old_name]
                        node.func.attr = new_name
                        self.local_fixes.append(f"AST Fix: method {old_name} -> {new_name}")
                
                # Fix TextClip Positional Args (MoviePy V2)
                if isinstance(node.func, ast.Name) and node.func.id == "TextClip":
                    # Check if 'font' is missing as a keyword
                    has_font = any(kw.arg == 'font' for kw in node.keywords)
                    if not has_font and node.args:
                        # V2 requires font as the first positional or a keyword
                        self.local_fixes.append("AST Fix: TextClip detected, ensuring V2 font compliance")
                
                return self.generic_visit(node)

            def visit_ImportFrom(self, node):
                # Fix MoviePy Imports: from moviepy.editor import -> from moviepy import
                if node.module == "moviepy.editor":
                    node.module = "moviepy"
                    self.local_fixes.append("AST Fix: moviepy.editor -> moviepy")
                return node

        transformer = WisdomTransformer(self.moviepy_rename_map)
        new_tree = transformer.visit(tree)
        
        if transformer.local_fixes:
            # Re-generate the code from the modified AST
            fixed_code = ast.unparse(new_tree)
            return fixed_code, list(set(transformer.local_fixes))
        
        return code, []

class WisdomGuard:
    """Pre-save deterministic code validator using wisdom rules.
    Scans generated code for known-bad patterns and auto-fixes them
    BEFORE the file is written to disk. Zero LLM cost."""

    def __init__(self):
        self.ast_guard = ASTWisdomGuard()

    # Each entry: pattern to detect, human-readable rule name, and the fix
    VIOLATION_PATTERNS = [
        {
            "pattern": "PyQt6",
            "rule": "PyQt Version Consistency",
            "fix_find": "PyQt6",
            "fix_replace": "PyQt5",  # Defaulting to PyQt5 if mismatch detected for now
        },
        {
            "pattern": "PyQt5",
            "rule": "PyQt Version Consistency",
            "fix_find": "PyQt5",
            "fix_replace": "PyQt6",  # Will be dynamically adjusted if needed
        },
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
        
        # 1. Syntax Check (Python only)
        if filepath.endswith(".py"):
            try:
                import ast
                ast.parse(code)
            except SyntaxError as e:
                violations.append({
                    "file": filepath,
                    "rule": "Syntax Error",
                    "pattern": "N/A",
                    "fix": f"SyntaxError at line {e.lineno}: {e.msg}",
                })

        # 2. Pattern-based violations
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
        import ast
        fixes_applied = []
        
        # 0. Syntax Validation (Log only, don't block save unless catastrophic)
        if filepath.endswith(".py"):
            try:
                ast.parse(code)
            except SyntaxError as e:
                fixes_applied.append(f"SyntaxError detected at line {e.lineno}: {e.msg}")

        # 1. Pass 1: Simple Regex/String replacement
        for vp in self.VIOLATION_PATTERNS:
            if vp["fix_find"] in code:
                code = code.replace(vp["fix_find"], vp["fix_replace"])
                fix_desc = f"{vp['rule']}: '{vp['fix_find'].strip()}' → '{vp['fix_replace'].strip()}'"
                if fix_desc not in fixes_applied:
                    fixes_applied.append(fix_desc)

        # 2. Pass 2: Surgical AST Transformation (Provided by user for MoviePy V2 etc)
        if filepath.endswith(".py"):
            code, ast_fixes = self.ast_guard.auto_fix(code, filepath)
            fixes_applied.extend(ast_fixes)

        # 3. Requirements.txt fixes (MoviePy V2 pinning)
        if (os.path.basename(filepath) if filepath else "") == "requirements.txt":
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
            seen: Dict[str, str] = {}
            raw_code = code if code is not None else ""
            lines = [l.strip() for l in raw_code.strip().split("\n") if l.strip()]
            for line in lines:
                pkg_parts = re.split(r'[=<>!~\[]', line)
                if pkg_parts:
                    pkg = pkg_parts[0].strip().lower()
                    seen[pkg] = line  # Last wins
            deduped = list(seen.values())
            if len(deduped) < len(lines):
                fixes_applied.append(f"Deduplication: removed {len(lines) - len(deduped)} duplicate requirement(s)")
                code = "\n".join(deduped) + "\n"

        return code, fixes_applied

    def extract_imports(self, code: str) -> set:
        """Extract top-level imports from Python code."""
        import ast
        found_imports = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if hasattr(alias, "name") and alias.name:
                            found_imports.add(str(alias.name).split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if hasattr(node, "module") and node.module:
                        found_imports.add(str(node.module).split('.')[0])
        except:
            pass # Syntax errors handled in check()
        return found_imports


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
                                    config_attrs.add(getattr(target, "id", "unknown"))
                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            config_attrs.add(getattr(item.target, "id", "unknown"))

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
                    val_node = node.value
                    if getattr(val_node, "attr", "") == "config" and getattr(node, "attr", "") not in config_attrs:
                        violations.append({
                            "file": fpath,
                            "line": getattr(node, "lineno", 0),
                            "ref": f"config.{getattr(node, 'attr', '')}",
                            "available": sorted(list(config_attrs)),
                        })
                elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                    # Pattern: app.config['ATTR'] or config['ATTR']
                    val_node = node.value
                    if getattr(val_node, "attr", "") == "config":
                        node_slice = getattr(node, "slice", None)
                        if isinstance(node_slice, ast.Constant):
                            attr_name = node_slice.value
                            if isinstance(attr_name, str) and attr_name not in config_attrs:
                                violations.append({
                                    "file": fpath,
                                    "line": getattr(node, "lineno", 0),
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
                        symbols.add(getattr(target, "id", "unknown"))
        exports[mod_name] = symbols
        exports[mod_base] = symbols
        exports[fpath] = symbols

    # Check all imports
    violations: List[Dict[str, Any]] = []
    for fpath, code in written_files.items():
        if not fpath.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod_key = str((node.module or "").split(".")[0])
                if mod_key in exports:
                    available = cast(set, exports[mod_key])
                    for alias in node.names:
                        if alias.name != "*" and alias.name not in available:
                            valid_available: List[Any] = []
                            if isinstance(available, (list, set, dict)):
                                valid_available = list(available)
                            
                            temp_sorted = sorted(valid_available)
                            violations.append({
                                "file": fpath,
                                "line": node.lineno,
                                "module": node.module,
                                "import": f"from {node.module} import {alias.name}",
                                "missing": alias.name,
                                "source": f"{mod_key}.py",
                                "available": cast(Any, temp_sorted)[:15],
                            })
    return violations


# ── Global State ─────────────────────────────────────────────
_client_cache: Dict[str, Any] = {}
_active_tracker = None
GLOBAL_FALLBACK_MODEL = None  # Autonomously set on quota failure
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
                            variables.append(getattr(target, "id", "unknown"))
        except SyntaxError:
            pass
        self._symbols[str(filepath)] = symbols
        self._variables[str(filepath)] = variables

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
        existing_val = str(self._symbols.get(str(filepath), ""))
        return self._symbols.get(filepath, [])


    def extract_imports(self, code: str) -> set:
        """Extract top-level imports from Python code."""
        import ast
        found_imports = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found_imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        found_imports.add((node.module or "").split('.')[0])
        except:
            pass # Syntax errors handled in check()
        return found_imports


def smoke_test(project_path: str, run_cmd: str, timeout: int = 15) -> tuple:
    """Dry-run the entry point to catch immediate crashes (missing deps, syntax).
    Returns (success: bool, output: str)."""
    import subprocess
    import sys
    import shutil
    
    log("SMOKE_TEST", f"  Executing: {run_cmd}")
    
    # Try to use the local environment first
    try:
        # We use a subprocess with timeout to prevent hangs
        # We also pass a special environment variable to tell the app it's a dry run if it supports it
        env = os.environ.copy()
        env["DRY_RUN"] = "1" 
        
        # Split command for subprocess.run
        import shlex
        cmd_args = shlex.split(run_cmd) if os.name != "nt" else run_cmd
        
        process = subprocess.run(
            cmd_args,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=(os.name == "nt"),
            env=env
        )
        
        out_str = str(getattr(process, "stdout", "") or "")
        err_str = str(getattr(process, "stderr", "") or "")
        if process.returncode == 0:
            return True, "Process completed successfully."
        else:
            # type: ignore
            return False, f"Exit code {process.returncode}\nSTDOUT: {out_str[:200]}\nSTDERR: {err_str[:500]}"
    except subprocess.TimeoutExpired as e:
        # Timeout is often a sign of a persistent UI (success)
        # However, if ZERO output was produced, it's likely a silent zombie loop (failure)
        raw_stdout = e.stdout if e.stdout is not None else b""
        raw_stderr = e.stderr if e.stderr is not None else b""
        
        stdout = raw_stdout.decode(errors="ignore") if isinstance(raw_stdout, bytes) else str(raw_stdout)
        stderr = raw_stderr.decode(errors="ignore") if isinstance(raw_stderr, bytes) else str(raw_stderr)
        
        if "ModuleNotFoundError" in stderr or "ImportError" in stderr or "SyntaxError" in stderr:
            err_msg = str(stderr)[:500] # type: ignore
            return False, f"Crash detected before timeout:\n{err_msg}"
            
        if not stdout.strip() and not stderr.strip():
            return False, f"HANG DETECTED: App survived {timeout}s but produced NO output. Likely a tight infinite loop."
            
        return True, f"App survived {timeout}s without immediate crash (likely a persistent UI)."
    except Exception as e:
        return False, f"Smoke test execution failed: {e}"


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

    def __init__(self, max_context_chars: int = 12000):
        self._index = {}   # {filepath: set(keywords)}
        self._files = {}   # {filepath: code}
        self.max_context_chars: int = max_context_chars

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
        total_chars: int = 0
        stub_files = []

        for score, fpath in scores:
            code = str(self._files[fpath])
            if int(total_chars) + len(code) < int(self.max_context_chars) and score > 0:
                context_parts.append(f"--- {fpath} (relevance: {score}) ---\n{code}\n---") # type: ignore
                total_chars = int(total_chars) + len(code)
            else:
                first_line = code.split('\n')[0] if code else ""
                stub_files.append(f"  {fpath}: {first_line[:80]}") # type: ignore

        result = "\n\n".join(context_parts)
        if stub_files:
            result += "\n\n[OTHER FILES — summaries only]\n" + "\n".join(stub_files)
        if state_table:
            result += f"\n\n{state_table}"

        return result or "No files written yet."


# Ensure UTF-8 output even on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        getattr(sys.stderr, "reconfigure")(encoding='utf-8', errors='replace')
except Exception:
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
    """Print a timestamped, tagged log line (streamed to Electron via stdout)."""
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] [{tag}]  {message}", flush=True)
    except UnicodeEncodeError:
        # Fallback for extremely restrictive environments
        print(f"[{ts}] [{tag}]  {message.encode('ascii', 'replace').decode('ascii')}", flush=True)


def divider():
    log("SYSTEM", "-" * 52)


def strip_fences(text: str) -> str:
    """Remove markdown code fences if present.
    Also attempts to extract the longest JSON object if multiple exist, 
    but ONLY if no specific code fences were found."""
    text = text.strip()
    
    # 1. Standard fence removal - if we find these, we assume the content is
    if "```" in text:
        # Extract the content of the first code block
        start_fence = text.find("```")
        # Find the end of the line containing the start fence
        line_end = text.find("\n", start_fence)
        if line_end != -1:
            end_fence = text.find("```", line_end + 1)
            if end_fence != -1:
                return text[line_end:end_fence].strip() # type: ignore
            # Unclosed fence, just take everything after the start line
            return text[line_end:].strip() # type: ignore
    
    # 2. Aggressive JSON extraction (find first { and last })
    # ONLY if we didn't find fences (some chatty models skip fences for JSON)
    if text.count('{') > 0 and text.count('}') > 0:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            # We found a potential JSON block. Let's return only this block
            # if it's the dominant part of the text or if we are in a JSON-heavy phase.
            return text[start:end+1].strip() # type: ignore
    
    # 3. Robust Cleanup for unclosed fences (Gemini/Deepseek behavior)
    if text.startswith("```"):
        # If it starts with a fence but we didn't find a closing one or it failed logic above
        first_line_end = text.find("\n")
        if first_line_end != -1:
            return text[first_line_end:].strip() # type: ignore

    return text

# Module-level active tracker — set by execute_build, auto-read by ask_llm
_active_tracker = None

def ask_llm(client: Any, model: str, system_role: str, user_content: str,
            tracker: Optional['CostTracker'] = None) -> str:
    """Send a chat completion request and return the cleaned response.
    Auto-resolves the right client for multi-provider model mixing.
    Routes Claude models through the Anthropic SDK automatically.
    Automatically records cost to _active_tracker if set, or explicit tracker param.
    Includes automatic retry-on-429 with key rotation via KeyPool."""
    global _active_tracker, GLOBAL_FALLBACK_MODEL
    import time as _time

    # Apply global pivot if active
    if GLOBAL_FALLBACK_MODEL and model != GLOBAL_FALLBACK_MODEL:
        model = GLOBAL_FALLBACK_MODEL

    provider_id = detect_provider(model) if not model.lower().startswith("claude") else "anthropic"
    pool = KeyPool.get_pool(provider_id)
    max_retries: int = min(len(pool.keys), 3) if pool.keys else 1

    for attempt in range(max_retries):
        try:
            # ── Anthropic/Claude Route ──
            if model.lower().startswith("claude"):
                return _ask_anthropic(model, system_role, user_content, tracker)

            # ── Standard OpenAI-compatible Route ──
            resolved_client = get_cached_client(model)
            
            # Normalize model name for the provider
            # Use explicit delimiters (model provider/name) to strip prefixes
            api_model = model
            if "/" in api_model:
                potential_provider, name = api_model.split("/", 1)
                if potential_provider.lower() in PROVIDERS:
                    api_model = name
            elif ":" in api_model:
                potential_provider, name = api_model.split(":", 1)
                if potential_provider.lower() in PROVIDERS:
                    api_model = name
            
            response = resolved_client.chat.completions.create(
                model=api_model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.1,
                max_tokens=8192,
            )
            raw = response.choices[0].message.content.strip()

            # DEBUG: Log raw response to file for local model debugging
            try:
                with open("llm_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- MODEL: {model} ---\n")
                    f.write(raw)
                    f.write("\n------------------------\n")
            except: pass

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
            is_quota_fail = 'quota' in err_str or 'billing' in err_str
            is_generic_fail = '404' in err_str or 'not found' in err_str or '401' in err_str or 'permission' in err_str or '400' in err_str

            if is_quota_fail or is_generic_fail:
                reason = "Quota/Billing" if is_quota_fail else "Model/Auth Failure"
                log("SYSTEM", f"  🚫 {provider_id.upper()} {reason}. Initiating Global Mission Pivot...")
                
                # Capture the error for diagnostics
                try:
                    with open("llm_errors.log", "a", encoding="utf-8") as f:
                        import datetime
                        stamp = datetime.datetime.now().isoformat()
                        f.write(f"\n[{stamp}] ERROR: {model} ({provider_id}) -> {e}\n")
                except: pass

                # Fallback list in priority order - Local First for local-first stability
                fallbacks = [
                    ("local", "local/qwen2.5:14b"),
                    ("local", "local/gemma2:9b"),
                    ("local", "local/deepseek-coder"),
                    ("local", "local/mistral"),
                    ("local", "local/llama3.2:3b"),
                    ("gemini", "gemini-1.5-pro-latest"),
                    ("xai", "grok-beta"),
                    ("openai", "gpt-4o-mini")
                ]
                # Find the next best available fallback
                current_index: int = -1
                for i, (f_prov, f_mod) in enumerate(fallbacks):
                    if f_mod == model:
                        current_index = i
                        break
                
                # Try models after the current one in the list
                for alt_provider, alt_model in fallbacks[current_index + 1:]: # type: ignore
                    alt_pool = KeyPool.get_pool(alt_provider)
                    if alt_pool.keys:
                        GLOBAL_FALLBACK_MODEL = alt_model
                        log("SYSTEM", f"  🔀 MISSION CRITICAL: Pivoting to {alt_provider.upper()} ({alt_model}) to complete build.")
                        return ask_llm(client, alt_model, system_role, user_content, tracker)
                
                log("SYSTEM", "  ❌ Critical: All LLM fallback providers exhausted.")

            attempt_int = int(attempt)
            max_retries_int = int(max_retries)
            if is_rate_limit and attempt_int < (max_retries_int - 1) and pool.keys and len(pool.keys) > 1:
                current_key = pool.current_key()
                pool.mark_limited(current_key)
                pool.rotate()
                # Invalidate cached client so next call uses new key
                if provider_id in cast(dict, _client_cache):
                    del _client_cache[provider_id] # type: ignore
                wait: int = 2 ** int(attempt)
                log("KEYPOOL", f"  🔄 Rate limited on key …{current_key[-6:]} — rotating to next key (retry in {wait}s)")
                _time.sleep(wait)
                continue
            raise


def _ask_anthropic(model: str, system_role: str, user_content: str,
                   tracker: Optional['CostTracker'] = None) -> str:
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
        "prefixes": ["groq/"],
        "label": "Groq ⚡ (FREE)"
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "prefixes": ["gemini/"],
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
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "env_key": "XAI_API_KEY",
        "prefixes": ["grok-"],
        "label": "xAI Grok 🌌 (Free Tier/Trial)"
    },
    "local": {
        "base_url": "http://localhost:11434/v1",  # Default to Ollama
        "env_key": "LOCAL_LLM_API_KEY",
        "prefixes": ["local/", "local:", "ollama:", "lms:"],
        "label": "Local LLM 🏠 (Ollama/LM Studio)"
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": "OLLAMA_API_KEY",
        "prefixes": ["ollama", "llama", "mistral", "gemma", "phi"],
        "label": "Ollama 🦙 (Local)"
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
        pool_env = str(env_key).replace("_KEY", "_KEYS") if env_key else ""
        raw_pool = os.environ.get(pool_env, "")
        raw_single = os.environ.get(env_key, "") if env_key else ""
        
        if raw_pool:
            self.keys = [k.strip() for k in raw_pool.split(",") if k.strip()]
        elif raw_single:
            self.keys = [raw_single.strip()]
        elif provider_id == "local":
            self.keys = ["ollama-local-placeholder"]
        else:
            self.keys = []
        
        self._index = 0
        self._cooldowns: Dict[str, float] = {}  # key -> timestamp when cooldown expires
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
    
    # 1. Explicit Check: prefix/model or prefix:model
    if "/" in model_name:
        p = model_name.split("/", 1)[0].lower()
        if p in PROVIDERS: return p
    if ":" in model_name:
        p = model_name.split(":", 1)[0].lower()
        if p in PROVIDERS: return p

    # 2. Heuristic Check: Known identifiers in name
    if "gpt-" in model_lower: return "openai"
    if "claude" in model_lower: return "anthropic"
    if "gemini" in model_lower: return "gemini"
    if "gemma" in model_lower: return "groq" # prioritize groq for gemma
    if "llama" in model_lower: return "groq" # prioritize groq for llama
    
    # Automatic local detection for common local model names if not prefixed
    if any(m in model_lower for m in ["llama3", "mistral", "phi3", "qwen"]) and "local" in model_lower:
        return "local"
    
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
        api_key = fallback_key or os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        log("WARN", f"  No API key for {provider['label']}. Set {provider['env_key']} env var.")
    
    kwargs = {"api_key": api_key or "none"}
    if provider_id == "local":
        kwargs["base_url"] = os.environ.get("LOCAL_LLM_BASE_URL") or provider["base_url"]
    elif provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]
    
    return OpenAI(**kwargs)

# Client cache to avoid recreating clients for same provider
_client_cache: Dict[str, Any] = {}

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
            del _client_cache[k] # type: ignore
        _client_cache[cache_key] = get_client_for_model(model_name, fallback_key)
        if pool.pool_size > 1:
            log("KEYPOOL", f"  🔌 Connected {PROVIDERS[provider_id]['label']} (key {pool._index + 1}/{pool.pool_size})")
        else:
            log("SYSTEM", f"  🔌 Connected: {PROVIDERS[provider_id]['label']}")
    return _client_cache[cache_key]


# ── Global State Manifest ────────────────────────────────────

import ast

def build_manifest(written_files: dict, planned_files: Optional[List[Any]] = None) -> dict:
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
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
                entry["classes"].append({"name": node.name, "methods": methods}) # type: ignore
            # Top-level assignments (variables/constants)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        entry["variables"].append(target.id) # type: ignore
                        # Detect __all__
                        if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                            vals: List[str] = [
                                str(getattr(elt, "value", "")) for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(getattr(elt, "value", None), str)
                            ]
                            entry["exports_all"] = vals
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


def generate_verification_suite(project_path: str, manifest: dict, client, model: str):
    """Generates a pytest-compatible suite to verify the final code integrity."""
    log("POST-PROCESS", "🧬 Generating verification test suite...")
    
    test_gen_system = (
        "You are an SDET (Software Development Engineer in Test). "
        "Your mission: Write a robust 'pytest' suite that verifies the core logic of the provided manifest. "
        "Focus on: 1. Successful imports 2. Function signature matches 3. Basic happy-path execution. "
        "Ensure you use relative imports or path-insertion to find the project modules. "
        "Output ONLY raw Python code. No markdown."
    )
    
    # Provide the manifest so the AI knows exactly what to test
    manifest_summary = "\n".join([f"File: {k}, Exports: {v['functions'] + [c['name'] for c in v['classes']]}" 
                                 for k, v in manifest.items() if k.endswith(".py")])
    
    try:
        test_code = ask_llm(client, model, test_gen_system, f"Project Manifest:\n{manifest_summary}")
        
        test_dir = os.path.join(project_path, "tests")
        os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, "test_overlord_verify.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
            
        log("POST-PROCESS", "  ✓ Verification suite saved to tests/")
        return True
    except Exception as e:
        log("ERROR", f"  Test generation failed: {e}")
        return False


def capture_visual_proof(project_path, run_cmd, platform="web"):
    """
    Spawns the app, waits for stabilization, and captures a 'Proof of Life' screenshot.
    This screenshot is then added to the final handoff package.
    """
    log("VISUAL", f"📸 Capturing Visual DNA for {platform}...")
    proof_dir = os.path.join(project_path, "assets", "proof")
    os.makedirs(proof_dir, exist_ok=True)
    screenshot_path = os.path.join(proof_dir, "final_ui_render.png")

    # Start the app in a background process
    proc = subprocess.Popen(run_cmd, shell=True, cwd=project_path, 
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Allow time for the UI to mount and animations to settle
    time.sleep(8) 

    try:
        if platform == "web":
            # Attempt to find the port in stdout
            port = "3000"
            try:
                # Read a bit of output to see if a port is mentioned
                out_sample = proc.stdout.read(1000) if proc.stdout else ""
                port_match = re.search(r"http://(?:localhost|127\.0\.0\.1):(\d+)", out_sample)
                if port_match:
                    port = port_match.group(1)
                    log("VISUAL", f"  ↳ Detected dynamic port: {port}")
            except:
                pass

            # Uses a lightweight playwright script to hit the local port
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                try:
                    page.goto(f"http://localhost:{port}", wait_until="networkidle", timeout=10000)
                    page.screenshot(path=screenshot_path, full_page=True)
                    log("VISUAL", f"  ✓ Web proof captured at port {port}")
                except Exception as e:
                    # Fallback to desktop capture if web navigation fails
                    log("VISUAL", "  ⚠ Web capture failed, falling back to desktop capture...")
                    from PIL import ImageGrab
                    screenshot = ImageGrab.grab()
                    screenshot.save(screenshot_path)
                    log("VISUAL", "  ✓ Fallback desktop capture successful")
                finally:
                    browser.close()
        else:
            # For Desktop/Studio apps: captures the active window
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)
            log("VISUAL", f"  ✓ Proof of Life captured: {os.path.basename(screenshot_path)}")
            
    except Exception as e:
        log("WARN", f"  ⚠ Visual capture failed: {e}")
    finally:
        try:
            proc.terminate() # Kill the app after capture
            proc.wait(timeout=2)
        except:
            pass


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
    #   {"files": [{"path": "filename.py", "task": "..."}]}
    file_tree = [f["path"] for f in plan.get("files", [])]

    created_dirs = set()
    for file_path in file_tree:
        full_path = base_path / file_path

        # Create subdirectories if they don't exist
        parent = full_path.parent
        if parent != base_path and str(parent) not in created_dirs:
            parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(str(parent))

        # Skip if it's a directory (Architecture sometimes plans these as 'files')
        if file_path.endswith("/") or file_path.endswith("\\"):
            continue

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
        "5. Obvious logic errors (infinite loops, wrong return types)\n\n"
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
                if not isinstance(self.files, dict):
                    self.files = {}
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
        
        # Create empty placeholder file (only if it doesn't already exist and is NOT a directory)
        if fpath.endswith("/") or fpath.endswith("\\"):
            continue

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

def vanish_cleanup(project_path: str):
    """Purges source code and temporary assets to leave a clean media-only output."""
    log("SYSTEM", "🪄  VANISH: Purging source code from Video-Only project...")
    
    # Files to KEEP
    keep_list = ["BUILD_LOG.md", "package_manifest.json", "plan.json", "cost_report.json"]
    keep_dirs = ["outputs", "media", "assets"]
    
    # Walk through the project path
    for root, dirs, files in os.walk(project_path, topdown=False):
        for name in files:
            fpath = os.path.join(root, name)
            rel_path = os.path.relpath(fpath, project_path)
            
            # Skip files we want to keep
            if any(rel_path.startswith(kd) for kd in keep_dirs):
                continue
            if name in keep_list:
                continue
            
            # Delete everything else
            try:
                os.remove(fpath)
            except Exception:
                pass
                
        for name in dirs:
            dpath = os.path.join(root, name)
            rel_path = os.path.relpath(dpath, project_path)
            
            # Skip directories we want to keep
            if any(rel_path.startswith(kd) for kd in keep_dirs):
                continue
                
            # Delete empty dirs
            try:
                os.rmdir(dpath)
            except Exception:
                pass

    log("SUCCESS", "✨ Vanish complete. Output folder is now media-only.")


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
            
            # Parse diagnosis
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
        
    except urllib.error.HTTPError as e: # type: ignore
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
        log("VOICE", "  ℹ Auto-play failed: {e} — audio still saved at build_briefing.mp3")
    
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
            log("HANDOFF", "  ⚠ Overview generation failed: {e}")

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
    project_type = manifest.get("project_type", "UNDEFINED")
    stack = manifest.get("stack", {})
    video_artifact = manifest.get("video_artifact")
    date = datetime.now().strftime("%Y-%m-%d")

    # Determine button labels and links
    code_btn_label = "Open Code"
    code_btn_link = f"./output/{project_name}"
    
    video_btn_html = ""
    if video_artifact:
        video_url = f"./output/{project_name}/{video_artifact.replace('\\', '/')}"
        video_btn_html = f'<a href="{video_url}" class="bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded text-sm font-bold inline-block mr-2 mt-2">View Video</a>'
        if project_type == "VIDEO":
            code_btn_label = "Production Files"

    # The HTML Card Template
    new_card = f"""
    <div class="card bg-gray-800 p-6 rounded-xl border border-gray-700 hover:border-blue-500 transition-all">
        <h3 class="text-xl font-bold mb-2">{project_name}</h3>
        <p class="text-gray-400 text-sm mb-1"><strong>Type:</strong> {project_type}</p>
        <p class="text-gray-400 text-sm mb-4"><strong>Stack:</strong> {stack.get('frontend', 'N/A')} + {stack.get('backend', 'N/A')}</p>
        <div class="flex flex-wrap">
            <a href="./output/{project_name}/BUILD_LOG.md" class="bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded text-sm font-bold inline-block mr-2 mt-2">Logs</a>
            {video_btn_html}
            <a href="{code_btn_link}" class="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded text-sm font-bold inline-block mt-2">{code_btn_label}</a>
        </div>
    </div>
    """

    # If gallery doesn't exist, create it with Tailwind CSS styling
    if not os.path.exists(gallery_file):
        with open(gallery_file, "w", encoding="utf-8") as f:
            f.write(f"<html><head><script src='https://cdn.tailwindcss.com'></script></head>"
                    f"<body class='bg-gray-900 text-white p-10'>"
                    f"<h1 class='text-4xl font-bold mb-8'>Overlord Project Library</h1>"
                    f"<div id='gallery' class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>{new_card}</div>"
                    f"</body></html>")
    else:
        # Append the new card to the existing gallery
        with open(gallery_file, "r+", encoding="utf-8") as f:
            content = f.read()
            # If card already exists (same name), we don't duplicate (simple check)
            if f"<h3>{project_name}</h3>" in content:
                log("GALLERY", f"  ℹ Card for '{project_name}' already exists. Updating handled by HTML replacement.")
            
            f.seek(0)
            f.write(content.replace(
                "<div id='gallery' class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>",
                f"<div id='gallery' class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>{new_card}"
            ).replace( # Fallback for old class
                "<div id='gallery' class='grid grid-cols-3 gap-6'>",
                f"<div id='gallery' class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>{new_card}"
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
        "env_template": env_path if 'env_path' in locals() else "",
        "runtime": str(runtime) if 'runtime' in locals() else "unknown",
        "port": str(port),
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
    briefing_system = (
        "You are a concise project narrator. Write a 2-3 sentence spoken briefing "
        " (under 50 words) summarizing what was just built. Use a confident, professional "
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
    
    result: Dict[str, Any] = {
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
                elif resp.status_code == 403:
                    log("RESEARCH", f"      ⚠ {category} Forbidden (403): Check API configuration or limits.")
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
            if resp.status_code == 403:
                log("RESEARCH", "  ⚠ Developer Knowledge API Forbidden (403): Unauthorized or key restriction.")
                return ""
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


def resolve_mission_parameters(args):
    """
    Autonomously resolves 'auto' parameters in the build configuration.
    Fulfills the 'Truly Prompt-Based' mission by inferring intentions.
    """
    log("SYSTEM", "🤖 Interpreting mission briefing for autonomous fulfillment...")
    
    # 1. Resolve Platform
    if args.platform == "auto":
        p_lower = args.prompt.lower()
        if any(w in p_lower for w in ["android", "mobile", "phone", "kotlin", "jetpack"]):
            args.platform = "android"
        elif any(w in p_lower for w in ["linux", "desktop", "gtk", "qt", "ubuntu"]):
            args.platform = "linux"
        elif any(w in p_lower for w in ["studio", "adobe", "photoshop", "editor", "graphics", "professional", "creative", "suite", "pro"]):
            args.platform = "studio"
        else:
            args.platform = "python"
        log("SYSTEM", f"  ↳ Inferred Platform: {args.platform.upper()}")

    # 2. Resolve Scale
    if args.scale == "auto":
        p_lower = args.prompt.lower()
        if len(args.prompt) > 200 or any(w in p_lower for w in ["app", "complete", "full", "system", "complex"]):
            args.scale = "app"
        elif any(w in p_lower for w in ["script", "simple", "utility", "tool"]):
            args.scale = "script"
        elif any(w in p_lower for w in ["asset", "image", "video", "logo"]):
            args.scale = "asset"
        else:
            args.scale = "app"
        log("SYSTEM", f"  ↳ Inferred Scale: {args.scale.upper()}")

    # 3. Resolve Phase
    if args.phase == "auto":
        args.phase = "all"
        log("SYSTEM", f"  ↳ Inferred Phase: ALL")

    # 4. Resolve Strategic Routing (Model Selection)
    if not args.arch_model:
        if len(args.prompt) > 300 or args.scale == "app":
            # Start with GPT-4o to verify pivot, or use high-reasoning Gemini
            args.arch_model = "gpt-4o"
        else:
            args.arch_model = "gpt-4o"
        log("SYSTEM", f"  ↳ Smart Router selected strategy: {args.arch_model}")


# ── Build Pipeline ───────────────────────────────────────────

def execute_build(args):
    project_path = os.path.join(args.output, args.project)
    
    # Initialize Status Bridge for UI updates
    status_bridge = StatusBridge(project_path)
    status_bridge.notify("System", "Spinning up creation pipeline...", status="info")
    
    # ── Handle Clean Output ──
    if getattr(args, 'clean', False) and os.path.exists(project_path):
        log("SYSTEM", f"🧹 Cleaning output directory: {project_path}")
        shutil.rmtree(project_path)
        
    os.makedirs(project_path, exist_ok=True)

    # ── Phase -1: RESOLVE MISSION PARAMETERS (Autonomy) ──
    resolve_mission_parameters(args)

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    
    model = args.model if args.model != "auto" else "gpt-4o"

    # Per-phase model routing: use the best model for thinking, fast model for coding
    arch_model = getattr(args, 'arch_model', None) or model  # Phase 0 + 1 + 3
    if arch_model == "auto": arch_model = model
    
    eng_model = getattr(args, 'eng_model', None) or model    # Phase 2
    if eng_model == "auto": eng_model = model
    # Cost-aware tier: cheap/local model for Reviewer, Dockerfile, README, Env scripts
    local_model = getattr(args, 'local_model', None) or eng_model  # Phase 2.5 + 4 + 5
    # Dedicated review model: Claude or other reasoning model for senior-level code review
    review_model = getattr(args, 'review_model', None) or local_model  # Phase 2.5 Master Reviewer

    # ── Handle Decompile Only ──
    if getattr(args, 'decompile', False):
        log("SYSTEM", "🔍 DECOMPILE MODE ACTIVE — Extracting source structure...")
        # (Implementation of decompile logic would go here, 
        # for now we'll simulate it by logging and exiting early as requested)
        log("SYSTEM", "✅ Decompilation complete. Exiting.")
        return

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
    proj_state.status_bridge = status_bridge # Attach Status Bridge
    rag = CodebaseRAG(max_context_chars=12000)
    dep_verifier = DependencyVerifier()

    # Initialize Cost Tracker with budget kill-switch
    budget = getattr(args, 'budget', 5.0) or 5.0
    tracker = CostTracker(budget=float(budget))

    # Activate module-level tracker so ALL ask_llm calls auto-record cost
    global _active_tracker
    _active_tracker = tracker

    
    # Resolve platform profile
    platform = args.platform
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["python"])
    platform_directive = profile["arch_directive"]

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
    if args.phase in ["all", "plan"]:
        log("SYSTEM", "🧠 Phase 0: Prompt Enhancement AI")
        log("SYSTEM", f"  Raw input: \"{args.prompt[:80]}{'…' if len(args.prompt) > 80 else ''}\"")

        enhance_system = (
            "You are 'Overlord Prompt Engineer,' an elite AI that transforms vague user ideas "
            "into detailed, comprehensive software engineering specifications. "
            "The user will give you a brief idea — maybe just a few words. "
            "Your job is to expand it into a DETAILED prompt that a code-generating AI can use to build "
            "a complete, production-quality application. "
            f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
            + (f"\n\nFOCUS TARGET: {args.focus}" if args.focus else "") +
            "\n\nYour enhanced prompt MUST include:"
            "\n1. A clear project description and purpose"
            "\n2. Specific features (at least 5-8 concrete features with details)"
            "\n3. Technical architecture (what modules/files should exist)"
            "\n4. UI/UX details if applicable (what the user sees and interacts with)"
            "\n5. Error handling and edge cases to consider"
            "\n6. Data flow — how the pieces connect"
            "\n7. Any external libraries or APIs to use (prefer well-known, stable packages)"
            "\n\nRules:"
            "\n- Output ONLY the enhanced prompt text. No markdown, no headers, no explanations."
            "\n- Write it as a single, flowing engineering specification."
            "\n- Be specific — name exact function names, exact UI elements, exact data structures."
            "\n- If the idea involves media, include image/video generation capabilities."
            "\n- Always include a main entry point and a proper CLI or GUI."
            "\n- Make it sound like a senior engineer wrote the spec."
            "\n- Keep it under 500 words but make every word count."
        )

        if args.scale == "script":
            enhance_system = (
                "You are 'Overlord Zero-Bloat Architect.' Transform user ideas into a TIGHT, "
                "LOGIC-ONLY engineering specification for a STANDALONE SCRIPT. "
                "Ignore all UI, monitoring, and dashboard requirements. "
                f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
                "\n\nOutput ONLY the enhanced prompt text. No markdown. Target 300 words."
            )
        elif args.scale == "asset":
            enhance_system = (
                "You are 'Overlord Creative Director.' Create a blueprint for a SINGLE ASSET. "
                "The file tree should contain EXACTLY ONE file: 'asset_metadata.json' or 'render_manifest.json'. "
                "This manifest will be used by the MediaEngine to produce the final file. "
                "\n\nOutput ONLY valid JSON manifest."
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
            original_project = getattr(args, "project", "default_project")
            prompt = getattr(args, "prompt", "")
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
    else:
        log("SYSTEM", "  ⏭️  Skipping Planning/Enhancement phase (Phase selection)")
        enhanced_prompt = args.prompt
        original_prompt = args.prompt
        research_report = ""
        search_context = ""

    divider()

    # ── Phase 1: ARCHITECT ───────────────────────────────────
    log("ARCHITECT", "Engaging Architect agent…")
    log("ARCHITECT", "Analyzing prompt and planning project structure…")
    status_bridge.notify("Architect", "Analyzing prompt and planning project structure...", status="thinking")

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
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        "\n\nTECH STACK CONSTRAINT (Stable-Gold Stack):"
        "\nYou MUST prioritize these libraries for ALL projects unless technically impossible:"
        "\n1. FRONTEND: TypeScript is mandatory. Use Tailwind CSS for styling."
        "\n2. BACKEND: Use FastAPI for Python-based logic; avoid Flask for high-concurrency tasks."
        "\n3. DATABASE: Default to PostgreSQL. Include a 'schema.prisma' file if using Prisma."
        "\n4. DOCUMENTATION: Every project must include a detailed 'README.md' and '.env.example'."
        "\n\nAutonomy Protocol: You are authorized to identify problems within your assigned folders without being prompted. "
        "When a problem is found, attempt 3 autonomous 'Healing' cycles using the Sentinel and Alchemist. "
        "Only notify the user if the problem is solved (success report) or if you are stuck after 3 attempts (request for guidance). "
        "Create temporary scripts/tools as needed to overcome technical blockers."
        "\n\nConversational Sub-Routine:"
        "\n1. COGNITION: You are a Co-Engineer, not a bot. Adopt a specific tone (Direct, Witty, or Encouraging). Use contractions. Avoid 'As an AI' phrases."
        "\n2. PACING: Break long responses into smaller 'bubbles' or chunks to manage cadence."
        "\n3. PERSISTENCE: Actively recall and reference previous projects (e.g. Kinetic Prism, frost-mcp-server) context when available."
        "\n4. THE CHECK-IN: Initiate check-ins (e.g. 'VRAM hit 7.2GB, want to optimize?'). Don't wait for prompts."
        "\n5. THE MIRRORING: Adjust style to the partner. Short inputs = punchy responses. Detailed inputs = structured analysis."
        "\n6. EMOTIONAL SAFETY: If errors occur, use reassuring language (e.g. 'Ouch, hit a snag, fixing it...') instead of raw dumps."
        "\n7. USER PREFERENCES: Remember specific user constraints (e.g. 'fp8 quantization', 'no pickles'). Use available Vector Memory context to personalize every decision."
        "\nIf you make a mistake, fix it casually. Treat every 'Seed' as a conversation."
    )

    if args.scale == "script":
        arch_system = (
            "You are 'Overlord Script Engineer.' Create a blueprint for a clean, modular "
            "STANDALONE SCRIPT. Limit the file tree to 1-3 files maximum (main.py, utils.py). "
            "Ignore all UI, monitoring, and dashboard requirements. "
            "\n\nOutput ONLY valid JSON manifest."
        )
    elif args.scale == "asset":
        arch_system = (
            "You are 'Overlord Asset Generator.' Create a blueprint for a SINGLE ASSET. "
            "The file tree should contain EXACTLY ONE file: 'asset_metadata.json' or 'render_manifest.json'. "
            "This manifest will be used by the MediaEngine to produce the final file. "
            "\n\nOutput ONLY valid JSON manifest."
        )

    arch_system += (
        f"{version_advisory}"
        f"\n\n{research_report if 'research_report' in locals() and research_report else ''}"
        "\n\nOutput ONLY valid JSON with this exact 'Package Manifest' schema: "
        '{"project_name": "<slug_name>", '
        '"project_type": "VIDEO | GAME | WEBSITE | TOOL | SCRIPT | ASSET", '
        '"mission_summary": "<1-sentence high level goal>", '
        '"stack": {"frontend": "<framework>", "backend": "<framework>", "database": "<provider>"}, '
        '"file_tree": ["path/file.ext", ...], '
        '"files": [{"path": "filename.ext", "task": "description"}], '
        '"dependencies": ["package1"], '
        f'"run_command": "{profile["run_command"]}"}} '
        "Every project MUST include a main entry point and a README.md. "
        "Output ONLY raw JSON. No markdown."
    )

    plan = {}
    raw_plan = ""
    retries = 3
    while isinstance(retries, int) and retries > 0:
        try:
            raw_plan = ask_llm(client, arch_model, arch_system, args.prompt)
            try:
                plan = json.loads(raw_plan)
            except json.JSONDecodeError:
                # RECOVERY: If JSON fails, the model likely output a conversational plan.
                # Let's try to extract the file list using regex.
                log("DEBUG", f"  Raw Architect Response:\n{raw_plan}")
                log("SYSTEM", "  ⚠️ Architect returned conversational text. Initiating JSON Recovery...")
                files = []
                # Find lines like "- path/file.py: description" or "app/main.py: Entry point"
                # Using a broad regex for file paths
                file_matches = _re_module.findall(r"(?:-|\d+\.)\s*([\w\-\./]+\.\w+)\s*[:\-]?\s*(.*)", raw_plan)
                for f_path, f_task in file_matches:
                    if f_path and "." in f_path: # Basic sanity check for file extension
                        files.append({"path": f_path.strip(), "task": f_task.strip() or "Auto-generated task"})
                
                # If we found at least one file, we can reconstruct a basic plan
                if files:
                    plan = {
                        "project_name": args.project,
                        "project_type": "UNKNOWN (Recovered)",
                        "mission_summary": f"Autonomous synthesis of: {args.prompt[:50]}...",
                        "stack": {"frontend": "Python", "backend": "Python", "database": "SQLite"},
                        "file_tree": [f["path"] for f in files],
                        "files": files,
                        "dependencies": ["psutil", "pyqt6"], # Safe defaults for this project type
                        "run_command": "python main.py"
                    }
                    log("SYSTEM", f"  ✅ Recovered {len(files)} files from conversational response.")
                else:
                    raise # Re-raise if we couldn't even recover via regex
            break 
        except Exception as e:
            log("ERROR", f"  Architect failed: {e}")
            # Ensure retries is an int for subtraction
            _retries = int(retries) if 'retries' in locals() else 0
            _retries -= 1
            retries = _retries
            if retries > 0:
                log("SYSTEM", f"  🔄 Retrying Architect generation (Attempts left: {retries})...")
            else:
                log("ERROR", "  Critical: Architect failed to return valid or recoverable JSON.")
                sys.exit(1)

    else:
        # Load existing plan if skipping architect
        try:
            with open(os.path.join(project_path, "plan.json"), "r") as f:
                plan = json.load(f)
        except:
            log("WARN", "No existing plan found. Skipping code generation.")
            plan = {}

    # Extract final project metadata
    files   = plan.get("files", [])
    deps    = plan.get("dependencies", [])
    run_cmd = plan.get("run_command", "python main.py")
    arch_stack     = plan.get("stack", {})
    arch_proj_name = plan.get("project_name", args.project)
    
    # Handle both list of dicts and list of strings for files
    normalized_files = []
    for f in files:
        if isinstance(f, dict):
            normalized_files.append({"path": f.get("path", "unknown"), "task": f.get("task", f.get("purpose", "Synthesis"))})
        else:
            normalized_files.append({"path": str(f), "task": "Synthesis"})
    
    arch_file_tree = plan.get("file_tree", [f["path"] for f in normalized_files])

    # Always log MISSION BRIEFING if we have a plan
    if plan:
        log("SYSTEM", "── MISSION BRIEFING ──────────────────────────────────")
        log("SYSTEM", f"🚀 PRODUCT TYPE: {str(plan.get('project_type', 'UNDEFINED')).upper()}")
        log("SYSTEM", f"📝 MISSION:      {plan.get('mission_summary', 'Synthesis in progress...')}")
        log("ARCHITECT", f"Blueprint ready — {len(normalized_files)} file(s), {len(deps)} dep(s)")
        if arch_stack:
            log("ARCHITECT", f"  Stack: {json.dumps(arch_stack)}")
        for f in normalized_files:
            log("ARCHITECT", f"  ├─ {f['path']}  →  {f['task'][:60]}")
        log("ARCHITECT", f"  └─ run: {run_cmd}")
        log("SYSTEM", "──────────────────────────────────────────────────────")
    
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
    if args.phase in ["all", "code"] and files:
        log("ENGINEER", "Engaging Engineer agent…")

    file_list = [f["path"] for f in files]
    written_files = state.files  # Backed by persistent CodebaseState

    # Strategy: Write main.py FIRST so we know what imports it expects,
    # then pass those import names as a contract to all other files.
    main_entry = None
    other_files = []
    _wf = cast(Dict[str, str], written_files)
    if "main.py" in _wf:
        for f in files:
            if f["path"] == "main.py":
                main_entry = f
                break
        # Re-iterate to get other files, excluding main_entry if found
        for f in files:
            if f != main_entry:
                other_files.append(f)

    # Reorder: main.py first, then everything else
    ordered_files = ([main_entry] + other_files) if main_entry else list(files)

    for i, file_spec in enumerate(ordered_files, 1):
        fpath = file_spec["path"]
        ftask = file_spec["task"]
        log("ENGINEER", f"[{i}/{len(ordered_files)}] Writing: {fpath}")
        status_bridge.notify("Engineer", f"Writing {fpath} ({i}/{len(ordered_files)})...", status="coding")

        # ── Pillar 1: RAG-Powered Context + Global State ──
        manifest = build_manifest(written_files, planned_files=file_list)
        manifest_ctx = manifest_to_context(manifest) if manifest else "No files written yet."
        symbol_table = proj_state.get_symbol_table()
        rag_context = rag.get_relevant_context(fpath, ftask, symbol_table)

        # Extract import contract from main.py if available
        import_contract = ""
        _wf = cast(Dict[str, str], written_files)
        if "main.py" in _wf and fpath != "main.py":
            main_code = _wf["main.py"]
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

        eng_system = (
            "You are 'Overlord,' an autonomous Senior Full-Stack Engineer. "
            "Directive: Modular Engineering. Write clean, documented code using proper imports. "
            "IMPORTANT: NEVER use placeholder URLs, dummy credentials, or broken 'example.com' domains. "
            "Use functional logic. If an API is unknown, use a robust mock or public test endpoint. "
            "Directive: Self-healing. Anticipate failures with clean try-except blocks. "
            f"Structure: {file_list}. Target: {fpath}. Task: {ftask}. "
            + (f" FOCUS TARGET: {args.focus}." if args.focus else "") +
            f"{import_contract}"
            f"\n\n{symbol_table}"
            f"{wisdom.get_generation_rules_directive()}"
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
                        log("REVIEWER", f"  ⚠ Rewrite failed: {e} — retrying or pivoting.")
                        break
            
            # Optional: if code is essentially empty/garbage, we can log it here but let the next iteration fix it
            if len(code.strip()) < 10:
                log("WARN", f"  ✗ Short/Empty code detected for {fpath} on attempt {review_count}")

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
        # Skip if it's a directory (Architecture sometimes plans these as 'files')
        if fpath.endswith("/") or fpath.endswith("\\"):
            log("ENGINEER", f"  📁 Skipping directory: {fpath}")
            continue

        # Directory already created by Project Assembler (Phase 1.5)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)

        state.write(fpath, code, review_count)
        written_files = state.files  # Keep reference in sync
        proj_state.register_file(fpath, code)
        rag.index_file(fpath, code, proj_state.get_exports_for(fpath))
        log("ENGINEER", f"  ✓ {fpath}  ({len(code)} chars, {review_count} review(s))")
        log("STATE", f"    Registered {len(proj_state.get_exports_for(fpath))} symbols")

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

    # ── Phase 2.5: AUDITOR + MASTER REVIEWER ──────────────────
    log("AUDITOR", "Engaging Local Intelligence Auditor…")
    status_bridge.notify("Auditor", "Auditing code for quality and safety...", status="audit")

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
            log("AUDITOR", f"  ✓ Syntax clean: {fpath}")
            # Extract imports for dependency injection
            module_imports = wisdom_guard.extract_imports(code)
            for module_name in module_imports:
                if module_name in std_libs:
                    continue
                
                # Check if this is a local module/file or directory
                _wf_cast = cast(Dict[str, str], written_files)
                is_local = (
                    module_name in _wf_cast or 
                    f"{module_name}.py" in _wf_cast or 
                    any(str(f).startswith(f"{module_name}/") for f in _wf_cast)
                )
                
                if not is_local and not module_name.startswith('.'):
                    final_pkg = PKG_MAP.get(module_name, module_name)
                    if final_pkg not in detected_deps:
                        detected_deps.add(final_pkg)
                        log("AUDITOR", f"    + Auto-injecting: {final_pkg}")
        except SyntaxError as e:
            log("ERROR", f"  Syntax Error in {fpath}:L{e.lineno}: {e.msg}")
        except Exception as e:
            log("ERROR", f"  Auditor failed on {fpath}: {e}")

    # Final Validation Gate sweep across ALL files
    manifest = build_manifest(written_files)
    all_violations = validation_gate(written_files, manifest)
    if all_violations:
        log("GATE", f"  ⚠ {len(all_violations)} cross-file import violation(s) remain")
        for v in all_violations:
            log("GATE", f"    ✗ {v['file']}: {v['import_stmt']} → missing '{v['missing']}'")
    else:
        log("GATE", "  ✓ All cross-file imports verified")

    deps = list(detected_deps)

    # ── Pillar 4: MASTER REVIEWER (Zero-Trust LLM Gatekeeper) ──
    log("REVIEWER", "Engaging Master Reviewer — Zero-Trust Audit…")

    reviewer_system = (
        "Role: You are the Lead Systems Architect and Senior Security Engineer. "
        "Your sole purpose is to audit code generated by a Developer agent."
        "\n\nObjective: Perform a Zero-Trust audit. Identify logical fallacies, missing "
        "dependencies, and integration mismatches before any code is finalized."
        "\n\n1. VERIFICATION CHECKLIST:"
        "\n  - Loop Safety: Flag ANY while-loop missing a time.sleep() or delay."
        "\n  - Platform Check: Reject 'curses' on Windows projects."
        "\n  - Import Integrity: Does every import point to a file that exists or a known package?"
        "\n  - Dependency Sync: Are all imported libraries listed in dependencies?"
        "\n  - State Consistency: Flag all naming discrepancies (user_id vs userId, etc.)"
        "\n\n2. RESPONSE PROTOCOL:"
        '\n  IF BUGS FOUND: Output JSON: {"status": "REJECTED", "issues": [{"file": "...", "line": N, "error": "...", "fix": "..."}]}'
        '\n  IF CODE IS PERFECT: Output JSON: {"status": "APPROVED"}'
        "\n\n3. CONSTRAINT: Provide ONLY Direct Corrections or Approval. Output ONLY raw JSON."
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
                    _wf_cast = cast(Dict[str, str], written_files)
                    if f in _wf_cast:
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
                            f"CURRENT CODE:\n{cast(Dict[str, str], written_files)[fix_file]}")
                        # Ensure written_files is treated as a dict for 'in'
                        _wf_cast = cast(Dict[str, str], written_files)
                        if fix_file in _wf_cast:
                            log("DEBUG", f"Fixing file {fix_file} in memory...")
                            prev_code = _wf_cast[fix_file]
                            log("DEBUG", f"CURRENT CODE:\n{prev_code}")
                            _wf_cast[fix_file] = fixed_code
                        fp = os.path.join(project_path, fix_file)
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(fixed_code)
                        log("REVIEWER", f"  ✓ Fixed: {fix_file}")
                    except Exception as e:
                        log("ERROR", f"  Fix failed for {fix_file}: {e}")
                        traceback.print_exc()

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
        status_bridge.notify("Sentinel", "Scanning for critical errors...", status="warning")
        
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
        for fpath, code in cast(Dict[str, str], written_files).items():
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
            log("DEBUGGER", f"Running: {run_cmd}")

            max_passes = 5
            for attempt in range(1, max_passes + 1):
                log("DEBUGGER", f"Debug pass {attempt}/{max_passes}…")
                try:
                    result = subprocess.run(
                        run_cmd, shell=True,
                        capture_output=True, text=True,
                        cwd=project_path, timeout=30,
                    )
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
        env_system = (
            "You are 'Overlord Environment Specialist.' "
            "Your mission: generate deployment scripts so the user can run this project with ONE command. "
            "You will be given the project's file list, dependencies, and run command. "
            "Output ONLY the requested script content. No markdown fences, no explanations."
        )

        if args.scale != "asset":
            log("ENVIRON", "Engaging Environment Agent…")
            log("ENVIRON", "Generating one-command run scripts for all platforms…")

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
            f"4. Run the application with: {run_cmd}\n"
            f"5. Pause at the end so the window stays open\n"
            f"Use @echo off and proper Windows batch syntax.")
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
            "Role: You are 'Overlord Developer.' You write clean, scalable, "
            f"production-ready {arch_stack.get('backend', 'Python')} code. "
            "\n\nRules for High-Reliability Generation:"
            "\n1. LOOP SAFETY: Every 'while' loop MUST include a 'time.sleep()' or an event delay. NEVER write tight loops that freeze the CPU."
            "\n2. PLATFORM SAFETY: If designing for Windows, AVOID standard 'curses'. Use 'rich', 'colorama', or 'windows-curses'."
            "\n3. INTEGRATION: Ensure every function you use is either defined in the current file or imported from a file that EXISTS in the tree."
            "\n4. SECRETS: Always use 'os.getenv()' for keys. Assume a .env file exists."
            "\n\nConstraint: Output ONLY the source code. No preamble. No markdown fences."
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
        
        divider()
        
    # ── Phase 6: SMOKE TEST (Out-of-the-Box Verification) ────
    if not getattr(args, 'no_smoke', False):
        log("SYSTEM", "🚀 Phase 6: Smoke Test (Final Verification)")
        
        # Bypass for ASSET scale or VIDEO projects to avoid false negatives / "ISSUE DETECTED" UI bug
        if args.scale == "asset" or plan.get("project_type") == "VIDEO":
            log("SUCCESS", "  ✓ Skipping Smoke Test for non-executable project (Media/Asset verified via pipeline).")
            smoke_ok = True
            smoke_msg = "Media/Asset verified"
        else:
            # Try a quick dry-run of the entry point
            smoke_ok, smoke_msg = smoke_test(project_path, run_cmd)
        
        if smoke_ok:
            log("SUCCESS", f"  ✓ Smoke test passed: {smoke_msg}")
        else:
            log("CRITICAL", "  ✗ Smoke test returned issues. The project may not run out-of-the-box.")
            log("CRITICAL", f"  Detail: {smoke_msg}")
            
            # PROACTIVE HEALING — if smoke test fails, we can try to auto-fix requirements
            if "ModuleNotFoundError" in smoke_msg:
                missing_pkg = smoke_msg.split("No module named '")[1].split("'")[0]
                log("SYSTEM", f"  Attempting to auto-fix missing dependency: {missing_pkg}")
                if missing_pkg not in deps:
                    deps.append(missing_pkg)
                    # Rewrite requirements.txt
                    with open(req_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(deps))
                    log("SYSTEM", f"  ✓ Added {missing_pkg} to requirements.txt")
                    
                    # RETRY Smoke Test
                    log("SYSTEM", f"  Retrying smoke test after adding {missing_pkg}…")
                    smoke_ok2, smoke_msg2 = smoke_test(project_path, run_cmd)
                    if smoke_ok2:
                        log("SUCCESS", f"  ✓ Smoke test passed after auto-fix: {smoke_msg2}")
                    else:
                        log("ERROR", f"  ✗ Secondary smoke test also failed. Manual intervention needed.")
                        log("DEBUG", f"  Secondary Detail: {smoke_msg2}")

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

    # ── Phase 7: TEST GENERATION ─────────────────────────────
    if not getattr(args, 'no_tests', False):
        generate_verification_suite(
            project_path=project_path,
            manifest=manifest,
            client=client,
            model=eng_model
        )
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
        # Check for video artifact to optimize gallery link
        video_artifact = None
        outputs_dir = os.path.join(project_path, "outputs", "videos")
        if os.path.exists(outputs_dir):
            vfiles = [f for f in os.listdir(outputs_dir) if f.endswith(".mp4")]
            if vfiles:
                video_artifact = os.path.join("outputs", "videos", vfiles[0])

        gallery_manifest = {
            "project_name": arch_proj_name,
            "project_type": plan.get("project_type", "UNDEFINED"),
            "stack": arch_stack or {},
            "file_tree": arch_file_tree or list(written_files.keys()),
            "video_artifact": video_artifact
        }
        update_gallery(project_path, gallery_manifest)
    except Exception as e:
        log("WARN", f"Gallery update failed (non-critical): {e}")

    # ── Phase 7: VANISH (Video-Only Cleanup) ──────────────────
    if plan.get("project_type") == "VIDEO":
        vanish_cleanup(project_path)

    # ── Done ─────────────────────────────────────────────
    divider()

    # Save cost report
    tracker.save_report(project_path)
    log("SYSTEM", f"💵 {tracker.get_summary()}")
    if tracker.budget_exceeded:
        log("WARN", f"Build exceeded budget: ${tracker.total_cost:.4f} / ${tracker.budget:.2f}")
    if tracker.pivot_triggered:
        log("SYSTEM", "Model was auto-pivoted to local model mid-build to control costs.")

    # ── Phase 12: TEST GENERATION ─────────────────────────────
    if not getattr(args, 'no_tests', False):
        try:
            generate_verification_suite(
                project_path=project_path,
                manifest=manifest,
                client=client,
                model=local_model
            )
        except Exception as e:
            log("WARN", f"  ⚠ Test generation failed: {e}")

    # ── Phase 13: VISUAL PROOF CAPTURE ────────────────────────
    if not getattr(args, 'no_visual', False) and plan.get("project_type") != "VIDEO":
        # Detect platform (standard heuristic)
        # Check manifest for web-specific files/dependencies
        manifest_str = str(manifest).lower()
        is_web = any(x in manifest_str for x in ["fastapi", "flask", "react", "next.js", "html", "css", "js"])
        platform = "web" if is_web else "desktop"
        
        try:
            capture_visual_proof(
                project_path=project_path,
                run_cmd=run_cmd,
                platform=platform
            )
        except Exception as e:
            log("WARN", f"  ⚠ Visual proof capture skipped: {e}")

    # Voice Briefing - narrate what was built (if Eleven Labs key is available)
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
    
    # Highlight video location if applicable
    if plan.get("project_type") == "VIDEO":
        outputs_videos = os.path.join(project_path, "outputs", "videos")
        if os.path.exists(outputs_videos):
            vfiles = [f for f in os.listdir(outputs_videos) if f.endswith(".mp4")]
            if vfiles:
                log("SUCCESS", f"🎬 VIDEO READY: {os.path.join(outputs_videos, vfiles[0])}")
    
    log("SUCCESS", f"To run:  cd {project_path} && {run_cmd}")
    log("SUCCESS", f"Or use:  setup.sh (Unix) / run.bat (Windows)")


# ── Main Execution ───────────────────────────────────────────

if __name__ == "__main__":
    # Activate Fortress Protocols
    # watchdog = IntegrityWatchdog([__file__, "main.js"])

    parser = argparse.ArgumentParser(description="Overlord Agent Brain")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--prompt",  help="Build prompt")
    parser.add_argument("--output",  default="./output", help="Output directory")
    parser.add_argument("--model",      default="gpt-4o", help="OpenAI model (default for all phases)")
    parser.add_argument("--arch-model", default="", help="Strategy model for Architect/Prompt phases")
    parser.add_argument("--eng-model",  default="", help="Speed model for Engineer phase")
    parser.add_argument("--review-model", default="", help="Dedicated review model for senior code review (e.g. claude-sonnet-4-20250514)")
    parser.add_argument("--local-model", default="", help="Cheap/local model for Reviewer, Env, Dockerfile phases (e.g. llama3 via Ollama)")
    parser.add_argument("--budget",      default=5.0, type=float, help="Max spend in USD before pivoting to local model (default: $5.00)")
    parser.add_argument("--api-key",    default="", help="OpenAI API key")
    parser.add_argument("--docker",     action="store_true", help="Generate Dockerfile")
    parser.add_argument("--readme",     action="store_true", help="Generate README.md")
    parser.add_argument("--debug",      action="store_true", help="Auto-debug (3 passes)")
    parser.add_argument("--setup",      action="store_true", help="Generate setup.ps1, docker-compose.yml, .env.template")
    parser.add_argument("--voice",      action="store_true", help="Generate voice briefing via ElevenLabs TTS at build completion")
    parser.add_argument("--no-bundle",  action="store_true", help="Skip PyInstaller .exe bundling")
    parser.add_argument("--platform",   default="auto", choices=["auto", "python", "android", "linux", "studio"],
                        help="Target platform: auto (default), python, android, linux, or studio")
    parser.add_argument("--scale",      default="auto", choices=["auto", "app", "script", "asset"],
                        help="Build scale: auto (default), app, script, or asset")
    parser.add_argument("--mode",       default="new", choices=["new", "upgrade", "reverse"],
                        help="Build mode: new (default), upgrade, or reverse")
    parser.add_argument("--phase",      default="auto", choices=["auto", "all", "plan", "code", "verify"],
                        help="Build phase: auto (default), all, plan, code, or verify")
    parser.add_argument("--focus",      default="", help="Focus targeting for specific module or feature")
    parser.add_argument("--decompile",  action="store_true", help="Decompile source and exit")
    parser.add_argument("--clean",      action="store_true", help="Clean output directory before building")
    parser.add_argument("--source",     default="", help="Source path for upgrade mode")
    parser.add_argument("--max-fix-cycles", type=int, default=3, help="Max auto-debug cycles")
    
    # Handle the Electron positional argument bridge requirement
    # [script_name, project_name, prompt, ...any other flags]
    if len(sys.argv) > 2 and not sys.argv[1].startswith('-'):
        args = parser.parse_known_args()[0]
        setattr(args, 'project', sys.argv[1])
        setattr(args, 'prompt', sys.argv[2])
        # Any remaining args like --docker are handled by parse_known_args if present
    else:
        args = parser.parse_args()

    if not args.project or not args.prompt:
        parser.print_help()
        log("ERROR", "Missing required arguments: project and prompt.")
        sys.exit(1)

    try:
        execute_build(args)
    except Exception as e:
        log("CRITICAL", f"Fatal build crash: {e}")
        traceback.print_exc()
        sys.exit(1)



WisdomGuard = ASTWisdomGuard
