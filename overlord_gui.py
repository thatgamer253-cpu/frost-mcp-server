#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  OVERLORD — PyQt6 Desktop Build Console  (Full-Feature)
  Run:  python overlord_gui.py
  Requires: pip install PyQt6
══════════════════════════════════════════════════════════════
"""

import sys, os, json, time, zipfile, io, traceback, shutil
from datetime import datetime
from pathlib import Path
import subprocess

# Windows-specific: suppress console windows for background processes
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox,
    QPushButton, QLabel, QSlider, QCheckBox, QFrame, QSplitter,
    QScrollArea, QFileDialog, QTabWidget, QProgressBar, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QSpacerItem, QSizePolicy,
    QMessageBox, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize,
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPalette,
)


# ── PyInstaller Resource Path ────────────────────────────────

# ── Interaction Hub (for GUI feed) ───────────────────────────
try:
    from interaction_hub import InteractionHub, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ACTION, SEVERITY_VERDICT
    _GUI_HAS_HUB = True
except ImportError:
    _GUI_HAS_HUB = False

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource — works in dev and inside PyInstaller .exe."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Ensure creation_engine is importable from the bundled path
_SCRIPT_DIR = get_resource_path(".")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)



# ── Palette (Emotional/Playful Cyber-Pop) ────────────────────
C = {
    "bg":          "#1e1b4b",  # Deep Indigo
    "bg_card":     "#2e1065",  # Deep Violet
    "bg_hover":    "#4c1d95",  # Violet Card
    "bg_input":    "#312e81",  # Dark Blue-Purple
    "accent":      "#d946ef",  # Electric Purple (Fuschia)
    "accent_dim":  "#a21caf",  # Darker Fuschia
    "accent_glow": "rgba(217, 70, 239, 0.5)",
    "success":     "#4ade80",  # Neon Green
    "warning":     "#facc15",  # Neon Yellow
    "error":       "#fb7185",  # Soft Red
    "info":        "#22d3ee",  # Cyan
    "text":        "#ffffff",
    "text_dim":    "#e9d5ff",  # Light Purple
    "text_muted":  "#c4b5fd",  # Pale Purple
    "border":      "#5b21b6",  # Violet Border
    "border_lt":   "#7c3aed",  # Lighter Violet
}
MONO = "Consolas" if sys.platform == "win32" else "JetBrains Mono"

STYLESHEET = f"""
QMainWindow, QWidget {{ background:{C["bg"]}; color:{C["text"]}; font-family:'Segoe UI','Inter',sans-serif; font-size:13px; }}
QLabel {{ color:{C["text"]}; background:transparent; }}
QLineEdit, QTextEdit, QPlainTextEdit {{
    background:{C["bg_input"]}; color:{C["text"]}; border:2px solid {C["border"]};
    border-radius:12px; padding:10px 14px; selection-background-color:{C["accent"]};
}}
QLineEdit:focus, QTextEdit:focus {{ border-color:{C["accent"]}; background:{C["bg_hover"]}; }}
QComboBox {{
    background:{C["bg_card"]}; color:{C["text"]}; border:2px solid {C["border"]};
    border-radius:12px; padding:8px 14px; min-height:32px; font-weight:bold;
}}
QComboBox::drop-down {{ border:none; width:30px; }}
QComboBox QAbstractItemView {{ background:{C["bg_card"]}; color:{C["text"]}; border:2px solid {C["border"]}; selection-background-color:{C["accent_dim"]}; }}
QPushButton {{
    background:{C["bg_card"]}; color:{C["text"]}; border:2px solid {C["border"]};
    border-radius:12px; padding:8px 20px; font-weight:700; min-height:36px;
}}
QPushButton:hover {{ background:{C["bg_hover"]}; border-color:{C["accent"]}; }}
QPushButton:pressed {{ background:{C["accent_dim"]}; }}
QPushButton#buildBtn {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {C["accent"]}, stop:1 #8b5cf6);
    color:white; border:none; font-size:16px; font-weight:800; min-height:50px; border-radius:16px;
}}
QPushButton#buildBtn:hover {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #f472b6, stop:1 #a78bfa); }}
QPushButton#buildBtn:disabled {{ background:{C["bg_card"]}; color:{C["text_muted"]}; }}
QPushButton#actionBtn {{
    background:{C["accent_dim"]}; color:white; border:none; border-radius:10px;
    font-weight:700; padding:8px 18px;
}}
QPushButton#actionBtn:hover {{ background:{C["accent"]}; }}
QSlider::groove:horizontal {{ border:none; height:8px; background:{C["bg_input"]}; border-radius:4px; }}
QSlider::handle:horizontal {{ background:{C["success"]}; width:20px; height:20px; margin:-6px 0; border-radius:10px; border:2px solid {C["bg"]}; }}
QSlider::sub-page:horizontal {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C["accent"]}, stop:1 {C["info"]}); border-radius:4px; }}
QCheckBox {{ color:{C["text_dim"]}; spacing:10px; font-weight:600; }}
QCheckBox::indicator {{ width:22px; height:22px; border-radius:6px; border:2px solid {C["border"]}; background:{C["bg_input"]}; }}
QCheckBox::indicator:checked {{ background:{C["success"]}; border-color:{C["success"]}; }}
QTabWidget::pane {{ border:2px solid {C["border"]}; border-radius:16px; background:{C["bg"]}; top:-2px; }}
QTabBar::tab {{
    background:{C["bg_card"]}; color:{C["text_muted"]}; border:2px solid {C["border"]};
    border-bottom:none; padding:10px 24px; margin-right:4px;
    border-top-left-radius:12px; border-top-right-radius:12px; font-weight:700;
}}
QTabBar::tab:selected {{ background:{C["bg"]}; color:{C["accent"]}; border-bottom:3px solid {C["accent"]}; }}
QTabBar::tab:hover {{ color:{C["text"]}; background:{C["bg_hover"]}; }}
QProgressBar {{ border:none; border-radius:8px; background:{C["bg_input"]}; height:14px; text-align:center; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C["accent"]}, stop:1 {C["info"]}); border-radius:8px; }}
QScrollBar:vertical {{ background:{C["bg"]}; width:10px; border-radius:5px; }}
QScrollBar::handle:vertical {{ background:{C["border"]}; border-radius:5px; min-height:40px; }}
QScrollBar::handle:vertical:hover {{ background:{C["accent_dim"]}; }}
QTreeWidget {{ background:{C["bg_input"]}; border:2px solid {C["border"]}; border-radius:12px; color:{C["text"]}; alternate-background-color:{C["bg_card"]}; }}
QTreeWidget::item {{ padding:6px 10px; }}
QTreeWidget::item:selected {{ background:{C["accent_dim"]}; border-radius:6px; }}
"""


class GamificationEngine:
    """Tracks XP, Level, Streak, and Ranks."""
    RANKS = [
        (0, "Script Kiddie"), (500, "Novice Coder"), (1200, "Junior Dev"),
        (2500, "Full-Stack Warrior"), (5000, "Senior Architect"), (10000, "Code Wizard"),
        (25000, "Overlord"), (50000, "Singularity")
    ]
    
    def __init__(self):
        self.save_file = Path("user_save_data.json")
        self.data = self._load()
        
    def _load(self):
        if self.save_file.exists():
            try:
                with open(self.save_file, "r") as f:
                    return json.load(f)
            except: pass
        return {"xp": 0, "level": 1, "streak": 0, "builds": 0, "last_build": ""}

    def save(self):
        with open(self.save_file, "w") as f:
            json.dump(self.data, f)

    def add_xp(self, amount: int) -> bool:
        """Returns True if leveled up."""
        self.data["xp"] += amount
        self.data["builds"] += 1
        
        # Streak logic
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data["last_build"] != today:
            self.data["streak"] += 1
            self.data["last_build"] = today
            
        # Level logic (Level = Sqrt(XP) / 10 is a simple curve, or strict brackets)
        # Using strict brackets for simplicity: Level N requires N*1000 XP roughly
        new_level = int((self.data["xp"] / 1000) ** 0.8) + 1
        leveled_up = new_level > self.data["level"]
        self.data["level"] = new_level
        self.save()
        return leveled_up

    @property
    def rank(self):
        xp = self.data["xp"]
        title = "Script Kiddie"
        for t, label in self.RANKS:
            if xp >= t: title = label
        return title

    @property
    def xp(self): return self.data["xp"]
    
    @property
    def level(self): return self.data["level"]
    
    @property
    def streak(self): return self.data["streak"]




# ── Consensus Indicator ───────────────────────────────────────
class ConsensusIndicator(QWidget):
    """Visual indicator for agent consensus status."""
    def __init__(self):
        super().__init__()
        self.setFixedWidth(180)
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"background: rgba(0,0,0,0.3); border-radius: 20px; border: 1px solid {C['border']};"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(8)

        self.light = QFrame()
        self.light.setFixedSize(12, 12)
        self.light.setStyleSheet(f"background: {C['warning']}; border-radius: 6px;")
        
        self.label = QLabel("Awaiting Input")
        self.label.setFont(QFont(MONO, 9, QFont.Weight.Bold))
        self.label.setStyleSheet(f"color: {C['text']};")
        
        lay.addWidget(self.light)
        lay.addWidget(self.label)
        lay.addStretch()

        # Animation
        self.anim = QPropertyAnimation(self.light, b"windowOpacity")
        self.anim.setDuration(1000)
        self.anim.setStartValue(0.4)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def set_status(self, state, label):
        self.label.setText(label)
        self.anim.stop()
        self.light.setWindowOpacity(1.0)

        if state == "reached":
            self.light.setStyleSheet(f"background: {C['success']}; border-radius: 6px; box-shadow: 0 0 10px {C['success']};")
            self.anim.start()
        elif state == "debating":
            self.light.setStyleSheet(f"background: {C['warning']}; border-radius: 6px;")
        elif state == "conflict":
            self.light.setStyleSheet(f"background: {C['error']}; border-radius: 6px;")
            # Fast pulse for alert
            self.anim.setDuration(300)
            self.anim.start()
        else:
            self.light.setStyleSheet(f"background: {C['text_muted']}; border-radius: 6px;")

# ═══════════════════════════════════════════════════════════════
#  WIDGETS
# ═══════════════════════════════════════════════════════════════

class BuildTerminal(QPlainTextEdit):
    """Live build log — dark console aesthetic."""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet(
            f"background:{C['bg_input']}; color:{C['text_dim']}; "
            f"border-radius:8px; border:1px solid {C['border_lt']}; padding:8px;"
        )
        self.setFont(QFont(MONO, 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def log(self, message: str, level: str = "INFO"):
        colors = {"INFO": C["info"], "ERROR": C["error"], "WARN": C["warning"],
                  "SUCCESS": C["success"], "SYSTEM": C["accent"]}
        color = colors.get(level, C["text_dim"])
        ts = datetime.now().strftime("%H:%M:%S")
        self.appendHtml(
            f"<span style='color:{C['text_muted']};'>{ts}</span> "
            f"<span style='color:{color}; font-weight:600;'>[{level}]</span> "
            f"<span style='color:{C['text']};'>{message}</span>"
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class StatCard(QFrame):
    """Glassy stat card."""
    def __init__(self, label: str, value: str = "—", color: str = C["text"]):
        super().__init__()
        self.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            f"stop:0 {C['bg_card']}, stop:1 {C['bg_hover']}); "
            f"border:1px solid {C['border']}; border-radius:12px; padding:14px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.val = QLabel(value)
        self.val.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.val.setStyleSheet(f"color:{color}; background:transparent;")
        self.val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc = QLabel(label.upper())
        self.desc.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.desc.setStyleSheet(f"color:{C['text_dim']}; letter-spacing:1px; background:transparent;")
        self.desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.val)
        layout.addWidget(self.desc)

    def set_value(self, v: str, color: str = None):
        self.val.setText(v)
        if color:
            self.val.setStyleSheet(f"color:{color}; background:transparent;")


# ═══════════════════════════════════════════════════════════════
#  ENGINE WORKER
# ═══════════════════════════════════════════════════════════════

class EngineWorker(QThread):
    """Runs CreationEngine.run() off the main thread."""
    log_signal = pyqtSignal(str, str)
    finished   = pyqtSignal(dict)
    progress   = pyqtSignal(int)

    def __init__(self, engine_kwargs: dict, use_legacy: bool = False):
        super().__init__()
        self.kwargs = engine_kwargs
        self.use_legacy = use_legacy
        self._engine = None

    def run(self):
        try:
            from creation_engine.llm_client import add_log_listener
            def _emit(tag, msg):
                self.log_signal.emit(msg, tag)
            add_log_listener(_emit)

            if self.use_legacy:
                self._run_legacy()
            else:
                self._run_creation_engine()
        except Exception as e:
            self.log_signal.emit(f"ENGINE CRASH: {e}", "ERROR")
            self.log_signal.emit(traceback.format_exc(), "ERROR")
            self.finished.emit({"success": False, "error": str(e)})

    def _run_creation_engine(self):
        from creation_engine.orchestrator import CreationEngine
        from creation_engine.llm_client import KeyPool
        KeyPool.reset_all() # Fresh load from Vault + Env
        self.log_signal.emit("Engine initializing…", "SYSTEM")
        self._engine = CreationEngine(**self.kwargs)
        self.progress.emit(10)
        self.log_signal.emit("Pipeline started", "SYSTEM")
        raw = self._engine.run()
        self.progress.emit(100)
        self.finished.emit({
            "success": raw.get("success", False),
            "error": raw.get("error", ""),
            "project_name": raw.get("project_name", ""),
            "project_path": raw.get("project_path", ""),
            "files_written": list(self._engine.written_files.keys()),
            "file_count": raw.get("files_written", 0),
            "run_command": raw.get("run_command", ""),
            "written_files": dict(self._engine.written_files),
        })

    def _run_legacy(self):
        """Fallback: run engine_core.py NexusEngine."""
        from engine_core import NexusEngine
        self.log_signal.emit("Legacy NexusEngine initializing…", "SYSTEM")
        prompt = self.kwargs.pop("prompt", "")
        name = self.kwargs.pop("project_name", "auto_app")
        model = self.kwargs.pop("model", "gemini-2.0-flash")
        output = self.kwargs.pop("output_dir", "./output")
        budget = self.kwargs.pop("budget", 5.0)
        platform = self.kwargs.pop("platform", "python")
        docker = self.kwargs.pop("docker", True)
        scale = self.kwargs.pop("scale", "app")
        max_fix = self.kwargs.pop("max_fix_cycles", 3)

        def _log_cb(tag, msg):
            self.log_signal.emit(msg, tag)

        engine = NexusEngine(
            project_name=name, model=model, output_dir=output,
            budget=budget, platform=platform, use_docker=docker,
            scale=scale, max_retries=max_fix, on_log=_log_cb,
        )
        self.progress.emit(10)
        raw = engine.run_full_build(prompt)
        self.progress.emit(100)
        self.finished.emit({
            "success": bool(raw),
            "project_name": name,
            "project_path": engine.project_dir,
            "files_written": list(engine.written_files.keys()),
            "file_count": len(engine.written_files),
            "run_command": "",
            "written_files": dict(engine.written_files),
        })

    def stop(self):
        if self._engine:
            self._engine.stop()
        self.terminate()
        self.wait()

class OverlordWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OVERLORD — OFFLINE BUILD CONSOLE")
        self.resize(1440, 880)
        self.setMinimumSize(1060, 640)
        self._worker = None
        self._result = None
        self._build_start = None
        
        # Gamification
        self.game = GamificationEngine()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header (Player HUD) ──────────────────────────────
        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet(f"background:{C['bg']}; border-bottom:2px solid {C['border']};")
        hdr = QHBoxLayout(header)
        hdr.setContentsMargins(24, 0, 24, 0)
        
        # Logo Area
        logo_area = QVBoxLayout()
        logo_area.setSpacing(4)
        t = QLabel("🛡️ OVERLORD [OFFLINE]")
        t.setFont(QFont("Segoe UI", 20, QFont.Weight.Black))
        t.setStyleSheet(f"color:{C['success']}; letter-spacing:1px;")
        st = QLabel(f"SECURE OFFLINE COMMAND CENTER • {self.game.rank.upper()}")
        st.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        st.setStyleSheet(f"color:{C['text_muted']}; letter-spacing:2px;")
        logo_area.addStretch()
        logo_area.addWidget(t)
        logo_area.addWidget(st)
        logo_area.addStretch()
        hdr.addLayout(logo_area)
        
        hdr.addStretch()
        
        # HUD Stats
        self.stat_level = StatCard("LEVEL", str(self.game.level), C["info"])
        self.stat_xp = StatCard("XP", f"{self.game.xp:,}", C["accent"])
        self.stat_streak = StatCard("STREAK", f"{self.game.streak}🔥", C["warning"])
        
        # Hardware Aware Stat (premium feel)
        try:
            import subprocess
            cmd = ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]
            vram_raw = int(subprocess.check_output(cmd, creationflags=0x08000000).decode().strip())
            vram_display = f"{round(vram_raw/1024, 1)}GB"
            color = C["success"] if vram_raw >= 8000 else C["warning"]
        except:
            vram_display = "N/A"
            color = C["text_muted"]
            
        self.stat_vram = StatCard("GPU VRAM", vram_display, color)
        self.stat_stability = StatCard("STABILITY", "CHECKING", C["text_muted"])
        self.stat_npu = StatCard("AI BOOST", "DETECTING", C["text_muted"])
        
        self.consensus = ConsensusIndicator()
        
        hdr.addWidget(self.stat_level)
        hdr.addWidget(self.stat_xp)
        hdr.addWidget(self.stat_streak)
        hdr.addWidget(self.stat_vram)
        hdr.addWidget(self.stat_stability)
        hdr.addWidget(self.stat_npu)
        hdr.addWidget(self.consensus)
        
        root.addWidget(header)

        # ── Body ──────────────────────────────────────────────
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        self._build_sidebar(body_lay)

        # Right: Tabbed content
        self.tabs = QTabWidget()
        self._build_tab = self._create_build_tab()
        self._history_tab = self._create_history_tab()
        self._settings_tab = self._create_settings_tab()
        self._vault_tab = self._create_vault_tab()
        self.tabs.addTab(self._build_tab, "🚀 START MISSION")
        self.tabs.addTab(self._history_tab, "📜 LOGS")
        self.tabs.addTab(self._settings_tab, "⚙️ SETTINGS")
        self.tabs.addTab(self._vault_tab, "🔐 KEY VAULT")
        self.tabs.addTab(self._create_logic_vault_tab(), "🧠 LOGIC VAULT")
        self.tabs.addTab(self._create_alchemist_tab(), "⚗️ VRAM ALCHEMIST")
        self._hub_tab = self._create_hub_tab()
        self.tabs.addTab(self._hub_tab, "💬 AGENT HUB")
        body_lay.addWidget(self.tabs, 1)
        root.addWidget(body, 1)

        # ── Status Bar ────────────────────────────────────────
        sbar = QWidget()
        sbar.setFixedHeight(32)
        sbar.setStyleSheet(f"background:{C['bg_input']}; border-top:2px solid {C['border']};")
        sb = QHBoxLayout(sbar)
        sb.setContentsMargins(16, 0, 16, 0)
        self.status_text = QLabel("SYSTEM READY")
        self.status_text.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_text.setStyleSheet(f"color:{C['success']};")
        sb.addWidget(self.status_text)
        sb.addStretch()
        
        # Wallet (Active Keys) - Smart Detection
        self.key_status_container = QWidget()
        self.key_layout = QHBoxLayout(self.key_status_container)
        self.key_layout.setContentsMargins(0,0,0,0)
        self.key_layout.setSpacing(12)
        sb.addWidget(self.key_status_container)
        
        root.addWidget(sbar)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        
        # Perform initial smart scan
        QTimer.singleShot(500, self._smart_scan_keys)
        
        # Hardware Telemetry Timer
        from creation_engine.hardware_steward import HardwareSteward
        self.hardware = HardwareSteward()
        self.hw_timer = QTimer()
        self.hw_timer.timeout.connect(self._update_hardware_telemetry)
        self.hw_timer.start(2000) # Every 2 seconds


    # ══════════════════════════════════════════════════════════
    #  SIDEBAR (GAMIFIED CONTROLS)
    # ══════════════════════════════════════════════════════════
    def _build_sidebar(self, parent):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(280)
        scroll.setStyleSheet(f"background:{C['bg_card']}; border-right:2px solid {C['border']}; border:none;")

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(12)

        lay.addWidget(self._h("MISSION CONFIG", 12))

        # ── Mode ──────────────────────────────────────────────
        lay.addWidget(self._dim("GAME MODE"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "✨ New Project",
            "♻️ Upgrade Existing",
            "🔍 Reverse Engineer",
            "🎬 Direct Media",
            "🌱 Seed & Synthesis",
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        lay.addWidget(self.mode_combo)

        # Source path (Collapsible)
        self.source_row = QWidget()
        sr_lay = QHBoxLayout(self.source_row)
        sr_lay.setContentsMargins(0, 0, 0, 0)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Path to source code…")
        sr_lay.addWidget(self.source_input, 1)
        browse_btn = QPushButton("📂")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._browse_source)
        sr_lay.addWidget(browse_btn)
        self.source_row.hide()
        lay.addWidget(self.source_row)

        # Focus
        self.focus_input = QLineEdit()
        self.focus_input.setPlaceholderText("Focus area (e.g. 'auth system')")
        self.focus_input.hide()
        lay.addWidget(self.focus_input)

        # ── Video Engine (Contextual) ─────────────────────────
        self.video_model_label = self._dim("VIDEO ENGINE")
        self.video_model_label.hide()
        lay.addWidget(self.video_model_label)
        
        self.video_model_combo = QComboBox()
        try:
            from creation_engine.kie_provider import KieAiProvider
            v_models = list(KieAiProvider.MODELS.values())
            self.video_model_combo.addItems(v_models)
        except:
            self.video_model_combo.addItems(["Wan 2.2 A14B", "Wan 2.2 5B", "Kling 2.1"])
        self.video_model_combo.hide()
        lay.addWidget(self.video_model_combo)

        # ── Smart Model Selector ──────────────────────────────
        lay.addWidget(self._h("INTELLIGENCE SOURCE", 10))
        self.model_combo = QComboBox()
        self.model_combo.addItem("🔮 Scanning keys...")
        # self.model_combo is populated by _smart_scan_keys
        lay.addWidget(self.model_combo)

        # ── Categorized Platform ──────────────────────────────
        lay.addWidget(self._dim("TARGET PLATFORM"))
        
        # Category Selector
        self.plat_cat_combo = QComboBox()
        self.PLATFORM_MAP = {
            "SOFTWARE": ["python", "windows", "linux", "macos", "cli-tool", "desktop-app"],
            "WEB": ["web-app", "web-fullstack", "web-frontend", "web-backend", "web-api", "ecommerce"],
            "MOBILE": ["android", "ios", "react-native", "flutter"],
            "GAME": ["game-2d", "game-3d", "game-rpg", "game-unity", "game-godot"],
            "SYSTEM": ["microservice", "docker", "kubernetes", "aws-lambda"],
            "DATA": ["data-pipeline", "ml-model", "visualization", "scraper"],
            "MEDIA": ["movie", "music", "media-asset"]
        }
        self.plat_cat_combo.addItems(list(self.PLATFORM_MAP.keys()))
        self.plat_cat_combo.currentIndexChanged.connect(self._update_platform_list)
        lay.addWidget(self.plat_cat_combo)
        
        # Platform Selector
        self.platform_combo = QComboBox()
        self._update_platform_list() # Init list based on default category
        lay.addWidget(self.platform_combo)

        # ── Params ────────────────────────────────────────────
        lay.addWidget(self._dim("CREATIVITY / BUDGET"))
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(70)
        lay.addWidget(self.temp_slider)

        self.budget_input = QLineEdit()
        self.budget_input.setPlaceholderText("Budget Limit ($5.00)")
        self.budget_input.setText("5.00")
        lay.addWidget(self.budget_input)

        # Options
        self.chk_docker = QCheckBox("Use Docker Sandbox")
        self.chk_docker.setChecked(True)
        lay.addWidget(self.chk_docker)
        
        self.chk_git = QCheckBox("Init Git Repo")
        self.chk_git.setChecked(True)
        lay.addWidget(self.chk_git)

        lay.addStretch()

        # ── Big Build Button ──────────────────────────────────
        self.sidebar_build_btn = QPushButton("🚀 LAUNCH MISSION")
        self.sidebar_build_btn.setObjectName("buildBtn")
        self.sidebar_build_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_build_btn.clicked.connect(self._on_build)
        lay.addWidget(self.sidebar_build_btn)

        inner.setLayout(lay)
        scroll.setWidget(inner)
        parent.addWidget(scroll)

    def _update_platform_list(self):
        cat = self.plat_cat_combo.currentText()
        items = self.PLATFORM_MAP.get(cat, [])
        self.platform_combo.clear()
        self.platform_combo.addItems(["🔮 auto"] + items)

    def _on_mode_changed(self, idx):
        """Show/hide source path and focus based on selected mode."""
        needs_source = idx in (1, 2)  # Upgrade, Reverse Engineer
        is_media     = (idx == 3)     # Direct Media
        is_seed      = (idx == 4)     # Seed & Synthesis
        
        self.source_row.setVisible(needs_source)
        self.focus_input.setVisible(needs_source or is_seed)
        
        self.video_model_label.setVisible(is_media)
        self.video_model_combo.setVisible(is_media)
        
        if is_seed:
             self.focus_input.setPlaceholderText("Iteration Seed (e.g. 'v1.1 recursive')")
             self.prompt_input.setPlaceholderText("Enter your CORE SEED prompt here. The engine will synthesize recursively.")
        else:
             self.focus_input.setPlaceholderText("Focus area (e.g. 'auth system')")
             self.prompt_input.setPlaceholderText("Describe what to build…")
        
        # Update build button text
        if is_media:
            self.sidebar_build_btn.setText("🎞️ GENERATE MEDIA")
            self.build_btn.setText("🎞️  GENERATE MEDIA")
        elif is_seed:
            self.sidebar_build_btn.setText("🌱 SYNTHESIZE")
            self.build_btn.setText("🌱  START SYNTHESIS")
        else:
            self.sidebar_build_btn.setText("🚀 LAUNCH MISSION")
            self.build_btn.setText("⚡  BUILD PROJECT")

    def _smart_scan_keys(self):
        """Auto-detects active keys and populates the model list."""
        self.model_combo.clear()
        
        active_providers = []
        
        offline = os.environ.get("OVERLORD_OFFLINE_MODE") == "1"
        
        # 1. Check Env (Skip if offline)
        if not offline:
            if os.environ.get("OPENAI_API_KEY"): active_providers.append("openai")
            if os.environ.get("ANTHROPIC_API_KEY"): active_providers.append("anthropic")
            if os.environ.get("GEMINI_API_KEY"): active_providers.append("gemini")
            if os.environ.get("GROQ_API_KEY"): active_providers.append("groq")
        
        # 2. Check Vault (Skip if offline)
        if not offline:
            try:
                from creation_engine.vault import Vault
                v = Vault()
                v_keys = v.load_keys()
                for pid, keys in v_keys.items():
                    if keys and pid not in active_providers:
                        active_providers.append(pid)
            except: pass
        
        # 3. Check Local Ollama / Local provider
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
            if resp.status == 200:
                active_providers.append("ollama")
        except: pass

        if offline or "local" not in active_providers:
            # Always ensure 'local' is available in offline mode
            active_providers.append("local")

        # Populate Combo
        if not active_providers:
            self.model_combo.addItem("⚠️ No Active Keys Found")
            self.model_combo.addItem("gemini-2.0-flash (Fallback)")
            return

        # Add "Auto" first
        self.model_combo.addItem(f"🔮 AUTO ({len(active_providers)} Providers Active)")
        
        for p in active_providers:
            # Add Provider Header
            self.model_combo.addItem(f"── {p.upper()} ──")
            # Add Top Models for Provider
            if p == "openai":
                self.model_combo.addItems(["gpt-4o", "gpt-4o-mini", "o3-mini"])
            elif p == "anthropic":
                self.model_combo.addItems(["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"])
            elif p == "gemini":
                self.model_combo.addItems(["gemini-2.0-flash", "gemini-1.5-pro"])
            elif p == "groq":
                self.model_combo.addItems(["groq:llama-3.3-70b", "groq:mixtral-8x7b"])
            elif p == "ollama":
                self.model_combo.addItems(["ollama:llama3", "ollama:qwen2.5-coder"])
            elif p == "local":
                self.model_combo.addItems(["local/qwen2.5-coder:7b", "local/llama3:8b", "local/mistral"])

        # Select Auto by default
        self.model_combo.setCurrentIndex(0)

        # Update status bar key indicators
        self._update_key_status_bar(active_providers)

    # ══════════════════════════════════════════════════════════
    #  BUILD TAB
    # ══════════════════════════════════════════════════════════
    def _create_build_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # Prompt area
        pf = QFrame()
        pf.setStyleSheet(f"background:{C['bg_card']}; border:1px solid {C['border']}; border-radius:12px;")
        pfl = QVBoxLayout(pf)
        pfl.setContentsMargins(14, 10, 14, 10)

        ph = QHBoxLayout()
        pl = QLabel("🎯 Goal / Instruction")
        pl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        pl.setStyleSheet("background:transparent;")
        ph.addWidget(pl)
        ph.addStretch()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Project name (auto)")
        self.name_input.setMaximumWidth(200)
        self.name_input.setStyleSheet(f"background:{C['bg_input']}; border-radius:6px; padding:4px 10px; font-size:12px;")
        ph.addWidget(self.name_input)
        pfl.addLayout(ph)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Describe what to build…\n\n"
            "Examples:\n"
            "  • A URL shortener with analytics and user auth\n"
            "  • Upgrade this project to use FastAPI and add a React frontend\n"
            "  • Reverse-engineer /path/to/project and generate docs"
        )
        self.prompt_input.setFixedHeight(90)
        self.prompt_input.setStyleSheet(f"background:{C['bg_input']}; border-radius:8px; border:1px solid {C['border_lt']};")
        pfl.addWidget(self.prompt_input)

        btn_row = QHBoxLayout()
        self.build_btn = QPushButton("⚡  BUILD PROJECT")
        self.build_btn.setObjectName("buildBtn")
        self.build_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.build_btn.clicked.connect(self._on_build)
        btn_row.addWidget(self.build_btn)

        self.phase_badge = QLabel("")
        self.phase_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.phase_badge.setStyleSheet(f"background:{C['bg_hover']}; color:{C['text_dim']}; border-radius:12px; padding:4px 14px;")
        self.phase_badge.hide()
        btn_row.addWidget(self.phase_badge)
        btn_row.addStretch()

        # Post-build action buttons
        self.zip_btn = QPushButton("📥 Save ZIP")
        self.zip_btn.setObjectName("actionBtn")
        self.zip_btn.clicked.connect(self._save_zip)
        self.zip_btn.hide()
        btn_row.addWidget(self.zip_btn)

        self.open_btn = QPushButton("📂 Open Folder")
        self.open_btn.setObjectName("actionBtn")
        self.open_btn.clicked.connect(self._open_folder)
        self.open_btn.hide()
        btn_row.addWidget(self.open_btn)

        pfl.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.hide()
        pfl.addWidget(self.progress)

        lay.addWidget(pf)

        # Stats
        sr = QHBoxLayout()
        self.st_files  = StatCard("Files")
        self.st_time   = StatCard("Time")
        self.st_status = StatCard("Status", "IDLE", C["text_dim"])
        self.st_sand   = StatCard("Sandbox", "—")
        for c in (self.st_files, self.st_time, self.st_status, self.st_sand):
            sr.addWidget(c)
        lay.addLayout(sr)

        # Splitter: file tree + preview || terminal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # Left pane
        lp = QWidget()
        ll = QVBoxLayout(lp)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        ll.addWidget(self._h("📁 Generated Files", 11))

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setFont(QFont(MONO, 10))
        self.file_tree.itemClicked.connect(self._on_file_click)
        ll.addWidget(self.file_tree, 1)

        ll.addWidget(self._h("👁 Preview", 11))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont(MONO, 10))
        self.preview.setStyleSheet(f"background:{C['bg_input']}; border:1px solid {C['border_lt']}; border-radius:8px; padding:8px;")
        ll.addWidget(self.preview, 2)

        # Right pane
        rp = QWidget()
        rl = QVBoxLayout(rp)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        rl.addWidget(self._h("🖥 Build Terminal", 11))
        self.terminal = BuildTerminal()
        rl.addWidget(self.terminal, 2)

        # Interaction Hub inline feed
        rl.addWidget(self._h("💬 Agent Dialogue", 11))
        self.hub_inline = QPlainTextEdit()
        self.hub_inline.setReadOnly(True)
        self.hub_inline.setFont(QFont(MONO, 9))
        self.hub_inline.setMaximumHeight(180)
        self.hub_inline.setStyleSheet(
            f"background:{C['bg_input']}; color:{C['text_dim']}; "
            f"border:1px solid {C['border_lt']}; border-radius:8px; padding:8px;"
        )
        self.hub_inline.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        rl.addWidget(self.hub_inline, 1)

        # Subscribe to Interaction Hub for live messages
        if _GUI_HAS_HUB:
            self._hub_instance = InteractionHub.get_instance()
            self._hub_instance.subscribe(self._on_hub_message)

        # Run command
        self.cmd_frame = QFrame()
        self.cmd_frame.setStyleSheet(f"background:{C['bg_card']}; border:1px solid {C['border']}; border-radius:8px; padding:6px;")
        self.cmd_frame.hide()
        cf = QHBoxLayout(self.cmd_frame)
        cf.setContentsMargins(8, 2, 8, 2)
        rl2 = QLabel("▶")
        rl2.setStyleSheet("background:transparent;")
        cf.addWidget(rl2)
        self.cmd_text = QLabel("")
        self.cmd_text.setFont(QFont(MONO, 11))
        self.cmd_text.setStyleSheet(f"color:{C['success']}; background:transparent;")
        cf.addWidget(self.cmd_text)
        cf.addStretch()
        rl.addWidget(self.cmd_frame)

        # Sandbox output
        self.sandbox_frame = QFrame()
        self.sandbox_frame.setStyleSheet(f"background:{C['bg_card']}; border:1px solid {C['border']}; border-radius:8px;")
        self.sandbox_frame.hide()
        sf_lay = QVBoxLayout(self.sandbox_frame)
        sf_lay.setContentsMargins(8, 6, 8, 6)
        sf_lay.addWidget(self._h("🐳 Sandbox Output", 10))
        self.sandbox_text = QPlainTextEdit()
        self.sandbox_text.setReadOnly(True)
        self.sandbox_text.setFont(QFont(MONO, 9))
        self.sandbox_text.setMaximumHeight(120)
        self.sandbox_text.setStyleSheet(f"background:{C['bg_input']}; border:1px solid {C['border_lt']}; border-radius:6px; padding:4px;")
        sf_lay.addWidget(self.sandbox_text)
        rl.addWidget(self.sandbox_frame)

        splitter.addWidget(lp)
        splitter.addWidget(rp)
        splitter.setSizes([480, 420])
        lay.addWidget(splitter, 1)
        return tab

    # ══════════════════════════════════════════════════════════
    #  HISTORY TAB
    # ══════════════════════════════════════════════════════════
    def _create_history_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lay.addWidget(self._h("🕒 Build History & Search", 14))

        search_row = QHBoxLayout()
        self.hist_search = QLineEdit()
        self.hist_search.setPlaceholderText("🔍  Search builds by name…")
        search_row.addWidget(self.hist_search, 3)
        self.hist_platform = QComboBox()
        self.hist_platform.addItems(["All", "python", "android", "linux", "studio"])
        search_row.addWidget(self.hist_platform, 1)
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_history)
        search_row.addWidget(refresh_btn)
        lay.addLayout(search_row)

        self.hist_tree = QTreeWidget()
        self.hist_tree.setHeaderLabels(["Project", "Status", "Platform", "Files", "Cost", "Date"])
        self.hist_tree.setAlternatingRowColors(True)
        self.hist_tree.setFont(QFont("Segoe UI", 10))
        self.hist_tree.setColumnWidth(0, 220)
        self.hist_tree.setColumnWidth(1, 90)
        self.hist_tree.setColumnWidth(2, 80)
        self.hist_tree.setColumnWidth(3, 60)
        self.hist_tree.setColumnWidth(4, 80)
        lay.addWidget(self.hist_tree, 1)

        # Auto-load on tab switch
        self.tabs_connected = False
        return tab

    # ══════════════════════════════════════════════════════════
    #  SETTINGS TAB
    # ══════════════════════════════════════════════════════════
    def _create_settings_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lay.addWidget(self._h("⚙️ Engine Settings", 14))
        lay.addWidget(QLabel("Customize engine directives and provider configuration."))

        # Directives
        grp = QGroupBox("🛠️ Directives")
        gl = QVBoxLayout(grp)
        self.directive_inputs = {}

        _directive_presets = {
            "safety": ["🔮 auto", "🚫 disabled", "🔓 minimal", "🛡️ standard", "🔒 strict", "🏰 maximum"],
            "stability": ["🔮 auto", "🚫 disabled", "⚡ minimal", "⚙️ standard", "🧱 hardened", "💎 maximum"],
            "richness": ["🔮 auto", "📄 minimal", "📋 standard", "✨ rich", "💫 premium", "🌟 maximum"],
            "portability": ["🔮 auto", "🚫 disabled", "📦 minimal", "🔧 standard", "🌍 full-cross-platform", "🚀 maximum"],
            "distribution": ["🔮 auto", "📁 source-only", "📦 pip-installable", "💻 standalone-exe", "🐳 docker-container", "📀 full-package"],
        }

        for key in ("safety", "stability", "richness", "portability", "distribution"):
            gl.addWidget(self._dim(key.upper()))
            cb = QComboBox()
            cb.addItems(_directive_presets.get(key, ["auto", "standard", "maximum"]))
            self.directive_inputs[key] = cb
            gl.addWidget(cb)
        lay.addWidget(grp)

        # Providers
        grp2 = QGroupBox("🔗 Providers (JSON)")
        gl2 = QVBoxLayout(grp2)
        self.providers_edit = QTextEdit()
        self.providers_edit.setFont(QFont(MONO, 9))
        self.providers_edit.setMaximumHeight(150)
        gl2.addWidget(self.providers_edit)
        lay.addWidget(grp2)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("📂 Load Defaults")
        load_btn.clicked.connect(self._load_settings)
        btn_row.addWidget(load_btn)
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("actionBtn")
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addStretch()
        return tab

    # ══════════════════════════════════════════════════════════
    #  VAULT TAB (MULTI-KEY SECURE STORAGE)
    # ══════════════════════════════════════════════════════════
    def _create_vault_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lay.addWidget(self._h("🔐 Secure Key Vault", 14))
        lay.addWidget(QLabel("Manage encrypted API keys. Keys are hardware-bound to this device."))

        # Tool bar
        tools = QHBoxLayout()
        self.vault_provider = QComboBox()
        self.vault_provider.addItems([
            "gemini", "openai", "anthropic", "groq", "openrouter", "deepseek", 
            "luma", "runway", "elevenlabs", "mistral", "stability"
        ])
        tools.addWidget(QLabel("Provider:"))
        tools.addWidget(self.vault_provider)
        
        self.vault_key_input = QLineEdit()
        self.vault_key_input.setPlaceholderText("Paste API key here…")
        self.vault_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.vault_key_input.textChanged.connect(self._on_vault_key_changed)
        tools.addWidget(self.vault_key_input, 1)
        
        add_btn = QPushButton("➕ Add Key")
        add_btn.setObjectName("actionBtn")
        add_btn.clicked.connect(self._add_key_to_vault)
        tools.addWidget(add_btn)
        lay.addLayout(tools)

        # Key List
        self.vault_tree = QTreeWidget()
        self.vault_tree.setHeaderLabels(["Provider", "Key (Obfuscated)", "Status"])
        self.vault_tree.setAlternatingRowColors(True)
        self.vault_tree.setColumnWidth(0, 120)
        self.vault_tree.setColumnWidth(1, 350)
        lay.addWidget(self.vault_tree, 1)

        btns = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Clear Vault")
        clear_btn.clicked.connect(self._clear_vault)
        btns.addWidget(clear_btn)
        btns.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_vault)
        btns.addWidget(refresh_btn)
        lay.addLayout(btns)

        return tab

    def _load_vault(self):
        self.vault_tree.clear()
        try:
            from creation_engine.vault import Vault
            vault = Vault()
            all_keys = vault.load_keys()
            for provider, keys in all_keys.items():
                for k in keys:
                    obfuscated = k[:6] + "..." + k[-4:] if len(k) > 10 else "********"
                    item = QTreeWidgetItem([provider, obfuscated, "🔒 Encrypted"])
                    item.setData(0, Qt.ItemDataRole.UserRole, k)
                    self.vault_tree.addTopLevelItem(item)
            self.status_text.setText(f"Vault loaded: {self.vault_tree.topLevelItemCount()} keys")
        except Exception as e:
            self.terminal.log(f"Vault load failed: {e}", "ERROR")

    def _on_vault_key_changed(self, text):
        if not text: return
        try:
            from creation_engine.llm_client import detect_provider_from_key
            provider = detect_provider_from_key(text)
            if provider:
                idx = self.vault_provider.findText(provider, Qt.MatchFlag.MatchFixedString)
                if idx >= 0:
                    self.vault_provider.setCurrentIndex(idx)
        except Exception:
            pass

    def _add_key_to_vault(self):
        raw_text = self.vault_key_input.text().strip()
        if not raw_text:
            return
        try:
            from creation_engine.vault import Vault
            from creation_engine.llm_client import detect_provider_from_key
            vault = Vault()
            
            # Split by common delimiters to support bulk paste
            keys = [k.strip() for k in raw_text.replace(",", " ").replace(";", " ").split() if k.strip()]
            
            added = 0
            for k in keys:
                # Try to detect provider for each key
                detected = detect_provider_from_key(k)
                target_provider = detected if detected else self.vault_provider.currentText()
                
                vault.add_key(target_provider, k)
                added += 1
                
            self.vault_key_input.clear()
            self._load_vault()
            self.terminal.log(f"✅ Injected {added} keys into {target_provider if added==1 else 'respective pools'}.", "SUCCESS")
        except Exception as e:
            self.terminal.log(f"Vault injection failed: {e}", "ERROR")

    def _clear_vault(self):
        reply = QMessageBox.question(
            self, "Clear Vault?", "Are you sure you want to delete ALL encrypted keys?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from creation_engine.vault import Vault
                Vault().clear()
                self._load_vault()
                self.terminal.log("Vault cleared.", "INFO")
            except Exception as e:
                self.terminal.log(f"Clear failed: {e}", "ERROR")

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════
    def _h(self, text: str, size: int = 11) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", size, QFont.Weight.DemiBold))
        return lbl

    def _dim(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color:{C['text_muted']}; letter-spacing:1.5px; margin-top:2px; background:transparent;")
        return lbl

    # ══════════════════════════════════════════════════════════
    #  STATUS BAR KEY INDICATORS
    # ══════════════════════════════════════════════════════════
    def _update_key_status_bar(self, active_providers=None):
        """Update status bar with live API key indicators."""
        # Clear old indicators
        while self.key_layout.count():
            w = self.key_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        if active_providers is None:
            active_providers = []

        all_providers = [
            ("GEMINI", "GEMINI_API_KEY"),
            ("OPENAI", "OPENAI_API_KEY"),
            ("ANTHROPIC", "ANTHROPIC_API_KEY"),
            ("GROQ", "GROQ_API_KEY"),
        ]
        for label, env_var in all_providers:
            p_id = label.lower()
            has_key = p_id in active_providers or os.environ.get(env_var)
            dot = "🟢" if has_key else "🔴"
            kl = QLabel(f"{dot} {label}")
            kl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            kl.setStyleSheet(f"color:{C['text_muted']}; background:transparent;")
            self.key_layout.addWidget(kl)

    def _browse_source(self):
        d = QFileDialog.getExistingDirectory(self, "Select Source Project")
        if d:
            self.source_input.setText(d)

    # ══════════════════════════════════════════════════════════
    #  MODEL READINESS CHECK
    # ══════════════════════════════════════════════════════════
    _PROVIDER_KEYS = {
        "gemini":    "GEMINI_API_KEY",
        "gpt":       "OPENAI_API_KEY",
        "o3":        "OPENAI_API_KEY",
        "o4":        "OPENAI_API_KEY",
        "claude":    "ANTHROPIC_API_KEY",
        "groq:":     "GROQ_API_KEY",
        "mistral":   "MISTRAL_API_KEY",
        "codestral": "MISTRAL_API_KEY",
        "deepseek":  "DEEPSEEK_API_KEY",
    }

    def _check_ollama_model(self, combo: QComboBox):
        """Check if the selected model is available; offer to install/configure."""
        model = combo.currentText().strip()
        # Strip install indicator prefix if present
        model = model.lstrip("✅⚠️ ")
        if not model or model == "(same as default)":
            return

        # ── Ollama local models ──────────────────────────────
        if model.startswith("ollama:"):
            model_tag = model.split(":", 1)[1]  # e.g. "llama3.2:3b"
            try:
                import subprocess
                result = subprocess.run(
                    ["ollama", "list"], capture_output=True, text=True, timeout=5,
                    creationflags=CREATE_NO_WINDOW
                )
                installed = result.stdout if result.returncode == 0 else ""
                # Check if model name appears (before the tag separator)
                base_name = model_tag.split(":")[0]
                if base_name in installed:
                    return  # Already installed
            except FileNotFoundError:
                reply = QMessageBox.question(
                    self, "Ollama Not Found",
                    "Ollama is not installed.\n\n"
                    "Visit https://ollama.com to install it,\n"
                    "then select an Ollama model again.",
                    QMessageBox.StandardButton.Ok
                )
                return
            except Exception:
                pass  # Timeout or other error — proceed to offer install

            reply = QMessageBox.question(
                self, "Install Ollama Model?",
                f"Model '{model_tag}' is not installed locally.\n\n"
                f"Run  ollama pull {model_tag}  to download it?\n\n"
                f"(This may take a few minutes depending on model size)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._pull_ollama(model_tag)
            return

        # ── Cloud API models ─────────────────────────────────
        needed_key = None
        for prefix, env_var in self._PROVIDER_KEYS.items():
            if model.startswith(prefix):
                needed_key = env_var
                break

        if needed_key and not os.environ.get(needed_key):
            dlg = QDialog(self)
            dlg.setWindowTitle(f"API Key Required — {needed_key}")
            dlg.setMinimumWidth(420)
            dlg_lay = QVBoxLayout(dlg)
            dlg_lay.addWidget(QLabel(
                f"Model <b>{model}</b> requires <b>{needed_key}</b>.\n\n"
                f"Paste your API key below to set it for this session:"
            ))
            key_input = QLineEdit()
            key_input.setPlaceholderText(f"Paste {needed_key} here…")
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            dlg_lay.addWidget(key_input)
            btns = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            dlg_lay.addWidget(btns)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                key_val = key_input.text().strip()
                if key_val:
                    os.environ[needed_key] = key_val
                    self.terminal.log(f"✅ {needed_key} set for this session", "SUCCESS")
                    # Update status bar dots
                    self._refresh_api_dots()
            return

    def _pull_ollama(self, model_tag: str):
        """Pull an Ollama model in a background thread with progress."""
        import subprocess

        progress = QDialog(self)
        progress.setWindowTitle(f"Pulling {model_tag}…")
        progress.setMinimumWidth(400)
        p_lay = QVBoxLayout(progress)
        p_label = QLabel(f"Downloading  ollama pull {model_tag}  — please wait…")
        p_lay.addWidget(p_label)
        p_bar = QProgressBar()
        p_bar.setRange(0, 0)  # Indeterminate
        p_lay.addWidget(p_bar)
        p_output = QPlainTextEdit()
        p_output.setReadOnly(True)
        p_output.setMaximumHeight(120)
        p_output.setFont(QFont(MONO, 9))
        p_lay.addWidget(p_output)
        cancel_btn = QPushButton("Cancel")
        p_lay.addWidget(cancel_btn)

        class PullWorker(QThread):
            line_signal = pyqtSignal(str)
            done_signal = pyqtSignal(bool, str)

            def __init__(self, tag):
                super().__init__()
                self.tag = tag
                self._proc = None

            def run(self):
                try:
                    self._proc = subprocess.Popen(
                        ["ollama", "pull", self.tag],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1, creationflags=CREATE_NO_WINDOW
                    )
                    for line in self._proc.stdout:
                        self.line_signal.emit(line.strip())
                    rc = self._proc.wait()
                    if rc == 0:
                        self.done_signal.emit(True, "Model installed successfully!")
                    else:
                        self.done_signal.emit(False, f"ollama pull exited with code {rc}")
                except Exception as e:
                    self.done_signal.emit(False, str(e))

            def kill(self):
                if self._proc:
                    self._proc.kill()

        worker = PullWorker(model_tag)
        worker.line_signal.connect(lambda l: p_output.appendPlainText(l))

        def on_done(ok, msg):
            p_bar.setRange(0, 100)
            p_bar.setValue(100 if ok else 0)
            p_label.setText(f"{'✅' if ok else '❌'}  {msg}")
            cancel_btn.setText("Close")
            if ok:
                self.terminal.log(f"Ollama model '{model_tag}' installed", "SUCCESS")

        worker.done_signal.connect(on_done)
        cancel_btn.clicked.connect(lambda: (worker.kill(), progress.close()))
        worker.start()
        progress.exec()

    def _refresh_api_dots(self):
        """Refresh the status bar API key dots."""
        try:
            from creation_engine.vault import Vault
            v_keys = Vault().load_keys()
        except Exception:
            v_keys = {}

        # Look for the status bar labels (they are after the stretch in the layout)
        # However, it's easier to just re-scan env and vault
        # In a real app we'd keep references, but for now we'll just log
        self.status_text.setText("Vault updated.")

    # ══════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════
    def _on_build(self):
        # ── DEBUG DIAGNOSTIC ──
        # from PyQt6.QtWidgets import QMessageBox
        # QMessageBox.information(self, "Debug", "Button Signal Received")
        # ──────────────────────

        goal = self.prompt_input.toPlainText().strip()
        
        if not goal:
            self.terminal.log("Enter a project description or question.", "WARN")
            # Explicit popup to prove life if terminal is missed
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Creation Engine", "Please enter a prompt (Create X...) or a question (How to...).")
            return
            
        # ── SYSTEM CHECK INTERCEPTION ──
        if goal.lower() == "system check":
            self.terminal.log("🔎 Running System Diagnostics...", "SYSTEM")
            try:
                from creation_engine.engine_eval import EngineSelfEval
                evaluator = EngineSelfEval()
                report = evaluator.run_eval()
                
                self.terminal.log("🛡️ SYSTEM STATUS REPORT:", "SYSTEM")
                for key, val in report.items():
                    level = "SUCCESS" if "Pass" in val or "Clean" in val or "Optimized" in val else "WARN"
                    self.terminal.log(f"  • {key}: {val}", level)
                self.terminal.log("Diagnostics Complete.", "SUCCESS")
            except Exception as e:
                self.terminal.log(f"Diagnostics Failed: {e}", "ERROR")
            return
        # ──────────────────────────────

        # ── INTENT DETECTION ──
        # Heuristics to determine if this is a chat question or a build command
        starts_with_question = goal.lower().split(" ")[0] in ("how", "what", "why", "who", "when", "can", "is", "explain")
        ends_with_qmark = goal.strip().endswith("?")
        
        # Explicit build keywords (overridden by explicit question formatting)
        build_keywords = ["create", "generate", "build", "make", "synthesize", "develop", "code", "upgrade", "reverse", "engineer", "scaffold"]
        has_build_keyword = any(k in goal.lower() for k in build_keywords)
        
        # If user selected a specific mode other than "New Project", force build
        force_build_mode = self.mode_combo.currentIndex() != 0
        
        # DECISION:
        # It is a BUILD if: (Has Keyword AND Not a Question) OR (Force Mode is On)
        is_build = (has_build_keyword and not (starts_with_question or ends_with_qmark)) or force_build_mode

        if not is_build:
            # TREATING AS CHAT
            self.terminal.log(f"💬 Asking Engine: '{goal}'", "INFO")
            
            # Disable button briefly
            self.build_btn.setEnabled(False)
            self.build_btn.setText("💭 THINKING…")
            
            # Quick Worker for Chat
            class ChatWorker(QThread):
                response_sig = pyqtSignal(str)
                def run(self):
                    try:
                        # Explicit import to ensure it works in the thread
                        from creation_engine.llm_client import ask_llm
                        system_prompt = (
                            "You are the Creation Engine Console. "
                            "You are an expert software architect. "
                            "Answer the user's technical questions concisely. "
                            "If the user wants to build something, guide them to use a clear command like 'Create a...'"
                        )
                        # Use auto model resolution
                        resp = ask_llm(client=None, model="auto", system_role=system_prompt, user_content=goal)
                        self.response_sig.emit(resp)
                    except Exception as e:
                        self.response_sig.emit(f"Error: {e}")

            self._chat_worker = ChatWorker()
            def on_chat_resp(resp):
                # Color code based on response content/error
                level = "SYSTEM"
                if "Error:" in resp:
                    level = "ERROR"
                
                self.terminal.log(f"🤖 {resp}", level)
                self.build_btn.setEnabled(True)
                self._on_mode_changed(self.mode_combo.currentIndex()) # Restore button text
                
            self._chat_worker.response_sig.connect(on_chat_resp)
            self._chat_worker.start()
            return
        # ────────────────────────────────────

        mode_idx = self.mode_combo.currentIndex()
        if mode_idx in (1, 2) and not self.source_input.text().strip():
            self.terminal.log("Source path required for Upgrade / Reverse Engineer mode.", "WARN")
            return

        name = self.name_input.text().strip()
        if not name:
            name = goal.lower().replace(" ", "-")[:30]
            name = "".join(c for c in name if c.isalnum() or c in "-_") or "project"

        mode_map = {0: "new", 1: "upgrade", 2: "reverse", 3: "new", 4: "new"}

        # Helper to strip emoji prefix from dropdown values
        def _strip_emoji(text):
            """Remove leading emoji + space from dropdown text: '🐍 python' → 'python'"""
            parts = text.split(" ", 1)
            if len(parts) == 2 and not parts[0].isascii():
                return parts[1]
            return text

        # Parse budget from text input
        try:
            budget_val = float(self.budget_input.text().strip())
        except (ValueError, AttributeError):
            budget_val = 5.0

        # Resolve model from combo text
        raw_model = self.model_combo.currentText().strip()
        if "AUTO" in raw_model.upper() or raw_model.startswith("──") or raw_model.startswith("🔮"):
            resolved_model = "auto"
        else:
            resolved_model = _strip_emoji(raw_model)
            # Strip indicator prefixes (✅/⚠️)
            resolved_model = resolved_model.lstrip("✅⚠️ ")

        # Resolve video model
        raw_video_model = self.video_model_combo.currentText()
        video_model_id = "kling/v2-1-master-text-to-video" # Fallback
        try:
            from creation_engine.kie_provider import KieAiProvider
            # Reverse lookup name to ID
            for vid, name_val in KieAiProvider.MODELS.items():
                if name_val == raw_video_model:
                    video_model_id = vid
                    break
        except:
            pass

        kwargs = {
            "project_name": name,
            "prompt": goal,
            "output_dir": "./output",
            "model": resolved_model,
            "video_model": video_model_id,
            "platform": _strip_emoji(self.platform_combo.currentText()),
            "budget": budget_val,
            "max_fix_cycles": 3,
            "docker": self.chk_docker.isChecked(),
            "mode": mode_map.get(mode_idx, "new"),
            "scale": "asset" if mode_idx == 3 else "auto",
            "phase": "all",
            "source_path": self.source_input.text().strip() if mode_idx in (1, 2) else None,
            "focus": self.focus_input.text().strip() or None,
            "decompile_only": False,
            "vram_serialized": self.chk_serialized.isChecked(),
            "thermal_throttling": self.chk_throttle.isChecked(),
            "llm_offload": self.chk_offload.isChecked(),
        }

        # Reset UI
        self.terminal.clear()
        self.file_tree.clear()
        self.preview.clear()
        self.cmd_frame.hide()
        self.sandbox_frame.hide()
        self.zip_btn.hide()
        self.open_btn.hide()
        self.progress.setValue(0)
        self.progress.show()
        self.phase_badge.setText("⏳ BUILDING…")
        self.phase_badge.setStyleSheet(f"background:{C['accent_dim']}; color:white; border-radius:12px; padding:4px 14px;")
        self.phase_badge.show()
        self.build_btn.setEnabled(False)
        self.build_btn.setText("⏳  BUILDING…")
        if hasattr(self, 'build_btn2'):
            self.build_btn2.setEnabled(False)
            self.build_btn2.setText("⏳ BUILDING…")
        self.st_status.set_value("BUILD", C["warning"])
        self._build_start = time.time()
        self._elapsed_timer.start(1000)

        self._worker = EngineWorker(kwargs, use_legacy=False)
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

        self.terminal.log(f"🚀 Mission '{name}' launched with {kwargs['model']}…", "SYSTEM")
        self.status_text.setText(f"⚡ BUILDING: {name}")
        if hasattr(self, 'consensus'):
            self.consensus.set_status("debating", "Negotiating Path")

    def _on_log(self, msg: str, level: str):
        lvl = {"ERROR": "ERROR", "CRASH": "ERROR", "WARN": "WARN"}.get(level, "INFO")
        if any(x in msg for x in ("✓", "✅", "APPROVED", "COMPLETE")):
            lvl = "SUCCESS"
        if "🔄 RECURSIVE SYNTHESIS: Iteration" in msg:
            self.status_text.setText(f"🧬 RE-ARCHITECTING: {msg.split('Iteration ')[1]}")
            self.game.add_xp(50) # Award XP for learning
            self.stat_xp.set_value(f"{self.game.xp:,}", C["accent"])

        # Consensus Updates
        if "CONSENSUS REACHED" in msg.upper():
            if hasattr(self, 'consensus'):
                self.consensus.set_status("reached", "Consensus Reached")
        elif "CONFLICT DETECTED" in msg.upper():
            if hasattr(self, 'consensus'):
                self.consensus.set_status("conflict", "Conflict! Recalculating...")
            
        self.terminal.log(msg, lvl)

    def _on_done(self, result: dict):
        self._elapsed_timer.stop()
        elapsed = time.time() - self._build_start if self._build_start else 0
        self._result = result

        self.build_btn.setEnabled(True)
        if hasattr(self, 'build_btn2'):
            self.build_btn2.setEnabled(True)
        self._on_mode_changed(self.mode_combo.currentIndex())  # restore button text
        self.progress.setValue(100)

        if result.get("success"):
            self.st_status.set_value("DONE", C["success"])
            self.phase_badge.setText("✅ COMPLETE")
            self.phase_badge.setStyleSheet(f"background:#064e3b; color:{C['success']}; border-radius:12px; padding:4px 14px;")
            self.terminal.log("🎉 MISSION COMPLETE!", "SUCCESS")
            self.status_text.setText("✅ Mission Succeeded")
            # Award XP for successful build
            self.game.add_xp(100)
            self.stat_level.set_value(str(self.game.level), C["info"])
            self.stat_xp.set_value(f"{self.game.xp:,}", C["accent"])
            self.stat_streak.set_value(f"{self.game.streak}🔥", C["warning"])
            self.terminal.log(f"+100 XP! Level {self.game.level} • {self.game.rank}", "SUCCESS")
        else:
            self.st_status.set_value("FAIL", C["error"])
            self.phase_badge.setText("❌ FAILED")
            self.phase_badge.setStyleSheet(f"background:#450a0a; color:{C['error']}; border-radius:12px; padding:4px 14px;")
            self.terminal.log(f"❌ Mission failed: {result.get('error', '?')}", "ERROR")
            self.status_text.setText("❌ Mission Failed")

        fc = result.get("file_count", len(result.get("files_written", [])))
        self.st_files.set_value(str(fc), C["accent"])
        self.st_time.set_value(f"{elapsed:.1f}s", C["info"])

        self._populate_tree(result.get("files_written", []))

        run_cmd = result.get("run_command", "")
        if run_cmd:
            self.cmd_text.setText(run_cmd)
            self.cmd_frame.show()

        # Show post-build actions
        if result.get("project_path") and os.path.isdir(result.get("project_path", "")):
            self.zip_btn.show()
            self.open_btn.show()

    def _tick_elapsed(self):
        if self._build_start:
            self.st_time.set_value(f"{time.time()-self._build_start:.0f}s", C["info"])

    def _populate_tree(self, files: list):
        self.file_tree.clear()
        if not files:
            return
        tree = {}
        for fp in sorted(files):
            parts = fp.replace("\\", "/").split("/")
            cur = tree
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = None

        def _add(parent, d, prefix=""):
            for key, val in sorted(d.items()):
                full = f"{prefix}/{key}" if prefix else key
                item = QTreeWidgetItem()
                if val is None:
                    icon = "🐍" if key.endswith(".py") else "📄" if key.endswith(".md") else "📋" if key.endswith((".txt",".cfg",".ini",".toml")) else "🌐" if key.endswith((".html",".css",".js")) else "📦"
                    item.setText(0, f"{icon} {key}")
                    item.setData(0, Qt.ItemDataRole.UserRole, full)
                else:
                    item.setText(0, f"📁 {key}")
                    _add(item, val, full)
                if isinstance(parent, QTreeWidget):
                    parent.addTopLevelItem(item)
                else:
                    parent.addChild(item)
        _add(self.file_tree, tree)
        self.file_tree.expandAll()

    def _on_file_click(self, item, col):
        fp = item.data(0, Qt.ItemDataRole.UserRole)
        if not fp or not self._result:
            return
        code = self._result.get("written_files", {}).get(fp, "")
        self.preview.setPlainText(code[:8000] if code else f"(no content for {fp})")

    # ══════════════════════════════════════════════════════════
    #  POST-BUILD ACTIONS
    # ══════════════════════════════════════════════════════════
    def _save_zip(self):
        if not self._result:
            return
        proj_dir = self._result.get("project_path", "")
        if not proj_dir or not os.path.isdir(proj_dir):
            self.terminal.log("No project directory to zip.", "WARN")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project ZIP",
            f"{self._result.get('project_name', 'project')}.zip",
            "ZIP Files (*.zip)"
        )
        if not save_path:
            return
        try:
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(proj_dir):
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "venv")]
                    for fname in files:
                        full = os.path.join(root, fname)
                        arc = os.path.relpath(full, proj_dir)
                        zf.write(full, arc)
            self.terminal.log(f"ZIP saved: {save_path}", "SUCCESS")
        except Exception as e:
            self.terminal.log(f"ZIP failed: {e}", "ERROR")

    def _open_folder(self):
        if not self._result:
            return
        proj_dir = self._result.get("project_path", "")
        if proj_dir and os.path.isdir(proj_dir):
            if sys.platform == "win32":
                os.startfile(proj_dir)
            elif sys.platform == "darwin":
                os.system(f'open "{proj_dir}"')
            else:
                os.system(f'xdg-open "{proj_dir}"')

    # ══════════════════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════════════════
    def _refresh_history(self):
        self.hist_tree.clear()
        try:
            from creation_engine.search import search_builds
            query = self.hist_search.text().strip()
            platform = self.hist_platform.currentText()
            plat = None if platform == "All" else platform
            builds = search_builds("./output", query, plat)
            for b in builds:
                item = QTreeWidgetItem([
                    b["name"],
                    b.get("status", "?"),
                    b.get("platform", "?"),
                    str(b.get("files", 0)),
                    f"${b.get('cost', 0):.4f}",
                    datetime.fromtimestamp(b["timestamp"]).strftime("%Y-%m-%d %H:%M") if b.get("timestamp") else "—",
                ])
                # Color code status
                status = b.get("status", "")
                if status == "COMPLETE":
                    item.setForeground(1, QColor(C["success"]))
                elif "FAIL" in status:
                    item.setForeground(1, QColor(C["error"]))
                if b.get("has_binary"):
                    item.setText(0, f"📦 {b['name']}")
                self.hist_tree.addTopLevelItem(item)
            self.status_text.setText(f"Found {len(builds)} build(s)")
        except Exception as e:
            self.terminal.log(f"History load failed: {e}", "ERROR")

    # ══════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════
    def _load_settings(self):
        try:
            from creation_engine.settings import load_settings
            settings = load_settings()
            for key, cb in self.directive_inputs.items():
                val = settings.get("directives", {}).get(key, "auto")
                idx = cb.findText(val)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                else:
                    cb.setCurrentIndex(0)  # default to 'auto'
            self.providers_edit.setPlainText(
                json.dumps(settings.get("providers", {}), indent=2)
            )
            self.terminal.log("Settings loaded from defaults", "SUCCESS")
        except Exception as e:
            self.terminal.log(f"Failed to load settings: {e}", "ERROR")

    def _save_settings(self):
        try:
            from creation_engine.settings import save_settings
            directives = {}
            for key, cb in self.directive_inputs.items():
                directives[key] = cb.currentText()
            providers_text = self.providers_edit.toPlainText()
            providers = json.loads(providers_text) if providers_text.strip() else {}
            result = save_settings({"directives": directives, "providers": providers})
            if result:
                self.terminal.log("Settings saved!", "SUCCESS")
            else:
                self.terminal.log("Settings save failed", "ERROR")
        except json.JSONDecodeError as e:
            self.terminal.log(f"Invalid JSON in Providers: {e}", "ERROR")
        except Exception as e:
            self.terminal.log(f"Save failed: {e}", "ERROR")

    def showEvent(self, event):
        super().showEvent(event)
        if not self.tabs_connected:
            self.tabs.currentChanged.connect(self._on_tab_changed)
            self.tabs_connected = True

    def _on_tab_changed(self, idx):
        if idx == 1:
            self._refresh_history()
        elif idx == 2:
            self._load_settings()
        elif idx == 3:
            self._load_vault()
        elif idx == 4:
            self._refresh_logic_vault()

    def _create_logic_vault_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 20, 16, 20)
        
        lay.addWidget(self._h("🧠 ENGINE LOGIC VAULT", 16))
        lay.addWidget(self._dim("Persistent recursive memories and successful synthesis patterns."))
        
        self.logic_vault_tree = QTreeWidget()
        self.logic_vault_tree.setHeaderLabels(["Project ID", "Status", "Timestamp", "Protocol"])
        self.logic_vault_tree.setColumnWidth(0, 200)
        lay.addWidget(self.logic_vault_tree)
        
        btn_lay = QHBoxLayout()
        refresh_btn = QPushButton("🔃 Refresh")
        refresh_btn.clicked.connect(self._refresh_logic_vault)
        btn_lay.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ Clear Memories")
        clear_btn.setStyleSheet(f"background:{C['error']}; border-color:{C['error']};")
        clear_btn.clicked.connect(self._clear_logic_vault)
        btn_lay.addWidget(clear_btn)
        btn_lay.addStretch()
        lay.addLayout(btn_lay)
        
        return tab

    def _refresh_logic_vault(self):
        self.logic_vault_tree.clear()
        memory_path = "engine_memory.json"
        if os.path.exists(memory_path):
            try:
                with open(memory_path, 'r') as f:
                    memory = json.load(f)
                for pid, data in memory.items():
                    item = QTreeWidgetItem([
                        pid,
                        data.get("status", "UNKNOWN"),
                        data.get("timestamp", "—"),
                        data.get("protocol", "—")
                    ])
                    if data.get("status") == "SUCCESS":
                        item.setForeground(1, QColor(C["success"]))
                    self.logic_vault_tree.addTopLevelItem(item)
            except: pass

    def _clear_logic_vault(self):
        if QMessageBox.question(self, "Clear Vault?", "Wipe all persistent memories?") == QMessageBox.StandardButton.Yes:
            if os.path.exists("engine_memory.json"):
                os.remove("engine_memory.json")
            self._refresh_logic_vault()

    def _create_alchemist_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(15)

        lay.addWidget(self._h("⚗️ VRAM ALCHEMIST Dashboard", 16))
        lay.addWidget(self._dim("Managed hardware stabilization for local-only synthesis."))

        # Gauges Row
        gauges = QHBoxLayout()
        self.hw_vram  = StatCard("VRAM USED", "0MB", C["info"])
        self.hw_temp  = StatCard("TEMP", "0°C", C["warning"])
        self.hw_util  = StatCard("UTILIZATION", "0%", C["accent"])
        for g in (self.hw_vram, self.hw_temp, self.hw_util):
            gauges.addWidget(g)
        lay.addLayout(gauges)

        # Controls
        ctrls = QGroupBox("🛠️ Stabilization Controls")
        cl = QVBoxLayout(ctrls)
        
        self.chk_serialized = QCheckBox("Force Serialized Model Loading (Prevents OOM)")
        self.chk_serialized.setChecked(True)
        self.chk_serialized.setToolTip("Ensures LLMs and Video models never occupy VRAM at the same time.")
        cl.addWidget(self.chk_serialized)

        self.chk_throttle = QCheckBox("Enable Thermal Throttling (Auto-Pause at 85°C)")
        self.chk_throttle.setChecked(True)
        cl.addWidget(self.chk_throttle)
        
        self.chk_offload = QCheckBox("Optimize for LLM Offload (High System RAM Strategy)")
        self.chk_offload.setChecked(False)
        self.chk_offload.setToolTip("Guards VRAM by recommending CPU-only execution for LLMs during Video synthesis.")
        cl.addWidget(self.chk_offload)
        
        self.chk_sentinel = QCheckBox("Enable Hardware Sentinel (Reactive Throttling)")
        self.chk_sentinel.setChecked(True)
        self.chk_sentinel.setToolTip("Automatically pauses visualizations if VRAM usage exceeds 7GB safety limit.")
        cl.addWidget(self.chk_sentinel)
        
        lay.addWidget(ctrls)

        # Purge Section
        purge_box = QFrame()
        purge_box.setStyleSheet(f"background:{C['bg_input']}; border-radius:12px; border:1px solid {C['border']}; padding:15px;")
        pl = QHBoxLayout(purge_box)
        pl.addWidget(QLabel("<b>VRAM CACHE PURGE</b><br><span style='font-size:10px; color:"+C['text_dim']+"'>Instantly unloads cached Ollama models to free memory.</span>"))
        pl.addStretch()
        purge_btn = QPushButton("🔥 PURGE VRAM")
        purge_btn.setObjectName("actionBtn")
        purge_btn.setStyleSheet(f"background:{C['error']}; min-width:140px;")
        purge_btn.clicked.connect(self._purge_vram)
        pl.addWidget(purge_btn)
        lay.addWidget(purge_box)

        # Mermaid Section
        mermaid_box = QFrame()
        mermaid_box.setStyleSheet(f"background:{C['bg_input']}; border-radius:12px; border:1px solid {C['border']}; padding:15px;")
        ml = QHBoxLayout(mermaid_box)
        ml.addWidget(QLabel("<b>HEADLESS VIZ BRIDGE</b><br><span style='font-size:10px; color:"+C['text_dim']+"'>Offload project diagrams to an external browser window.</span>"))
        ml.addStretch()
        mermaid_btn = QPushButton("🌐 MERMAID LIVE")
        mermaid_btn.setObjectName("actionBtn")
        mermaid_btn.setStyleSheet(f"background:{C['accent']}; min-width:140px;")
        mermaid_btn.clicked.connect(self._launch_mermaid_live)
        ml.addWidget(mermaid_btn)
        lay.addWidget(mermaid_box)

        lay.addStretch()
        return tab

    # ══════════════════════════════════════════════════════════
    #  AGENT HUB TAB
    # ══════════════════════════════════════════════════════════

    def _create_hub_tab(self) -> QWidget:
        """Full-page Agent Interaction Hub — live dialogue feed."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("💬 Sovereign Agent Dialogue")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color:{C['text']}; background:transparent;")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("🗑 Clear")
        clear_btn.setObjectName("actionBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_hub)
        header.addWidget(clear_btn)
        lay.addLayout(header)

        # Description
        desc = QLabel("Real-time agent-to-agent communication. Watch agents collaborate during builds.")
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet(f"color:{C['text_dim']}; background:transparent;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Chat Feed
        self.hub_feed = QPlainTextEdit()
        self.hub_feed.setReadOnly(True)
        self.hub_feed.setFont(QFont(MONO, 10))
        self.hub_feed.setStyleSheet(
            f"background:{C['bg_input']}; color:{C['text']}; "
            f"border:1px solid {C['border']}; border-radius:10px; padding:12px;"
        )
        self.hub_feed.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.hub_feed.setPlaceholderText(
            "Agent dialogue will appear here during builds...\n\n"
            "  🏗️ Architect: \"Analyzing request...\"\n"
            "  ⚙️ Fabricator: \"Forging 3 files from blueprint...\"\n"
            "  🛡️ Sentinel: \"Red-team scan clean.\"\n"
            "  ⚖️ Judge: \"Gauntlet passed. 0% downtime.\"\n"
        )
        lay.addWidget(self.hub_feed, 1)

        # Legend
        legend_frame = QFrame()
        legend_frame.setStyleSheet(
            f"background:{C['bg_card']}; border:1px solid {C['border']}; "
            f"border-radius:8px; padding:8px;"
        )
        legend_lay = QHBoxLayout(legend_frame)
        legend_lay.setContentsMargins(12, 4, 12, 4)
        for emoji, name in [("🏗️", "Architect"), ("⚙️", "Fabricator"),
                             ("🧪", "Alchemist"), ("🛡️", "Sentinel"),
                             ("⚖️", "Judge"), ("💰", "Merchant")]:
            lbl = QLabel(f"{emoji} {name}")
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet(f"color:{C['text_dim']}; background:transparent;")
            legend_lay.addWidget(lbl)
        legend_lay.addStretch()
        lay.addWidget(legend_frame)

        return tab

    def _on_hub_message(self, msg):
        """Called by Interaction Hub when an agent posts a message (from any thread)."""
        try:
            display = msg.to_display()

            # Color based on severity
            severity_colors = {
                "INFO": C["text_dim"],
                "WARNING": C["warning"],
                "ACTION": C["info"],
                "VERDICT": C["success"],
            }
            color = severity_colors.get(msg.severity, C["text_dim"])
            colored = f'<span style="color:{color}">{display}</span>'

            # Update inline feed (build tab)
            if hasattr(self, 'hub_inline'):
                self.hub_inline.appendPlainText(display)
                self.hub_inline.verticalScrollBar().setValue(
                    self.hub_inline.verticalScrollBar().maximum()
                )

            # Update full hub tab feed
            if hasattr(self, 'hub_feed'):
                self.hub_feed.appendPlainText(display)
                self.hub_feed.verticalScrollBar().setValue(
                    self.hub_feed.verticalScrollBar().maximum()
                )
        except Exception:
            pass  # Never crash the GUI from a hub message

    def _clear_hub(self):
        """Clear the Agent Hub feed."""
        if hasattr(self, 'hub_feed'):
            self.hub_feed.clear()
        if hasattr(self, 'hub_inline'):
            self.hub_inline.clear()
        if _GUI_HAS_HUB:
            InteractionHub.get_instance().clear()

    def _update_hardware_telemetry(self):
        stats = self.hardware.get_gpu_stats()
        
        # Check Stability (Local Memory/Ollama)
        try:
            from creation_engine.local_memory import LocalMemoryManager
            is_active = LocalMemoryManager.check_health()
            if is_active:
                # If VRAM > 7GB, it's "STRESSED" but managed. 
                # If < 5GB, it's "STABLE".
                if stats["vram_used"] > 7000:
                    self.stat_stability.set_value("STRESSED", C["warning"])
                else:
                    self.stat_stability.set_value("ACTIVE", C["success"])
            else:
                self.stat_stability.set_value("OFFLINE", C["error"])
                
            # Update NPU Status
            if stats.get("npu_active"):
                self.stat_npu.set_value("READY", C["success"])
            else:
                self.stat_npu.set_value("N/A", C["text_muted"])
        except:
            self.stat_stability.set_value("UNAVAILABLE", C["text_muted"])
            self.stat_npu.set_value("N/A", C["text_muted"])

        stats = self.hardware.get_gpu_stats()
        # VRAM Used
        vram_val = f"{int(stats['vram_used'])}MB"
        vram_color = C["info"] if stats["vram_used"] < stats["vram_total"]*0.8 else C["error"]
        self.hw_vram.set_value(vram_val, vram_color)
        
        # Temp
        temp_val = f"{int(stats['temp'])}°C"
        temp_color = C["warning"] if stats["temp"] < 80 else C["error"]
        self.hw_temp.set_value(temp_val, temp_color)
        
        # Utilization
        self.hw_util.set_value(f"{int(stats['utilization'])}%", C["accent"])
        
        # Update header stat too
        vram_display = f"{round(stats['vram_total']/1024, 1)}GB"
        self.stat_vram.set_value(vram_display, C["success"] if stats["vram_total"] >= 8000 else C["warning"])

        # Sentinel Check (Tactic 4)
        if hasattr(self, 'chk_sentinel') and self.chk_sentinel.isChecked():
            self.hardware.monitor_and_throttle(threshold_gb=7.0, callback=self._on_sentinel_throttled)

    def _on_sentinel_throttled(self, status):
        """Callback for Hardware Sentinel."""
        if status == "PAUSE":
            self.terminal.log("⚠️ Sentinel: VRAM Critical (>7GB). Visualizations throttled.", "WARN")
            # This is where we would trigger actual visualization pausing
        else:
            self.terminal.log("✅ Sentinel: VRAM Stabilized. Visualizations resumed.", "SUCCESS")

    def _purge_vram(self):
        self.hardware.purge_vram()
        self.terminal.log("VRAM Purge signal sent to local engine.", "SYSTEM")

    def _launch_mermaid_live(self):
        """Offloads the visualization to a browser window (Tactic 1 & 3)."""
        import webbrowser
        import base64
        import json
        
        # Look for the last generated blueprint
        blueprint_path = "blueprint.mermaid"
        if hasattr(self, '_last_project_path'):
            path = os.path.join(self._last_project_path, "blueprint.mermaid")
            if os.path.exists(path):
                blueprint_path = path

        if not os.path.exists(blueprint_path):
            self.terminal.log("No active blueprint found. Generate a project first.", "WARN")
            return

        try:
            with open(blueprint_path, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Mermaid Live uses a base64 encoded JSON state
            state = {
                "code": code,
                "mermaid": {"theme": "dark"},
                "updateEditor": False,
                "autoSync": True,
                "updateDiagram": True
            }
            json_str = json.dumps(state)
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            url = f"https://mermaid.live/edit#base64:{encoded}"
            
            webbrowser.open(url)
            self.terminal.log("Headless Viz Bridge opened in browser.", "SUCCESS")
        except Exception as e:
            self.terminal.log(f"Failed to bridge to Mermaid Live: {e}", "ERROR")


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def main():
    if sys.platform == "win32":
        os.environ["PYTHONUTF8"] = "1"
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    
    window = OverlordWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
