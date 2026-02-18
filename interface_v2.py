#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  N E X U S   C O M M A N D   v3.0                          ║
║  eDEX-UI / TRON Legacy Inspired Terminal Interface          ║
║  Powered by Antigravity Engine + Ollama                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import sys
import time
import threading
from datetime import datetime

# Textual Imports
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import (
    Header, Footer, Input, Static, Label, Tree, 
    ProgressBar, RichLog, Rule,
)
from textual.reactive import reactive
from textual.worker import Worker, WorkerState
from textual import work
from textual.timer import Timer

# Rich Imports
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

# System monitoring (graceful fallback)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Engine + Ollama Imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from engine_core import NexusEngine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

import requests

# ─── Configuration ────────────────────────────────────────────
OLLAMA_API_BASE = "http://localhost:11434/api"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "antigravity")

# ─── Color Palette (TRON Legacy) ─────────────────────────────
C_BG       = "#0a0a12"
C_PRIMARY  = "#00e5ff"   # Neon Cyan
C_SECOND   = "#7c3aed"   # Electric Purple
C_SUCCESS  = "#00ff41"   # Matrix Green
C_WARNING  = "#ffab00"   # Amber
C_ERROR    = "#ff1744"   # Hot Red
C_DIM      = "#2a2a3a"   # Muted
C_BORDER   = "#1a3a4a"   # Subtle Cyan
C_TEXT     = "#c0d0e0"   # Soft White


# ══════════════════════════════════════════════════════════════
#  WIDGETS
# ══════════════════════════════════════════════════════════════

