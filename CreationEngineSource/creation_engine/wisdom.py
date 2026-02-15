"""
Creation Engine — Wisdom System
GlobalWisdom (cross-project learnings), WisdomGuard (deterministic fixer),
and KnowledgeBase (persistent memory).
"""

import os
import re
import time
import json

from .llm_client import log


# ── Global Wisdom System ────────────────────────────────────

class GlobalWisdom:
    """Cross-project learning system. Stores error→fix patterns
    at both project-local and global scopes."""

    def __init__(self, project_path):
        self.wisdom_file = os.path.join(project_path, "local_wisdom.json")
        self.global_wisdom_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "global_wisdom.json"
        )
        self.wisdom = self._load(self.wisdom_file)
        self.global_wisdom = self._load(self.global_wisdom_file)

    def _load(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.wisdom_file, "w") as f:
            json.dump(self.wisdom, f, indent=2)

    def _save_global(self):
        with open(self.global_wisdom_file, "w") as f:
            json.dump(self.global_wisdom, f, indent=2)

    def consult(self, error_trace):
        """Finds if this error pattern has been solved before."""
        for pattern, fix_logic in self.wisdom.items():
            if pattern in error_trace:
                return fix_logic
        for pattern, fix_logic in self.global_wisdom.items():
            if pattern in error_trace:
                return fix_logic
        return None

    def learn(self, error_trace, fix_strategy):
        """Extracts a pattern and saves an actionable fix strategy."""
        lines = error_trace.strip().split('\n')
        key = lines[-1].strip() if lines else error_trace[:100]
        self.wisdom[key] = fix_strategy
        self._save()
        self.global_wisdom[key] = fix_strategy
        self._save_global()

    def get_generation_rules(self) -> str:
        """Return all GENERATION_RULE__ entries as a formatted block."""
        rules = {k: v for k, v in self.global_wisdom.items() if k.startswith("GENERATION_RULE__")}
        if not rules:
            return ""
        lines = ["MANDATORY GENERATION RULES (learned from past build failures):"]
        for key, rule in rules.items():
            label = key.replace("GENERATION_RULE__", "").replace("_", " ").title()
            lines.append(f"- [{label}]: {rule}")
        return "\n".join(lines)

    def get_generation_rules_directive(self) -> str:
        """Build a prompt directive string from GENERATION_RULE entries."""
        rules = [f"- {fix}" for key, fix in self.global_wisdom.items()
                 if key.startswith("GENERATION_RULE__")]
        if not rules:
            return ""
        return (
            "\n\nCRITICAL WISDOM RULES (from past failures — DO NOT VIOLATE):\n"
            + "\n".join(rules)
        )

    def review_against_wisdom(self, code: str, filepath: str) -> list:
        """Proactively scan generated code against all known wisdom rules."""
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

    def _check_generation_rule(self, rule_key, fix_text, code, filepath):
        code_lower = code.lower()
        rule_checks = {
            "GENERATION_RULE__MOVIEPY_V2_IMPORTS": lambda: "from moviepy.editor import" in code,
            "GENERATION_RULE__NO_DUPLICATE_CLASS_DEFINITIONS": lambda: self._has_duplicate_class_defs(code),
            "GENERATION_RULE__FLASK_DEPRECATED_APIS": lambda: "before_first_request" in code,
            "GENERATION_RULE__PYTHON_314_STDLIB_REMOVALS": lambda: any(
                f"import {mod}" in code or f"from {mod}" in code
                for mod in ["audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr",
                            "mailcap", "msilib", "nis", "nntplib", "ossaudiodev",
                            "pipes", "sndhdr", "spwd", "sunau", "telnetlib", "uu", "xdrlib"]
            ),
            "GENERATION_RULE__ENUM_CASING_CONVENTION": lambda: False,
            "GENERATION_RULE__CROSS_FILE_SYMBOL_CONSISTENCY": lambda: False,
            "GENERATION_RULE__CONFIG_ATTRIBUTE_NAMES": lambda: False,
            "GENERATION_RULE__PYDANTIC_V2_MIGRATION": lambda: (
                "from pydantic import validator" in code
                or ("class Config:" in code and "BaseModel" in code)
                or (".dict()" in code and "pydantic" in code_lower)
                or "from pydantic import BaseSettings" in code
            ),
            "GENERATION_RULE__FASTAPI_PYDANTIC_PINNING": lambda: False,
        }
        checker = rule_checks.get(rule_key)
        return checker() if checker else False

    def _check_error_pattern(self, pattern, code):
        checks = {
            "moviepy.editor": "from moviepy.editor import" in code,
            "audioop": "import audioop" in code or "from audioop" in code,
            "pyaudioop": "import pyaudioop" in code or "from pyaudioop" in code,
            "before_first_request": "before_first_request" in code,
        }
        for keyword, triggered in checks.items():
            if keyword in pattern.lower() and triggered:
                return True
        return False

    def _has_duplicate_class_defs(self, code):
        class_defs = re.findall(r'^class\s+(\w+)', code, re.MULTILINE)
        imports = re.findall(r'from\s+\S+\s+import\s+(.+)', code)
        imported_names = set()
        for imp_line in imports:
            for name in imp_line.split(','):
                imported_names.add(name.strip().split(' as ')[0].strip())
        for cls in class_defs:
            if cls in imported_names:
                return True
        return False


