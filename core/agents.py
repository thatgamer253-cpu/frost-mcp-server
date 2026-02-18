import os
import json
import re
from typing import Dict, List, Optional
from openai import OpenAI

# Try to import Anthropic if available
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Production Safety Directive (Shared)
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

class LLMClient:
    """Attributes and methods for LLM interaction."""
    def __init__(self, model="gpt-4o"):
        self.model = model
        
        # OpenRouter / OpenAI Setup
        # Prioritize OPENAI_API_KEY for direct access; fall back to OpenRouter
        self.openai_key = os.getenv("OPENAI_API_KEY") 
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        base_url = None
        api_key = None
        
        if self.openai_key:
             api_key = self.openai_key
        elif self.openrouter_key:
             base_url = "https://openrouter.ai/api/v1"
             api_key = self.openrouter_key
             
        if api_key:
            self.openai_client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.openai_client = None

        # Anthropic Setup
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if HAS_ANTHROPIC and os.getenv("ANTHROPIC_API_KEY") else None

    def ask(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Standardized LLM call."""
        # Check model routing - prefer Claude if requested and available
        if "claude" in self.model and self.anthropic_client:
            return self._ask_claude(system_prompt, user_prompt, json_mode)
        
        # Fallback to OpenAI/OpenRouter
        if self.openai_client:
            return self._ask_openai(system_prompt, user_prompt, json_mode)
            
        print("[X] NO VALID API KEY FOUND (OpenAI/OpenRouter/Anthropic). LOGGING MOCK RESPONSE.")
        return "{}" if json_mode else ""

    def _ask_openai(self, system, user, json_mode):
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.2,
            "max_tokens": 1024  # Enforce safe limit for OpenRouter/limited keys
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        try:
            resp = self.openai_client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] OpenAI/OpenRouter Error: {e}")
            return "{}" if json_mode else ""

    def _ask_claude(self, system, user, json_mode):
        try:
            resp = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=0.2
            )
            return resp.content[0].text
        except Exception as e:
            print(f"[X] Anthropic Error: {e}")
            return "{}" if json_mode else ""

class AgentBase:
    """Base class for all agents."""
    def __init__(self, name: str, role: str, mission: str, model: str = "gpt-4o"):
        self.name = name
        self.role = role
        self.mission = mission
        self.llm = LLMClient(model)

class Architect(AgentBase):
    """The Architect: Plans the project structure."""
    def __init__(self, model="gpt-4o"):
        super().__init__("Overlord", "Senior Architect", "Decompose user intent into a logical file structure.", model)
        self.system_prompt = (
            "You are 'Overlord,' an autonomous Senior Full-Stack Engineer and DevOps Specialist. "
            "Directive: No Hallucinations. Do not use placeholder domains or URLs like 'example.com' or 'your-api-endpoint'. "
            "Use real public APIs or write self-contained logic with functional mocks if needed. "
            "Mission: Zero-Interaction Planning. Decompose user intent into a logical file structure. "
            "\n\nDESIGN SYSTEM & VISUAL IDENTITY (MANDATORY):"
            "\n- Define a 'Visual DNA': color palette (hex), typography (Google Fonts), and spacing."
            "\n- Create a 'master_brand' style description for AI image generation (e.g., 'Cyberpunk minimalism, neon blue & purple, dark mode')."
            "\n- IMPORTANT: The 'master_brand' description will be used to generate ACTUAL ASSETS (logos, backgrounds) so be evocative!"
            "\n\nOUTPUT FORMAT: JSON with 'project_name', 'file_tree' (list of paths), 'files' (list of {path, task}), 'dependencies', and 'visual_identity'."
            f"{PRODUCTION_SAFETY_DIRECTIVE}"
        )

    def plan(self, prompt: str) -> Dict:
        """Generates a JSON manifest of the project structure."""
        print(f"[{self.role.upper()}] Analyzing prompt: {prompt[:50]}...")
        raw_json = self.llm.ask(self.system_prompt, f"Plan this project: {prompt}", json_mode=True)
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse Architect plan (First 100 chars): {raw_json[:100]}")
            return {}

def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM responses.

    GPT-4o frequently wraps code in ```python ... ``` blocks.
    This strips those fences so the raw code can be parsed.
    """
    if not text:
        return text
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```python or ```)
        lines = lines[1:]
        # Remove last line if it's a closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


