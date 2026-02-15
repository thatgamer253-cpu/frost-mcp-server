#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Local Agent Brain (Ollama Backend)
  Fully offline code generation using local LLMs.
  No API keys needed — runs on your hardware.
  
  Requires: Ollama running at http://localhost:11434
  Model:    deepseek-coder:6.7b (default, configurable)
==============================================================
"""

import os
import sys
import json
import subprocess
import time
import shutil
import requests
from datetime import datetime

# Force UTF-8 encoding for Windows pipes
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ── Shared Config ────────────────────────────────────────────
# Import shared resources from the main agent brain
try:
    from agent_brain import PKG_MAP, GlobalWisdom, log, divider, strip_fences
except ImportError:
    # Standalone fallback if agent_brain isn't available
    PKG_MAP = {
        "PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
        "yaml": "PyYAML", "bs4": "beautifulsoup4", "dotenv": "python-dotenv",
        "ffmpeg": "ffmpeg-python", "gi": "PyGObject", "fal_client": "fal-client",
        "googleapiclient": "google-api-python-client",
    }

    class GlobalWisdom:
        def __init__(self, project_path):
            self.wisdom_file = os.path.join(project_path, "local_wisdom.json")
            self.wisdom = {}
            if os.path.exists(self.wisdom_file):
                try:
                    with open(self.wisdom_file, "r") as f:
                        self.wisdom = json.load(f)
                except Exception:
                    pass

        def consult(self, error_trace):
            for pattern, fix in self.wisdom.items():
                if pattern in error_trace:
                    return fix
            return None

        def learn(self, error_trace, fix_strategy):
            lines = error_trace.strip().split('\n')
            key = lines[-1].strip() if lines else error_trace[:100]
            self.wisdom[key] = fix_strategy
            with open(self.wisdom_file, "w") as f:
                json.dump(self.wisdom, f, indent=2)

    def log(tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}]  {msg}", flush=True)

    def divider():
        print("─" * 60, flush=True)

    def strip_fences(raw):
        lines = raw.strip().split('\n')
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════
#  LOCAL OVERLORD — Offline Agent Brain
# ══════════════════════════════════════════════════════════════

class LocalOverlord:
    """Fully offline code generation agent powered by Ollama."""

    # Recommended models (sorted by capability)
    MODELS = {
        "deepseek-coder:6.7b": "Fast, great for code generation",
        "deepseek-coder:33b": "High quality, needs 20GB+ RAM",
        "codellama:13b": "Meta's coding model, balanced",
        "qwen2.5-coder:7b": "Alibaba's latest, excellent at code",
        "mistral:7b": "General purpose, good fallback",
    }

    def __init__(self, project_name, output_dir=None, model=None,
                 arch_model=None, eng_model=None):
        self.project_name = project_name
        self.output_dir = output_dir or os.getcwd()
        self.project_path = os.path.join(self.output_dir, project_name)
        self.local_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

        # Per-phase model routing
        default_model = model or os.environ.get("OLLAMA_MODEL", "deepseek-coder:6.7b")
        self.arch_model = arch_model or os.environ.get("OLLAMA_ARCH_MODEL", default_model)
        self.eng_model = eng_model or os.environ.get("OLLAMA_ENG_MODEL", default_model)
        self.model = default_model  # Fallback for any phase without a specific model

        self.max_heal_passes = 5
        self.written_files = {}

        os.makedirs(self.project_path, exist_ok=True)

        # Initialize wisdom system
        self.wisdom = GlobalWisdom(self.project_path)

        # Check Ollama connectivity
        self._verify_connection()

    def _verify_connection(self):
        """Verify Ollama is running and the model is available."""
        try:
            resp = requests.get(f"{self.local_url}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]

            if self.model in models or any(self.model.split(":")[0] in m for m in models):
                log("LOCAL", f"✓ Connected to Ollama | Model: {self.model}")
            else:
                log("WARN", f"Model '{self.model}' not found locally. Available: {models}")
                log("WARN", f"Run: ollama pull {self.model}")
        except requests.ConnectionError:
            log("ERROR", "Cannot connect to Ollama at " + self.local_url)
            log("ERROR", "Start Ollama: 'ollama serve' or download from https://ollama.com")
        except Exception as e:
            log("WARN", f"Ollama check failed: {e}")

    def _ask_local_ai(self, system_role, user_content, model=None):
        """Communicate with Ollama running locally.
        
        Args:
            model: Which model to use for this specific call.
                   Defaults to self.model if not specified.
        """
        use_model = model or self.model
        full_prompt = f"System: {system_role}\nUser: {user_content}\nAssistant:"

        payload = {
            "model": use_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
                "top_p": 0.95,
            }
        }

        try:
            response = requests.post(
                f"{self.local_url}/api/generate",
                json=payload,
                timeout=300  # Local models can be slow
            )
            response.raise_for_status()
            raw_text = response.json().get("response", "")
            return strip_fences(raw_text.strip())
        except requests.ConnectionError:
            raise RuntimeError(
                "Lost connection to Ollama. Is it still running? "
                "Start with: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Local AI error: {e}")

    # ── Build Pipeline ───────────────────────────────────────

    def build_and_heal(self, user_prompt):
        """Full pipeline: Plan → Code → Test → Self-Heal."""
        log("SYSTEM", f"Local build initiated for: {self.project_name}")
        log("SYSTEM", f"Output: {os.path.abspath(self.project_path)}")
        if self.arch_model != self.eng_model:
            log("SYSTEM", f"Architect Model: {self.arch_model}")
            log("SYSTEM", f"Engineer Model:  {self.eng_model}")
        else:
            log("SYSTEM", f"Model: {self.model}")
        divider()

        # ── Phase 0: PROMPT ENGINEER (Auto-Enhance) ──────────
        log("SYSTEM", "🧠 Phase 0: Prompt Enhancement AI")
        log("SYSTEM", f"  Raw input: \"{user_prompt[:80]}{'…' if len(user_prompt) > 80 else ''}\"")

        enhance_system = (
            "You are a Prompt Engineer. Transform the user's vague idea into a detailed "
            "software engineering specification. Include: specific features (5-8), "
            "technical architecture, UI/UX details, error handling, data flow, and "
            "recommended libraries. Output ONLY the enhanced prompt text, no markdown. "
            "Keep it under 400 words but make every word count."
        )

        try:
            enhanced = self._ask_local_ai(enhance_system, user_prompt, model=self.arch_model)
            if enhanced and len(enhanced.strip()) > len(user_prompt):
                log("SYSTEM", "  ✓ Prompt enhanced successfully")
                preview_lines = enhanced.strip().split("\n")[:3]
                for line in preview_lines:
                    if line.strip():
                        log("SYSTEM", f"    → {line.strip()[:100]}")
                user_prompt = enhanced
            else:
                log("WARN", "  Enhancement too short, using original prompt.")
        except Exception as e:
            log("WARN", f"  Prompt enhancement failed: {e}. Using original.")

        divider()

        # ── Phase 1: ARCHITECT ─────────────────────────────
        log("ARCHITECT", "Planning project structure…")

        arch_system = (
            "You are a Senior Software Architect. "
            "Decompose the user's request into a logical file structure. "
            "Output ONLY valid JSON with this EXACT schema: "
            '{"files": [{"path": "filename.py", "task": "description"}], '
            '"dependencies": ["package1"], '
            '"run_command": "python main.py"} '
            "Every project MUST have a main.py entry point. "
            "Output ONLY raw JSON, no markdown fences or explanation."
            "\n\nTECH STACK CONSTRAINT (Stable-Gold Stack):"
            "\nYou MUST prioritize these libraries for ALL projects unless technically impossible:"
            "\n1. FRONTEND: TypeScript is mandatory. Use Tailwind CSS for styling."
            "\n2. BACKEND: Use FastAPI for Python-based logic; avoid Flask for high-concurrency tasks."
            "\n3. DATABASE: Default to PostgreSQL. Include a 'schema.prisma' file if using Prisma."
            "\n4. DOCUMENTATION: Every project must include a detailed 'README.md' and '.env.example'."
        )

        try:
            plan_raw = self._ask_local_ai(arch_system, user_prompt, model=self.arch_model)
            plan = json.loads(plan_raw)
            log("ARCHITECT", f"  ✓ Plan: {len(plan.get('files', []))} files")
        except json.JSONDecodeError:
            log("WARN", "  Architect returned invalid JSON. Retrying…")
            try:
                plan_raw = self._ask_local_ai(
                    arch_system + " You MUST output ONLY raw JSON.",
                    user_prompt, model=self.arch_model
                )
                plan = json.loads(plan_raw)
            except Exception as e:
                log("ERROR", f"  Architect failed: {e}")
                return
        except Exception as e:
            log("ERROR", f"  Architect failed: {e}")
            return

        divider()

        # ── Phase 2: ENGINEER ──────────────────────────────
        log("ENGINEER", "Generating code for each file…")

        file_list = [f['path'] for f in plan.get('files', [])]
        deps = plan.get('dependencies', [])
        run_cmd = plan.get('run_command', 'python main.py')

        for file_spec in plan.get('files', []):
            fname = file_spec['path']
            log("ENGINEER", f"  Writing: {fname}")

            eng_system = (
                f"You are a Lead Developer. Project files: {file_list}. "
                "Write complete, production-ready code. "
                "Use proper error handling and imports. "
                "Output ONLY the raw source code, no markdown fences."
            )

            try:
                code = self._ask_local_ai(eng_system, file_spec['task'], model=self.eng_model)
                filepath = os.path.join(self.project_path, fname)
                os.makedirs(os.path.dirname(filepath) or self.project_path,
                            exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                self.written_files[fname] = code
                log("ENGINEER", f"  ✓ Saved: {fname}")
            except Exception as e:
                log("ERROR", f"  Failed to write {fname}: {e}")

        divider()

        # ── Phase 2.5: AUDITOR ─────────────────────────────
        log("AUDITOR", "Scanning dependencies…")
        detected_deps = set()
        std_libs = {
            'os', 'sys', 'json', 'time', 'datetime', 're', 'math',
            'random', 'shutil', 'subprocess', 'pathlib', 'collections',
            'itertools', 'functools', 'hashlib', 'threading', 'logging',
            'argparse', 'urllib', 'http', 'io', 'csv', 'typing',
            'dataclasses', 'enum', 'abc', 'copy', 'tempfile', 'glob',
        }

        for fname, code in self.written_files.items():
            for line in code.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    parts = line.split()
                    if line.startswith('from'):
                        module_name = parts[1].split('.')[0]
                    else:
                        module_name = parts[1].split('.')[0]

                    if (module_name not in std_libs and
                            module_name not in self.written_files and
                            not module_name.startswith('.')):
                        final_pkg = PKG_MAP.get(module_name, module_name)
                        if final_pkg not in detected_deps:
                            detected_deps.add(final_pkg)
                            log("AUDITOR", f"    + Detected: {final_pkg}")

        # Merge with architect-specified deps
        for dep in deps:
            final_dep = PKG_MAP.get(dep, dep)
            detected_deps.add(final_dep)

        # Write requirements.txt
        if detected_deps:
            req_path = os.path.join(self.project_path, "requirements.txt")
            with open(req_path, "w") as f:
                f.write('\n'.join(sorted(detected_deps)) + '\n')
            log("AUDITOR", f"  ✓ requirements.txt ({len(detected_deps)} packages)")

            # Auto-install
            log("AUDITOR", "  Installing dependencies…")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_path],
                capture_output=True, text=True
            )

        divider()

        # ── Phase 3: DEBUGGER ──────────────────────────────
        log("DEBUGGER", f"Testing: {run_cmd}")

        main_file = run_cmd.split()[-1] if run_cmd else "main.py"
        main_path = os.path.join(self.project_path, main_file)

        for attempt in range(1, self.max_heal_passes + 1):
            log("DEBUGGER", f"  Pass {attempt}/{self.max_heal_passes}…")

            try:
                result = subprocess.run(
                    [sys.executable, main_path],
                    capture_output=True, text=True,
                    timeout=30, cwd=self.project_path
                )
                stderr = result.stderr or ""
                stdout = result.stdout or ""

                # ── Smart Detection: CLI apps that require arguments ──
                output_combined = (stdout + "\n" + stderr).lower()
                usage_indicators = ["usage:", "positional arguments", "too few arguments",
                                    "the following arguments are required",
                                    "expected one argument", "expected at least"]
                is_usage_message = any(u in output_combined for u in usage_indicators)

                if is_usage_message and "traceback" not in output_combined:
                    log("DEBUGGER", "  ✓ Program is a CLI tool — requires arguments to run.")
                    log("DEBUGGER", "    This is NOT an error. The code structure is valid.")
                    combined_out = (stdout.strip() + "\n" + stderr.strip()).strip()
                    for line in combined_out.split("\n")[:4]:
                        if line.strip():
                            log("DEBUGGER", f"    {line.strip()}")
                    break

                if result.returncode == 0 and "error" not in stderr.lower():
                    log("DEBUGGER", "  ✓ Build verified — no errors detected.")
                    if stdout.strip():
                        for line in stdout.strip().split('\n')[:5]:
                            log("OUTPUT", f"    {line}")
                    break

            except subprocess.TimeoutExpired:
                log("DEBUGGER", "  ✓ Process running (timed out — likely a server/UI).")
                break
            except Exception as e:
                stderr = str(e)

            log("DEBUGGER", f"  ✗ Error detected (exit code {result.returncode})")

            # Dynamic Healing: Missing modules
            if "modulenotfounderror" in stderr.lower():
                import re
                match = re.search(r"no module named ['\"]([^'\"]+)['\"]",
                                  stderr.lower())
                if match:
                    missing = match.group(1)
                    pkg = PKG_MAP.get(missing, missing)
                    log("DEBUGGER", f"  Healing: Installing {pkg}…")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", pkg],
                        capture_output=True, text=True
                    )
                    continue

            # Dynamic Healing: Missing binary (ffmpeg etc.)
            if "winerror 2" in stderr.lower() or "filenotfounderror" in stderr.lower():
                if "ffmpeg" in stderr.lower():
                    log("DEBUGGER", "  Binary missing: Installing imageio-ffmpeg…")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "imageio-ffmpeg"],
                        capture_output=True, text=True
                    )
                    self.wisdom.learn(
                        "[WinError 2] The system cannot find the file specified",
                        "Use imageio_ffmpeg.get_ffmpeg_exe() for ffmpeg path."
                    )

            # Print error context
            for line in stderr.split('\n')[:6]:
                log("ERROR", f"    {line}")

            if attempt < self.max_heal_passes:
                # Consult wisdom
                known_fix = self.wisdom.consult(stderr)
                previous_wisdom = ""
                if known_fix:
                    log("WISDOM", "  🧠 Known pattern — applying fix…")
                    previous_wisdom = f"\n\n[WISDOM]: {known_fix}"

                # Find the file to fix
                fix_target = self._find_error_file(stderr, main_file)
                self._heal_file(fix_target, stderr, previous_wisdom)

        divider()
        log("SYSTEM", f"✓ Local build complete: {os.path.abspath(self.project_path)}")

    def _find_error_file(self, stderr, default):
        """Find which project file is mentioned last in the traceback."""
        fix_target = default
        last_pos = -1
        for fname in self.written_files:
            pos = stderr.rfind(fname)
            if pos != -1 and pos > last_pos:
                last_pos = pos
                fix_target = fname
        return fix_target

    def _heal_file(self, fix_target, stderr, wisdom_hint=""):
        """Use local LLM to repair a broken file."""
        log("DEBUGGER", f"  Engaging local LLM to repair: {fix_target}")

        filepath = os.path.join(self.project_path, fix_target)
        if not os.path.exists(filepath):
            log("ERROR", f"  Cannot find {fix_target} for healing.")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            broken_code = f.read()

        # Build context from other project files
        context_files = []
        for fname, code in self.written_files.items():
            if fname != fix_target and fname in stderr:
                context_files.append(f"--- {fname} ---\n{code}\n---")
        context_block = "\n\n".join(context_files)

        dbg_system = (
            "You are a Self-Healing Debugger. "
            "Analyze the error and fix the code. "
            "If 'ImportError', ensure the symbol exists. "
            "If '[WinError 2]', use imageio_ffmpeg.get_ffmpeg_exe(). "
            "Preserve existing logic. "
            "Output ONLY the complete corrected source code. "
            "No markdown fences, no explanations."
        )

        dbg_prompt = (
            f"FILES: {list(self.written_files.keys())}\n"
            f"TARGET: {fix_target}\n\n"
            f"```\n{broken_code}\n```\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"ERROR:\n{stderr}{wisdom_hint}"
        )

        try:
            fixed = self._ask_local_ai(dbg_system, dbg_prompt, model=self.eng_model)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fixed)
            self.written_files[fix_target] = fixed
            log("DEBUGGER", f"  ✓ Patched: {fix_target}")

            # Learn from the fix
            if "importerror" in stderr.lower():
                strategy = "Ensure imported symbol exists in source module."
            elif "winerror 2" in stderr.lower():
                strategy = "Use imageio_ffmpeg.get_ffmpeg_exe() for binary path."
            elif "syntaxerror" in stderr.lower():
                strategy = "Fix syntax: check colons, brackets, indentation."
            else:
                strategy = f"LLM repaired {fix_target}."
            self.wisdom.learn(stderr, strategy)

        except Exception as e:
            log("ERROR", f"  Heal attempt failed: {e}")


# ══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Overlord Local Agent (Ollama)")
    parser.add_argument("project", help="Project name")
    parser.add_argument("prompt", help="What to build")
    parser.add_argument("--model", default=None,
                        help="Default Ollama model (default: deepseek-coder:6.7b)")
    parser.add_argument("--arch-model", default=None,
                        help="Model for Architect phase (planning). Uses --model if not set.")
    parser.add_argument("--eng-model", default=None,
                        help="Model for Engineer/Debugger phases (coding). Uses --model if not set.")
    parser.add_argument("--output", default=os.path.join(os.path.expanduser("~"),
                        "Desktop", "GeneratedApp"),
                        help="Output directory")
    args = parser.parse_args()

    agent = LocalOverlord(
        args.project,
        output_dir=args.output,
        model=args.model,
        arch_model=args.arch_model,
        eng_model=args.eng_model
    )
    agent.build_and_heal(args.prompt)