# ── Wisdom Guard (Pre-Save Deterministic Fixer) ─────────────

class WisdomGuard:
    """Pre-save deterministic code validator. Scans generated code for
    known-bad patterns and auto-fixes them BEFORE writing to disk.
    Zero LLM cost."""

    VIOLATION_PATTERNS = [
        {"pattern": "from moviepy.editor import", "rule": "MoviePy V2 Imports",
         "fix_find": "from moviepy.editor import", "fix_replace": "from moviepy import"},
        {"pattern": "from moviepy.editor", "rule": "MoviePy V2 Imports",
         "fix_find": "from moviepy.editor", "fix_replace": "from moviepy"},
        {"pattern": "@app.before_first_request", "rule": "Flask 2.3+ Deprecated APIs",
         "fix_find": "@app.before_first_request",
         "fix_replace": "# @app.before_first_request REMOVED in Flask 2.3+ — call directly during init"},
        {"pattern": "import audioop\n", "rule": "Python 3.13+ Stdlib Removals",
         "fix_find": "import audioop\n", "fix_replace": "import audioop_lts as audioop  # audioop removed in 3.13+\n"},
        {"pattern": "from audioop import", "rule": "Python 3.13+ Stdlib Removals",
         "fix_find": "from audioop import", "fix_replace": "from audioop_lts import"},
        {"pattern": "from pydantic import validator", "rule": "Pydantic V2 Migration",
         "fix_find": "from pydantic import validator",
         "fix_replace": "from pydantic import field_validator  # Pydantic V2"},
        {"pattern": ".subclip(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".subclip(", "fix_replace": ".subclipped("},
        {"pattern": ".set_position(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_position(", "fix_replace": ".with_position("},
        {"pattern": ".set_duration(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_duration(", "fix_replace": ".with_duration("},
        {"pattern": ".set_audio(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_audio(", "fix_replace": ".with_audio("},
        {"pattern": ".set_start(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_start(", "fix_replace": ".with_start("},
        {"pattern": ".set_end(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_end(", "fix_replace": ".with_end("},
        {"pattern": ".set_opacity(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_opacity(", "fix_replace": ".with_opacity("},
        {"pattern": ".set_fps(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".set_fps(", "fix_replace": ".with_fps("},
        {"pattern": ".volumex(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".volumex(", "fix_replace": ".with_volume_scaled("},
        {"pattern": ".resize(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".resize(", "fix_replace": ".resized("},
        {"pattern": ".crop(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".crop(", "fix_replace": ".cropped("},
        {"pattern": ".rotate(", "rule": "MoviePy V2 API Renames",
         "fix_find": ".rotate(", "fix_replace": ".rotated("},
        {"pattern": "TextClip(text,", "rule": "MoviePy V2 TextClip Constructor",
         "fix_find": "TextClip(text,",
         "fix_replace": "TextClip(font=font, text=text,  # MoviePy V2: font is 1st positional arg"},
        {"pattern": "fontsize=", "rule": "MoviePy V2 TextClip Params",
         "fix_find": "fontsize=", "fix_replace": "font_size="},
    ]

    REQUIREMENTS_FIXES = [
        {"pattern_re": r"moviepy\s*[=<>!~]=\s*[01]\.\S*",
         "replace_with": "moviepy>=2.0.0", "rule": "MoviePy V2 Pinning"},
    ]

    def check(self, code: str, filepath: str) -> list:
        violations = []
        for vp in self.VIOLATION_PATTERNS:
            if vp["pattern"] in code:
                violations.append({
                    "file": filepath, "rule": vp["rule"],
                    "pattern": vp["pattern"],
                    "fix": f"Replace '{vp['fix_find']}' → '{vp['fix_replace']}'",
                })
        return violations

    def auto_fix(self, code: str, filepath: str = "") -> tuple:
        """Apply deterministic fixes. Returns (fixed_code, list_of_fixes)."""
        fixes_applied = []

        # Simple string replacements
        for vp in self.VIOLATION_PATTERNS:
            if vp["fix_find"] in code:
                code = code.replace(vp["fix_find"], vp["fix_replace"])
                fix_desc = f"{vp['rule']}: '{vp['fix_find'].strip()}' → '{vp['fix_replace'].strip()}'"
                if fix_desc not in fixes_applied:
                    fixes_applied.append(fix_desc)

        # Surgical AST Transformation for Python files
        if filepath.endswith(".py"):
            try:
                import ast
                tree = ast.parse(code)
                
                # MoviePy Rename Map
                rename_map = {
                    "subclip": "subclipped", "set_position": "with_position",
                    "set_duration": "with_duration", "set_audio": "with_audio",
                    "set_start": "with_start", "set_end": "with_end",
                    "set_opacity": "with_opacity", "set_fps": "with_fps",
                    "volumex": "with_volume_scaled", "resize": "resized",
                    "crop": "cropped", "rotate": "rotated"
                }

                class WisdomTransformer(ast.NodeTransformer):
                    def __init__(self, r_map):
                        self.r_map = r_map
                        self.local_fixes = []
                    def visit_Call(self, node):
                        if isinstance(node.func, ast.Attribute) and node.func.attr in self.r_map:
                            old = node.func.attr
                            new = self.r_map[old]
                            node.func.attr = new
                            self.local_fixes.append(f"AST Fix: method {old} -> {new}")
                        if isinstance(node.func, ast.Name) and node.func.id == "TextClip":
                            if not any(kw.arg == 'font' for kw in node.keywords) and node.args:
                                self.local_fixes.append("AST Fix: TextClip detected, ensuring V2 font compliance")
                        return self.generic_visit(node)
                    def visit_ImportFrom(self, node):
                        if node.module == "moviepy.editor":
                            node.module = "moviepy"
                            self.local_fixes.append("AST Fix: moviepy.editor -> moviepy")
                        return node

                transformer = WisdomTransformer(rename_map)
                new_tree = transformer.visit(tree)
                if transformer.local_fixes:
                    code = ast.unparse(new_tree)
                    fixes_applied.extend(list(set(transformer.local_fixes)))
            except Exception as e:
                # Fallback to current code if AST fails
                pass

        basename = os.path.basename(filepath) if filepath else ""
        if basename == "requirements.txt":
            for rf in self.REQUIREMENTS_FIXES:
                match = re.search(rf["pattern_re"], code)
                if match:
                    code = re.sub(rf["pattern_re"], rf["replace_with"], code)
                    fixes_applied.append(f"{rf['rule']}: '{match.group()}' -> '{rf['replace_with']}'")

            # Deduplicate requirements
            seen = {}
            lines = [l.strip() for l in code.strip().split("\n") if l.strip()]
            for line in lines:
                pkg = re.split(r'[=<>!~\[]', line)[0].strip().lower()
                seen[pkg] = line
            deduped = list(seen.values())
            if len(deduped) < len(lines):
                fixes_applied.append(f"Deduplication: removed {len(lines) - len(deduped)} duplicate(s)")
                code = "\n".join(deduped) + "\n"

        return code, fixes_applied


# ── Aura Registry (Persistent Memory) ────────────────────────

class AuraRegistry:
    """
    Nexus persistent memory system. Stores 'Lessons Learned' from past builds
    to prevent repeating errors in future projects.
    """

    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        self.registry_file = os.path.join(memory_dir, "aura_registry.json")
        self.knowledge = self._load_registry()

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def memorize(self, lesson: dict):
        """Append a new lesson to the global memory."""
        self.knowledge.append({
            "timestamp": str(time.time()),
            "lesson": lesson.get("text", ""),
            "trigger": lesson.get("error", "General"),
            "tags": lesson.get("tags", []),
            "success": lesson.get("success", True)
        })
        self._save_registry()

    def _save_registry(self):
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.knowledge, f, indent=2)
        except Exception:
            pass

    def recall(self, context: str) -> str:
        """Retrieves relevant lessons based on contextual keyword matching."""
        if not self.knowledge:
            return ""
        context_lower = context.lower()
        matches = []
        for item in self.knowledge:
            tags = item.get("tags", [])
            trigger = item.get("trigger", "")
            score = sum(1 for t in tags if t.lower() in context_lower)
            if trigger.lower() in context_lower:
                score += 3
            if score > 0:
                matches.append((score, item))
        
        if not matches:
            return ""
            
        matches.sort(reverse=True, key=lambda x: x[0])
        lines = ["\n🧠 [AURA PERSISTENT MEMORY RECALLED]"]
        for _, item in matches[:5]:
            lines.append(f"  - Pattern: {item.get('trigger', '?')}")
            lines.append(f"    Wisdom: {item.get('lesson', 'N/A')}")
        return "\n".join(lines)