class NexusHeader(Static):
    """Animated TRON-style header with live clock and connection pulse."""

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_clock)

    def refresh_clock(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.update(
            f"[bold {C_PRIMARY}]◆ N E X U S  C O M M A N D[/]  "
            f"[dim]v3.0[/]"
            f"[{C_TEXT}]{'':>20}[/]"
            f"[{C_DIM}]{now}[/] "
            f"[bold {C_SUCCESS}]⚡ LIVE[/]"
        )


class SystemMonitor(Static):
    """Real-time CPU / RAM / Disk usage bars."""

    cpu_pct = reactive(0.0)
    ram_pct = reactive(0.0)
    disk_pct = reactive(0.0)

    def on_mount(self) -> None:
        self.set_interval(1.5, self.poll_system)

    def poll_system(self) -> None:
        if HAS_PSUTIL:
            self.cpu_pct = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            self.ram_pct = mem.percent
            disk = psutil.disk_usage("/")
            self.disk_pct = disk.percent
        else:
            import random
            self.cpu_pct = random.uniform(5, 60)
            self.ram_pct = random.uniform(30, 75)
            self.disk_pct = random.uniform(20, 50)

    def watch_cpu_pct(self) -> None:
        self._render_bars()

    def watch_ram_pct(self) -> None:
        self._render_bars()

    def watch_disk_pct(self) -> None:
        self._render_bars()

    def _render_bars(self) -> None:
        def bar(label: str, pct: float, color: str) -> str:
            filled = int(pct / 100 * 12)
            empty = 12 - filled
            return (
                f"[{C_DIM}]{label}[/] "
                f"[{color}]{'█' * filled}[/][{C_DIM}]{'░' * empty}[/] "
                f"[{C_TEXT}]{pct:5.1f}%[/]"
            )

        self.update(
            bar("CPU", self.cpu_pct, C_PRIMARY) + "\n" +
            bar("RAM", self.ram_pct, C_SECOND) + "\n" +
            bar("DSK", self.disk_pct, C_WARNING)
        )


class EnginePanel(Static):
    """Engine status: model, phase, errors."""

    phase_text = reactive("IDLE")
    error_count = reactive(0)

    def on_mount(self) -> None:
        self._render()

    def watch_phase_text(self) -> None:
        self._render()

    def watch_error_count(self) -> None:
        self._render()

    def _render(self) -> None:
        phase_color = C_SUCCESS if self.phase_text == "IDLE" else C_WARNING
        err_color = C_ERROR if self.error_count > 0 else C_DIM

        self.update(
            f"[bold {C_PRIMARY}]ENGINE[/]\n"
            f"[{phase_color}]● {self.phase_text}[/]\n"
            f"[{C_TEXT}]Model: [{C_PRIMARY}]{DEFAULT_MODEL}[/]\n"
            f"[{err_color}]Errors: {self.error_count}[/]"
        )


class BuildStats(Static):
    """Build statistics: files, lines, time."""

    files_count = reactive(0)
    lines_count = reactive(0)
    elapsed = reactive("00:00")

    def on_mount(self) -> None:
        self._render()

    def watch_files_count(self) -> None:
        self._render()

    def watch_lines_count(self) -> None:
        self._render()

    def watch_elapsed(self) -> None:
        self._render()

    def _render(self) -> None:
        self.update(
            f"[bold {C_PRIMARY}]BUILD STATS[/]\n"
            f"[{C_TEXT}]Files : [{C_SUCCESS}]{self.files_count}[/]\n"
            f"[{C_TEXT}]Lines : [{C_SUCCESS}]{self.lines_count}[/]\n"
            f"[{C_TEXT}]Time  : [{C_WARNING}]{self.elapsed}[/]"
        )


class FileBrowser(Tree):
    """Live file tree for the output directory."""

    def __init__(self, label: str = "📁 output/"):
        super().__init__(label)
        self.root.expand()

    def refresh_tree(self, directory: str) -> None:
        """Rebuild the tree from a directory path."""
        self.root.remove_children()
        if not os.path.exists(directory):
            return
        self._add_dir(self.root, directory, depth=0, max_depth=2)

    def _add_dir(self, parent, path, depth, max_depth):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        for entry in entries:
            if entry.startswith("."):
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                node = parent.add(f"📁 {entry}", expand=True)
                self._add_dir(node, full, depth + 1, max_depth)
            else:
                icon = self._icon(entry)
                parent.add_leaf(f"{icon} {entry}")

    @staticmethod
    def _icon(name: str) -> str:
        ext = os.path.splitext(name)[1].lower()
        icons = {
            ".py": "🐍", ".js": "⚡", ".ts": "🔷", ".html": "🌐",
            ".css": "🎨", ".json": "📊", ".md": "📝", ".txt": "📄",
            ".png": "🖼️", ".jpg": "🖼️", ".exe": "⚙️", ".bat": "🔧",
        }
        return icons.get(ext, "📄")


# ══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════

class NexusCommandApp(App):
    """TRON Legacy / eDEX-UI inspired terminal interface."""

    TITLE = "NEXUS COMMAND v3.0"
    BINDINGS = [
        ("ctrl+q", "quit", "Exit"),
        ("ctrl+l", "clear_log", "Clear"),
    ]

    CSS = """
    Screen {
        background: #0a0a12;
        color: #c0d0e0;
    }

    /* ── Header ─────────────────────────────── */
    #nexus-header {
        dock: top;
        height: 3;
        background: #0d0d1a;
        border-bottom: solid #1a3a4a;
        content-align: center middle;
        text-style: bold;
        padding: 0 2;
    }

    /* ── Main 3-Column Grid ─────────────────── */
    #main-grid {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 3fr 1fr;
        height: 1fr;
    }

    /* ── Left Sidebar ────────────────────────── */
    #left-sidebar {
        background: #0d0d1a;
        border-right: solid #1a3a4a;
        padding: 1;
        height: 100%;
    }
    #sys-label {
        text-style: bold;
        color: #00e5ff;
        margin-bottom: 1;
    }
    #sys-monitor {
        height: auto;
        margin-bottom: 1;
    }
    #engine-panel {
        height: auto;
        margin-top: 1;
        border-top: dashed #1a3a4a;
        padding-top: 1;
    }

    /* ── Center Terminal ──────────────────────── */
    #center-terminal {
        background: #08080f;
        padding: 0;
        height: 100%;
    }
    #terminal-log {
        height: 100%;
        border: solid #1a3a4a;
        background: #08080f;
        scrollbar-background: #0a0a12;
        scrollbar-color: #00e5ff;
        scrollbar-color-hover: #7c3aed;
    }

    /* ── Right Sidebar ───────────────────────── */
    #right-sidebar {
        height: 100%;
        background: #0d0d1a;
        border-left: solid #1a3a4a;
        padding: 1;
    }
    #files-label {
        text-style: bold;
        color: #00e5ff;
        margin-bottom: 1;
    }
    FileBrowser {
        height: 1fr;
        border: solid #1a3a4a;
        background: #0d0d1a;
        scrollbar-background: #0a0a12;
        scrollbar-color: #00e5ff;
    }
    #build-stats {
        height: auto;
        margin-top: 1;
        border-top: dashed #1a3a4a;
        padding-top: 1;
    }

    /* ── Command Input Bar ────────────────────── */
    #command-bar {
        dock: bottom;
        height: 3;
        background: #0d0d1a;
        border-top: solid #1a3a4a;
    }
    #cmd-prefix {
        width: 14;
        content-align: right middle;
        padding: 0 1;
        color: #00e5ff;
        text-style: bold;
        height: 3;
    }
    #cmd-input {
        border: none;
        background: #0d0d1a;
        color: #c0d0e0;
        height: 3;
    }
    #cmd-input:focus {
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        # ── Header
        yield NexusHeader(id="nexus-header")

        # ── 3 Column Grid
        with Grid(id="main-grid"):
            # Left sidebar
            with Vertical(id="left-sidebar"):
                yield Label("SYSTEM", id="sys-label")
                yield SystemMonitor(id="sys-monitor")
                yield EnginePanel(id="engine-panel")

            # Center terminal
            with Vertical(id="center-terminal"):
                yield RichLog(id="terminal-log", highlight=True, max_lines=2000)

            # Right sidebar
            with Vertical(id="right-sidebar"):
                yield Label("FILE BROWSER", id="files-label")
                yield FileBrowser()
                yield BuildStats(id="build-stats")

        # ── Bottom command bar
        with Horizontal(id="command-bar"):
            yield Static("◆ DIRECTIVE >", id="cmd-prefix")
            yield Input(placeholder="Enter command or ask anything...", id="cmd-input")

    # ── Lifecycle ──────────────────────────────────────────────

    def on_mount(self) -> None:
        self.terminal = self.query_one("#terminal-log", RichLog)
        self.engine_panel = self.query_one("#engine-panel", EnginePanel)
        self.build_stats = self.query_one("#build-stats", BuildStats)
        self.file_browser = self.query_one(FileBrowser)
        self.ollama_context = []
        self.build_start_time = None

        # Engine
        if HAS_ENGINE:
            self.engine = NexusEngine(
                project_name="nexus_session",
                model=f"ollama:{DEFAULT_MODEL}",
                on_log=self._engine_log_callback,
                use_docker=False,
            )
            self.output_dir = self.engine.project_dir
        else:
            self.engine = None
            self.output_dir = os.path.join(os.getcwd(), "output")

        self._write_welcome()
        self.set_interval(3.0, self._poll_files)

    def _write_welcome(self) -> None:
        self.terminal.write(Text(""))
        self.terminal.write(
            Text("  ╔══════════════════════════════════════════════╗", style=f"bold {C_PRIMARY}")
        )
        self.terminal.write(
            Text("  ║   N E X U S   C O M M A N D   v 3 . 0      ║", style=f"bold {C_PRIMARY}")
        )
        self.terminal.write(
            Text("  ║   Powered by Antigravity + Ollama            ║", style=f"bold {C_PRIMARY}")
        )
        self.terminal.write(
            Text("  ╚══════════════════════════════════════════════╝", style=f"bold {C_PRIMARY}")
        )
        self.terminal.write(Text(""))
        self.terminal.write(
            Text(f"  Model: {DEFAULT_MODEL}   |   Type /help for commands", style=C_DIM)
        )
        self.terminal.write(Text(""))

    # ── Engine Log Callback ───────────────────────────────────

    def _engine_log_callback(self, category: str, message: str) -> None:
        colors = {
            "ERROR": C_ERROR, "SUCCESS": C_SUCCESS, "WARN": C_WARNING,
            "ENGINE": C_PRIMARY, "ARCHITECT": C_SECOND, "DEV": "#00bcd4",
            "REVIEW": "#e040fb", "STATE": C_DIM, "SANDBOX": "#ff9800",
        }
        color = colors.get(category, C_TEXT)
        self.call_from_thread(
            self.terminal.write,
            Text(f"  [{category:>10}] {message}", style=color)
        )

    # ── File Polling ──────────────────────────────────────────

    def _poll_files(self) -> None:
        if os.path.exists(self.output_dir):
            self.file_browser.refresh_tree(self.output_dir)
            # Count stats
            total_files = 0
            total_lines = 0
            for root, _, files in os.walk(self.output_dir):
                for f in files:
                    if f.startswith("."):
                        continue
                    total_files += 1
                    try:
                        with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as fh:
                            total_lines += sum(1 for _ in fh)
                    except Exception:
                        pass
            self.build_stats.files_count = total_files
            self.build_stats.lines_count = total_lines

        if self.build_start_time:
            elapsed = int(time.time() - self.build_start_time)
            mins, secs = divmod(elapsed, 60)
            self.build_stats.elapsed = f"{mins:02d}:{secs:02d}"

    # ── Input Handling ────────────────────────────────────────

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        raw = message.value.strip()
        if not raw:
            return
        self.query_one("#cmd-input", Input).value = ""

        # Echo user input
        self.terminal.write(Text(f"\n  > {raw}", style=f"bold {C_SUCCESS}"))

        # Command routing
        parts = raw.split(" ", 1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            self.exit()
            return
        elif cmd == "/clear":
            self.action_clear_log()
            return
        elif cmd == "/help":
            self._show_help()
            return
        elif cmd == "/model":
            if len(parts) > 1:
                global DEFAULT_MODEL
                DEFAULT_MODEL = parts[1]
                self.terminal.write(Text(f"  Model set to: {DEFAULT_MODEL}", style=C_SUCCESS))
            else:
                self.terminal.write(Text(f"  Current model: {DEFAULT_MODEL}", style=C_TEXT))
            return
        elif cmd == "/build":
            if len(parts) > 1:
                self._do_build(parts[1])
            else:
                self.terminal.write(Text("  Usage: /build <what to build>", style=C_ERROR))
            return

        # Auto-build detection
        lower = raw.lower()
        build_kw = ["create", "make", "build", "generate", "code", "program", "app", "script", "write"]
        skip_kw = ["how to", "explain", "what is", "tell me"]
        if (any(k in lower for k in build_kw)
                and len(raw.split()) > 2
                and not any(k in lower for k in skip_kw)):
            self.terminal.write(Text("  🚀 Auto-Build Detected!", style=f"bold {C_WARNING}"))
            self._do_build(raw)
            return

        # Default: Ollama chat
        self._do_chat(raw)

    # ── Chat (Ollama Streaming) ───────────────────────────────

    @work(exclusive=True, thread=True)
    def _do_chat(self, prompt: str) -> None:
        self.call_from_thread(self.engine_panel.__setattr__, "phase_text", "CHATTING")
        url = f"{OLLAMA_API_BASE}/generate"
        data = {
            "model": DEFAULT_MODEL,
            "prompt": prompt,
            "context": self.ollama_context,
            "stream": True,
        }

        full_response = ""
        try:
            with requests.post(url, json=data, stream=True, timeout=120) as r:
                if r.status_code != 200:
                    self.call_from_thread(
                        self.terminal.write,
                        Text(f"  ❌ Ollama error: {r.status_code}", style=C_ERROR)
                    )
                    return

                # Stream chunks
                buffer = ""
                for line in r.iter_lines():
                    if line:
                        body = json.loads(line)
                        chunk = body.get("response", "")
                        full_response += chunk
                        buffer += chunk

                        # Flush on newlines or when buffer gets long
                        if "\n" in buffer or len(buffer) > 80:
                            lines = buffer.split("\n")
                            for ln in lines[:-1]:
                                self.call_from_thread(
                                    self.terminal.write,
                                    Text(f"  {ln}", style=C_TEXT)
                                )
                            buffer = lines[-1]

                        if body.get("done"):
                            self.ollama_context = body.get("context", [])

                # Flush remaining buffer
                if buffer.strip():
                    self.call_from_thread(
                        self.terminal.write,
                        Text(f"  {buffer}", style=C_TEXT)
                    )

        except requests.exceptions.ConnectionError:
            self.call_from_thread(
                self.terminal.write,
                Text("  ❌ Cannot connect to Ollama. Is 'ollama serve' running?", style=C_ERROR)
            )
        except Exception as e:
            self.call_from_thread(
                self.terminal.write,
                Text(f"  ❌ Chat error: {e}", style=C_ERROR)
            )
        finally:
            self.call_from_thread(self.engine_panel.__setattr__, "phase_text", "IDLE")

    # ── Build (NexusEngine) ───────────────────────────────────

    @work(exclusive=True, thread=True)
    def _do_build(self, prompt: str) -> None:
        if not HAS_ENGINE:
            self.call_from_thread(
                self.terminal.write,
                Text("  ❌ NexusEngine not available. Cannot build.", style=C_ERROR)
            )
            return

        self.call_from_thread(self.engine_panel.__setattr__, "phase_text", "BUILDING")
        self.build_start_time = time.time()
        self.call_from_thread(self.engine_panel.__setattr__, "error_count", 0)

        self.call_from_thread(
            self.terminal.write,
            Text(f"\n  🚀 CREATION ENGINE ONLINE", style=f"bold {C_SUCCESS}")
        )
        self.call_from_thread(
            self.terminal.write,
            Text(f"  Goal: {prompt}", style=C_DIM)
        )

        try:
            result = self.engine.run_full_build(prompt)

            self.call_from_thread(
                self.terminal.write,
                Text(f"\n  ✅ BUILD COMPLETE!", style=f"bold {C_SUCCESS}")
            )
            if isinstance(result, dict):
                path = result.get("project_path", self.output_dir)
                files = result.get("files_written", "?")
                self.call_from_thread(
                    self.terminal.write,
                    Text(f"  📂 Output: {path}  |  Files: {files}", style=C_TEXT)
                )
        except Exception as e:
            self.call_from_thread(self.engine_panel.__setattr__, "error_count",
                                 self.engine_panel.error_count + 1)
            self.call_from_thread(
                self.terminal.write,
                Text(f"\n  ❌ Build failed: {e}", style=C_ERROR)
            )
        finally:
            self.build_start_time = None
            self.call_from_thread(self.engine_panel.__setattr__, "phase_text", "IDLE")
            self.call_from_thread(self._poll_files)

    # ── Actions ───────────────────────────────────────────────

    def action_clear_log(self) -> None:
        self.terminal.clear()
        self._write_welcome()

    def _show_help(self) -> None:
        help_lines = [
            ("", ""),
            ("  COMMANDS", f"bold {C_PRIMARY}"),
            (f"  {'─' * 40}", C_DIM),
            ("  /build <prompt>    Create software from a description", C_TEXT),
            ("  /model <name>      Switch Ollama model", C_TEXT),
            ("  /clear             Clear terminal", C_TEXT),
            ("  /help              Show this help", C_TEXT),
            ("  /exit              Quit Nexus Command", C_TEXT),
            ("", ""),
            ("  AUTO-BUILD", f"bold {C_WARNING}"),
            (f"  {'─' * 40}", C_DIM),
            ("  Just type naturally! Phrases like 'Create a snake game'", C_TEXT),
            ("  are automatically detected and sent to the build engine.", C_TEXT),
            ("", ""),
            ("  SHORTCUTS", f"bold {C_SECOND}"),
            (f"  {'─' * 40}", C_DIM),
            ("  Ctrl+Q  Exit    |   Ctrl+L  Clear", C_TEXT),
            ("", ""),
        ]
        for line, style in help_lines:
            self.terminal.write(Text(line, style=style))


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = NexusCommandApp()
    app.run()
