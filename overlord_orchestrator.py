#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  OVERLORD ORCHESTRATOR — Master Entry Point
  The single command that triggers the entire autonomous
  build pipeline:

    Architect → Assembler → Developer → Reviewer → Setup → Recovery → Handoff

  Usage:
    python overlord_orchestrator.py "Build a REST API for task management"
    python overlord_orchestrator.py --prompt "Build a chatbot" --project MyChatBot
    python overlord_orchestrator.py "E-commerce site" --docker --debug --model gemini-2.0-flash

  Alias-friendly (add to your shell profile):
    alias overlord='python /path/to/overlord_orchestrator.py'
    overlord "Build me a web scraper"

══════════════════════════════════════════════════════════════
"""

import os
import sys
import argparse
import time
import shutil
import asyncio
from datetime import datetime


# ── Ensure we can import the agent brain ─────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from agent_brain import (
    execute_build,
    log,
    divider,
    IntegrityWatchdog,
    CostTracker,
)


# ── Banner ───────────────────────────────────────────────────

BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║     ██████╗ ██╗   ██╗███████╗██████╗ ██╗      ██████╗    ║
  ║    ██╔═══██╗██║   ██║██╔════╝██╔══██╗██║     ██╔═══██╗   ║
  ║    ██║   ██║██║   ██║█████╗  ██████╔╝██║     ██║   ██║   ║
  ║    ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██║     ██║   ██║   ║
  ║    ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║███████╗╚██████╔╝   ║
  ║     ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝   ║
  ║                                                          ║
  ║         Autonomous Code Generation Engine v2.0           ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
"""


# ── CLI Argument Parser ──────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the comprehensive argument parser for the Overlord pipeline."""
    parser = argparse.ArgumentParser(
        prog="overlord",
        description=(
            "Overlord Orchestrator — Autonomous Code Generation Engine.\n"
            "Triggers the full pipeline: "
            "Architect → Assembler → Developer → Reviewer → Setup → Recovery → Handoff"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  overlord "Build a REST API for todo management"\n'
            '  overlord "AI chatbot with Telegram" --docker --debug\n'
            '  overlord --prompt "E-commerce site" --project MyStore --model gemini-2.0-flash\n'
            '  overlord "Web scraper" --arch-model gemini-2.0-flash --eng-model llama-3.3-70b-versatile\n'
            '  overlord "Dashboard app" --full --budget 2.0 --local-model llama3\n'
        ),
    )

    # ── Core Arguments ───────────────────────────────────────
    parser.add_argument(
        "idea", nargs="?", default=None,
        help="Quick-start: just describe what you want to build (positional arg)."
    )
    parser.add_argument(
        "--prompt", "-p", default="",
        help="The build prompt — what to build. Overrides positional 'idea' if both given."
    )
    parser.add_argument(
        "--project", "-n", default="",
        help="Project name / slug (auto-generated from prompt if omitted)."
    )
    parser.add_argument(
        "--output", "-o", default="./output",
        help="Output directory for generated projects (default: ./output)."
    )

    # ── Model Configuration ──────────────────────────────────
    model_group = parser.add_argument_group("Model Configuration")
    model_group.add_argument(
        "--model", "-m", default="gpt-4o",
        help="Default model for all phases (default: gpt-4o)."
    )
    model_group.add_argument(
        "--arch-model", default="",
        help="Strategy model for Architect + Prompt phases (overrides --model)."
    )
    model_group.add_argument(
        "--eng-model", default="",
        help="Speed model for Engineer + coding phases (overrides --model)."
    )
    model_group.add_argument(
        "--local-model", default="",
        help="Cheap/local model for Reviewer, Dockerfile, README, Env scripts (e.g. llama3 via Ollama)."
    )
    model_group.add_argument(
        "--api-key", default="",
        help="API key (or set OPENAI_API_KEY / GEMINI_API_KEY / GROQ_API_KEY env vars)."
    )
    model_group.add_argument(
        "--budget", default=5.0, type=float,
        help="Max spend in USD before pivoting to local model (default: $5.00)."
    )

    # ── Pipeline Feature Flags ───────────────────────────────
    features = parser.add_argument_group("Pipeline Features")
    features.add_argument(
        "--docker", "-d", action="store_true",
        help="Generate Dockerfile + docker-compose.yml and run Auto-Heal deployment."
    )
    features.add_argument(
        "--debug", action="store_true",
        help="Enable Autonomic Debugger (up to 5 self-healing debug passes)."
    )
    features.add_argument(
        "--readme", action="store_true",
        help="Generate a professional README.md."
    )
    features.add_argument(
        "--setup", action="store_true",
        help="Generate setup.ps1, .env.template via the deterministic Setup Agent."
    )
    features.add_argument(
        "--compile", action="store_true",
        help="Compile project to standalone EXE (Nuitka for GUI, PyInstaller for CLI)."
    )
    features.add_argument(
        "--graph", action="store_true",
        help="Use LangGraph orchestration with conditional routing (requires: pip install langgraph)."
    )
    features.add_argument(
        "--full", action="store_true",
        help="Enable ALL features: --docker --debug --readme --setup --compile."
    )

    return parser


