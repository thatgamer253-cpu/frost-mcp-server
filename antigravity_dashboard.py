#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  ANTIGRAVITY DASHBOARD — Real-Time Build Command Center
  
  A Streamlit dashboard that visualizes the Creator's build
  pipeline in real time. Reads events from build_events.jsonl
  written by the EventBus in pipeline_events.py.

  Launch:
    streamlit run antigravity_dashboard.py -- --project /path/to/project
    streamlit run antigravity_dashboard.py -- --demo

══════════════════════════════════════════════════════════════
"""

import streamlit as st
import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# ── Page Config (MUST be first Streamlit call) ───────────────
st.set_page_config(
    page_title="Antigravity — Build Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Resolve project path from CLI args ───────────────────────
def get_project_path():
    """Parse --project from Streamlit's CLI args."""
    # Streamlit passes extra args after '--'
    args = sys.argv[1:]
    if "--demo" in args:
        return "__demo__"
    for i, arg in enumerate(args):
        if arg == "--project" and i + 1 < len(args):
            return args[i + 1]
    # Fallback: check environment
    return os.environ.get("ANTIGRAVITY_PROJECT", "")


PROJECT_PATH = get_project_path()
IS_DEMO = PROJECT_PATH == "__demo__"
EVENTS_FILE = os.path.join(PROJECT_PATH, "build_events.jsonl") if not IS_DEMO else ""


# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global Reset ─────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #13131f 50%, #0d0d1a 100%);
        color: #e0e0f0;
    }
    
    /* Hide default Streamlit chrome */
    #MainMenu, header, footer { visibility: hidden; }
    .block-container { padding: 1rem 2rem; max-width: 100%; }
    
    /* ── Top Bar ──────────────────────────────── */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: linear-gradient(90deg, rgba(108,99,255,0.15) 0%, rgba(0,200,150,0.08) 100%);
        border: 1px solid rgba(108,99,255,0.25);
        border-radius: 12px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
    }
    .top-bar .title {
        font-size: 22px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF, #00C896);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .top-bar .meta {
        font-size: 12px;
        color: #8888aa;
        display: flex;
        gap: 24px;
        align-items: center;
    }
    .top-bar .meta .badge {
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 11px;
    }
    .badge-running {
        background: rgba(0,200,100,0.15);
        color: #00ff88;
        border: 1px solid rgba(0,255,136,0.3);
    }
    .badge-complete {
        background: rgba(108,99,255,0.15);
        color: #6C63FF;
        border: 1px solid rgba(108,99,255,0.3);
    }
    .badge-failed {
        background: rgba(255,59,92,0.15);
        color: #FF3B5C;
        border: 1px solid rgba(255,59,92,0.3);
    }
    
    /* ── Phase Stepper ────────────────────────── */
    .phase-stepper {
        display: flex;
        gap: 4px;
        align-items: stretch;
        margin-bottom: 20px;
    }
    .phase-step {
        flex: 1;
        padding: 10px 12px;
        border-radius: 8px;
        text-align: center;
        font-size: 11px;
        font-weight: 600;
        transition: all 0.3s ease;
        position: relative;
    }
    .phase-step .icon { font-size: 18px; display: block; margin-bottom: 4px; }
    .phase-step .label { opacity: 0.9; }
    
    .phase-waiting {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        color: #555577;
    }
    .phase-active {
        background: linear-gradient(135deg, rgba(108,99,255,0.25), rgba(0,200,150,0.15));
        border: 1px solid rgba(108,99,255,0.5);
        color: #ffffff;
        box-shadow: 0 0 20px rgba(108,99,255,0.2);
        animation: pulse-glow 2s ease-in-out infinite;
    }
    .phase-done {
        background: rgba(0,200,100,0.1);
        border: 1px solid rgba(0,255,136,0.25);
        color: #00ff88;
    }
    .phase-error {
        background: rgba(255,59,92,0.1);
        border: 1px solid rgba(255,59,92,0.25);
        color: #FF3B5C;
    }
    
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 15px rgba(108,99,255,0.15); }
        50% { box-shadow: 0 0 30px rgba(108,99,255,0.35); }
    }
    
    /* ── Log Panel ────────────────────────────── */
    .log-container {
        background: #0a0a12;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px;
        max-height: 500px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
        font-size: 11.5px;
        line-height: 1.7;
    }
    .log-line {
        padding: 1px 0;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .log-line .tag {
        font-weight: 700;
        margin-right: 6px;
    }
    .log-line .time {
        color: #444466;
        margin-right: 8px;
        font-size: 10px;
    }
    
    /* Tag colors */
    .tag-ARCHITECT  { color: #00D4FF; }
    .tag-ENGINEER   { color: #FFD700; }
    .tag-REVIEWER   { color: #00FFAA; }
    .tag-DEBUGGER   { color: #FF69B4; }
    .tag-WISDOM     { color: #E040FB; }
    .tag-DOCKER     { color: #69B1FF; }
    .tag-SYSTEM     { color: #8888AA; }
    .tag-ERROR      { color: #FF3B5C; }
    .tag-SUCCESS    { color: #00FF88; }
    .tag-GATE       { color: #FFA500; }
    .tag-SEARCH     { color: #00D4FF; }
    .tag-BUNDLER    { color: #DDA0DD; }
    .tag-CONFIG     { color: #FFA500; }
    .tag-LINT       { color: #FFD700; }
    
    /* ── Code Viewer ─────────────────────────── */
    .code-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 14px;
        background: rgba(108,99,255,0.08);
        border: 1px solid rgba(108,99,255,0.15);
        border-bottom: none;
        border-radius: 10px 10px 0 0;
        font-size: 12px;
        font-weight: 600;
    }
    .code-panel-header .filepath {
        color: #00D4FF;
        font-family: 'JetBrains Mono', monospace;
    }
    .code-panel-header .lang-badge {
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(0,200,150,0.15);
        color: #00C896;
        font-size: 10px;
        text-transform: uppercase;
    }
    
    /* ── Stats Cards ─────────────────────────── */
    .stat-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 14px 18px;
        text-align: center;
    }
    .stat-card .value {
        font-size: 24px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF, #00C896);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-card .label {
        font-size: 10px;
        color: #8888aa;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }
    
    /* ── Docker Status ────────────────────────── */
    .docker-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .docker-running {
        background: rgba(0,150,255,0.12);
        color: #69B1FF;
        border: 1px solid rgba(100,180,255,0.3);
    }
    .docker-stopped {
        background: rgba(255,255,255,0.05);
        color: #666688;
        border: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────
if "events" not in st.session_state:
    st.session_state.events = []
if "last_line" not in st.session_state:
    st.session_state.last_line = 0
if "current_phase" not in st.session_state:
    st.session_state.current_phase = "planning"
if "current_file" not in st.session_state:
    st.session_state.current_file = ""
if "current_code" not in st.session_state:
    st.session_state.current_code = ""
if "current_language" not in st.session_state:
    st.session_state.current_language = "python"
if "build_complete" not in st.session_state:
    st.session_state.build_complete = False
if "build_success" not in st.session_state:
    st.session_state.build_success = False
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "budget" not in st.session_state:
    st.session_state.budget = 5.0
if "docker_status" not in st.session_state:
    st.session_state.docker_status = "stopped"
if "files_written" not in st.session_state:
    st.session_state.files_written = 0
if "log_filter" not in st.session_state:
    st.session_state.log_filter = "ALL"


# ── Demo Data Generator ─────────────────────────────────────
def generate_demo_events():
    """Generate realistic demo events for testing the dashboard."""
    return [
        {"event_type": "build_start", "phase": "planning", "status": "active",
         "message": "Build pipeline initialized", "tag": "SYSTEM",
         "timestamp": time.time() - 120, "metadata": {"project_path": "/demo/MyApp"}},
        {"event_type": "phase_change", "phase": "planning", "status": "active",
         "message": "Phase: 🧠 Planning", "tag": "", "timestamp": time.time() - 115},
        {"event_type": "log", "phase": "planning", "tag": "SYSTEM",
         "message": "🛡️  Loaded 8 generation rule(s) from global wisdom", "timestamp": time.time() - 114},
        {"event_type": "log", "phase": "planning", "tag": "PROMPT",
         "message": "Enhancing prompt: 'Build a task manager'", "timestamp": time.time() - 110},
        {"event_type": "log", "phase": "planning", "tag": "SEARCH",
         "message": "  🔍 Pre-flight: Verifying FastAPI, React, PostgreSQL", "timestamp": time.time() - 105},
        {"event_type": "log", "phase": "planning", "tag": "SEARCH",
         "message": "  ✓ fastapi==0.109.0, react==18.2.0, psycopg2==2.9.9", "timestamp": time.time() - 100},
        {"event_type": "log", "phase": "planning", "tag": "ARCHITECT",
         "message": "Engaged — blueprinting architecture...", "timestamp": time.time() - 95},
        {"event_type": "log", "phase": "planning", "tag": "ARCHITECT",
         "message": "  📐 Planned 12 files across 4 modules", "timestamp": time.time() - 85},
        {"event_type": "phase_change", "phase": "provisioning", "status": "active",
         "message": "Phase: 🏗️ Provisioning", "tag": "", "timestamp": time.time() - 80},
        {"event_type": "log", "phase": "provisioning", "tag": "ASSEMBLER",
         "message": "  Created: backend/main.py, backend/models.py, frontend/App.tsx", "timestamp": time.time() - 78},
        {"event_type": "phase_change", "phase": "coding", "status": "active",
         "message": "Phase: ⚙️ Coding", "tag": "", "timestamp": time.time() - 70},
        {"event_type": "log", "phase": "coding", "tag": "ENGINEER",
         "message": "Engaged — writing backend/main.py [1/12]", "timestamp": time.time() - 68},
        {"event_type": "file_write", "phase": "coding", "file": "backend/main.py",
         "code": 'from fastapi import FastAPI, HTTPException\nfrom fastapi.middleware.cors import CORSMiddleware\nimport uvicorn\n\napp = FastAPI(title="Task Manager API", version="1.0.0")\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["*"],\n    allow_methods=["*"],\n    allow_headers=["*"],\n)\n\n@app.get("/health")\nasync def health_check():\n    return {"status": "healthy", "uptime": "running"}\n\n@app.get("/api/tasks")\nasync def get_tasks():\n    return {"tasks": [], "count": 0}\n\nif __name__ == "__main__":\n    uvicorn.run(app, host="0.0.0.0", port=8000)',
         "language": "python", "message": "Writing: backend/main.py", "timestamp": time.time() - 65},
        {"event_type": "cost_update", "phase": "coding",
         "message": "Cost: $0.0042 / $5.00", "metadata": {"total_cost": 0.0042, "budget": 5.0}, "timestamp": time.time() - 60},
        {"event_type": "log", "phase": "coding", "tag": "REVIEWER",
         "message": "  ✓ backend/main.py APPROVED (Clean code)", "timestamp": time.time() - 55},
        {"event_type": "log", "phase": "coding", "tag": "WISDOM",
         "message": "  🛡️ Auto-fixed 1 violation(s) in backend/config.py", "timestamp": time.time() - 50},
        {"event_type": "log", "phase": "coding", "tag": "ENGINEER",
         "message": "Engaged — writing frontend/App.tsx [5/12]", "timestamp": time.time() - 45},
        {"event_type": "file_write", "phase": "coding", "file": "frontend/App.tsx",
         "code": 'import React from "react";\nimport { TaskList } from "./components/TaskList";\nimport { Header } from "./components/Header";\nimport "./App.css";\n\nexport default function App() {\n  return (\n    <div className="app">\n      <Header />\n      <main>\n        <TaskList />\n      </main>\n    </div>\n  );\n}',
         "language": "typescript", "message": "Writing: frontend/App.tsx", "timestamp": time.time() - 40},
        {"event_type": "cost_update", "phase": "coding",
         "message": "Cost: $0.0189 / $5.00", "metadata": {"total_cost": 0.0189, "budget": 5.0}, "timestamp": time.time() - 35},
        {"event_type": "phase_change", "phase": "reviewing", "status": "active",
         "message": "Phase: 🔍 Reviewing", "tag": "", "timestamp": time.time() - 25},
        {"event_type": "log", "phase": "reviewing", "tag": "GATE",
         "message": "  ✓ All cross-file imports verified", "timestamp": time.time() - 22},
        {"event_type": "log", "phase": "reviewing", "tag": "CONFIG",
         "message": "  ✓ All config attribute references verified", "timestamp": time.time() - 20},
        {"event_type": "phase_change", "phase": "testing", "status": "active",
         "message": "Phase: 🐛 Testing", "tag": "", "timestamp": time.time() - 15},
        {"event_type": "docker_status", "status": "running",
         "message": "Docker: Container abc123def provisioned", "metadata": {"container_id": "abc123def456"}, "timestamp": time.time() - 12},
        {"event_type": "log", "phase": "testing", "tag": "DEBUGGER",
         "message": "  ✓ main.py exits cleanly (exit code 0)", "timestamp": time.time() - 8},
        {"event_type": "docker_status", "status": "stopped",
         "message": "Docker: Container destroyed", "metadata": {"container_id": "abc123def456"}, "timestamp": time.time() - 5},
        {"event_type": "phase_change", "phase": "success", "status": "done",
         "message": "Phase: ✅ Success", "tag": "", "timestamp": time.time() - 2},
        {"event_type": "cost_update", "phase": "success",
         "message": "Cost: $0.0312 / $5.00", "metadata": {"total_cost": 0.0312, "budget": 5.0}, "timestamp": time.time() - 1},
        {"event_type": "build_complete", "phase": "success", "status": "done",
         "message": "Built 12 files in 118s", "metadata": {"elapsed": 118.4, "success": True}, "timestamp": time.time()},
    ]


# ── Event Loader ─────────────────────────────────────────────
def load_events():
    """Load new events from the JSONL file."""
    if IS_DEMO:
        if not st.session_state.events:
            st.session_state.events = generate_demo_events()
            st.session_state.build_complete = True
            st.session_state.build_success = True
        return

    if not EVENTS_FILE or not os.path.exists(EVENTS_FILE):
        return

    try:
        new_events = []
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < st.session_state.last_line:
                    continue
                line = line.strip()
                if line:
                    try:
                        new_events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if new_events:
            st.session_state.last_line += len(new_events)
            st.session_state.events.extend(new_events)

            # Process events for state updates
            for ev in new_events:
                _process_event(ev)
    except Exception:
        pass


def _process_event(ev: dict):
    """Update session state based on a new event."""
    etype = ev.get("event_type", "")

    if etype == "phase_change":
        st.session_state.current_phase = ev.get("phase", st.session_state.current_phase)

    elif etype == "file_write":
        st.session_state.current_file = ev.get("file", "")
        st.session_state.current_code = ev.get("code", "")
        st.session_state.current_language = ev.get("language", "python")
        st.session_state.files_written += 1

    elif etype == "cost_update":
        meta = ev.get("metadata", {})
        st.session_state.total_cost = meta.get("total_cost", st.session_state.total_cost)
        st.session_state.budget = meta.get("budget", st.session_state.budget)

    elif etype == "docker_status":
        st.session_state.docker_status = ev.get("status", "stopped")

    elif etype == "build_complete":
        st.session_state.build_complete = True
        meta = ev.get("metadata", {})
        st.session_state.build_success = meta.get("success", False)
        st.session_state.current_phase = "success" if st.session_state.build_success else "failed"


# ── Render: Top Bar ──────────────────────────────────────────
def render_top_bar():
    """Render the dashboard top bar with project info and status."""
    project_name = os.path.basename(PROJECT_PATH) if not IS_DEMO else "Demo Project"

    # Determine status badge
    if st.session_state.build_complete:
        if st.session_state.build_success:
            badge_class = "badge-complete"
            badge_text = "COMPLETE"
        else:
            badge_class = "badge-failed"
            badge_text = "FAILED"
    else:
        badge_class = "badge-running"
        badge_text = "BUILDING"

    # Calculate elapsed time
    events = st.session_state.events
    start_time = events[0]["timestamp"] if events else time.time()
    end_time = events[-1]["timestamp"] if events and st.session_state.build_complete else time.time()
    elapsed = end_time - start_time
    elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

    # Docker status
    docker_status = st.session_state.docker_status
    docker_class = "docker-running" if docker_status == "running" else "docker-stopped"
    docker_icon = "🐳" if docker_status == "running" else "⏹"

    st.markdown(f"""
    <div class="top-bar">
        <div class="title">🚀 Antigravity — {project_name}</div>
        <div class="meta">
            <span>⏱ {elapsed_str}</span>
            <span>📁 {st.session_state.files_written} files</span>
            <span>💰 ${st.session_state.total_cost:.4f}</span>
            <span class="docker-indicator {docker_class}">{docker_icon} Docker</span>
            <span class="badge {badge_class}">{badge_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Render: Phase Stepper ────────────────────────────────────
def render_phase_stepper():
    """Render the visual pipeline progress stepper."""
    phases = [
        ("planning",     "🧠", "Planning"),
        ("provisioning", "🏗️", "Provisioning"),
        ("coding",       "⚙️", "Coding"),
        ("reviewing",    "🔍", "Reviewing"),
        ("testing",      "🐛", "Testing"),
        ("deploying",    "🚀", "Deploying"),
        ("success",      "✅", "Success"),
    ]

    current = st.session_state.current_phase
    phase_order = [p[0] for p in phases]
    current_idx = phase_order.index(current) if current in phase_order else -1

    # If failed, mark current as error
    if current == "failed":
        current_idx = len(phases) - 1  # Will mark last reached phase as error

    steps_html = ""
    for i, (phase_id, icon, label) in enumerate(phases):
        if phase_id == current or (current == "failed" and i == current_idx):
            css_class = "phase-error" if current == "failed" else "phase-active"
        elif i < current_idx:
            css_class = "phase-done"
        else:
            css_class = "phase-waiting"

        steps_html += f"""
        <div class="phase-step {css_class}">
            <span class="icon">{icon}</span>
            <span class="label">{label}</span>
        </div>
        """

    st.markdown(f'<div class="phase-stepper">{steps_html}</div>', unsafe_allow_html=True)


# ── Render: Log Panel ────────────────────────────────────────
def render_log_panel():
    """Render the streaming log panel with color-coded tags."""
    st.markdown("#### 📡 Antigravity Log")

    # Filter buttons
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    with filter_col1:
        if st.button("ALL", type="primary" if st.session_state.log_filter == "ALL" else "secondary", use_container_width=True):
            st.session_state.log_filter = "ALL"
    with filter_col2:
        if st.button("❌ Errors", type="primary" if st.session_state.log_filter == "ERRORS" else "secondary", use_container_width=True):
            st.session_state.log_filter = "ERRORS"
    with filter_col3:
        if st.button("🛡️ Wisdom", type="primary" if st.session_state.log_filter == "WISDOM" else "secondary", use_container_width=True):
            st.session_state.log_filter = "WISDOM"
    with filter_col4:
        if st.button("🐳 Docker", type="primary" if st.session_state.log_filter == "DOCKER" else "secondary", use_container_width=True):
            st.session_state.log_filter = "DOCKER"
    with filter_col5:
        if st.button("⚙️ Engineer", type="primary" if st.session_state.log_filter == "ENGINEER" else "secondary", use_container_width=True):
            st.session_state.log_filter = "ENGINEER"

    # Build log HTML
    events = st.session_state.events
    log_lines = []

    for ev in events:
        tag = ev.get("tag", "SYSTEM")
        message = ev.get("message", "")
        timestamp = ev.get("timestamp", 0)
        etype = ev.get("event_type", "")

        if not message:
            continue

        # Apply filter
        if st.session_state.log_filter != "ALL":
            filter_map = {
                "ERRORS": lambda: tag == "ERROR" or "error" in message.lower() or "❌" in message or "✗" in message,
                "WISDOM": lambda: tag in ("WISDOM", "GATE", "CONFIG", "DRY-RUN") or "wisdom" in message.lower(),
                "DOCKER": lambda: tag == "DOCKER" or etype == "docker_status",
                "ENGINEER": lambda: tag in ("ENGINEER", "LINT", "REVIEWER"),
            }
            filter_fn = filter_map.get(st.session_state.log_filter, lambda: True)
            if not filter_fn():
                continue

        # Format timestamp
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""

        # Escape HTML in message
        safe_message = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        tag_class = f"tag-{tag}" if tag else "tag-SYSTEM"
        log_lines.append(
            f'<div class="log-line">'
            f'<span class="time">{time_str}</span>'
            f'<span class="tag {tag_class}">[{tag}]</span>'
            f'{safe_message}</div>'
        )

    # Show last 200 lines
    visible_lines = log_lines[-200:]
    log_html = "\n".join(visible_lines) if visible_lines else '<div style="color:#555577; padding:20px; text-align:center;">Waiting for events...</div>'

    st.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)


# ── Render: Code Viewer ─────────────────────────────────────
def render_code_viewer():
    """Render the live code viewer showing the current file being written."""
    st.markdown("#### 💻 Live Code Viewer")

    filepath = st.session_state.current_file
    code = st.session_state.current_code
    language = st.session_state.current_language

    if filepath and code:
        st.markdown(f"""
        <div class="code-panel-header">
            <span class="filepath">📄 {filepath}</span>
            <span class="lang-badge">{language}</span>
        </div>
        """, unsafe_allow_html=True)
        st.code(code, language=language, line_numbers=True)
    else:
        st.info("Waiting for the Engineer to start writing code...")


# ── Render: Stats Cards ─────────────────────────────────────
def render_stats():
    """Render cost and progress stat cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cost = st.session_state.total_cost
        budget = st.session_state.budget
        pct = (cost / budget * 100) if budget > 0 else 0
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">${cost:.4f}</div>
            <div class="label">Cost ({pct:.1f}% of ${budget:.2f})</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{st.session_state.files_written}</div>
            <div class="label">Files Written</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        event_count = len(st.session_state.events)
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{event_count}</div>
            <div class="label">Pipeline Events</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # Count wisdom/guard events
        wisdom_count = sum(1 for e in st.session_state.events
                          if e.get("tag") in ("WISDOM", "GATE", "CONFIG", "DRY-RUN"))
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{wisdom_count}</div>
            <div class="label">Wisdom Triggers</div>
        </div>
        """, unsafe_allow_html=True)

    # Cost progress bar
    if st.session_state.budget > 0:
        progress = min(st.session_state.total_cost / st.session_state.budget, 1.0)
        st.progress(progress, text=f"Budget: ${st.session_state.total_cost:.4f} / ${st.session_state.budget:.2f}")


# ══════════════════════════════════════════════════════════════
#  MAIN LAYOUT
# ══════════════════════════════════════════════════════════════

# Load events
load_events()

# Process all loaded events for state
if IS_DEMO:
    for ev in st.session_state.events:
        _process_event(ev)

# ── Top Bar ──────────────────────────────────────────────────
render_top_bar()

# ── Phase Stepper ────────────────────────────────────────────
render_phase_stepper()

# ── Stats Row ────────────────────────────────────────────────
render_stats()

st.markdown("---")

# ── Main Content: Two Columns ────────────────────────────────
left_col, right_col = st.columns([3, 2])

with left_col:
    render_log_panel()

with right_col:
    render_code_viewer()

# ── Auto-refresh (if build is still running) ─────────────────
if not st.session_state.build_complete and not IS_DEMO:
    time.sleep(1)
    st.rerun()
