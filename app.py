#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║            NEXUS SUITE — Streamlit Command Center            ║
║                  Pro Dashboard  •  v1.0                      ║
╚══════════════════════════════════════════════════════════════╝

Launch:  streamlit run app.py
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

import streamlit as st

# Add this directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine_core import (
    StateReducer, CreationEngine, BuildConfig,
    DockerSandbox, LogCapture, NexusEngine,
)
from creation_engine import NexusDecompiler

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Nexus Suite — Command Center",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');

    /* Root theme - Nexus Dark */
    .stApp { background: #05050a; }
    [data-testid="stSidebar"] { background: #080a12; border-right: 1px solid #1a1e2e; }

    /* Header gradient - Nexus Indigo/Violet */
    .engine-header {
        background: linear-gradient(135deg, #0f111a 0%, #07080f 50%, #101426 100%);
        border: 1px solid #232a45;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .engine-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #7f00ff, #e100ff, #00d2ff, #7f00ff);
        background-size: 300% 100%;
        animation: shimmer 3s linear infinite;
    }
    @keyframes shimmer {
        0% { background-position: 0% 0%; }
        100% { background-position: 300% 0%; }
    }
    .engine-header h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2rem;
        color: #e8e6f0;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .engine-header p {
        font-family: 'Inter', sans-serif;
        color: #6b6f80;
        margin: 4px 0 0 0;
        font-size: 0.95rem;
    }

    /* Phase stepper */
    .phase-card {
        background: #12131f;
        border: 1px solid #1e2030;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s ease;
    }
    .phase-card.active {
        border-color: #6C63FF;
        background: #15162a;
        box-shadow: 0 0 20px rgba(108, 99, 255, 0.1);
    }
    .phase-card.done {
        border-color: #00FF88;
        background: #0d1a14;
    }
    .phase-icon {
        font-size: 1.3rem;
        min-width: 28px;
        text-align: center;
    }
    .phase-name {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #e8e6f0;
        font-weight: 600;
    }
    .phase-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #6b6f80;
        margin-left: auto;
    }

    /* Stats card */
    .stat-card {
        background: linear-gradient(145deg, #12131f, #161830);
        border: 1px solid #1e2030;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }
    .stat-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #e8e6f0;
        line-height: 1;
    }
    .stat-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        color: #6b6f80;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 6px;
    }

    /* Log console */
    .log-container {
        background: #080810;
        border: 1px solid #1a1d2e;
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        max-height: 480px;
        overflow-y: auto;
        line-height: 1.6;
    }
    .log-line { margin: 0; padding: 1px 0; }
    .log-ts { color: #3a3d50; }
    .log-tag-SYSTEM { color: #6b6f80; }
    .log-tag-ARCHITECT { color: #00D4FF; }
    .log-tag-ENGINEER { color: #FFD600; }
    .log-tag-REVIEWER { color: #00FFAA; }
    .log-tag-DEBUGGER { color: #FF44CC; }
    .log-tag-DOCKER { color: #FF8A00; }
    .log-tag-WISDOM { color: #E040FB; }
    .log-tag-SUCCESS { color: #00FF88; }
    .log-tag-ERROR { color: #FF3B5C; }
    .log-tag-WARN { color: #FF8A00; }
    .log-tag-ENGINE { color: #6C63FF; }
    .log-msg { color: #c5c8d4; }

    /* File explorer */
    .file-item {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #c5c8d4;
        padding: 6px 12px;
        border-bottom: 1px solid #1a1d2e;
    }
    .file-item:hover { background: #15162a; }

    /* Sidebar styling */
    .sidebar-section {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #6b6f80;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 18px 0 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

if "engine" not in st.session_state:
    st.session_state.engine = None
if "build_running" not in st.session_state:
    st.session_state.build_running = False
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []
if "last_progress" not in st.session_state:
    st.session_state.last_progress = None
if "build_error" not in st.session_state:
    st.session_state.build_error = None
if "build_artifacts" not in st.session_state:
    st.session_state.build_artifacts = []


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR — BUILD CONFIGURATION
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p class="sidebar-section">◈ NEXUS SUITE</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="sidebar-section">PROJECT CONFIG</p>', unsafe_allow_html=True)
    
    # --- Aura Registry Sidebar ---
    st.markdown("---")
    st.markdown('<p class="sidebar-section">🧠 AURA REGISTRY</p>', unsafe_allow_html=True)
    memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builds", "memory")
    if os.path.exists(memory_dir):
        aura = NexusDecompiler() # Placeholder for viewing, or just use json
        registry_path = os.path.join(memory_dir, "aura_registry.json")
        if os.path.exists(registry_path):
            with open(registry_path, "r") as f:
                data = json.load(f)
                st.info(f"Registry Depth: {len(data)} lessons")
                if st.button("🔍 Open Memory Bank"):
                    st.session_state.show_memory = True
        else:
            st.info("Registry is empty. Run a build to seed wisdom.")
    else:
        st.info("No memory directory found.")

    project_name = st.text_input(
        "Project Name",
        value="MyApp",
        help="Name of the generated project directory",
    )

    output_dir = st.text_input(
        "Output Directory",
        value="./output",
        help="Root directory for generated projects",
    )

    prompt = st.text_area(
        "Build Prompt",
        value="",
        height=120,
        placeholder="Describe the application you want to build…",
        help="Natural language description of your project",
    )

    st.markdown("---")
    st.markdown('<p class="sidebar-section">MODEL CONFIG</p>', unsafe_allow_html=True)

    model = st.selectbox(
        "Primary Model",
        options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gemini-2.5-flash",
                 "claude-sonnet-4-20250514", "llama-3.3-70b-versatile"],
        index=0,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        arch_model = st.text_input("Architect Model", value="", placeholder="auto")
    with col_b:
        eng_model = st.text_input("Engineer Model", value="", placeholder="auto")

    budget = st.slider("Budget (USD)", min_value=0.5, max_value=20.0, value=5.0, step=0.5)

    st.markdown("---")
    st.markdown('<p class="sidebar-section">BUILD OPTIONS</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        docker = st.checkbox("Docker", value=True)
        debug = st.checkbox("Auto-Debug", value=True)
    with col2:
        readme = st.checkbox("README", value=True)
        voice = st.checkbox("Voice", value=False)

    platform = st.selectbox("Platform", ["python", "android", "linux"])

    st.markdown("---")
    st.markdown('<p class="sidebar-section">ACTIONS</p>', unsafe_allow_html=True)

    col_s, col_r = st.columns(2)
    with col_s:
        start_build = st.button("⚡ BUILD", use_container_width=True, type="primary",
                                disabled=st.session_state.build_running)
    with col_r:
        resume_build = st.button("♻ RESUME", use_container_width=True,
                                 disabled=st.session_state.build_running)

    col_st, col_rs = st.columns(2)
    with col_st:
        check_status = st.button("📊 STATUS", use_container_width=True)
    with col_rs:
        reset_checkpoint = st.button("🗑 RESET", use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════

st.markdown("""
<div class="engine-header">
    <h1>🧬 Nexus Suite</h1>
    <p>Autonomous Intelligence & Creation Suite — High-Stability Pipeline</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_project_path():
    return os.path.join(output_dir, project_name)


def render_phase_stepper(progress: dict):
    """Render the visual phase progress tracker."""
    st.markdown("### 📡 Build Phases")

    phase_icons = {
        "INIT": "🔧", "ENHANCED": "🧠", "RESEARCHED": "🔍",
        "ARCHITECTED": "📐", "ASSEMBLED": "🏗", "ENGINEERED": "⚙️",
        "AUDITED": "🔎", "DEPLOYED": "🚀", "FINALIZED": "✅",
    }

    for phase_name, info in progress.get("phases", {}).items():
        icon = phase_icons.get(phase_name, "○")
        status = info.get("status", "○")

        if status == "✓":
            css_class = "done"
            icon_display = "✅"
        elif status == "⏳":
            css_class = "active"
            icon_display = "⏳"
        else:
            css_class = ""
            icon_display = "○"

        cost_str = f"${info.get('cost', 0):.4f}" if info.get('cost') else ""
        dur_str = f"{info.get('duration', 0):.1f}s" if info.get('duration') else ""
        meta = f"{cost_str}  {dur_str}".strip()

        st.markdown(f"""
        <div class="phase-card {css_class}">
            <span class="phase-icon">{icon_display}</span>
            <span class="phase-name">{icon} {phase_name}</span>
            <span class="phase-meta">{meta}</span>
        </div>
        """, unsafe_allow_html=True)


def render_stats(progress: dict):
    """Render stats cards."""
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{progress.get('percent', 0)}%</div>
            <div class="stat-label">Progress</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{progress.get('completed', 0)}/{progress.get('total', 9)}</div>
            <div class="stat-label">Phases</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">${progress.get('total_cost', 0):.4f}</div>
            <div class="stat-label">Total Cost</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        dur = progress.get('total_duration', 0)
        if dur > 60:
            dur_display = f"{dur/60:.1f}m"
        else:
            dur_display = f"{dur:.0f}s"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{dur_display}</div>
            <div class="stat-label">Duration</div>
        </div>
        """, unsafe_allow_html=True)


def render_log_console(log_lines: list):
    """Render the live build log."""
    if not log_lines:
        st.info("No build logs yet. Click **⚡ BUILD** to start.")
        return

    html_lines = []
    for entry in log_lines[-200:]:  # Show last 200 lines
        ts = entry.get("timestamp", entry.get("time", ""))
        tag = entry.get("tag", "SYSTEM")
        msg = entry.get("message", "")
        # Escape HTML
        msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        tag_class = f"log-tag-{tag}"
        html_lines.append(
            f'<p class="log-line">'
            f'<span class="log-ts">[{ts}]</span> '
            f'<span class="{tag_class}">[{tag}]</span> '
            f'<span class="log-msg">{msg}</span>'
            f'</p>'
        )

    log_html = "\n".join(html_lines)
    st.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)


def render_file_explorer(project_path: str):
    """Render a file explorer for the built project."""
    if not os.path.exists(project_path):
        st.info("No project directory yet.")
        return

    files = []
    for root, dirs, filenames in os.walk(project_path):
        # Skip hidden/checkpoint files
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.startswith(".overlord"):
                continue
            fpath = os.path.join(root, fn)
            rel = os.path.relpath(fpath, project_path)
            size = os.path.getsize(fpath)
            files.append((rel, size))

    if not files:
        st.info("No files generated yet.")
        return

    for rel, size in files:
        if size > 1024:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size} B"

        ext = os.path.splitext(rel)[1]
        icon = {
            ".py": "🐍", ".js": "📜", ".ts": "📘", ".json": "📋",
            ".md": "📝", ".html": "🌐", ".css": "🎨", ".yml": "⚙️",
            ".yaml": "⚙️", ".txt": "📄", ".sh": "🔧", ".bat": "🔧",
        }.get(ext, "📄")

        st.markdown(f'<div class="file-item">{icon} {rel} <span style="color:#6b6f80">({size_str})</span></div>',
                    unsafe_allow_html=True)

    # File viewer
    selected = st.selectbox("View file contents", ["(none)"] + [f[0] for f in files])
    if selected and selected != "(none)":
        fpath = os.path.join(project_path, selected)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            ext = os.path.splitext(selected)[1].lstrip(".")
            lang = {"py": "python", "js": "javascript", "ts": "typescript",
                    "json": "json", "md": "markdown", "html": "html",
                    "css": "css", "yml": "yaml", "yaml": "yaml"}.get(ext, "")
            st.code(content, language=lang, line_numbers=True)
        except Exception as e:
            st.error(f"Cannot read {selected}: {e}")


# ═══════════════════════════════════════════════════════════════
#  BUILD EXECUTION
# ═══════════════════════════════════════════════════════════════

def start_build_thread(config: BuildConfig, resume: bool = False):
    """Start the build in a background thread."""
    engine = CreationEngine(config)
    st.session_state.engine = engine
    st.session_state.build_running = True
    st.session_state.build_error = None
    st.session_state.log_lines = []

    def _run():
        try:
            engine.run(resume=resume, blocking=True)
            if engine.error:
                st.session_state.build_error = engine.error
            # Capture artifacts after build
            if engine.artifacts:
                st.session_state.build_artifacts = engine.artifacts
        except Exception as e:
            st.session_state.build_error = str(e)
        finally:
            st.session_state.build_running = False
            # Capture final logs
            st.session_state.log_lines = engine.log_capture.get_all_lines()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


# ═══════════════════════════════════════════════════════════════
#  ACTION HANDLERS
# ═══════════════════════════════════════════════════════════════

if start_build:
    if not prompt.strip():
        st.error("Please enter a build prompt in the sidebar.")
    elif prompt.strip().lower() == "system check":
        from creation_engine.engine_eval import EngineSelfEval
        st.info("🔎 Running System Diagnostics...")
        evaluator = EngineSelfEval()
        report = evaluator.run_eval()
        
        st.markdown("### 🛡️ System Status Report")
        col_rep1, col_rep2 = st.columns(2)
        for i, (key, val) in enumerate(report.items()):
            icon = "✅" if "Pass" in val or "Clean" in val or "Optimized" in val else "⚠️"
            with (col_rep1 if i % 2 == 0 else col_rep2):
                st.markdown(f"{icon} **{key}**: `{val}`")
    else:
        # Check for specific seed synthesis keywords if needed, or just run standard build
        # The standard build engine handles synthesis prompts fine, so we just pass it through.
        config = BuildConfig(
            project_name=project_name,
            prompt=prompt,
            output_dir=output_dir,
            model=model,
            arch_model=arch_model,
            eng_model=eng_model,
            budget=budget,
            platform=platform,
            docker=docker,
            readme=readme,
            debug=debug,
            voice=voice,
        )
        start_build_thread(config, resume=False)
        st.rerun()

if resume_build:
    config = BuildConfig(
        project_name=project_name,
        prompt=prompt or "Resume build",
        output_dir=output_dir,
        model=model,
        arch_model=arch_model,
        eng_model=eng_model,
        budget=budget,
        platform=platform,
        docker=docker,
        readme=readme,
        debug=debug,
        voice=voice,
    )
    start_build_thread(config, resume=True)
    st.rerun()

if reset_checkpoint:
    pp = get_project_path()
    os.makedirs(pp, exist_ok=True)
    reducer = StateReducer(pp)
    reducer.reset()
    st.success(f"✓ Checkpoints cleared for '{project_name}'")
    st.session_state.log_lines = []
    st.session_state.last_progress = None


# ═══════════════════════════════════════════════════════════════
#  MAIN LAYOUT
# ═══════════════════════════════════════════════════════════════

# Fetch current progress
project_path = get_project_path()
if os.path.exists(project_path):
    reducer = StateReducer(project_path)
    progress = reducer.get_progress()
else:
    progress = {
        "build_id": "—",
        "current_phase": None,
        "completed": 0,
        "total": 9,
        "percent": 0,
        "phases": {p: {"status": "○", "cost": 0, "duration": 0}
                   for p in StateReducer.PHASES},
        "total_cost": 0,
        "total_duration": 0,
        "started_at": None,
        "last_checkpoint": None,
        # Interaction Architecture State
        "thinking_bubble": "Idle",  # Current Architect thought stream
        "healer_status": {          # Healer Status Bar badges
            "Sentinel": "idle",     # idle, running, pass, fail
            "Alchemist": "idle",
            "Stealth": "idle"
        },
        "breakpoint_request": None  # Current interactive breakpoint (e.g. {sender: "Sentinel", msg: "Syntax error..."})
    }

# Status check action
if check_status:
    st.session_state.last_progress = progress

# Running indicator
if st.session_state.build_running:
    st.warning("🔧 **Build in progress…** The page will update when phases complete.")
    # Auto-refresh
    time.sleep(2)
    st.rerun()

# Error display
if st.session_state.build_error:
    st.error(f"**Build Error:** {st.session_state.build_error}")
    st.info("💡 Use **♻ RESUME** to continue from the last successful checkpoint.")

# Stats row
render_stats(progress)

st.markdown("---")

# Main columns

# ═══════════════════════════════════════════════════════════════
#  INTERACTION ARCHITECTURE — UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

# 1. Interactive Breakpoint (The "Text Message")
if progress.get("breakpoint_request"):
    bp = progress["breakpoint_request"]
    with st.container():
        st.info(f"💬 **{bp.get('sender', 'System')}:** {bp.get('content', '')}")
        col_yes, col_no = st.columns(2)
        if col_yes.button("✅ Approve Fix"):
            # Signal approval (implementation would invoke backend handler)
            st.success("Fix approved. Resuming...")
            st.session_state.last_progress["breakpoint_request"] = None  # Clear state locally
            st.rerun()
        if col_no.button("❌ Show Code"):
             st.code(bp.get('code_snippet', '# No code provided'), language='python')

# 2. Healer Status Bar
h_status = progress.get("healer_status", {})
if any(s != "idle" for s in h_status.values()):
    cols = st.columns(len(h_status))
    for idx, (healer, state) in enumerate(h_status.items()):
        with cols[idx]:
            color = "gray"
            if state == "running": color = "orange"
            elif state == "pass": color = "green" 
            elif state == "fail": color = "red"
            st.markdown(f"**{healer}**: <span style='color:{color}'>● {state.upper()}</span>", unsafe_allow_html=True)
    st.markdown("---")

# 3. The Thinking Bubble
if progress.get("thinking_bubble") and progress["thinking_bubble"] != "Idle":
    st.markdown(f"""
    <div style="background: #1a1b26; border-left: 4px solid #7aa2f7; padding: 10px; margin-bottom: 20px; font-family: monospace; color: #a9b1d6;">
        <strong>🧠 Architect Thought Stream:</strong><br>
        {progress["thinking_bubble"]}
    </div>
    """, unsafe_allow_html=True)


col_left, col_right = st.columns([3, 2])

with col_left:
    # Tabs: Log | File Explorer | Artifacts | Decompiler | Architecture
    tab_log, tab_files, tab_artifacts, tab_events, tab_decompile, tab_arch = st.tabs([
        "📡 Live Log", "📁 Files", "📦 Artifacts", "📋 Events", "🧬 Nexus Decompiler", "🏗 System Arch"
    ])

    with tab_log:
        # Get logs from engine if running, or from session state
        if st.session_state.engine and hasattr(st.session_state.engine, 'log_capture'):
            log_lines = st.session_state.engine.log_capture.get_all_lines()
            st.session_state.log_lines = log_lines
        else:
            log_lines = st.session_state.log_lines

        render_log_console(log_lines)

    with tab_files:
        render_file_explorer(project_path)

    with tab_artifacts:
        st.markdown("### 📦 Harvested Artifacts")
        st.markdown("Media, documents, and data files produced by the generated program.")

        artifacts = st.session_state.get("build_artifacts", [])
        if not artifacts:
            # Try scanning the artifacts dir
            artifacts_dir = os.path.join(project_path, "artifacts")
            if os.path.isdir(artifacts_dir):
                for fname in sorted(os.listdir(artifacts_dir)):
                    fpath = os.path.join(artifacts_dir, fname)
                    if os.path.isfile(fpath):
                        ext = os.path.splitext(fname.lower())[1]
                        size = os.path.getsize(fpath)
                        artifact_type = "image" if ext in {".png",".jpg",".jpeg",".gif",".webp",".bmp",".svg"} \
                            else "video" if ext in {".mp4",".avi",".mov",".mkv",".webm"} \
                            else "audio" if ext in {".mp3",".wav",".ogg",".flac",".aac"} \
                            else "document" if ext in {".pdf",".docx",".xlsx",".pptx"} \
                            else "data" if ext in {".csv",".parquet",".sqlite",".db"} \
                            else "file"
                        artifacts.append({
                            "path": fname,
                            "full_path": fpath,
                            "artifact_path": fpath,
                            "type": artifact_type,
                            "extension": ext,
                            "size_bytes": size,
                            "size_human": f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB",
                        })

        if artifacts:
            st.success(f"✓ {len(artifacts)} artifact(s) collected")

            for art in artifacts:
                with st.expander(f"{art['path']} — {art.get('size_human', '?')} ({art['type']})", expanded=True):
                    art_path = art.get("artifact_path", art.get("full_path", ""))

                    if art["type"] == "image":
                        st.image(art_path, caption=art["path"], use_container_width=True)

                    elif art["type"] == "video":
                        st.video(art_path)

                    elif art["type"] == "audio":
                        st.audio(art_path)

                    elif art["type"] == "data" and art["extension"] == ".csv":
                        try:
                            import pandas as pd
                            df = pd.read_csv(art_path)
                            st.dataframe(df.head(50), use_container_width=True)
                        except Exception:
                            st.info("CSV preview unavailable")
                    else:
                        st.info(f"📄 {art['type'].title()} file — use download button below")

                    # Download button for all artifacts
                    if os.path.exists(art_path):
                        with open(art_path, "rb") as fp:
                            st.download_button(
                                f"⬇ Download {art['path']}",
                                data=fp.read(),
                                file_name=os.path.basename(art["path"]),
                                use_container_width=True,
                            )
        else:
            st.info("No artifacts yet. Run a build that produces media (images, videos, PDFs) to see results here.")
    with tab_events:
        st.markdown("### Event Audit Log")
        if os.path.exists(project_path):
            events = StateReducer(project_path).get_events(last_n=30)
            if events:
                for ev in reversed(events):
                    ts = ev.get("timestamp", "?")[:19]
                    action = ev.get("action", "?")
                    payload = ev.get("payload", {})
                    phase = payload.get("phase", "")
                    detail = f" — {phase}" if phase else ""
                    st.markdown(f"`{ts}` **{action}**{detail}")
            else:
                st.info("No events recorded yet.")
        else:
            st.info("No project directory found.")

    with tab_decompile:
        st.markdown("### 🧬 Nexus Decompiler")
        st.markdown("Digest an existing project into instructions and architectural overviews.")
        
        decompile_path = st.text_input("Source Directory to Decompile", value="", placeholder="C:/path/to/my/project")
        
        if st.button("🚀 INITIATE DIGESTION", use_container_width=True):
            if not decompile_path or not os.path.exists(decompile_path):
                st.error("Please provide a valid directory path.")
            else:
                with st.spinner("Digesting project structure and logic…"):
                    decompiler = NexusDecompiler()
                    digest = decompiler.digest_project(decompile_path)
                    
                    st.success(f"✓ Digestion complete: {digest['project_name']}")
                    
                    d_tab1, d_tab2, d_tab3 = st.tabs(["🏗 Architecture", "📄 Documentation", "📊 Analysis"])
                    
                    with d_tab1:
                        st.markdown(digest["architecture"])
                    with d_tab2:
                        st.markdown(digest["documentation"])
                    with d_tab3:
                        st.json(digest["analysis"])
                        
                    st.info("💡 You can now copy these instructions into the **NEXUS SUITE** creator tab to rebuild or modularize the project.")

    with tab_arch:
        st.markdown("### 🏗 Visual Blueprint (Mermaid.js)")
        mermaid_path = os.path.join(project_path, "blueprint.mermaid")
        if os.path.exists(mermaid_path):
            with open(mermaid_path, "r", encoding="utf-8") as f:
                mermaid_code = f.read()
            st.markdown(f"```mermaid\n{mermaid_code}\n```")
            st.info("💡 This diagram is auto-generated by the Nexus Architect during the planning phase.")
        else:
            st.info("No visual blueprint found for this project. Result of the Architect phase will appear here.")

with col_right:
    render_phase_stepper(progress)

    # Build info
    st.markdown("---")
    st.markdown("### 🔑 Build Info")
    if progress.get("build_id") and progress["build_id"] != "—":
        st.code(f"Build ID:    {progress['build_id']}\n"
                f"Started:     {progress.get('started_at', 'N/A')}\n"
                f"Checkpoint:  {progress.get('last_checkpoint', 'N/A')}\n"
                f"Phase:       {progress.get('current_phase', 'Not started')}",
                language="yaml")
    else:
        st.info("No active build. Configure settings and click ⚡ BUILD.")

    # Docker sandbox status
    st.markdown("### 🐳 Docker Sandbox")
    sandbox = DockerSandbox(project_path, project_name)
    if sandbox.available:
        st.success("Docker is available")
        if st.button("🔨 Build Sandbox Image"):
            with st.spinner("Building Docker image…"):
                ok, msg = sandbox.build()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        st.warning("Docker not available on this system")