# ── Project Name Auto-Generation ─────────────────────────────

def slugify_prompt(prompt: str) -> str:
    """Generate a clean project name from the user's prompt."""
    import re
    # Take first 3-4 meaningful words
    words = re.findall(r'[a-zA-Z]+', prompt)
    # Filter out common stopwords
    stopwords = {"a", "an", "the", "for", "and", "or", "with", "to", "in", "on", "by", "my", "is", "it", "of"}
    meaningful = [w.capitalize() for w in words if w.lower() not in stopwords][:4]
    if not meaningful:
        meaningful = ["Project"]
    return "".join(meaningful)


# ── Packaging Strategy ───────────────────────────────────────

PACKAGING_STRATEGY = {
    "gui":       {"tool": "nuitka",      "reason": "Faster runtime; native PyQt6 plugin handles DLLs."},
    "cli":       {"tool": "pyinstaller", "reason": "Fast compile; ideal for simple CLI tools."},
    "api":       {"tool": "pyinstaller", "reason": "Quick bundling; APIs rarely need code obfuscation."},
    "prototype": {"tool": "pyinstaller", "reason": "Fast iteration; compile speed matters most."},
    "default":   {"tool": "nuitka",      "reason": "Professional default; C-compiled for speed + obfuscation."},
}


def detect_project_type(project_dir: str) -> str:
    """Detect project type by scanning for framework indicators."""
    main_py = os.path.join(project_dir, "main.py")
    if not os.path.exists(main_py):
        return "default"
    try:
        with open(main_py, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if any(kw in content for kw in ["PyQt", "PySide", "tkinter", "customtkinter", "QApplication"]):
            return "gui"
        if any(kw in content for kw in ["Flask", "FastAPI", "Django", "uvicorn"]):
            return "api"
        if any(kw in content for kw in ["argparse", "click", "typer", "sys.argv"]):
            return "cli"
    except Exception:
        pass
    return "default"


# ── Resource Bridge ──────────────────────────────────────────

RESOURCE_BRIDGE = '''
import sys, os

def get_asset_path(relative_path):
    """2026 Resource Bridge for Nuitka/PyInstaller standalone mode."""
    if hasattr(sys, '_MEIPASS'):  # PyInstaller
        return os.path.join(sys._MEIPASS, relative_path)
    # Nuitka / Source mode
    return os.path.join(os.path.abspath("."), relative_path)
'''


def inject_resource_bridge(project_dir: str) -> bool:
    """Inject get_asset_path() into main.py if not already present."""
    main_py = os.path.join(project_dir, "main.py")
    if not os.path.exists(main_py):
        return False
    try:
        with open(main_py, "r", encoding="utf-8") as f:
            content = f.read()
        if "get_asset_path" in content:
            return True  # Already injected
        # Insert after imports
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith(("import ", "from ", "#", '"""', "'''")):
                insert_idx = i
                break
        lines.insert(insert_idx, RESOURCE_BRIDGE)
        with open(main_py, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log("COMPILE", "  🧬 Resource Bridge injected into main.py")
        return True
    except Exception as e:
        log("COMPILE", f"  ⚠ Bridge injection failed: {e}")
        return False


# ── Compilation Specialist Node ──────────────────────────────

async def compilation_specialist_node(project_dir: str, project_name: str):
    """Role: Binary Architect. Goal: Compile to single EXE and move to Desktop."""
    log("COMPILE", f"💎 Compilation Specialist: Hardening {project_name}...")

    # Detect project type and choose strategy
    ptype = detect_project_type(project_dir)
    strategy = PACKAGING_STRATEGY.get(ptype, PACKAGING_STRATEGY["default"])
    tool = strategy["tool"]
    log("COMPILE", f"  📊 Detected: {ptype} → Using {tool.upper()} ({strategy['reason']})")

    # Inject Resource Bridge
    inject_resource_bridge(project_dir)

    # Dynamic Desktop Path Resolution
    desktop_path = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    dist_folder = os.path.join(project_dir, "dist")
    exe_name = f"{project_name}.exe"

    # Check for assets directory
    has_assets = os.path.isdir(os.path.join(project_dir, "assets"))

    if tool == "nuitka":
        cmd = [
            "python", "-m", "nuitka",
            "--standalone",
            "--onefile",
            f"--output-filename={exe_name}",
            f"--output-dir={dist_folder}",
        ]
        # Auto-detect GUI framework plugins
        main_content = ""
        main_py = os.path.join(project_dir, "main.py")
        if os.path.exists(main_py):
            with open(main_py, "r", encoding="utf-8", errors="ignore") as f:
                main_content = f.read()
        if "PyQt6" in main_content or "PyQt5" in main_content:
            cmd.append("--plugin-enable=pyqt6")
        elif "PySide6" in main_content:
            cmd.append("--plugin-enable=pyside6")
        elif "tkinter" in main_content:
            cmd.append("--plugin-enable=tk-inter")
        if has_assets:
            cmd.append("--include-data-dir=assets=assets")
        cmd.append("main.py")
    else:
        # PyInstaller
        cmd = [
            "python", "-m", "PyInstaller",
            "--onefile",
            "--clean",
            f"--name={project_name}",
            f"--distpath={dist_folder}",
        ]
        if has_assets:
            cmd.append("--add-data=assets;assets")
        cmd.append("main.py")

    log("COMPILE", f"  🔧 Command: {' '.join(cmd)}")

    # Execute compilation from the project directory
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=project_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        log("COMPILE", f"  ❌ Compilation failed (exit {process.returncode})")
        if stderr:
            for line in stderr.decode(errors='ignore').strip().split('\n')[-5:]:
                log("COMPILE", f"     {line}")
        return None

    # Find the built EXE
    source_path = os.path.join(dist_folder, exe_name)
    if not os.path.exists(source_path):
        # PyInstaller may put it in a different subfolder
        for root, dirs, files in os.walk(dist_folder):
            if exe_name in files:
                source_path = os.path.join(root, exe_name)
                break

    if os.path.exists(source_path):
        destination_path = os.path.join(desktop_path, exe_name)
        log("COMPILE", f"  🚀 Moving binary to Desktop: {destination_path}")
        shutil.move(source_path, destination_path)
        return destination_path
    else:
        log("COMPILE", "  ❌ Binary not found in dist folder after compilation.")
        return None


# ── Main Orchestration ───────────────────────────────────────

def main():
    """
    Master entry point for the Overlord pipeline.

    Pipeline Phases:
      Phase 0   — Prompt Enhancement (auto-expand vague ideas)
      Phase 1   — Architect (JSON blueprint: file tree, deps, stack)
      Phase 1.5 — Project Assembler (scaffold dirs + empty files)
      Phase 2   — Engineer + Recursive Refinement (write code)
      Phase 2.5 — Auditor + Master Reviewer (zero-trust audit)
      Phase 3   — Debugger / Autonomic Healing (if --debug)
      Phase 4   — Packaging (requirements.txt, Dockerfile, README)
      Phase 5   — Environment Agent (setup scripts, docker-compose)
      Phase 5.5 — Auto-Heal Deployment (if --docker)
      Phase 6   — Handoff (FULL_PACKAGE.md + package_manifest.json)
    """
    parser = build_parser()
    args = parser.parse_args()

    # ── Resolve prompt ───────────────────────────────────────
    # Priority: --prompt flag > positional "idea" arg
    prompt = args.prompt or args.idea or ""
    if not prompt:
        print(BANNER)
        parser.print_help()
        print("\n  ❌ No prompt provided. Describe what you want to build.\n")
        sys.exit(1)
    args.prompt = prompt

    # ── Resolve project name ─────────────────────────────────
    if not args.project:
        args.project = slugify_prompt(prompt)
    # Clean the project name for filesystem safety
    args.project = "".join(c for c in args.project if c.isalnum() or c in "-_")

    # ── Handle --full shorthand ──────────────────────────────
    if args.full:
        args.docker = True
        args.debug = True
        args.readme = True
        args.setup = True
        args.compile = True

    # ── Show banner + mission briefing ───────────────────────
    print(BANNER)
    start_time = time.time()

    log("OVERLORD", "═" * 52)
    log("OVERLORD", "  MISSION BRIEFING")
    log("OVERLORD", "═" * 52)
    log("OVERLORD", f"  Project:   {args.project}")
    log("OVERLORD", f"  Prompt:    {prompt[:80]}{'…' if len(prompt) > 80 else ''}")
    log("OVERLORD", f"  Output:    {os.path.abspath(args.output)}")
    log("OVERLORD", f"  Model:     {args.model}")
    if args.arch_model:
        log("OVERLORD", f"  Architect: {args.arch_model}")
    if args.eng_model:
        log("OVERLORD", f"  Engineer:  {args.eng_model}")
    local_model = getattr(args, 'local_model', '') or ''
    if local_model:
        log("OVERLORD", f"  Local:     {local_model} (Reviewer/Env/Dockerfile)")
    log("OVERLORD", f"  Budget:    ${args.budget:.2f} (kill-switch enabled)")

    features_active = []
    if args.docker:  features_active.append("Docker")
    if args.debug:   features_active.append("Debug")
    if args.readme:  features_active.append("README")
    if args.setup:   features_active.append("Setup Agent")
    if args.compile: features_active.append("Compile → EXE")
    if args.graph:   features_active.append("LangGraph")
    log("OVERLORD", f"  Features:  {', '.join(features_active) or 'Standard build'}")
    log("OVERLORD", "═" * 52)

    divider()

    # ── Pipeline Roadmap ─────────────────────────────────────
    log("OVERLORD", "📋 PIPELINE ROADMAP:")
    phases = [
        ("Phase 0",   "Prompt Enhancement",      "🧠", True),
        ("Phase 1",   "Architect Agent",          "📐", True),
        ("Phase 1.5", "Project Assembler",        "🏗️", True),
        ("Phase 2",   "Engineer + Refinement",    "⚙️", True),
        ("Phase 2.5", "Auditor + Reviewer",       "🔍", True),
        ("Phase 3",   "Autonomic Debugger",       "🐛", args.debug),
        ("Phase 4",   "Packaging",                "📦", True),
        ("Phase 5",   "Environment Agent",        "🌐", True),
        ("Phase 5.5", "Auto-Heal Deployment",     "🩺", args.docker),
        ("Phase 6",   "Compilation → EXE",        "💎", args.compile),
        ("Phase 7",   "Handoff",                  "🤝", True),
    ]
    for phase_id, phase_name, icon, active in phases:
        status = "✓" if active else "○ skip"
        log("OVERLORD", f"  {icon} {phase_id}: {phase_name}  [{status}]")

    divider()

    # ── Activate Fortress Protocols ──────────────────────────
    brain_path = os.path.join(SCRIPT_DIR, "agent_brain.py")
    main_js_path = os.path.join(SCRIPT_DIR, "main.js")
    core_files = [f for f in [brain_path, main_js_path, __file__] if os.path.exists(f)]
    watchdog = IntegrityWatchdog(core_files)

    # ── Pulse-Sync: Capture Developer Context ──────────────────
    try:
        from pulse_sync_logger import PulseSyncLogger
        pulse = PulseSyncLogger(project_root=SCRIPT_DIR)
        pulse.capture_heartbeat()
        pulse_context = pulse.get_context_for_orchestrator()
        if pulse_context:
            log("OVERLORD", "💓 Pulse-Sync: Developer context loaded")
    except ImportError:
        pulse_context = ""
    except Exception as e:
        log("OVERLORD", f"  ⚠ Pulse-Sync failed: {e}")
        pulse_context = ""

    # ── Execute the pipeline ─────────────────────────────────
    try:
        if args.graph:
            # LangGraph mode: stateful graph with conditional routing
            try:
                from overlord_graph import run_graph
                log("OVERLORD", "🧬 Graph Mode: LangGraph orchestration engine active")
                final_state = run_graph(args)
            except ImportError:
                log("OVERLORD", "⚠ langgraph not installed. Falling back to linear pipeline.")
                log("OVERLORD", "  Install with: pip install langgraph")
                execute_build(args)
        else:
            # Linear mode: classic sequential pipeline
            execute_build(args)

        # ── Phase 6: Compilation ─────────────────────────────
        if args.compile:
            divider()
            log("OVERLORD", "💎 Phase 6: Compilation Specialist...")
            project_dir = os.path.abspath(os.path.join(args.output, args.project))
            binary_path = asyncio.run(
                compilation_specialist_node(project_dir, args.project)
            )
            if binary_path:
                log("OVERLORD", f"  ✅ EXE delivered: {binary_path}")
            else:
                log("OVERLORD", "  ⚠ Compilation skipped or failed (project still available).")
            divider()
    except KeyboardInterrupt:
        log("OVERLORD", "\n  ⚠ Build interrupted by user.")
        sys.exit(130)
    except SystemExit:
        raise  # Let sys.exit() propagate
    except Exception as e:
        log("CRITICAL", f"  Pipeline crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Deactivate watchdog
        watchdog.active = False

    # ── Final Summary ────────────────────────────────────────
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    project_dir = os.path.abspath(os.path.join(args.output, args.project))

    # Check if a cost report was generated
    cost_report_path = os.path.join(project_dir, "cost_report.json")
    cost_line = ""
    if os.path.exists(cost_report_path):
        try:
            import json
            with open(cost_report_path, "r") as f:
                report = json.load(f)
            cost_line = f"${report.get('total_cost', 0):.4f} / ${report.get('budget', 0):.2f}"
        except Exception:
            cost_line = "see cost_report.json"

    log("OVERLORD", "")
    log("OVERLORD", "═" * 52)
    log("OVERLORD", "  MISSION COMPLETE")
    log("OVERLORD", "═" * 52)
    log("OVERLORD", f"  Project:  {args.project}")
    log("OVERLORD", f"  Location: {project_dir}")
    log("OVERLORD", f"  Duration: {minutes}m {seconds}s")
    if cost_line:
        log("OVERLORD", f"  Cost:     {cost_line}")
    log("OVERLORD", "═" * 52)
    log("OVERLORD", "")
    log("OVERLORD", "  Quick Start:")
    log("OVERLORD", f"    cd {os.path.join(args.output, args.project)}")
    if args.compile:
        exe_path = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop", f"{args.project}.exe")
        if os.path.exists(exe_path):
            log("OVERLORD", f"    💎 Or run: {exe_path}")
    if args.docker:
        log("OVERLORD", "    docker compose up -d")
    else:
        log("OVERLORD", "    python main.py")
    log("OVERLORD", "")


# ── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    main()
