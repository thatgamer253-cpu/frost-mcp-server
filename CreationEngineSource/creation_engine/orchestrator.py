"""
Creation Engine — Orchestrator
The master controller. Manages the state machine and agent hand-offs.
Implements the recursive self-correction loop:
  Architect → Developer → Supervisor → [errors?] → Developer → Supervisor → repeat
"""

import os
import sys
import json

from .config import PLATFORM_PROFILES, STUDIO_KEYWORDS
from .llm_client import (
    log, divider, ask_llm,
    get_cached_client, reset_client_cache,
    set_active_tracker, CostTracker,
)
from .wisdom import GlobalWisdom, WisdomGuard, AuraRegistry
from .validators import (
    CodebaseState, ProjectState, CodebaseRAG,
    ReviewerAgent, DependencyVerifier,
    build_manifest, manifest_to_context,
    validation_gate, import_dry_run,
    project_assembler,
    ConfigConsistencyChecker,
)
from .architect import enhance_prompt, generate_blueprint, resolve_platform
from .developer import write_all_files, write_file
from .supervisor import Supervisor


class CreationEngine:
    """The complete creation pipeline as a single callable object.

    Usage:
        engine = CreationEngine(
            project_name="my-app",
            prompt="A personal finance app with CSV upload",
            output_dir="./output",
            model="gemini-2.0-flash",
        )
        engine.run()
    """

    def __init__(self, project_name: str, prompt: str, output_dir: str = "./output",
                 model: str = "gemini-2.0-flash", api_key: str = "",
                 arch_model: str = None, eng_model: str = None,
                 local_model: str = None, review_model: str = None,
                 platform: str = "python", budget: float = 5.0,
                 max_fix_cycles: int = 3, docker: bool = True,
                 supervisor_timeout: int = 30,
                 source_path: str = None, mode: str = "new",
                 decompile_only: bool = False, phase: str = "all",
                 focus: str = None, clean_output: bool = False, scale: str = "app"):
        self.project_name = project_name
        self.prompt = prompt
        self.output_dir = output_dir
        self.project_path = os.path.join(output_dir, project_name)

        # Advanced Controls
        self.source_path = source_path
        self.mode = mode  # "new", "upgrade", "reverse"
        self.decompile_only = decompile_only
        self.phase = phase  # "plan", "code", "verify", "all"
        self.focus = focus
        self.clean_output = clean_output
        self.scale = scale  # "app", "script", "asset"

        # Model routing
        self.model = model
        self.arch_model = arch_model or model
        self.eng_model = eng_model or model
        self.local_model = local_model or (eng_model or model)
        self.review_model = review_model or self.local_model

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.platform = platform
        self.budget = budget
        self.max_fix_cycles = max_fix_cycles
        self.use_docker = docker
        self.supervisor_timeout = supervisor_timeout

        # State (initialized in run())
        self.tracker = None
        self.client = None
        self.plan = None
        self.written_files = {}

    def run(self) -> dict:
        """Execute the full creation pipeline. Returns a summary dict."""
        os.makedirs(self.project_path, exist_ok=True)

        # ── Handle Decompile Only ─────────────────────────────
        if self.decompile_only and self.source_path:
            log("SYSTEM", f"🔍 Decompiling source: {self.source_path}")
            context = self._ingest_source_code(self.source_path)
            out_file = os.path.join(self.project_path, "decompiled_context.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(context)
            log("SYSTEM", f"✅ Decompiled context saved to: {out_file}")
            print(f"DECOMPILED_OUTPUT:{out_file}") # Signal for UI
            return {"success": True, "output": out_file}

        # ── Initialize Infrastructure ──
        reset_client_cache()
        self.client = get_cached_client(self.arch_model, self.api_key)

        self.tracker = CostTracker(budget=self.budget)
        set_active_tracker(self.tracker)

        # Resolve platform profile
        profile, platform_directive = resolve_platform(self.prompt, self.platform)

        log("SYSTEM", f"Build initiated for project: {self.project_name}")
        log("SYSTEM", f"Output path: {os.path.abspath(self.project_path)}")
        log("SYSTEM", f"Mode: {self.mode} | Phase: {self.phase}")

        # ── Handling Upgrade / Reverse Mode ──
        existing_context = ""
        if (self.mode in ["upgrade", "reverse"]) and self.source_path:
            log("SYSTEM", f"🛠️  {self.mode.upper()} MODE DETECTED. Analyzing source: {self.source_path}")
            existing_context = self._ingest_source_code(self.source_path)
            # Create a backup just in case
            import shutil
            backup_path = self.source_path.rstrip("/\\") + "_bak"
            if not os.path.exists(backup_path):
                shutil.copytree(self.source_path, backup_path, dirs_exist_ok=True)
                log("SYSTEM", f"  💾 Backup created at: {backup_path}")
            
            # Use source path as project path if in upgrade mode (modify in place)
            # But normally we output to output_dir. 
            # If user wants to upgrade IN PLACE, we should probably set output_dir to parent of source_path
            # For now, let's copy source to output dir if they are different, or work in place.
            # Decision: The UI passes a source_Path. 
            # If we want to upgrade "in place", we should treat project_path AS source_path.
            abs_source = os.path.normpath(os.path.abspath(self.source_path)).lower()
            abs_project = os.path.normpath(os.path.abspath(self.project_path)).lower()
            
            if abs_source != abs_project:
                 log("SYSTEM", f"  Cloning source to output directory...")
                 import shutil
                 try:
                    shutil.copytree(self.source_path, self.project_path, dirs_exist_ok=True)
                 except shutil.Error as e:
                    # Ignore errors if copying to self (redundant safety)
                    pass
                 except OSError as e:
                    log("WARN", f"  Copy warning: {e}")


        log("SYSTEM", f"🎯 Platform: {profile['label']}")
        self._log_model_config()
        log("SYSTEM", f"💵 Budget: ${self.tracker.budget:.2f} (kill-switch enabled)")

        # ── Initialize Subsystems ──
        wisdom = GlobalWisdom(self.project_path)
        wisdom_guard = WisdomGuard()
        wisdom_rules = wisdom.get_generation_rules()
        if wisdom_rules:
            rule_count = len([k for k in wisdom.global_wisdom if k.startswith('GENERATION_RULE__')])
            log("SYSTEM", f"🛡️  Loaded {rule_count} generation rule(s) from global wisdom")

        reviewer = ReviewerAgent(self.client, self.local_model, wisdom_context=wisdom_rules)
        state = CodebaseState(self.project_path)
        proj_state = ProjectState()
        rag = CodebaseRAG(max_context_chars=12000)

        # Initialize memory
        memory_dir = os.path.join(os.path.dirname(self.project_path), "memory")
        aura = AuraRegistry(memory_dir)
        recalled_wisdom = aura.recall(self.prompt)

        divider()

        # ══════════════════════════════════════════════════════
        # PHASE 0: PROMPT ENHANCEMENT
        # ══════════════════════════════════════════════════════
        if self.mode == "reverse":
            log("SYSTEM", "🧠 Phase 0: Reverse Engineering Analysis")
            # In reverse mode, the prompt is basically "Analyze and refactor this"
            if not self.prompt.strip():
                self.prompt = "Analyze this codebase, generate a blueprint, and document it."
        else:
            log("SYSTEM", "🧠 Phase 0: Prompt Enhancement AI")
            log("SYSTEM", f"  Raw input: \"{self.prompt[:80]}{'…' if len(self.prompt) > 80 else ''}\"")

            # Inject existing context into prompt if upgrading
            enhancement_prompt = self.prompt
            if existing_context:
                enhancement_prompt += f"\n\nEXISTING CODEBASE CONTEXT:\n{existing_context[:20000]}... [truncated]"
                log("SYSTEM", "  (Including existing codebase context for enhancement)")

            self.prompt = enhance_prompt(self.client, self.arch_model,
                                         enhancement_prompt, platform_directive,
                                         scale=self.scale)
        divider()

        # ══════════════════════════════════════════════════════
        # PHASE 1: ARCHITECT (Plan / Blueprint)
        # ══════════════════════════════════════════════════════
        if self.phase == "code" or self.phase == "verify":
             log("ARCHITECT", "⏩ Skipping Phase 1 (Architect) per phase control.")
             # If skipping plan, we must assume a plan exists or we force a dummy plan?
             # For now, let's look for existing blueprint or create minimal plan.
             # If upgrading/reverse, maybe we don't need a full plan if we just want to lint/verify?
             pass
        else:
            log("ARCHITECT", "Engaging Architect agent…")
            if recalled_wisdom:
                log("ARCHITECT", "  🧠 Recalling Aura Persistent Memory…")
            
            # If upgrading, pass the existing context as "research report" or distinct arg
            arch_context = recalled_wisdom
            if existing_context:
                arch_context += "\n\nEXISTING SOURCE CODE TO ANALYZE/UPGRADE:\n" + existing_context
                if self.mode == "reverse":
                    arch_context += "\n\nMISSION: REVERSE ENGINEER. Create a blueprint that reflects the CURRENT or IMPROVED structure."

            self.plan = generate_blueprint(
                client=self.client,
                model=self.arch_model,
                prompt=self.prompt,
                profile=profile,
                platform_directive=platform_directive,
                research_report=arch_context,
                scale=self.scale
            )
            
            # Save Visual Blueprint (Mermaid)
            mermaid_code = self.plan.get("mermaid")
            if mermaid_code:
                mermaid_path = os.path.join(self.project_path, "blueprint.mermaid")
                with open(mermaid_path, "w", encoding="utf-8") as f:
                    f.write(mermaid_code)
                log("ARCHITECT", "  🎨 Visual Blueprint saved to blueprint.mermaid")

            # ── REVERSE ENGINEERING: DOCUMENTATION GENERATION ──
            if self.mode == "reverse":
                log("SYSTEM", "📚 Generating Documentation (Reverse Mode)...")
                try:
                    docs = ask_llm(self.client, self.arch_model,
                        "You are a Technical Writer. Write comprehensive documentation for this system.",
                        f"Blueprint:\n{json.dumps(self.plan, indent=2)}\n\n"
                        f"Source Context:\n{existing_context[:10000] if existing_context else ''}..."
                    )
                    doc_path = os.path.join(self.project_path, "documentation.md")
                    with open(doc_path, "w", encoding="utf-8") as f:
                        f.write(docs)
                    log("SYSTEM", f"  ✅ Documentation saved to {doc_path}")
                except Exception as e:
                    log("WARN", f"  Failed to generate docs: {e}")
                
        divider()

        # STOP IF PHASE == PLAN
        if self.phase == "plan":
            log("SYSTEM", "🛑 Stopping after Phase 1 (Plan Only).")
            return self._build_summary(success=True)

        # Budget checkpoint after Architect
        if self.tracker.budget_exceeded and not self.tracker.pivot_triggered:
            log("SYSTEM", f"💸 Budget exceeded after Architect: ${self.tracker.total_cost:.4f}")
            log("SYSTEM", f"   Pivoting ALL models → {self.local_model}")
            self.arch_model = self.local_model
            self.eng_model = self.local_model
            self.tracker.trigger_pivot()
        else:
            log("SYSTEM", f"💵 Cost: ${self.tracker.total_cost:.4f} / ${self.tracker.budget:.2f}")

        # ══════════════════════════════════════════════════════
        # PHASE 1.5: PROJECT ASSEMBLER
        # ══════════════════════════════════════════════════════
        if not (self.mode == "reverse" and not self.clean_output):
             # Skip assembler in reverse mode UNLESS we are producing clean output (rebuilding)
             # Actually, assembler creates folders. Safe to run.
             log("SYSTEM", "🏗️  Phase 1.5: Project Assembler")
             project_assembler(self.plan, self.project_path)
             divider()

        # ══════════════════════════════════════════════════════
        # PHASE 2: DEVELOPER (Write All Files)
        # ══════════════════════════════════════════════════════
        if self.phase == "verify":
             log("ENGINEER", "⏩ Skipping Phase 2 (Developer) per phase control.")
        elif self.mode == "reverse" and not self.clean_output:
             log("ENGINEER", "⏩ Skipping Code Generation (Reverse Mode - no clean output requested).")
             # We just wanted Plan + Docs
        else:
            log("ENGINEER", "Engaging Engineer agent…")
            self.written_files = state.files

            # If Focus is set, filter plan? 
            # Or just pass focus to write_all_files? 
            # For now, simplistic approach: The plan dictates files. 
            # If we want to focus, we should have told Architect to only plan for X?
            # Or we filter `self.plan['files']` here.
            
            run_plan = self.plan
            if self.focus:
                import fnmatch
                log("ENGINEER", f"🎯 Focus Mode: Filtering for pattern '{self.focus}'")
                filtered_files = [f for f in self.plan.get("files", []) if fnmatch.fnmatch(f.get("path",""), self.focus)]
                if filtered_files:
                    run_plan = self.plan.copy()
                    run_plan["files"] = filtered_files
                else:
                    log("WARN", f"  No files matched focus pattern '{self.focus}'! Running full plan.")

            self.written_files = write_all_files(
                client=self.client,
                model=self.model,
                plan=run_plan,
                project_path=self.project_path,
                written_files=self.written_files,
                state=state,
                proj_state=proj_state,
                rag=rag,
                wisdom=wisdom,
                reviewer=reviewer,
                eng_model=self.eng_model,
            )
        divider()

        # STOP IF PHASE == CODE
        if self.phase == "code":
            log("SYSTEM", "🛑 Stopping after Phase 2 (Code Only).")
            return self._build_summary(success=True)

        # ══════════════════════════════════════════════════════
        # PHASE 3: SUPERVISOR + RECURSIVE FIX-IT LOOP
        # ══════════════════════════════════════════════════════
        if self.mode == "reverse" and not self.clean_output:
             log("SUPERVISOR", "⏩ Skipping Verification (Reverse Mode).")
        else:
            log("SUPERVISOR", "🔄 Phase 3: Supervisor — Testing & Self-Correction Loop")

            run_cmd = self.plan.get("run_command", profile["run_command"])
            supervisor = Supervisor(
                project_path=self.project_path,
                run_command=run_cmd,
                timeout=self.supervisor_timeout,
                use_docker=self.use_docker,
            )

            final_result = None
            for cycle in range(1, self.max_fix_cycles + 1):
                log("SUPERVISOR", f"  ── Run Cycle {cycle}/{self.max_fix_cycles} ──")
                result = supervisor.run()
                final_result = result

                if result.success:
                    log("SUPERVISOR", f"  ✅ Child program runs clean on cycle {cycle}!")
                    break

                # ── ERROR: Enter fix-it loop ──
                log("SUPERVISOR", f"  ✗ Execution failed on cycle {cycle}")
                supervisor.save_error_log(result, cycle)

                if cycle >= self.max_fix_cycles:
                    log("SUPERVISOR", f"  ✗ All {self.max_fix_cycles} fix cycles exhausted.")
                    break

                # Diagnose the error
                log("SUPERVISOR", "  🔍 Diagnosing failure…")
                diagnosis = self._diagnose_error(result)

                if diagnosis:
                    fix_file = diagnosis.get("fix_file", "")
                    fix_instruction = diagnosis.get("fix_instruction", "")
                    root_cause = diagnosis.get("root_cause", "Unknown")

                    log("SUPERVISOR", f"  Root cause: {root_cause[:120]}")
                    log("SUPERVISOR", f"  Fix target: {fix_file}")

                    if fix_file and fix_file in self.written_files:
                        log("ENGINEER", f"  🔧 Patching: {fix_file}")
                        patched = self._patch_file(
                            fix_file, root_cause, fix_instruction,
                            result.error_summary, state, proj_state, rag, wisdom
                        )
                        if patched:
                            log("ENGINEER", f"  ✓ Patched: {fix_file}")
                            log("SUPERVISOR", "  ↻ Retrying with patched code…")
                        else:
                            log("ENGINEER", f"  ⚠ Patch failed for {fix_file}")
                    else:
                        log("SUPERVISOR", f"  ⚠ Cannot locate fix target '{fix_file}'")

        divider()

        # ══════════════════════════════════════════════════════
        # PHASE 4: PACKAGING
        # ══════════════════════════════════════════════════════
        log("SYSTEM", "📦 Phase 4: Packaging")
        self._generate_packaging(profile)

        # Save cost report
        self.tracker.save_report(self.project_path)
        log("SYSTEM", f"\n{self.tracker.get_summary()}")
        divider()

        # ── DONE ──
        success = final_result.success if final_result else False
        # If we skipped supervisor (reverse mode), we consider it a success if we got this far?
        if (self.mode == "reverse" and not self.clean_output) or self.phase in ["plan", "code"]:
            success = True

        log("SYSTEM", f"{'✅' if success else '⚠'} Build {'complete' if success else 'finished (with errors)'}!")
        log("SYSTEM", f"  📁 Output: {os.path.abspath(self.project_path)}")
        if 'run_cmd' in locals() and run_cmd:
            log("SYSTEM", f"  ▶️  Run: cd {self.project_name} && {run_cmd}")

        return self._build_summary(success, final_result, run_cmd if 'run_cmd' in locals() else "")

    def _build_summary(self, success: bool, final_result=None, run_cmd: str="") -> dict:
        """Helper to build the return summary dict."""
        return {
            "project_name": self.project_name,
            "project_path": os.path.abspath(self.project_path),
            "success": success,
            "files_written": len(self.written_files),
            "run_command": run_cmd,
            "cost": self.tracker.get_summary() if self.tracker else "$0.00",
            "fix_cycles": (self.max_fix_cycles if not success and final_result else
                           (0 if not final_result else self.max_fix_cycles)),
        }

    # ── Private Helpers ─────────────────────────────────────

    def _log_model_config(self):
        if (self.arch_model != self.eng_model or self.local_model != self.eng_model
                or self.review_model != self.local_model):
            log("SYSTEM", f"🧠 Strategy Model (Architect): {self.arch_model}")
            log("SYSTEM", f"⚡ Speed Model (Engineer):     {self.eng_model}")
            if self.local_model != self.eng_model:
                log("SYSTEM", f"💰 Local Model (Reviewer/Env):  {self.local_model}")
            if self.review_model != self.local_model:
                log("SYSTEM", f"🔒 Review Model (Senior):      {self.review_model}")
        else:
            log("SYSTEM", f"Model: {self.model}")

    def _ingest_source_code(self, source_path: str) -> str:
        """Use the Decompiler to digest existing source code into an LLM-friendly format."""
        try:
            from .decompiler import NexusDecompiler
            decompiler = NexusDecompiler()
            # We want the raw context string, not the dictionary
            context = decompiler.generate_llm_context(source_path)
            log("SYSTEM", f"  📄 Ingested {len(context)} chars of source code context")
            return context
        except Exception as e:
            log("WARN", f"  Failed to ingest source code: {e}")
            return ""

    def _diagnose_error(self, result) -> dict:
        """Use the LLM to diagnose what went wrong."""
        diag_prompt = (
            f"A program execution FAILED. Analyze this error and identify:\n"
            f"1. The ROOT CAUSE of the failure\n"
            f"2. Which source file needs to be fixed\n"
            f"3. The exact fix required\n\n"
            f"Project files: {list(self.written_files.keys())}\n\n"
            f"ERROR OUTPUT:\n{result.error_summary[:3000]}\n\n"
            f"STDOUT:\n{result.stdout[:2000]}\n\n"
            f"STDERR:\n{result.stderr[:2000]}\n\n"
            f'Respond as JSON: {{"root_cause": "...", "fix_file": "filename.py", '
            f'"fix_instruction": "exactly what to change"}}'
        )

        try:
            raw = ask_llm(self.client, self.local_model,
                "You are 'Overlord Supervisor.' You diagnose program failures. "
                "Read errors carefully and output a precise diagnosis as JSON.",
                diag_prompt)
            try:
                diag = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    diag = json.loads(raw[start:end])
                else:
                    log("SUPERVISOR", f"  ⚠ Could not parse diagnosis: {raw[:200]}")
                    return None
            
            # Explicitly check for zombie hangs to ensure they are fixed with sleep
            if "ZOMBIE HANG" in result.error_summary:
                diag["root_cause"] = "Infinite loop detected with no I/O or sleep."
                diag["fix_instruction"] += " MUST add time.sleep() or event-based delays inside the while loops."
            
            return diag
        except Exception as e:
            log("SUPERVISOR", f"  ⚠ Diagnosis failed: {e}")
            return None

    def _patch_file(self, fix_file, root_cause, fix_instruction,
                    error_output, state, proj_state, rag, wisdom):
        """Have the Developer rewrite a broken file."""
        current_code = self.written_files.get(fix_file, "")
        patch_prompt = (
            f"The program FAILED. The Supervisor diagnosed the issue:\n"
            f"Root cause: {root_cause}\n"
            f"Fix instruction: {fix_instruction}\n\n"
            f"Current source code for {fix_file}:\n"
            f"```\n{current_code}\n```\n\n"
            f"Error output:\n{error_output[:2000]}\n\n"
            f"Rewrite the COMPLETE file with the fix applied. "
            f"Output ONLY raw source code. No markdown fences."
        )

        eng_system = (
            "You are 'Overlord,' an autonomous Senior Full-Stack Engineer. "
            "Directive: Fix the bug. Write clean, documented code. "
            "Directive: Loop Safety. All while loops MUST contain a sleep or delay to prevent hangs. "
            "Output ONLY raw source code. No explanations."
        )

        try:
            fixed_code = ask_llm(self.client, self.eng_model, eng_system, patch_prompt)

            # Apply wisdom guard
            wisdom_guard = WisdomGuard()
            fixed_code, _ = wisdom_guard.auto_fix(fixed_code, fix_file)

            # Write to disk
            full_path = os.path.join(self.project_path, fix_file)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)

            # Update state
            state.write(fix_file, fixed_code)
            self.written_files[fix_file] = fixed_code
            proj_state.register_file(fix_file, fixed_code)

            return True
        except Exception as e:
            log("ERROR", f"  Patch failed: {e}")
            return False

    def _generate_packaging(self, profile):
        """Generate requirements.txt, README.md, and other packaging artifacts."""
        deps = self.plan.get("dependencies", [])
        run_cmd = self.plan.get("run_command", profile["run_command"])

        # requirements.txt
        req_path = os.path.join(self.project_path, "requirements.txt")
        if deps and not os.path.exists(req_path):
            with open(req_path, "w", encoding="utf-8") as f:
                f.write("\n".join(deps) + "\n")
            log("SYSTEM", f"  📄 requirements.txt ({len(deps)} deps)")

        # README.md
        readme_path = os.path.join(self.project_path, "README.md")
        if not os.path.exists(readme_path):
            try:
                readme = ask_llm(self.client, self.local_model,
                    "Write a professional README.md for this project. "
                    "Include: title, description, features, installation, usage, and license.",
                    f"Project: {self.project_name}\n"
                    f"Files: {list(self.written_files.keys())}\n"
                    f"Dependencies: {deps}\n"
                    f"Run command: {run_cmd}\n"
                    f"Original prompt: {self.prompt[:500]}")
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme)
                log("SYSTEM", "  📄 README.md")
            except Exception as e:
                log("WARN", f"  README generation failed: {e}")

        # .env.example
        env_path = os.path.join(self.project_path, ".env.example")
        if not os.path.exists(env_path):
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Environment Variables\n# Copy this file to .env and fill in values\n")
            log("SYSTEM", "  📄 .env.example")
