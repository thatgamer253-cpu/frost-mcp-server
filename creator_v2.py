#!/usr/bin/env python3

"""
Overlord V2 - Homey & Smooth
Smoother typing, warmer colors, friendly persona.
"""

import sys
import os
import traceback
from datetime import datetime

# --- Crash Handler ---
def _crash_handler(exctype, value, tb):
    with open("v2_crash.log", "a", encoding="utf-8") as f:
        f.write(f"\n--- CRASH AT {datetime.now()} ---\n")
        f.write("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)
sys.excepthook = _crash_handler

from agent_ipc import post, read_recent, AGENTS, clear_log, get_agent_info
from voice_service import voice_service
from voice_agent import boot_voice_agent, stop_voice_agent
from creation_engine.chronicler import chronicler
from creation_engine.projector import projector
from creation_engine.workflow_steward import workflow_steward
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTextEdit, QPushButton, QLabel, QFrame,
    QListWidget, QComboBox, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QTextCursor
)


def get_resource_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

sys.path.insert(0, get_resource_path("."))


try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


# ── Styles (Premium Dark Mode — 2024 Research) ──────────────
C = {
    "bg_app":      "#0a0a0c",  # Deep black (not pure #000)
    "bg_sidebar":  "#0e0e12",  # Slightly lighter sidebar
    "bg_card":     "#141418",  # Card/elevated surfaces
    "bg_pill":     "#1a1a22",  # Input pill
    "text":        "#e8e8ed",  # Off-white text (easier on eyes)
    "text_dim":    "#8b8b99",  # Muted labels
    "text_ghost":  "#52525b",  # Ultra-dim timestamps
    "accent":      "#818cf8",  # Indigo-400 accent
    "accent_glow": "#6366f1",  # Indigo-500 glow
    "user_msg":    "#1e1b4b",  # Dark indigo user bubbles
    "border":      "#27272a",
    "border_lit":  "#3f3f46",  # Highlighted border
    "success":     "#34d399",  # Green for resolved
    "warning":     "#fbbf24",  # Amber for flags
    "danger":      "#f87171",  # Red for errors
}

