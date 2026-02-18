#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  ANTIGRAVITY CREATION ENGINE  —  Streamlit Dashboard

  Run:  streamlit run creation_engine_ui.py
  Requires: pip install streamlit docker
══════════════════════════════════════════════════════════════
"""

import streamlit as st
import os
import time
import json
import zipfile
import io
from datetime import datetime

# Engine Imports
from creation_engine.search import search_builds
from creation_engine.settings import load_settings, save_settings

# Page config (MUST be first Streamlit call)
st.set_page_config(
    page_title="Antigravity Creation Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary: #0a0a0f;
    --bg-card: #12121a;
    --bg-card-hover: #1a1a2e;
    --accent: #7c3aed;
    --accent-glow: rgba(124, 58, 237, 0.3);
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --border: #1e293b;
}

.stApp {
    font-family: 'Inter', sans-serif;
}

/* Phase badge */
.phase-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.phase-idle { background: #1e293b; color: #94a3b8; }
.phase-planning { background: #1e3a5f; color: #60a5fa; }
.phase-writing { background: #1a3520; color: #4ade80; }
.phase-reviewing { background: #3b1f0b; color: #fb923c; }
.phase-sandbox { background: #2e1065; color: #a78bfa; }
.phase-bundling { background: #312e81; color: #818cf8; }
.phase-complete { background: #064e3b; color: #34d399; }
.phase-failed { background: #450a0a; color: #f87171; }

/* Log entry */
.log-entry {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    padding: 3px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    line-height: 1.5;
}
.log-tag {
    display: inline-block;
    min-width: 90px;
    font-weight: 600;
    color: #7c3aed;
}
.log-tag-error { color: #ef4444; }
.log-tag-success { color: #10b981; }
.log-tag-warn { color: #f59e0b; }

/* Stats card */
.stat-card {
    background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f1f5f9;
}
.stat-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

/* File tree */
.file-item {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    padding: 6px 12px;
    margin: 2px 0;
    background: #12121a;
    border-radius: 6px;
    border-left: 3px solid #7c3aed;
}

/* Gradient header */
.engine-header {
    background: linear-gradient(135deg, #7c3aed 0%, #3b82f6 50%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0;
}
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────
if "engine" not in st.session_state:
    st.session_state.engine = None
if "build_result" not in st.session_state:
    st.session_state.build_result = None
if "live_logs" not in st.session_state:
    st.session_state.live_logs = []
if "is_building" not in st.session_state:
    st.session_state.is_building = False


def add_log(tag: str, message: str):
    """Callback for engine logs — stores in session state."""
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.live_logs.append({"time": ts, "tag": tag, "message": message})


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # Mode Selection (New vs Upgrade)
    creation_mode = st.selectbox("🛠️ Mode", [
        "✨ New Project",
        "♻️ Upgrade Existing"
    ], index=0)

    source_path = ""
    if creation_mode == "♻️ Upgrade Existing":
        source_path = st.text_input("📂 Source Path", help="Absolute path to the project folder to upgrade")
        if source_path and not os.path.exists(source_path):
            st.error("❌ Path does not exist")

    model_choice = st.selectbox("🧠 Model", [
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
        "ollama:llama3.2:3b",
        "Custom / Local...",
    ], index=1)

    if model_choice == "Custom / Local...":
        model = st.text_input("Enter Model ID", value="ollama:mistral", help="e.g. ollama:mistral, grok-beta, etc.")
    else:
        model = model_choice

    platform = st.selectbox("🎯 Platform", [
        "python", "android", "linux", "studio"
    ], index=0)

    # Scale Selection
    scale_label_map = {
        "🏢 Full Application": "app",
        "📜 Standalone Script": "script",
        "🖼️ Raw Asset": "asset"
    }
    scale_selection = st.selectbox("🏗️ Scale", list(scale_label_map.keys()), index=0,
                                   help="Control the complexity and scope of the creation.")
    scale = scale_label_map[scale_selection]

    budget = st.slider("💰 Budget ($)", min_value=0.5, max_value=20.0, value=5.0, step=0.5)
    fix_cycles = st.slider("🔄 Fix Cycles", min_value=1, max_value=5, value=3)
    use_docker = st.checkbox("🐳 Docker Sandbox", value=True,
                             help="Use Docker for sandboxed verification. Fallback: subprocess.")

    st.markdown("---")
    st.markdown("### 🔑 API Keys")
    st.caption("Keys are read from environment variables. Set them in your `.env` or shell.")

    # Show which keys are available
    key_status = {
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
    }
    for key, available in key_status.items():
        icon = "✅" if available else "❌"
        st.markdown(f"{icon} `{key}`")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#64748b; font-size:0.75rem;'>"
        "Antigravity Creation Engine v2.1<br>Multi-Agent Build System"
        "</div>",
        unsafe_allow_html=True
    )


# ── Main Tabs ───────────────────────────────────────────────
tab_build, tab_history, tab_settings = st.tabs(["🚀 Build", "🕒 Search & History", "⚙️ Engine Settings"])

with tab_build:
    # ── Header ───────────────────────────────────────────────────
    st.markdown('<h1 class="engine-header">🚀 Antigravity Creation Engine</h1>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; margin-top:-8px;'>"
        "Multi-agent AI build system with Docker sandboxing. "
        "Plan, Write, Review, Verify, and Upgrade."
        "</p>",
        unsafe_allow_html=True
    )

    # ── Input Section ────────────────────────────────────────────
    col_input, col_name = st.columns([3, 1])
    with col_input:
        goal_placeholder = "e.g. A URL shortener with analytics..."
        if creation_mode == "♻️ Upgrade Existing":
            goal_placeholder = "e.g. Refactor this to use FastAPI and add a React frontend..."
            
        goal = st.text_area(
            "🎯 Goal / Instruction",
            placeholder=goal_placeholder,
            height=100,
            key="goal_input",
        )
    with col_name:
        project_name = st.text_input(
            "📁 Project Name",
            value="",
            placeholder="auto-generated",
            help="Leave blank to auto-generate from your goal"
        )

    # ── Build Button ─────────────────────────────────────────────
    col_btn, col_phase = st.columns([1, 3])
    with col_btn:
        btn_label = "🔨 Build Project" if creation_mode == "✨ New Project" else "♻️ Upgrade Project"
        build_clicked = st.button(
        btn_label,
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_building,
    )
with col_phase:
    if st.session_state.engine:
        # TODO: Engine phase tracking is not exposed as a simple property in the new engine
        # We might need to rely on logs or add a property to CreationEngine
        st.markdown(f'<span class="phase-badge phase-planning">RUNNING</span>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  BUILD EXECUTION
# ══════════════════════════════════════════════════════════════
if build_clicked and goal.strip():
    # Import the NEW engine
    from creation_engine.orchestrator import CreationEngine
    from creation_engine.llm_client import add_log_listener

    # Register log listener
    add_log_listener(add_log)

    # Reset state
    st.session_state.live_logs = []
    st.session_state.build_result = None
    st.session_state.is_building = True

    # Validate inputs
    if creation_mode == "♻️ Upgrade Existing" and not source_path:
        st.error("Please provide a Source Path for upgrade.")
        st.session_state.is_building = False
        st.stop()

    # Auto-generate project name
    name = project_name.strip() or goal.strip().lower().replace(" ", "-")[:30]
    name = "".join(c for c in name if c.isalnum() or c in "-_")

    # Create engine
    # Map 'mode' UI selection to internal string
    engine_mode = "upgrade" if creation_mode == "♻️ Upgrade Existing" else "new"
    
    engine = CreationEngine(
        project_name=name,
        prompt=goal.strip(),
        output_dir="./output",
        model=model,
        budget=budget,
        platform=platform,
        max_fix_cycles=fix_cycles,
        docker=use_docker,
        source_path=source_path,
        mode=engine_mode,
        scale=scale
    )
    st.session_state.engine = engine

    # Run the build with live log display
    with st.status("🚀 Running engine task…", expanded=True) as status:
        log_container = st.empty()

        # Run the full build
        try:
            raw_result = engine.run()
            
            # Normalize result for UI
            # metrics = engine.tracker.get_summary() # Tracker is available on engine
            
            result = {
                "status": "COMPLETE" if raw_result.get("success") else "FAILED",
                "project_name": raw_result.get("project_name"),
                "project_dir": raw_result.get("project_path"),
                "files_written": list(engine.written_files.keys()), # Get list of keys
                "file_count": raw_result.get("files_written", 0),
                "run_command": raw_result.get("run_command", ""),
                "elapsed_seconds": 0, # orchestrator doesn't return this yet, insignificant
                "final_report": {"status": "SUCCESS" if raw_result.get("success") else "FAILED", "output": "See logs"},
                "log": st.session_state.live_logs
            }

            # Update status text
            if result["status"] == "COMPLETE":
                status.update(label="✅ Task Complete!", state="complete", expanded=False)
            else:
                status.update(label="❌ Task Failed", state="error", expanded=True)
                
        except Exception as e:
            st.error(f"Engine Crash: {e}")
            result = {"status": "CRASH", "error": str(e)}
            status.update(label="💥 Engine Crashed", state="error")

    st.session_state.build_result = result
    st.session_state.is_building = False
    st.rerun()

elif build_clicked and not goal.strip():
    st.warning("Please enter a description.")


# ══════════════════════════════════════════════════════════════
#  RESULTS DISPLAY
# ══════════════════════════════════════════════════════════════
if st.session_state.build_result:
    result = st.session_state.build_result

    st.markdown("---")

    # ── Stats Cards ───────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{result.get('file_count', 0)}</div>
            <div class="stat-label">Files Written</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{result.get('elapsed_seconds', 0)}s</div>
            <div class="stat-label">Build Time</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        status = result.get("status", "UNKNOWN")
        color = "#10b981" if status == "COMPLETE" else "#ef4444"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{color};">{status}</div>
            <div class="stat-label">Status</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        sandbox = result.get("final_report", {}).get("status", "N/A")
        sandbox_color = "#10b981" if sandbox == "SUCCESS" else "#f59e0b"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{sandbox_color};">{sandbox}</div>
            <div class="stat-label">Sandbox</div>
        </div>""", unsafe_allow_html=True)

    # ── Two-Column Layout: Files + Logs ───────────────────────
    col_files, col_logs = st.columns([1, 2])

    with col_files:
        st.markdown("### 📁 Generated Files")
        for fpath in result.get("files_written", []):
            icon = "🐍" if fpath.endswith(".py") else "📄" if fpath.endswith(".md") else "📋" if fpath.endswith(".txt") else "📦"
            st.markdown(f'<div class="file-item">{icon} {fpath}</div>', unsafe_allow_html=True)

        # Run command
        run_cmd = result.get("run_command", "python main.py")
        st.markdown("### ▶️ Run Command")
        st.code(run_cmd, language="bash")

        # Download ZIP
        st.markdown("### 📥 Download")
        project_dir = result.get("project_dir", "")
        if project_dir and os.path.isdir(project_dir):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files_in_dir in os.walk(project_dir):
                    # Skip __pycache__ and .git
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
                    for fname in files_in_dir:
                        fpath_full = os.path.join(root, fname)
                        arcname = os.path.relpath(fpath_full, project_dir)
                        zf.write(fpath_full, arcname)
            zip_buffer.seek(0)
            st.download_button(
                label="⬇️ Download Project ZIP",
                data=zip_buffer,
                file_name=f"{result.get('project_name', 'project')}.zip",
                mime="application/zip",
                use_container_width=True,
            )

        # Download Binary
        binary_info = result.get("binary")
        if binary_info:
            bin_name = binary_info.get("name")
            bin_path = binary_info.get("path")
            if bin_name and bin_path and os.path.exists(bin_path):
                with open(bin_path, "rb") as f:
                    st.download_button(
                        label=f"📦 Download {bin_name}",
                        data=f,
                        file_name=bin_name,
                        key="dl_binary_main"
                    )

    with col_logs:
        st.markdown("### 📋 Build Log")
        log_entries = result.get("log", st.session_state.live_logs)
        if log_entries:
            log_html_parts = []
            for entry in log_entries:
                tag = entry.get("tag", "")
                msg = entry.get("message", "").replace("<", "&lt;").replace(">", "&gt;")
                ts = entry.get("time", "")

                tag_class = "log-tag"
                if tag in ("ERROR", "CRASH"):
                    tag_class += " log-tag-error"
                elif tag in ("WARN",):
                    tag_class += " log-tag-warn"
                elif "✓" in msg or "✅" in msg:
                    tag_class += " log-tag-success"

                log_html_parts.append(
                    f'<div class="log-entry">'
                    f'<span style="color:#475569;">{ts}</span> '
                    f'<span class="{tag_class}">[{tag}]</span> '
                    f'{msg}</div>'
                )

            log_html = "\n".join(log_html_parts)
            st.markdown(
                f'<div style="max-height:500px; overflow-y:auto; padding:8px; '
                f'background:#0a0a0f; border-radius:8px; border:1px solid #1e293b;">'
                f'{log_html}</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("No logs available.")

    # ── Sandbox Output ────────────────────────────────────────
    final_report = result.get("final_report", {})
    if final_report.get("output"):
        st.markdown("### 🐳 Sandbox Output")
        st.code(final_report["output"][:3000], language="text")
    if final_report.get("error"):
        st.markdown("### ⚠️ Errors")
        st.error(final_report["error"][:2000])

    # ── File Preview ──────────────────────────────────────────
    if st.session_state.engine and st.session_state.engine.written_files:
        st.markdown("### 👁️ File Preview")
        written = st.session_state.engine.written_files
        selected_file = st.selectbox("Select file", list(written.keys()))
        if selected_file:
            lang = "python" if selected_file.endswith(".py") else "markdown" if selected_file.endswith(".md") else "text"
            st.code(written[selected_file][:5000], language=lang, line_numbers=True)


# ── Empty State ──────────────────────────────────────────────
        if not st.session_state.build_result and not st.session_state.is_building:
            st.markdown("---")
            st.markdown(
                "<div style='text-align:center; padding:60px 20px; color:#475569;'>"
                "<h3 style='color:#64748b;'>Ready to Create</h3>"
                "<p>Enter a project description above and click <strong>Build Project</strong> "
                "to start the multi-agent pipeline.</p>"
                "<p style='font-size:0.85rem;'>The engine will: Enhance your prompt → "
                "Research versions → Plan architecture → Write code → "
                "Review for bugs → Verify in Docker sandbox</p>"
                "</div>",
                unsafe_allow_html=True
            )

with tab_history:
    st.markdown("## 🕒 Build History & Search")
    sq_col, sp_col = st.columns([3, 1])
    with sq_col:
        search_query = st.text_input("🔍 Search builds...", placeholder="Project name or keyword")
    with sp_col:
        search_platform = st.selectbox("🎯 Filter Platform", ["All", "python", "android", "linux", "studio"], index=0)

    output_dir = "./output"
    platforms = None if search_platform == "All" else search_platform
    history = search_builds(output_dir, search_query, platforms)

    if not history:
        st.info("No matching builds found.")
    else:
        for entry in history:
            with st.expander(f"📁 {entry['name']} — {entry['status']} ({entry['platform']})"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Cost", f"${entry['cost']:.4f}")
                c2.metric("Files", entry['files'])
                c3.write(f"Created: {datetime.fromtimestamp(entry['timestamp']).strftime('%Y-%m-%d %H:%M')}")
                
                if entry['has_binary']:
                    st.success(f"📦 Binary available: {entry['binary_name']}")
                    # Button to download existing binary
                    bin_path = os.path.join(entry['path'], "dist", entry['binary_name'])
                    if os.path.exists(bin_path):
                        with open(bin_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {entry['binary_name']}",
                                data=f,
                                file_name=entry['binary_name'],
                                key=f"dl_{entry['name']}"
                            )
                
                if st.button(f"🔎 View Details", key=f"view_{entry['name']}"):
                    # Logic to reload this build into view (optional enhancement)
                    st.info("Feature coming soon: Reload build details into dashboard.")

with tab_settings:
    st.markdown("## ⚙️ Engine Settings")
    st.caption("Customize engine behavior and directives without modifying code.")
    
    current_settings = load_settings()
    
    with st.form("settings_form"):
        st.markdown("### 🛠️ Directives")
        directives = current_settings["directives"]
        new_directives = {}
        for key, val in directives.items():
            new_directives[key] = st.text_area(f"Directive: {key.capitalize()}", value=val, height=100)
            
        st.markdown("### 🔗 Providers")
        providers = current_settings["providers"]
        new_providers = st.text_area("LLM Providers (JSON)", value=json.dumps(providers, indent=2), height=150)
        
        save_btn = st.form_submit_button("💾 Save Settings")
        if save_btn:
            try:
                updated_settings = {
                    "directives": new_directives,
                    "providers": json.loads(new_providers)
                }
                if save_settings(updated_settings):
                    st.success("✅ Settings saved successfully!")
                else:
                    st.error("❌ Failed to save settings.")
            except Exception as e:
                st.error(f"❌ Invalid JSON in Providers: {e}")
