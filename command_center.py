#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          OVERLORD — AUTONOMOUS PROGRAM BUILDER              ║
║               Command Center  •  v2.0                       ║
╚══════════════════════════════════════════════════════════════╝

A standalone desktop app that orchestrates three AI agents
(Architect, Engineer, Debugger) to build entire projects
from a single natural-language prompt.

Requirements:  pip install customtkinter openai
"""

import os
import json
import time
import subprocess
import threading
import customtkinter as ctk
from openai import OpenAI
from datetime import datetime

# ─── Theme ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Color Palette ────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#0D0D0D",
    "bg_sidebar":    "#111318",
    "bg_card":       "#161922",
    "bg_input":      "#1C1F2B",
    "accent":        "#6C63FF",
    "accent_hover":  "#5A52E0",
    "accent_glow":   "#7B73FF",
    "text_primary":  "#E8E6F0",
    "text_dim":      "#6B6F80",
    "green":         "#00FF88",
    "cyan":          "#00D4FF",
    "yellow":        "#FFD600",
    "magenta":       "#FF44CC",
    "red":           "#FF3B5C",
    "orange":        "#FF8A00",
    "border":        "#2A2D3A",
}

# ─── Log Tag Colors ──────────────────────────────────────────
TAG_COLORS = {
    "SYSTEM":    COLORS["text_dim"],
    "ARCHITECT": COLORS["cyan"],
    "ENGINEER":  COLORS["yellow"],
    "REVIEWER":  "#00FFAA",         # Teal-green — zero-inference reviewer
    "DEBUGGER":  COLORS["magenta"],
    "DOCKER":    COLORS["orange"],
    "ENVIRON":   "#B388FF",         # Light purple — environment agent
    "HANDOFF":   "#FFD740",         # Amber — package finalization
    "STATE":     "#40C4FF",         # Light blue — state persistence
    "GATE":      "#FF6E40",         # Deep orange — validation gate
    "AUDITOR":   "#69F0AE",         # Mint green — auditor phase
    "WISDOM":    "#E040FB",         # Bright magenta — global wisdom
    "DOCS":      COLORS["text_primary"],
    "SUCCESS":   COLORS["green"],
    "ERROR":     COLORS["red"],
    "WARN":      COLORS["orange"],
}


class CommandCenter(ctk.CTk):
    """Main application window — the Overlord Command Center."""

    def __init__(self):
        super().__init__()

        # ── Window ───────────────────────────────────────────
        self.title("OVERLORD ▸ Autonomous Program Builder")
        self.geometry("1060x720")
        self.minsize(800, 520)
        self.configure(fg_color=COLORS["bg_dark"])

        # ── State ────────────────────────────────────────────
        self._stop_flag = threading.Event()
        self._building = False

        # ── Grid ─────────────────────────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_panel()

    # ═══════════════════════════════════════════════════════════
    #  SIDEBAR
    # ═══════════════════════════════════════════════════════════
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=240, corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=1, border_color=COLORS["border"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # ── Logo / Title ─────────────────────────────────────
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(24, 4))

        ctk.CTkLabel(
            logo_frame, text="◈  OVERLORD",
            font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
            text_color=COLORS["accent_glow"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Autonomous Program Builder",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(2, 0))

        # ── Divider ──────────────────────────────────────────
        ctk.CTkFrame(
            self.sidebar, height=1,
            fg_color=COLORS["border"],
        ).pack(fill="x", padx=16, pady=16)

        # ── Section: Project Config ──────────────────────────
        self._sidebar_heading("PROJECT CONFIG")

        self._sidebar_label("Project Name")
        self.name_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="MyNewApp",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))
        self.name_entry.insert(0, "GeneratedApp")

        self._sidebar_label("Output Directory")
        self.dir_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="./output",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.dir_entry.pack(fill="x", padx=20, pady=(0, 10))
        self.dir_entry.insert(0, "./output")

        self._sidebar_label("Model")
        self.model_var = ctk.StringVar(value="gpt-4o")
        self.model_menu = ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.model_var,
            values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            dropdown_fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
        )
        self.model_menu.pack(fill="x", padx=20, pady=(0, 10))

        self._sidebar_label("API Key  (or set OPENAI_API_KEY)")
        self.key_entry = ctk.CTkEntry(
            self.sidebar, show="•",
            placeholder_text="sk-…",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.key_entry.pack(fill="x", padx=20, pady=(0, 10))
        env_key = os.environ.get("OPENAI_API_KEY", "")
        if env_key:
            self.key_entry.insert(0, env_key)

        # ── Section: Stripe Config ───────────────────────────
        self._sidebar_heading("STRIPE PAYOUT")
        
        self._sidebar_label("Stripe API Key")
        self.stripe_key_entry = ctk.CTkEntry(
            self.sidebar, show="•",
            placeholder_text="sk_test_…",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.stripe_key_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        from creation_engine.vault import Vault
        vault = Vault()
        stripe_keys = vault.get_stripe_keys()
        if stripe_keys.get("api_key"):
            self.stripe_key_entry.insert(0, stripe_keys["api_key"])

        self.cashout_btn = ctk.CTkButton(
            self.sidebar,
            text="💰 CASH OUT NOW",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=COLORS["green"],
            text_color=COLORS["bg_dark"],
            hover_color="#00DD77",
            height=32, corner_radius=6,
            command=self._on_cashout_click,
        )
        self.cashout_btn.pack(fill="x", padx=20, pady=(4, 10))

        # ── Divider ──────────────────────────────────────────
        ctk.CTkFrame(
            self.sidebar, height=1,
            fg_color=COLORS["border"],
        ).pack(fill="x", padx=16, pady=12)

        # ── Section: Build Options ───────────────────────────
        self._sidebar_heading("BUILD OPTIONS")

        self.docker_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.sidebar, text="Generate Dockerfile",
            variable=self.docker_var,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        ).pack(anchor="w", padx=20, pady=4)

        self.readme_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.sidebar, text="Generate README.md",
            variable=self.readme_var,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        ).pack(anchor="w", padx=20, pady=4)

        self.debug_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.sidebar, text="Auto-Debug (up to 3 passes)",
            variable=self.debug_var,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        ).pack(anchor="w", padx=20, pady=4)

        # ── File Tree (populated after build) ────────────────
        ctk.CTkFrame(
            self.sidebar, height=1,
            fg_color=COLORS["border"],
        ).pack(fill="x", padx=16, pady=12)

        self._sidebar_heading("OUTPUT FILES")
        self.tree_label = ctk.CTkLabel(
            self.sidebar,
            text="No build yet.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_dim"],
            justify="left", anchor="nw",
            wraplength=200,
        )
        self.tree_label.pack(fill="both", padx=20, pady=(0, 10), expand=True)

    # ═══════════════════════════════════════════════════════════
    #  MAIN PANEL
    # ═══════════════════════════════════════════════════════════
    def _build_main_panel(self):
        self.main = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        self.main.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        # ── Header ───────────────────────────────────────────
        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(16, 4), sticky="ew")

        ctk.CTkLabel(
            header, text="MISSION PROMPT",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=COLORS["accent_glow"],
        ).pack(side="left")

        self.status_label = ctk.CTkLabel(
            header, text="● STANDBY",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["text_dim"],
        )
        self.status_label.pack(side="right")

        # ── Prompt Input ─────────────────────────────────────
        self.prompt_entry = ctk.CTkTextbox(
            self.main, height=90,
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=8,
        )
        self.prompt_entry.grid(row=1, column=0, padx=20, pady=(4, 8), sticky="ew")
        self.prompt_entry.insert("0.0", "Design a Python script that...")

        # ── Log Console Header ───────────────────────────────
        console_head = ctk.CTkFrame(self.main, fg_color="transparent")
        console_head.grid(row=2, column=0, padx=20, pady=(4, 0), sticky="new")

        ctk.CTkLabel(
            console_head, text="◉  LIVE FEED",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["green"],
        ).pack(side="left")

        # ── Log Console ──────────────────────────────────────
        self.log_output = ctk.CTkTextbox(
            self.main, state="disabled",
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["green"],
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.log_output.grid(row=2, column=0, padx=20, pady=(24, 8), sticky="nsew")

        # Configure tag colors for the textbox
        for tag, color in TAG_COLORS.items():
            self.log_output.tag_config(tag, foreground=color)

        # ── Button Row ───────────────────────────────────────
        btn_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(4, 16), sticky="ew")

        self.build_btn = ctk.CTkButton(
            btn_frame,
            text="⚡  INITIATE BUILD",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=44, corner_radius=8,
            command=self._on_build_click,
        )
        self.build_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="■  ABORT",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            fg_color=COLORS["red"],
            hover_color="#CC2E48",
            height=44, corner_radius=8,
            state="disabled",
            command=self._on_cancel_click,
        )
        self.cancel_btn.pack(side="right", width=120)

    # ═══════════════════════════════════════════════════════════
    #  SIDEBAR HELPERS
    # ═══════════════════════════════════════════════════════════
    def _sidebar_heading(self, text):
        ctk.CTkLabel(
            self.sidebar, text=text,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=20, pady=(4, 8))

    def _sidebar_label(self, text):
        ctk.CTkLabel(
            self.sidebar, text=text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=20, pady=(4, 2))

    # ═══════════════════════════════════════════════════════════
    #  LOGGING
    # ═══════════════════════════════════════════════════════════
    def _log(self, message: str, tag: str = "SYSTEM"):
        """Thread-safe log with color tag."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{tag}]  {message}\n"

        def _insert():
            self.log_output.configure(state="normal")
            self.log_output.insert("end", line, tag)
            self.log_output.configure(state="disabled")
            self.log_output.see("end")

        # Schedule on the main thread
        self.after(0, _insert)

    def _set_status(self, text: str, color: str = COLORS["text_dim"]):
        def _update():
            self.status_label.configure(text=text, text_color=color)
        self.after(0, _update)

    # ═══════════════════════════════════════════════════════════
    #  LLM INTERFACE
    # ═══════════════════════════════════════════════════════════
    def _get_client(self) -> OpenAI:
        api_key = self.key_entry.get().strip() or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("No API key provided. Set OPENAI_API_KEY or enter it in the sidebar.")
        return OpenAI(api_key=api_key)

    def _ask_llm(self, client: OpenAI, system_role: str, user_content: str) -> str:
        response = client.chat.completions.create(
            model=self.model_var.get(),
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        return raw

    # ═══════════════════════════════════════════════════════════
    #  BUILD ORCHESTRATION
    # ═══════════════════════════════════════════════════════════
    def _on_build_click(self):
        if self._building:
            return
        self._building = True
        self._stop_flag.clear()
        self.build_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")

        # Clear log
        self.log_output.configure(state="normal")
        self.log_output.delete("0.0", "end")
        self.log_output.configure(state="disabled")

        threading.Thread(target=self._execute_build, daemon=True).start()

    def _on_cancel_click(self):
        self._stop_flag.set()
        self._log("Build aborted by operator.", "ERROR")
        self._set_status("● ABORTED", COLORS["red"])

    def _on_cashout_click(self):
        """Save keys and trigger payout IPC."""
        api_key = self.stripe_key_entry.get().strip()
        if not api_key:
            self._log("Stripe API Key missing. Cannot cash out.", "ERROR")
            return
        
        from creation_engine.vault import Vault
        vault = Vault()
        vault.save_stripe_keys(api_key, "") # Account ID optional for now
        
        self._log("Stripe credentials secured in Vault.", "SYSTEM")
        self._log("Broadcasting payout command to Sovereign Ambassador for settlement...", "SYSTEM")
        
        if _HAS_HUB:
             hub.post("human", "PROPOSE", "cash out now", target="ambassador")
        else:
             self._log("IPC Hub unavailable. Cannot communicate with agents.", "ERROR")

    def _finish_build(self, success: bool = True):
        self._building = False

        def _ui():
            self.build_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")

        self.after(0, _ui)

    def _stopped(self) -> bool:
        return self._stop_flag.is_set()

    def _execute_build(self):
        """Main build pipeline — runs on a worker thread."""
        project_name = self.name_entry.get().strip() or "GeneratedApp"
        output_dir = self.dir_entry.get().strip() or "./output"
        user_prompt = self.prompt_entry.get("0.0", "end").strip()
        project_path = os.path.join(output_dir, project_name)

        try:
            os.makedirs(project_path, exist_ok=True)
        except OSError as e:
            self._log(f"Cannot create output directory: {e}", "ERROR")
            self._set_status("● ERROR", COLORS["red"])
            self._finish_build(False)
            return

        try:
            client = self._get_client()
        except ValueError as e:
            self._log(str(e), "ERROR")
            self._set_status("● ERROR", COLORS["red"])
            self._finish_build(False)
            return

        self._set_status("● BUILDING", COLORS["accent_glow"])
        self._log(f"Build initiated for project: {project_name}", "SYSTEM")
        self._log(f"Output path: {os.path.abspath(project_path)}", "SYSTEM")
        self._log("─" * 52, "SYSTEM")
        time.sleep(0.3)

        # ── Phase 1: ARCHITECT ───────────────────────────────
        if self._stopped():
            self._finish_build(False)
            return

        self._set_status("● PHASE 1 — ARCHITECT", COLORS["cyan"])
        self._log("Engaging Architect agent…", "ARCHITECT")
        self._log("Analyzing prompt and planning project structure…", "ARCHITECT")

        arch_system = (
            "You are a Senior Software Architect. "
            "Given a project description, output ONLY valid JSON with this exact schema: "
            '{"files": [{"path": "filename.py", "task": "description of what this file does"}], '
            '"dependencies": ["package1", "package2"], '
            '"run_command": "python main.py"} '
            "Be thorough. Include all necessary files. Do NOT wrap in markdown."
            "\n\nTECH STACK CONSTRAINT (Stable-Gold Stack):"
            "\nYou MUST prioritize these libraries for ALL projects unless technically impossible:"
            "\n1. FRONTEND: TypeScript is mandatory. Use Tailwind CSS for styling."
            "\n2. BACKEND: Use FastAPI for Python-based logic; avoid Flask for high-concurrency tasks."
            "\n3. DATABASE: Default to PostgreSQL. Include a 'schema.prisma' file if using Prisma."
            "\n4. DOCUMENTATION: Every project must include a detailed 'README.md' and '.env.example'."
        )

        try:
            raw_plan = self._ask_llm(client, arch_system, user_prompt)
            plan = json.loads(raw_plan)
        except json.JSONDecodeError:
            self._log("Architect returned invalid JSON. Retrying…", "ERROR")
            try:
                raw_plan = self._ask_llm(client, arch_system + " Output ONLY raw JSON, no markdown.", user_prompt)
                plan = json.loads(raw_plan)
            except Exception as e:
                self._log(f"Architect failed: {e}", "ERROR")
                self._set_status("● ERROR", COLORS["red"])
                self._finish_build(False)
                return
        except Exception as e:
            self._log(f"Architect failed: {e}", "ERROR")
            self._set_status("● ERROR", COLORS["red"])
            self._finish_build(False)
            return

        files = plan.get("files", [])
        deps = plan.get("dependencies", [])
        run_cmd = plan.get("run_command", "python main.py")

        self._log(f"Blueprint ready — {len(files)} file(s), {len(deps)} dep(s)", "ARCHITECT")
        for f in files:
            self._log(f"  ├─ {f['path']}  →  {f['task'][:60]}", "ARCHITECT")
        self._log(f"  └─ run: {run_cmd}", "ARCHITECT")
        self._log("─" * 52, "SYSTEM")
        time.sleep(0.2)

        # ── Phase 2: ENGINEER ────────────────────────────────
        if self._stopped():
            self._finish_build(False)
            return

        self._set_status("● PHASE 2 — ENGINEER", COLORS["yellow"])
        self._log("Engaging Engineer agent…", "ENGINEER")

        file_list = [f["path"] for f in files]
        written_files = {}

        for i, file_spec in enumerate(files, 1):
            if self._stopped():
                self._finish_build(False)
                return

            fpath = file_spec["path"]
            ftask = file_spec["task"]
            self._log(f"[{i}/{len(files)}] Writing: {fpath}", "ENGINEER")

            eng_system = (
                f"You are a Lead Software Developer. "
                f"The full project has these files: {file_list}. "
                f"Write ONLY the raw source code for the file described. "
                f"No markdown fences, no explanations. Just code."
            )

            try:
                code = self._ask_llm(client, eng_system, f"Write `{fpath}`: {ftask}")
            except Exception as e:
                self._log(f"Engineer failed on {fpath}: {e}", "ERROR")
                continue

            full_path = os.path.join(project_path, fpath)
            os.makedirs(os.path.dirname(full_path) or project_path, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code)

            written_files[fpath] = code
            self._log(f"  ✓ {fpath}  ({len(code)} chars written)", "ENGINEER")

        self._log("─" * 52, "SYSTEM")
        time.sleep(0.2)

        # ── Phase 3: DEBUGGER ────────────────────────────────
        if self.debug_var.get() and not self._stopped():
            self._set_status("● PHASE 3 — DEBUGGER", COLORS["magenta"])
            self._log("Engaging Debugger agent…", "DEBUGGER")
            self._log(f"Attempting to run: {run_cmd}", "DEBUGGER")

            max_debug_passes = 3
            for attempt in range(1, max_debug_passes + 1):
                if self._stopped():
                    self._finish_build(False)
                    return

                self._log(f"Debug pass {attempt}/{max_debug_passes}…", "DEBUGGER")
                try:
                    result = subprocess.run(
                        run_cmd, shell=True,
                        capture_output=True, text=True,
                        cwd=project_path, timeout=30,
                    )
                except subprocess.TimeoutExpired:
                    self._log("  ⏱ Process timed out (30s). Skipping debug.", "DEBUGGER")
                    break
                except Exception as e:
                    self._log(f"  Cannot execute: {e}", "DEBUGGER")
                    break

                if result.returncode == 0:
                    self._log("  ✓ Program executed successfully — no errors.", "DEBUGGER")
                    if result.stdout.strip():
                        for line in result.stdout.strip().split("\n")[:8]:
                            self._log(f"    stdout: {line}", "DEBUGGER")
                    break
                else:
                    stderr = result.stderr.strip()
                    self._log(f"  ✗ Exit code {result.returncode}", "DEBUGGER")
                    for line in stderr.split("\n")[:6]:
                        self._log(f"    {line}", "ERROR")

                    if attempt < max_debug_passes:
                        self._log("  Sending error to LLM for auto-fix…", "DEBUGGER")

                        # Determine which file to fix from traceback
                        fix_target = None
                        for fname in written_files:
                            if fname in stderr:
                                fix_target = fname
                                break
                        if not fix_target and written_files:
                            fix_target = list(written_files.keys())[0]

                        if fix_target:
                            dbg_system = (
                                "You are a Senior Debugger. You will receive source code and an error message. "
                                "Fix the code. Output ONLY the complete, corrected source code. "
                                "No markdown, no explanations."
                            )
                            dbg_prompt = (
                                f"FILE: {fix_target}\n\n"
                                f"```\n{written_files[fix_target]}\n```\n\n"
                                f"ERROR:\n{stderr}"
                            )
                            try:
                                fixed_code = self._ask_llm(client, dbg_system, dbg_prompt)
                                full_path = os.path.join(project_path, fix_target)
                                with open(full_path, "w", encoding="utf-8") as f:
                                    f.write(fixed_code)
                                written_files[fix_target] = fixed_code
                                self._log(f"  ✓ Patched: {fix_target}", "DEBUGGER")
                            except Exception as e:
                                self._log(f"  Fix attempt failed: {e}", "ERROR")
                                break

            self._log("─" * 52, "SYSTEM")
            time.sleep(0.2)

        # ── Phase 4: PACKAGING ───────────────────────────────
        if self._stopped():
            self._finish_build(False)
            return

        self._set_status("● PACKAGING", COLORS["orange"])
        self._log("Generating project artifacts…", "SYSTEM")

        # requirements.txt
        req_path = os.path.join(project_path, "requirements.txt")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("\n".join(deps))
        self._log(f"  ✓ requirements.txt  ({len(deps)} packages)", "SYSTEM")

        # Dockerfile
        if self.docker_var.get():
            self._log("Generating Dockerfile…", "DOCKER")
            docker_system = (
                "DevOps Engineer. Create a production-ready Dockerfile for this Python project. "
                "Use python:3.12-slim as the base. Output ONLY the Dockerfile content, no markdown."
            )
            try:
                dockerfile = self._ask_llm(client, docker_system, f"Project plan: {json.dumps(plan)}")
                with open(os.path.join(project_path, "Dockerfile"), "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                self._log("  ✓ Dockerfile written", "DOCKER")
            except Exception as e:
                self._log(f"  Dockerfile generation failed: {e}", "ERROR")

        # README.md
        if self.readme_var.get():
            self._log("Generating README.md…", "DOCS")
            doc_system = (
                "Technical Writer. Create a professional README.md with: project description, "
                "installation, usage, Docker instructions. Output ONLY markdown."
            )
            try:
                readme = self._ask_llm(
                    client, doc_system,
                    f"Goal: {user_prompt}\nFiles: {file_list}\nRun: {run_cmd}"
                )
                with open(os.path.join(project_path, "README.md"), "w", encoding="utf-8") as f:
                    f.write(readme)
                self._log("  ✓ README.md written", "DOCS")
            except Exception as e:
                self._log(f"  README generation failed: {e}", "ERROR")

        # ── DONE ─────────────────────────────────────────────
        self._log("─" * 52, "SYSTEM")
        self._log(f"BUILD COMPLETE  →  {os.path.abspath(project_path)}", "SUCCESS")
        self._log(f"To run:  cd {project_path} && {run_cmd}", "SUCCESS")
        self._set_status("● COMPLETE", COLORS["green"])

        # Update file tree in sidebar
        self._update_file_tree(project_path)
        self._finish_build(True)

    # ═══════════════════════════════════════════════════════════
    #  FILE TREE
    # ═══════════════════════════════════════════════════════════
    def _update_file_tree(self, project_path: str):
        """Walk the output directory and display a file tree in the sidebar."""
        lines = []
        for root, dirs, files in os.walk(project_path):
            level = root.replace(project_path, "").count(os.sep)
            indent = "  " * level
            folder = os.path.basename(root)
            if level == 0:
                lines.append(f"📁 {folder}/")
            else:
                lines.append(f"{indent}📂 {folder}/")
            sub_indent = "  " * (level + 1)
            for fname in sorted(files):
                size = os.path.getsize(os.path.join(root, fname))
                lines.append(f"{sub_indent}📄 {fname}  ({size}B)")

        tree_text = "\n".join(lines) if lines else "Empty."

        def _update():
            self.tree_label.configure(text=tree_text)

        self.after(0, _update)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = CommandCenter()
    app.mainloop()