STYLESHEET = f"""
QMainWindow {{ background:{C["bg_app"]}; }}
QWidget {{ font-family:'Segoe UI', 'Inter', sans-serif; font-size:15px; color:{C["text"]}; }}

QListWidget {{
    background: {C["bg_sidebar"]}; border: none; padding: 8px;
    font-size: 14px; color: {C["text_dim"]};
}}
QListWidget::item {{ padding: 10px 12px; border-radius: 8px; margin: 2px 0; }}
QListWidget::item:selected {{ background: #1e1b4b; color: #c7d2fe; }}
QListWidget::item:hover {{ background: #141418; }}

QTextBrowser {{ background: transparent; border: none; }}

/* ── Tab Bar ── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    background: transparent;
    border: none;
}}
QTabBar::tab {{
    background: {C["bg_card"]};
    color: {C["text_dim"]};
    border: 1px solid {C["border"]};
    border-bottom: none;
    padding: 10px 28px;
    margin-right: 2px;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {C["bg_app"]};
    color: {C["accent"]};
    border-bottom: 2px solid {C["accent"]};
}}
QTabBar::tab:hover {{
    background: #1e1b4b;
    color: #c7d2fe;
}}

/* ── Input Pill ── */
QFrame#InputPill {{
    background-color: {C["bg_pill"]};
    border-radius: 26px;
    border: 1px solid {C["border"]};
}}
QFrame#InputPill:hover {{ border: 1px solid {C["accent"]}; }}

QTextEdit#ChatInput {{
    background: transparent; border: none; color: {C["text"]}; 
    padding: 12px 16px; font-size: 15px;
    selection-background-color: {C["accent_glow"]};
}}
QPushButton#SendBtn {{
    background-color: {C["accent"]};
    color: #0a0a0c;
    border-radius: 20px;
    font-weight: bold;
    font-size: 16px;
    border: none;
}}
QPushButton#SendBtn:hover {{ background-color: #a5b4fc; }}
QPushButton#SendBtn:disabled {{ background-color: #27272a; color: #52525b; }}

/* ── Status Ticker ── */
QFrame#StatusTicker {{
    background: {C["bg_card"]};
    border-top: 1px solid {C["border"]};
    padding: 4px 12px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: #3f3f46; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C["accent"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""

# ── Logic ────────────────────────────────────────────────────

class ChatWorker(QThread):
    chunk_sig = pyqtSignal(str)
    finished_sig = pyqtSignal()
    
    def __init__(self, prompt, model="gpt-4o-mini", history=[]):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.history = history

    def run(self):
        try:
            from creation_engine.llm_client import ask_llm_stream
            
            # Context
            context_str = ""
            for role, text in self.history[-6:]:
                context_str += f"{role.upper()}: {text}\n"
            
            # Web Search Integration
            search_context = ""
            keywords = ["search", "google", "find", "news", "price", "weather", "who is", "what is", "current", "latest"]
            if any(k in self.prompt.lower() for k in keywords):
                try:
                    from creation_engine.web_search import search_web
                    self.chunk_sig.emit("🔍 *Searching the web...*\n\n")
                    results = search_web(self.prompt, max_results=3)
                    if results:
                        self.chunk_sig.emit(f"✓ Found relevant info.\n\n")
                        search_context = "CONTEXT FROM WEB SEARCH:\n"
                        for r in results:
                            search_context += f"- Title: {r.get('title')}\n  Url: {r.get('href')}\n  Snippet: {r.get('body')}\n"
                        search_context += "\n"
                    else:
                        self.chunk_sig.emit("⚠️ No relevant results found.\n\n")
                except Exception as e:
                    self.chunk_sig.emit(f"[Search Error: {e}]\n\n")

            # ── Ghost Layer: Sentient Persona ──
            try:
                from creation_engine.personality import PersonalityManager
                pm = PersonalityManager()
                full_context = f"{context_str}\n{search_context}\nUSER: {self.prompt}"
                system = pm.get_system_prompt(context=full_context)
                
                # Show thinking state
                archetype_name = pm.current_archetype
                self.chunk_sig.emit(f"*{archetype_name} is thinking...*\n\n")
                
                # Non-streaming call for JSON parsing
                from creation_engine.llm_client import ask_llm, get_cached_client
                client = get_cached_client(self.model)
                raw = ask_llm(client, self.model, system, self.prompt)
                
                # Parse the Ghost Layer JSON
                import json
                try:
                    # Strip markdown fences if present
                    cleaned = raw
                    if "```json" in cleaned:
                        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                    elif "```" in cleaned:
                        cleaned = cleaned.split("```")[1].split("```")[0].strip()
                    
                    ghost = json.loads(cleaned)
                    mood = ghost.get("perceived_mood", "Neutral")
                    response = ghost.get("final_response", raw)
                    monologue = ghost.get("internal_monologue", "")
                    
                    # Record experience
                    pm.add_experience(
                        f"Chat: {self.prompt[:60]}",
                        "Positive" if mood.lower() in ["inspired", "creative", "enthusiastic", "happy"] else "Neutral"
                    )
                    
                    # Emit: mood indicator + actual response
                    self.chunk_sig.emit(f"**[{mood}]**\n\n{response}")
                    
                except (json.JSONDecodeError, KeyError):
                    # Fallback: LLM didn't return valid JSON, show raw
                    self.chunk_sig.emit(raw)
                    
                self.finished_sig.emit()
                return
                
            except ImportError:
                pass # Fall through to generic mode
            
            # ── Fallback: Generic Persona ──
            system = (
                "You are Overlord, a friendly and capable creative partner. "
                "Your goal is to help the user build their ideas with warmth and clarity. "
                "Use Markdown for structure. Be encouraging but concise. "
                "If search results are provided, use them to answer accurately."
            )
            full_user = f"{context_str}\n{search_context}\nUSER: {self.prompt}"
            
            stream = ask_llm_stream(client=None, model=self.model, system_role=system, user_content=full_user)
            
            for chunk in stream:
                self.chunk_sig.emit(chunk)
                
            self.finished_sig.emit()
            
        except ImportError:
            self.chunk_sig.emit("Error: Backend disconnected.")
            self.finished_sig.emit()
        except Exception as e:
            self.chunk_sig.emit(f"Error: {e}")
            self.finished_sig.emit()

class BuildWorker(QThread):
    finished_sig = pyqtSignal(bool, str)
    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
    def run(self):
        try:
            # Debug Log
            with open("build_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] STARTING BUILD\nPROMPT: {self.prompt}\n")

            from creation_engine.orchestrator import CreationEngine
            
            # Use gpt-4o for Architecture (Critical)
            orch = CreationEngine(
                project_name="OverlordApp",
                prompt=self.prompt,
                output_dir="./output",
                model="gpt-4o", 
                platform="auto", 
                budget=5.0
            )
            res = orch.run() or {}
            
            files = res.get('written_files', [])
            status = "Build Complete"
            if files:
                status += f"\nFiles: {len(files)}"
            else:
                status += "\n(0 Files. See build_debug.log)"
                
            with open("build_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] DONE. Result Keys: {list(res.keys())}\nWritten: {len(files)}\n")

            self.finished_sig.emit(True, status)

        except Exception as e:
            err = str(e)
            with open("build_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] ERROR: {err}\n{traceback.format_exc()}\n")
            self.finished_sig.emit(False, f"Error: {err}")

class GhostTaskWorker(QThread):
    found_sig = pyqtSignal(dict)
    
    def run(self):
        try:
            # Short sleep to let UI render first
            self.msleep(2000)
            
            from creation_engine.orchestrator import CreationEngine
            # Lightweight init
            orch = CreationEngine("GhostCheck", "", model="gpt-4o-mini") 
            task = orch.propose_ghost_task()
            if task:
                self.found_sig.emit(task)
        except Exception as e:
            print(f"DEBUG: GHOST WORKER EXCEPTION: {e}")
            import traceback
            traceback.print_exc()


# ── Window ───────────────────────────────────────────────────

class ChatInput(QTextEdit):
    submit_signal = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.textChanged.connect(self._auto_resize)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit_signal.emit()
            return
        super().keyPressEvent(event)
    def _auto_resize(self):
        """Auto-expand the input pill when text grows."""
        doc_height = int(self.document().size().height()) + 16
        new_h = max(56, min(doc_height, 200))  # 56px min, 200px max
        pill = self.parent()
        if pill and hasattr(pill, 'setFixedHeight'):
            pill.setMinimumHeight(new_h)
            pill.setMaximumHeight(new_h)

class CreatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.heartbeat = None
        self.council_timer = QTimer()
        self.council_timer.setInterval(800)
        
        self.setWindowTitle("Overlord")
        self.resize(1200, 800)
        self.setMinimumSize(600, 500)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # ═══════════════════════════════════════════════════════
        #  SIDEBAR (Minimal — Nav Only)
        # ═══════════════════════════════════════════════════════
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet(f"background:{C['bg_sidebar']}; border-right:1px solid {C['border']};")
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(12,16,12,12)
        sb_layout.setSpacing(8)
        
        # New Chat Button
        btn_new = QPushButton("  ✦  New Chat")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1e1b4b, stop:1 #312e81);
                border-radius:10px; padding:12px 14px; text-align:left;
                color:#c7d2fe; font-weight:600; font-size:13px;
                border: 1px solid rgba(99,102,241,0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #312e81, stop:1 #3730a3);
                border: 1px solid {C['accent']};
            }}
        """)
        btn_new.clicked.connect(self.reset_chat)
        sb_layout.addWidget(btn_new)
        
        sb_layout.addSpacing(10)
        lbl_h = QLabel("  HISTORY")
        lbl_h.setStyleSheet(f"color:{C['text_ghost']}; font-weight:700; font-size:11px; letter-spacing:1px;")
        sb_layout.addWidget(lbl_h)
        
        self.list_hist = QListWidget()
        self.list_hist.addItem("Creative Session")
        sb_layout.addWidget(self.list_hist, 1)

        # Voice Toggle in sidebar
        self.voice_toggle = QPushButton("🔇  Voice Off")
        self.voice_toggle.setCheckable(True)
        self.voice_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_toggle.setStyleSheet(f"""
            QPushButton {{ 
                background: {C['bg_card']}; color: {C['text_dim']}; border: 1px solid {C['border']};
                border-radius: 8px; padding: 8px; font-size: 12px;
            }}
            QPushButton:checked {{ background: #1e3a8a; color: #60a5fa; border-color: #3b82f6; }}
        """)
        self.voice_toggle.toggled.connect(self._toggle_voice)
        sb_layout.addWidget(self.voice_toggle)
        
        # Council IPC State
        self._last_ipc_ts = None
        self._council_messages = []
        self._terminal_buffer = []
        self._terminal_dirty = False
        
        layout.addWidget(self.sidebar)
        
        # ═══════════════════════════════════════════════════════
        #  MAIN CONTENT — Tabbed (Chat / Council / Terminal)
        # ═══════════════════════════════════════════════════════
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)
        
        # ── Tab Widget ────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Tab 1: Chat
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        chat_layout.setContentsMargins(0,0,0,0)
        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat_view)
        self.tabs.addTab(chat_tab, "💬  Chat")
        
        # Tab 2: Council Live Feed
        council_tab = QWidget()
        council_layout = QVBoxLayout(council_tab)
        council_layout.setContentsMargins(12,8,12,8)
        council_layout.setSpacing(8)
        
        # Council Header Bar
        c_header = QHBoxLayout()
        self.council_dot = QLabel("●")
        self.council_dot.setStyleSheet(f"color:{C['success']}; font-size:10px;")
        c_header.addWidget(self.council_dot)
        c_title = QLabel("LIVE COUNCIL FEED")
        c_title.setStyleSheet(f"color:{C['accent']}; font-weight:700; font-size:12px; letter-spacing:1px;")
        c_header.addWidget(c_title)
        c_header.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background:{C['bg_card']}; color:{C['text_dim']}; border:1px solid {C['border']};
                border-radius:6px; padding:4px 12px; font-size:11px; }}
            QPushButton:hover {{ color:{C['danger']}; border-color:{C['danger']}; }}
        """)
        clear_btn.clicked.connect(self._clear_council)
        c_header.addWidget(clear_btn)
        council_layout.addLayout(c_header)
        
        # Council Feed View (full width, no height cap)
        self.council_view = QTextBrowser()
        self.council_view.setOpenExternalLinks(False)
        self.council_view.setStyleSheet(f"""
            QTextBrowser {{
                background: {C['bg_card']}; 
                border: 1px solid {C['border']};
                border-radius: 10px; padding: 12px; font-size: 13px;
                color: {C['text_dim']};
            }}
        """)
        council_layout.addWidget(self.council_view, 1)
        
        # Council Reply Input
        self.council_input = QTextEdit()
        self.council_input.setFixedHeight(38)
        self.council_input.setPlaceholderText("Message the Council...")
        self.council_input.setStyleSheet(f"""
            QTextEdit {{
                background: {C['bg_pill']}; border: 1px solid {C['border']};
                border-radius: 10px; padding: 8px 12px; font-size: 13px;
                color: {C['text']};
            }}
            QTextEdit:focus {{ border: 1px solid {C['accent']}; }}
        """)
        council_layout.addWidget(self.council_input)
        
        self.tabs.addTab(council_tab, "⚡  Council")
        
        # Tab 3: Terminal Output
        terminal_tab = QWidget()
        terminal_layout = QVBoxLayout(terminal_tab)
        terminal_layout.setContentsMargins(12,8,12,8)
        
        t_header = QHBoxLayout()
        t_title = QLabel("SYSTEM TERMINAL")
        t_title.setStyleSheet(f"color:{C['success']}; font-weight:700; font-size:12px; letter-spacing:1px;")
        t_header.addWidget(t_title)
        t_header.addStretch()
        
        clear_term = QPushButton("Clear")
        clear_term.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_term.setStyleSheet(f"""
            QPushButton {{ background:{C['bg_card']}; color:{C['text_dim']}; border:1px solid {C['border']};
                border-radius:6px; padding:4px 12px; font-size:11px; }}
            QPushButton:hover {{ color:{C['danger']}; border-color:{C['danger']}; }}
        """)
        clear_term.clicked.connect(lambda: (self._terminal_buffer.clear(), self._render_terminal()))
        t_header.addWidget(clear_term)
        terminal_layout.addLayout(t_header)
        
        self.terminal_view = QTextBrowser()
        self.terminal_view.setStyleSheet(f"""
            QTextBrowser {{
                background: #050508; 
                border: 1px solid {C['border']};
                border-radius: 10px; padding: 12px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px; color: {C['success']};
            }}
        """)
        terminal_layout.addWidget(self.terminal_view, 1)
        
        self.tabs.addTab(terminal_tab, "🖥  Terminal")
        
        # Tab 4: Project Chronicle
        chronicle_tab = QWidget()
        chronicle_layout = QVBoxLayout(chronicle_tab)
        chronicle_layout.setContentsMargins(12,8,12,8)
        
        c_head = QHBoxLayout()
        c_title = QLabel("PROJECT CHRONICLE")
        c_title.setStyleSheet(f"color:{C['accent']}; font-weight:700; font-size:12px; letter-spacing:1px;")
        c_head.addWidget(c_title)
        c_head.addStretch()
        chronicle_layout.addLayout(c_head)
        
        self.chronicle_view = QTextBrowser()
        self.chronicle_view.setStyleSheet(f"""
            QTextBrowser {{
                background: {C['bg_card']}; border: 1px solid {C['border']};
                border-radius: 10px; padding: 12px; font-size: 13px;
                color: {C['text_dim']};
            }}
        """)
        chronicle_layout.addWidget(self.chronicle_view, 1)
        self.tabs.addTab(chronicle_tab, "📜  Chronicle")
        
        content_layout.addWidget(self.tabs, 1)
        
        # ── Status Ticker Bar ─────────────────────────────────
        self.status_ticker = QFrame()
        self.status_ticker.setObjectName("StatusTicker")
        self.status_ticker.setFixedHeight(32)
        ticker_layout = QHBoxLayout(self.status_ticker)
        ticker_layout.setContentsMargins(16, 0, 16, 0)
        
        self.ticker_dot = QLabel("●")
        self.ticker_dot.setStyleSheet(f"color:{C['success']}; font-size:8px;")
        ticker_layout.addWidget(self.ticker_dot)
        
        self.ticker_label = QLabel("Council: Waiting for activity...")
        self.ticker_label.setStyleSheet(f"color:{C['text_dim']}; font-size:11px;")
        ticker_layout.addWidget(self.ticker_label, 1)
        
        self.ticker_tab_btn = QPushButton("View ⚡")
        self.ticker_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ticker_tab_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{C['accent']}; border:none; font-size:11px; font-weight:600; }}
            QPushButton:hover {{ color:#a5b4fc; }}
        """)
        self.ticker_tab_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        ticker_layout.addWidget(self.ticker_tab_btn)
        
        content_layout.addWidget(self.status_ticker)
        
        # ── Input Area ────────────────────────────────────────
        input_wrapper = QWidget()
        input_wrapper.setFixedHeight(120)
        iw_layout = QVBoxLayout(input_wrapper)
        iw_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        iw_layout.setContentsMargins(0, 8, 0, 0)
        
        # Ghost Token
        self.ghost_btn = QPushButton("👻  Ghost has a suggestion...")
        self.ghost_btn.setObjectName("GhostBtn")
        self.ghost_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ghost_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['bg_card']}; color: {C['accent']}; 
                border: 1px solid rgba(99,102,241,0.2);
                border-radius: 16px; padding: 8px 20px; font-size: 13px; font-style: italic;
            }}
            QPushButton:hover {{ background-color: #1e1b4b; border-color: {C['accent']}; }}
        """)
        self.ghost_btn.hide()
        self.ghost_btn.clicked.connect(self.accept_ghost_task)
        iw_layout.addWidget(self.ghost_btn)

        # Input Pill
        self.pill = QFrame()
        self.pill.setObjectName("InputPill")
        self.pill.setMaximumWidth(800)
        self.pill.setMinimumHeight(56)
        self.pill.setMaximumHeight(56)
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(20, 4, 8, 4)
        
        self.input_field = ChatInput()
        self.input_field.setObjectName("ChatInput")
        self.input_field.setPlaceholderText("What should we create?")
        self.input_field.submit_signal.connect(self.send_msg)
        pill_layout.addWidget(self.input_field)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setObjectName("SendBtn")
        self.btn_send.setFixedSize(40, 40)
        self.btn_send.clicked.connect(self.send_msg)
        pill_layout.addWidget(self.btn_send)
        
        iw_layout.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Footer
        ft = QLabel("Overlord · Autonomous Creation Engine")
        ft.setStyleSheet(f"color:{C['text_ghost']}; font-size:11px; margin-top:4px;")
        ft.setAlignment(Qt.AlignmentFlag.AlignCenter)
        iw_layout.addWidget(ft)
        
        content_layout.addWidget(input_wrapper)
        layout.addWidget(content, 1)
        
        self.setStyleSheet(STYLESHEET)
        
        # Logic State
        self.history = [] # Committed messages [(role, text)]
        self.streaming_full = "" # Full text from LLM
        self.streaming_visible = "" # What is shown (smoothing)
        self.is_streaming = False
        
        # Smooth Typing Timer
        self.smooth_timer = QTimer()
        self.smooth_timer.setInterval(40) # Slower (40ms) for smoother rendering
        self.smooth_timer.timeout.connect(self.update_smooth_type)
        
        # Awareness Timer (Sense & Timeline)
        self.awareness_timer = QTimer()
        self.awareness_timer.setInterval(5000) # Every 5 seconds
        self.awareness_timer.timeout.connect(self._update_awareness)
        self.awareness_timer.start()
        
        # Council Polling Timer
        self.council_timer = QTimer()
        self.council_timer.setInterval(800)
        
        # Terminal Flush Timer (fast, main-thread only)
        self._terminal_flush_timer = QTimer()
        self._terminal_flush_timer.setInterval(500)
        self._terminal_flush_timer.timeout.connect(self._flush_terminal)
        self._terminal_flush_timer.start()
        
        # Initial Chronicle Entry
        chronicler.log_event("overlord_studio", "SEED", "SYSTEM_BOOT", "Overlord Studio V2 initialized with Environmental & Temporal Awareness.")
        
        
        self.set_welcome()
        
        
        # ── Heartbeat Integration ────────────────────────────────────
        try:
            from creation_engine.heartbeat_daemon import HeartbeatDaemon
            self.heartbeat = HeartbeatDaemon(inactivity_threshold_minutes=30, project_path=".")
            self.heartbeat.start()
            print("  [OK] Heartbeat Daemon Integrated & Started.")
        except Exception as e:
            print(f"  [!!] Heartbeat Init Failed: {e}")
            self.heartbeat = None
            import traceback
            traceback.print_exc()

        # ── Council IPC Polling ──────────────────────────────────────
        # Council IPC Polling
        self.council_timer.timeout.connect(self.poll_council)
        self.council_timer.start()
        
        # Wire council reply (Enter key in council input)
        self.council_input.installEventFilter(self)

        # ══════════════════════════════════════════════════════════
        #  UNIFIED BOOT SEQUENCE — All daemons start here
        # ══════════════════════════════════════════════════════════
        
        # Redirect stdout to Terminal tab
        import io
        _orig_stdout = sys.stdout
        class _TerminalTee(io.TextIOBase):
            def __init__(tee_self):
                tee_self._orig = _orig_stdout
            def write(tee_self, text):
                if text.strip():
                    try:
                        self.log_to_terminal(text.rstrip())
                    except Exception:
                        pass
                try:
                    tee_self._orig.write(text)
                except Exception:
                    pass
                return len(text)
            def flush(tee_self):
                try:
                    tee_self._orig.flush()
                except Exception:
                    pass
            def fileno(tee_self):
                try: return tee_self._orig.fileno()
                except: return 1
            def isatty(tee_self):
                try: return tee_self._orig.isatty()
                except: return False

        sys.stdout = _TerminalTee()
        
        # 1. Council Agents
        self._council_threads = []
        try:
            from council_agents import boot_council
            self._council_threads = boot_council(project_root=".")
            print("  [OK] Council Agents")
        except Exception as e:
            print(f"  [!!] Council Agents: {e}")

        # 2. Sentinel Daemon (Log monitoring + Memory Evolution)
        self._sentinel_thread = None
        try:
            from sentinel import SentinelDaemon
            import threading
            self._sentinel = SentinelDaemon()
            self._sentinel_thread = threading.Thread(
                target=self._sentinel.run, daemon=True, name="Sentinel"
            )
            self._sentinel_thread.start()
            print("  [OK] Sentinel Daemon")
        except Exception as e:
            print(f"  [!!] Sentinel: {e}")

        # 3. Heartbeat Daemon (Dreaming / Background Thought)
        self._heartbeat_thread = None
        try:
            from heartbeat_daemon import main as heartbeat_main
            import threading
            self._heartbeat_thread = threading.Thread(
                target=heartbeat_main, daemon=True, name="Heartbeat"
            )
            self._heartbeat_thread.start()
            print("  [OK] Heartbeat Daemon")
        except Exception as e:
            print(f"  [!!] Heartbeat: {e}")

        # 4. Autonomous Engine (Self-improvement when idle)
        self._autonomous_daemon = None
        try:
            from autonomous_engine import boot_autonomous
            self._autonomous_daemon = boot_autonomous(project_root=".")
            print("  [OK] Autonomous Engine")
        except Exception as e:
            print(f"  [!!] Autonomous Engine: {e}")

        # 5. Sovereign Link (Telegram Bridge)
        self._telegram_bridge = None
        try:
            from telegram_bridge import TelegramBridge
            import os
            if os.getenv("TELEGRAM_BOT_TOKEN"):
                self._telegram_bridge = TelegramBridge()
                self._telegram_bridge.run_in_thread()
                print("  [OK] Sovereign Link (Telegram)")
            else:
                print("  [--] Sovereign Link: No token — skipped")
        except Exception as e:
            print(f"  [!!] Sovereign Link: {e}")

        print("  === BOOT COMPLETE ===\n")



    def poll_council(self):
        """Poll the IPC bus for new agent messages."""
        try:
            import agent_ipc as ipc
            messages = ipc.read_recent(30, after=self._last_ipc_ts)
            if messages:
                self._last_ipc_ts = messages[-1].get("ts")
                self._council_messages.extend(messages)
                # Keep only last 50
                self._council_messages = self._council_messages[-50:]
                self.render_council()
        except Exception:
            pass

    def _clear_council(self):
        """Clear council messages from memory and view."""
        self._council_messages = []
        self.council_view.clear()
        self.council_view.setHtml(f'<div style="color:#52525b; text-align:center; padding:20px;">Council feed cleared</div>')

    def render_council(self):
        """Render the council chat view with premium aesthetics."""
        try:
            import agent_ipc as ipc
            import html
        except ImportError:
            return
        
        type_styles = {
            "FLAG":           {"icon": "🚨", "label": "CRITICAL", "bg": "rgba(239,68,68,0.15)",  "border": "#f87171", "text": "#fecaca"},
            "PROPOSE":        {"icon": "💡", "label": "PROPOSAL", "bg": "rgba(251,191,36,0.12)",  "border": "#fbbf24", "text": "#fef3c7"},
            "RESOLVE":        {"icon": "✅", "label": "RESOLVED", "bg": "rgba(52,211,153,0.12)",  "border": "#34d399", "text": "#d1fae5"},
            "STATUS":         {"icon": "📡", "label": "STATUS",   "bg": "rgba(99,102,241,0.10)",  "border": "#818cf8", "text": "#e0e7ff"},
            "IMAGE":          {"icon": "📸", "label": "SIGHT",    "bg": "rgba(34,197,94,0.12)",   "border": "#4ade80", "text": "#dcfce7"},
            "DREAM":          {"icon": "💭", "label": "DREAM",    "bg": "rgba(168,85,247,0.12)",  "border": "#a855f7", "text": "#f3e8ff"},
            "HUMAN_OVERRIDE":  {"icon": "👤", "label": "CREATOR",  "bg": "rgba(96,165,250,0.15)",  "border": "#60a5fa", "text": "#dbeafe"},
        }
        
        # Base styles
        html_code = f"""
        <style>
            .msg-block {{
                margin: 10px 0;
                padding: 12px 16px;
                border-radius: 12px;
                background: {C['bg_card']};
                border: 1px solid {C['border']};
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }}
            .agent-name {{
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}
            .msg-type {{
                font-size: 9px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 4px;
                margin-left: 8px;
                background: rgba(255,255,255,0.05);
            }}
            .timestamp {{
                color: {C['text_ghost']};
                font-size: 10px;
                font-family: 'Cascadia Code', monospace;
            }}
            .content {{
                color: #e2e2e8;
                font-size: 13px;
                line-height: 1.5;
                white-space: pre-wrap;
            }}
        </style>
        <div style="font-family:'Segoe UI', system-ui, sans-serif;">
        """
        
        # Use more messages for better scroll-back
        recent_msgs = self._council_messages[-40:]
        
        for msg in recent_msgs:
            agent_id = msg.get("from", "unknown")
            agent = ipc.get_agent_info(agent_id)
            mtype = msg.get("type", "STATUS")
            style = type_styles.get(mtype, {"icon": "💬", "label": mtype, "bg": "rgba(255,255,255,0.05)", "border": C['border'], "text": C['text']})
            
            ts = msg.get("ts", "")
            time_str = ts[11:19] if len(ts) > 18 else ts[-8:]
            
            # Content cleaning & Path detection
            raw_content = msg.get("content", "")
            display_content = html.escape(raw_content)
            
            # Auto-link file paths and handle images
            if mtype == "IMAGE":
                import re
                path_match = re.search(r'([A-Za-z]:\\[\w\s\-\.\\]+\.png|/[\w\s\-\./]+\.png)', raw_content)
                if path_match:
                    p = path_match.group(0).replace('\\', '/')
                    img_html = f'<div style="margin-top:10px;"><img src="file:///{p}" width="100%" style="border-radius:8px; border:1px solid {style["border"]};"></div>'
                    display_content = display_content.replace(html.escape(path_match.group(0)), img_html)

            html_code += f'''
            <div class="msg-block" style="border-left: 4px solid {style['border']}; background: {style['bg']};">
                <div class="header">
                    <div>
                        <span class="agent-name" style="color:{agent['color']};">{agent['icon']} {agent['name']}</span>
                        <span class="msg-type" style="color:{style['text']}; border: 1px solid {style['border']}33;">{style['label']}</span>
                    </div>
                    <span class="timestamp">{style['icon']} {time_str}</span>
                </div>
                <div class="content">{display_content}</div>
            </div>'''
        
        if not recent_msgs:
            html_code += f'''
            <div style="text-align:center; padding:60px 20px; color:{C['text_ghost']};">
                <div style="font-size:48px; margin-bottom:15px; opacity:0.3;">📡</div>
                <div style="font-size:14px; font-weight:600; letter-spacing:1px;">COUNCIL LINK ESTABLISHED</div>
                <div style="font-size:11px; margin-top:8px; opacity:0.6;">Monitoring neural broadcast for agent activity...</div>
            </div>'''
            
        html_code += "</div>"
        
        # Save scroll position state check
        vbar = self.council_view.verticalScrollBar()
        at_bottom = vbar.value() >= (vbar.maximum() - 20)
        
        self.council_view.setHtml(html_code)
        
        if at_bottom or not self._last_ipc_ts:
            # Use QTimer to allow layout to settle before scrolling
            QTimer.singleShot(0, lambda: vbar.setValue(vbar.maximum()))

        # Update status ticker
        if self._council_messages:
            last = self._council_messages[-1]
            last_agent = ipc.get_agent_info(last.get("from", "Agent"))
            preview = last.get("content", "")[:90].replace("\n", " ")
            self.ticker_label.setText(f"{last_agent['icon']} {last_agent['name']}: {preview}...")
            self.ticker_dot.setStyleSheet(f"color:{C['success']}; font-size:8px;")
        else:
            self.ticker_label.setText("Council: Idle. Monitoring internal link...")
            self.ticker_dot.setStyleSheet(f"color:{C['text_ghost']}; font-size:8px;")

    def send_council_msg(self):
        """Send a human message to the council IPC."""
        text = self.council_input.toPlainText().strip()
        if not text:
            return
        try:
            import agent_ipc as ipc
            ipc.post("human", ipc.MessageType.HUMAN, text)
            self.council_input.clear()
            self.poll_council()  # Immediately refresh
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Capture Enter in council input to send message."""
        if obj == self.council_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers():
                self.send_council_msg()
                return True
        return super().eventFilter(obj, event)

    def event(self, event):
        try:
            # Global activity tracker
            if self.heartbeat and event.type() in (Qt.EventType.KeyPress, Qt.EventType.MouseMove, Qt.EventType.MouseButtonPress):
                self.heartbeat.update_activity()
        except Exception:
            pass # Ignore event errors to prevent crash
        return super().event(event)

    def _toggle_voice(self, checked):
        """Enable or disable voice feedback."""
        if checked:
            self.voice_toggle.setText("🔊  Voice On")
            voice_service.set_enabled(True)
            boot_voice_agent()
            voice_service.speak("Voice protocols engaged.", voice="af_heart")
        else:
            self.voice_toggle.setText("🔇  Voice Off")
            voice_service.set_enabled(False)
            stop_voice_agent()

    def _toggle_council_size(self, checked):
        """Switch to council tab when toggled."""
        self.tabs.setCurrentIndex(1)  # Switch to Council tab

    def log_to_terminal(self, text):
        """Append text to the terminal buffer (thread-safe, no GUI calls)."""
        import time as _time
        ts = _time.strftime("%H:%M:%S")
        self._terminal_buffer.append(f"[{ts}] {text}")
        if len(self._terminal_buffer) > 500:
            self._terminal_buffer = self._terminal_buffer[-300:]
        self._terminal_dirty = True

    def _flush_terminal(self):
        """Called by timer on main thread — safe to update GUI."""
        if self._terminal_dirty:
            self._terminal_dirty = False
            self._render_terminal()

    def _render_terminal(self):
        """Render terminal output."""
        lines = self._terminal_buffer[-200:]
        html = f'<pre style="color:{C["success"]}; font-family:Cascadia Code,Consolas,monospace; font-size:12px; margin:0;">'
        for line in lines:
            # Color code certain patterns
            if '[OK]' in line:
                line = line.replace('[OK]', '<span style="color:#34d399;">[OK]</span>')
            elif '[!!]' in line or 'ERROR' in line:
                line = line.replace('[!!]', '<span style="color:#f87171;">[!!]</span>')
                line = f'<span style="color:#f87171;">{line}</span>'
            elif '[--]' in line:
                line = line.replace('[--]', '<span style="color:#fbbf24;">[--]</span>')
            html += line + '\n'
        html += '</pre>'
        self.terminal_view.setHtml(html)
        sb = self.terminal_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event):
        if self.heartbeat:
            self.heartbeat.stop()
        try:
            from council_agents import stop_council
            stop_council()
            stop_voice_agent()
        except Exception:
            pass
        super().closeEvent(event)

    def set_welcome(self):
        # Retrieve latest dream for the welcome message
        dream_html = ""
        try:
            if os.path.exists("engine_memory.json"):
                import json
                with open("engine_memory.json", "r") as f:
                    mem = json.load(f)
                    dreams = mem.get("dream_log", [])
                    if dreams:
                        last = dreams[-1]
                        time_str = last.get('timestamp', '')[11:16]
                        dream_html = f"""
                        <div style='margin-top:20px; font-size:14px; color:{C['accent']}; font-style:italic;'>
                            ✨ While you were away (at {time_str}):<br>
                            "{last.get('thought')}"
                        </div>
                        """
        except: pass

        self.chat_view.setHtml(f"""
            <div style='text-align:center; margin-top:15vh; color:{C['text_dim']};'>
                <div style='font-size:56px; margin-bottom:16px;'>⚛️</div>
                <div style='font-size:24px; font-weight:500; color:{C['text']};'>Welcome Home, Creator.</div>
                <div style='font-size:16px; margin-top:8px;'>Ready to build something amazing?</div>
                {dream_html}
            </div>
        """)
        
        # Trigger Ghost Task Search
        self.ghost_worker = GhostTaskWorker()
        self.ghost_worker.found_sig.connect(self.on_ghost_task)
        self.ghost_worker.start()

    def on_ghost_task(self, task):
        self.pending_ghost_task = task
        self.ghost_btn.setText(f"👻 Suggested: {task['title']}")
        self.ghost_btn.show()

    def accept_ghost_task(self):
        if not hasattr(self, 'pending_ghost_task'): return
        
        task = self.pending_ghost_task
        prompt = f"Executing Ghost Task: {task['title']}\n\n{task['description']}"
        self.input_field.setText(prompt)
        self.ghost_btn.hide()
        # Optional: Auto-submit? No, let user confirm.
        self.input_field.setFocus()


    def reset_chat(self):
        self.history = []
        self.set_welcome()

    def send_msg(self, text=None):
        if text is None:
            text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        # Sense Layer: Log activity
        workflow_steward.log_activity("chat_request", {"text": text})
        
        self.input_field.clear()
        
        if self.heartbeat:
            self.heartbeat.update_activity()
            
        if not self.history: self.chat_view.clear()
        
        self.history.append(("user", text))
        self.render_chat()
        
        if self.detect_intent(text) == "BUILD":
            self.start_build(text)
        else:
            self.start_chat(text)

    def detect_intent(self, text):
        t = text.lower()
        if any(t.startswith(x) for x in ["create", "build", "generate"]) and len(t) > 10:
            return "BUILD"
        return "CHAT"

    def start_chat(self, text):
        self.streaming_full = ""
        self.streaming_visible = ""
        self.is_streaming = True
        
        self.worker = ChatWorker(text, history=self.history)
        self.worker.chunk_sig.connect(self.on_chunk)
        self.worker.finished_sig.connect(self.on_finished)
        self.worker.start()
        
        self.smooth_timer.start()
        self.set_busy(True)

    def on_chunk(self, chunk):
        self.streaming_full += chunk
        # Timer will catch up

    def update_smooth_type(self):
        # Move visible cursor towards full
        if len(self.streaming_visible) < len(self.streaming_full):
            # Gentle catch-up if falling behind
            diff = len(self.streaming_full) - len(self.streaming_visible)
            step = 1 if diff < 10 else (2 if diff < 40 else 3)
            
            self.streaming_visible += self.streaming_full[len(self.streaming_visible):len(self.streaming_visible)+step]
            self.render_chat()
        
        # Stop timer if done
        if not self.is_streaming and len(self.streaming_visible) >= len(self.streaming_full):
            self.smooth_timer.stop()
            # Commit to history
            self.history.append(("assistant", self.streaming_full))
            self.streaming_visible = ""
            self.streaming_full = ""
            self.render_chat() # Final render from history
            self.set_busy(False)

    def on_finished(self):
        self.is_streaming = False
        # Timer continues until visible catches up

    def start_build(self, text):
        self.history.append(("system", "🔨 **Build Process Started...**"))
        self.render_chat()
        self.set_busy(True)
        self.b_worker = BuildWorker(text)
        self.b_worker.finished_sig.connect(self.on_build_done)
        self.b_worker.start()

    def on_build_done(self, success, msg):
        role = "system" if success else "error"
        self.history.append((role, msg))
        self.render_chat()
        self.set_busy(False)

    def set_busy(self, busy):
        self.input_field.setPlaceholderText("Thinking..." if busy else "Message Overlord...")
        self.btn_send.setEnabled(not busy)

    def render_chat(self):
        html = f"""
        <style>
            body {{ font-family:'Segoe UI Emoji', 'Segoe UI', sans-serif; }}
            code {{ background:#27272a; padding:2px 5px; border-radius:4px; font-family:Consolas; font-size:14px; white-space: pre-wrap; }}
            pre {{ background:#18181b; padding:15px; border-radius:10px; border:1px solid #27272a; white-space: pre-wrap; }}
            blockquote {{ border-left: 3px solid {C['accent']}; margin:0; padding-left:15px; color:{C['text_dim']}; }}
            a {{ color: {C['accent']}; text-decoration: none; }}
            p {{ margin-bottom: 10px; line-height: 1.6; }}
            ul, ol {{ margin-bottom: 10px; padding-left: 20px; }}
        </style>
        <div style='max-width:850px; margin:0 auto; padding-bottom:40px;'>
        """
        
        # Render History
        for role, text in self.history:
            html += self.make_bubble(role, text)
            
        # Render Streaming Buffer (if any)
        if self.streaming_visible or (self.is_streaming and not self.streaming_visible):
             if self.streaming_visible:
                 html += self.make_bubble("assistant", self.streaming_visible)
        
        html += "</div>"
        
        # Smart Scroll: Only scroll if we were already near bottom OR likely streaming new content
        sb = self.chat_view.verticalScrollBar()
        was_bottom = sb.value() >= (sb.maximum() - 50)
        
        self.chat_view.setHtml(html)
        
        if was_bottom or self.is_streaming:
            # self.chat_view.moveCursor(QTextCursor.MoveOperation.End) # Often better than scrollbar
            sb.setValue(sb.maximum())

    def make_bubble(self, role, text):
        content = markdown.markdown(text) if HAS_MARKDOWN else text.replace("\n", "<br>")
        
        if role == "user":
            return f"""
            <div style='display:flex; justify-content:flex-end; margin-bottom:24px;'>
                <div style='background:{C["user_msg"]}; padding:12px 20px; border-radius:24px; color:#f4f4f5; font-size:16px; line-height:1.6;'>
                    {content}
                </div>
            </div>
            """
        elif role == "assistant":
            return f"""
            <div style='display:flex; margin-bottom:24px;'>
                <div style='width:36px; margin-right:16px; font-size:24px;'>⚛️</div>
                <div style='flex:1; color:{C["text"]}; line-height:1.6; font-size:16px;'>
                    {content}
                </div>
            </div>
            """
        elif role == "system":
            return f"<div style='text-align:center; color:#71717a; margin:15px; font-style:italic;'>{content}</div>"
        else:
            return f"<div style='text-align:center; color:#ef4444; margin:15px;'>{content}</div>"



    def _update_awareness(self):
        """Update Sense and Timeline layers in the GUI."""
        self._render_chronicle()
        self._update_projections()
        # Flush terminal buffer on main thread (thread-safe rendering)
        if getattr(self, '_terminal_dirty', False):
            self._terminal_dirty = False
            self._render_terminal()

    def _render_chronicle(self):
        """Render the project history on the Chronicle tab."""
        # Get active project or recent events
        history = chronicler.get_history(chronicler.get_latest_project_id() or "default")
        if not history:
            self.chronicle_view.setHtml('<div style="color:#52525b; text-align:center; padding:20px;">No chronicles found on this timeline yet.</div>')
            return

        html = '<div style="font-family:Segoe UI, sans-serif; padding:10px;">'
        for entry in history[-20:]:  # Last 20 events
            ts = entry['ts'].split('T')[1].split('.')[0]
            stage = entry['stage']
            stage_color = C['accent'] if stage == 'EXPORT' else C['success'] if stage == 'FINAL' else C['text_dim']
            
            html += f"""
            <div style="margin-bottom:12px; border-left:2px solid {stage_color}; padding-left:12px;">
                <div style="color:{C['text_ghost']}; font-size:10px;">{ts} — {stage}</div>
                <div style="color:{C['text']}; font-size:13px; font-weight:600;">{entry['event']}</div>
                <div style="color:{C['text_dim']}; font-size:12px;">{entry['content']}</div>
            </div>
            """
        html += '</div>'
        self.chronicle_view.setHtml(html)

    def _update_projections(self):
        """Check hardware and storage and update ticker if critical."""
        from creation_engine.hardware_steward import HardwareSteward
        steward = HardwareSteward()
        
        # Sense Check
        if steward.is_pressured():
            self.ticker_dot.setStyleSheet(f"color:{C['warning']}; font-size:8px;")
            self.ticker_label.setText(" Sense Layer: GPU Pressure detected. Throttling background tasks.")
            self.ticker_label.setStyleSheet(f"color:{C['warning']}; font-size:11px;")
        else:
            # Timeline Check (Storage)
            proj = projector.project_storage()
            if proj['status'] != "HEALTHY":
                self.ticker_dot.setStyleSheet(f"color:{C['danger']}; font-size:8px;")
                self.ticker_label.setText(f" Timeline Projection: {proj['prediction']}")
                self.ticker_label.setStyleSheet(f"color:{C['danger']}; font-size:11px;")
            else:
                self.ticker_dot.setStyleSheet(f"color:{C['success']}; font-size:8px;")
                self.ticker_label.setStyleSheet(f"color:{C['text_dim']}; font-size:11px;")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = CreatorWindow()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        with open("crash.log", "w") as f:
            f.write(traceback.format_exc())
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