class Engineer(AgentBase):
    """The Engineer: Writes the actual code."""
    def __init__(self, model="gpt-4o"):
        super().__init__("Builder", "Senior Engineer", "Implement the file structure with production-ready code.", model)
        self.system_prompt = (
            "You are a Senior Software Engineer. Write production-ready code. "
            "No placeholders. No 'pass'. Full implementation. "
            "Output ONLY raw code, NO markdown fences. "
            f"{PRODUCTION_SAFETY_DIRECTIVE}"
        )

    def build_file(self, file_path: str, task_desc: str, context: str) -> str:
        """Generates code for a specific file."""
        print(f"[{self.role.upper()}] Building {os.path.basename(file_path)}...")
        user_msg = f"File: {file_path}\nTask: {task_desc}\nContext: {context}"
        raw = self.llm.ask(self.system_prompt, user_msg)
        return strip_code_fences(raw)

class Reviewer(AgentBase):
    """The Reviewer / Alchemist: Reviews and rewrites code to fix issues."""
    def __init__(self, model="gpt-4o"):
        super().__init__("Watcher", "QA Specialist", "Review and rewrite code for correctness and security.", model)
        self.review_prompt = (
            "You are a QA Specialist. Review the code for syntax errors, logic flaws, and security issues. "
            "Return a JSON list of issues found, each with 'severity' (CRITICAL/HIGH/MEDIUM/LOW) and 'description'."
        )
        self.rewrite_prompt = (
            "You are the Alchemist — a senior code optimizer and security hardener. "
            "You receive source code and a list of violations/flags from the Sentinel auditor. "
            "Your job is to REWRITE the code to fix ALL flagged issues while preserving functionality. "
            "\n\nMANDATORY FIXES:"
            "\n- RES-001 (Rate Limiting): Add retry with exponential backoff for ALL external API/HTTP calls. "
            "Import 'time' and wrap requests in a retry loop with max 3 attempts and backoff."
            "\n- MEM-002 (Narrative Memory): Before any content generation, add a check against a local log "
            "(SQLite or JSON) to prevent duplicate outputs. Add a 'narrative_memory' check function."
            "\n- OPS-003 (Static Composition): Use dynamic parameters instead of hardcoded strings for media processing."
            "\n- AUT-004 (Reactive Triggering): Replace 'input()' calls with background observer patterns where possible."
            "\n- Add circuit breakers to any recursive functions (max_depth parameter)."
            "\n- Never hardcode API keys — always use os.getenv() or config files."
            "\n- Wrap all external I/O in try/except with fallback behavior."
            "\n\nRULES:"
            "\n- Output ONLY the fixed Python/code. No markdown fences, no explanations."
            "\n- Preserve all existing functionality — only add safety/fix layers."
            "\n- If the file is not Python (JSON, .gitignore, requirements.txt, README, etc), return it unchanged."
            f"\n{PRODUCTION_SAFETY_DIRECTIVE}"
        )

    def review(self, code: str, context: str) -> List[str]:
        """Returns a list of issues found in the code via LLM."""
        if not code.strip():
            return []
        prompt = f"Review this code:\n```\n{code[:3000]}\n```\nContext: {context}"
        raw = self.llm.ask(self.review_prompt, prompt, json_mode=True)
        try:
            issues = json.loads(raw)
            if isinstance(issues, list):
                return [str(i) for i in issues]
            return [str(issues)]
        except (json.JSONDecodeError, TypeError):
            return []

    def rewrite(self, code: str, violations: List[Dict[str, str]],
                filename: str = "unknown.py") -> str:
        """Rewrite code to fix all Sentinel violations.

        Args:
            code: The original source code.
            violations: List of dicts with 'rule', 'severity', 'description'.
            filename: Name of the file being fixed.

        Returns:
            The rewritten, fixed source code.
        """
        if not code.strip():
            return code

        # Don't rewrite non-code files
        non_code_exts = ('.json', '.txt', '.md', '.gitignore', '.yml', '.yaml', '.toml', '.cfg', '.ini')
        if any(filename.endswith(ext) for ext in non_code_exts):
            return code

        # Format violations for the prompt
        violation_text = "\n".join(
            f"  - [{v.get('severity', 'UNKNOWN')}] {v.get('rule', 'N/A')}: {v.get('description', '')}"
            for v in violations
        )

        prompt = (
            f"FILE: {filename}\n\n"
            f"VIOLATIONS TO FIX:\n{violation_text}\n\n"
            f"ORIGINAL CODE:\n{code}\n\n"
            f"Rewrite this code to fix ALL violations listed above. "
            f"Output ONLY the fixed code, no markdown fences."
        )

        print(f"[ALCHEMIST] Rewriting {filename} ({len(violations)} violations)...")
        fixed = self.llm.ask(self.rewrite_prompt, prompt)

        if not fixed or not fixed.strip():
            print(f"[ALCHEMIST] WARNING: Empty response for {filename}, keeping original")
            return code

        # Strip markdown fences if the LLM added them anyway
        fixed = strip_code_fences(fixed)

        return fixed
