import streamlit as st
import json
import os
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Lazy loading managers
def get_components():
    from strategies import SearchStrategy, StrategyManager
    from generator import MaterialGenerator
    from revenue import RevenueManager
    from hive import hive
    return SearchStrategy, StrategyManager, MaterialGenerator, RevenueManager, hive

# --- Initialization ---
SearchStrategy, StrategyManager, MaterialGenerator, RevenueManager, hive = get_components()
rev_manager = RevenueManager()
agents = hive.list_agents()

# --- Styles & Config ---
st.set_page_config(page_title="Project Frost - Mission Control", layout="wide", page_icon="❄️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* More targeted font application to avoid breaking icons */
    .stApp, .stMarkdown, .stMetric, .stSelectbox, .stTextInput, .stButton, .stDataframe, .stExpander {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #05070a;
        color: #e6edf3;
    }
    
    .main {
        background: radial-gradient(circle at 50% 50%, #0d1117 0%, #05070a 100%);
    }
    
    /* Glassmorphism Containers */
    .st-emotion-cache-1r6slb0, .bento-card {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        transition: transform 0.2s ease, border 0.2s ease;
    }
    
    .bento-card:hover {
        border: 1px solid rgba(0, 212, 255, 0.4);
        transform: translateY(-2px);
    }
    
    /* Header Gradient */
    .title-gradient {
        background: linear-gradient(90deg, #00d4ff 0%, #00f5d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    
    /* Glowing Indicators */
    .live-pulse {
        width: 12px;
        height: 12px;
        background: #3fb950;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 10px #3fb950;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(63, 185, 80, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(63, 185, 80, 0); }
    }
    
    /* Social Box / Hive Chat */
    .social-box {
        background: rgba(1, 4, 9, 0.9);
        height: 300px;
        overflow-y: auto;
        padding: 15px;
        border-radius: 12px;
        border-left: 4px solid #00d4ff;
        font-size: 0.9em;
    }
    
    .chat-msg {
        margin-bottom: 12px;
        padding: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        transition: background 0.2s ease, transform 0.1s ease;
    }
    
    .chat-msg:hover {
        background: rgba(0, 212, 255, 0.08);
        border-color: rgba(0, 212, 255, 0.2);
        transform: translateX(4px);
    }
    
    .agent-name {
        color: #00d4ff;
        font-weight: 600;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Helper for Hive Chat
def get_hive_chat():
    chat_file = 'hive_chat.json'
    if not os.path.exists(chat_file): return []
    try:
        with open(chat_file, 'r') as f:
            return json.load(f)
    except:
        return []

# Helper for logs
def get_latest_logs(n=10):
    if not os.path.exists('agent_oversight.log'): return "Initializing logs..."
    with open('agent_oversight.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return "".join(lines[-n:])

# --- Main Mission Control ---
st.markdown('<div class="title-gradient">FROST MISSION CONTROL</div>', unsafe_allow_html=True)

# Status Bar
is_live = os.getenv("AGENT_MODE") == "production"
status_class = "live-pulse" if is_live else ""
status_text = "HIVE ACTIVE // PRODUCTION" if is_live else "SIMULATION MODE // TESTING"
st.markdown(f'<div><span class="{status_class}"></span><strong>{status_text}</strong> <span style="background: rgba(0, 212, 255, 0.1); color: #00d4ff; padding: 2px 8px; border-radius: 4px; font-size: 0.7em; border: 1px solid rgba(0, 212, 255, 0.2); margin-left: 10px;">URL DE-DUPLICATION ACTIVE</span></div>', unsafe_allow_html=True)

st.divider()

# --- Bento Grid Layout ---
col_health, col_leads, col_intel = st.columns([1, 1.8, 1.2])

with col_health:
    st.markdown("### 🐝 Swarm Status")
    st.metric("Total Agents", len(agents), delta=f"{len(agents)} Active")
    
    with st.container():
        st.markdown("**Active Personas**")
        for agent in agents[:8]:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 8px; margin-bottom: 5px; font-size: 0.8em;">
                <span style="color: #00d4ff;">●</span> {agent['name']} <small>({agent['strategy']})</small>
            </div>
            """, unsafe_allow_html=True)
    
    if st.button("➕ Deploy Random Agent"):
        import random
        personas = ["python_hunter", "ai_strategist", "social_scout", "saas_builder", "data_alchemist", "automation_architect"]
        r_persona = random.choice(personas)
        first_names = ["Alex", "Jordan", "Casey", "Riley", "Taylor", "Morgan", "Skyler", "Quinn", "Sloane", "Reese"]
        r_name = f"{random.choice(first_names)}."
        success, msg = hive.create_specialized_agent(r_persona, r_name)
        if success: st.success(f"Deployed {r_name} ({r_persona})"); st.rerun()

    st.divider()
    st.markdown("### 🏗️ Creation Engine")
    
    # Scan for projects in applications/
    app_dir = 'applications'
    if os.path.exists(app_dir):
        projects = []
        for d in os.listdir(app_dir):
            state_file = os.path.join(app_dir, d, 'state.json')
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        state = json.load(f)
                    projects.append({
                        "id": d,
                        "phase": state.get('current_phase', 'RESEARCH'),
                        "mode": state.get('mode', 'new'),
                        "target": state.get('target', 'python'),
                        "last_update": state['history'][-1]['timestamp'] if state.get('history') else "N/A"
                    })
                except: pass
        
        if projects:
            for p in projects:
                phase_color = "#00d4ff" if p['phase'] != "COMPLETE" else "#3fb950"
                mode_label = p.get('mode', 'new').upper()
                target_label = p.get('target', 'python').upper()
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid {phase_color};">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="font-size: 0.8em; font-weight: bold; color: {phase_color};">{p['phase']}</div>
                        <div style="display: flex; gap: 4px;">
                            <div style="font-size: 0.6em; background: rgba(0, 212, 255, 0.1); color: #00d4ff; padding: 1px 5px; border-radius: 3px;">{target_label}</div>
                            <div style="font-size: 0.6em; background: rgba(255,255,255,0.1); padding: 1px 5px; border-radius: 3px;">{mode_label}</div>
                        </div>
                    </div>
                    <div style="font-size: 0.9em; margin-top: 4px;">Project: {p['id']}</div>
                    <div style="font-size: 0.7em; color: #8b949e;">Last Sync: {p['last_update']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No active builds.")
    else:
        st.info("Creation Engine Idle.")

    st.divider()
    st.markdown("### 💰 Financials")
    st.metric("Wallet (Paid)", f"${rev_manager.data.get('total_paid', 0)}", delta=f"+${rev_manager.data.get('total_invoiced', 0)}")
    if st.button("💸 Trigger Payout"):
        st.success(rev_manager.request_payout())

with col_leads:
    st.markdown("### 🎯 Live Opportunity Feed")
    if os.path.exists('found_jobs.json'):
        with open('found_jobs.json', 'r') as f:
            jobs = json.load(f)
        if jobs:
            # Sort and Filter: Show only jobs that haven't been manually pushed or already applied.
            # We filter FIRST, then sort the remaining to keep the list clean.
            filtered_jobs = [j for j in jobs if not j.get('manual_push')]
            filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('score', 0), reverse=True)
            
            for job in filtered_jobs[:10]: # Increased visibility range
                with st.expander(f"{job['title']} [{job['score']}%]"):
                    st.markdown(f"**Company**: {job.get('company', 'Unknown')}")
                    st.markdown(f"**Platform**: {job['platform']}")
                    st.write(job['description'][:300] + "...")
                    if st.button("🚀 Push to Diplomat", key=f"btn_{job['id']}"):
                        # Mark as manually pushed in the file
                        for j in jobs:
                            if j['id'] == job['id']:
                                j['manual_push'] = True
                                break
                        with open('found_jobs.json', 'w') as f:
                            json.dump(jobs, f, indent=2)
                        st.success(f"Lead '{job['title']}' pushed to Diplomat.")
                        st.rerun()
        else:
            st.write("Hive is currently decrypting new leads...")
    else:
        st.write("Waiting for Hunter scan sync...")

with col_intel:
    st.markdown("### 💬 Social Hive Chat")
    chat_history = get_hive_chat()
    # Build complete HTML string first
    chat_inner = ""
    for msg in reversed(chat_history):
        chat_inner += f"""<div class="chat-msg">
<span class="agent-name">[{msg['timestamp']}] {msg['agent']}</span><br>
{msg['message']}
</div>"""
    
    # Wrap in container and render in a SINGLE st.markdown body to avoid escaping issues
    full_chat_html = f'<div class="social-box">{chat_inner}</div>'
    st.markdown(full_chat_html, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 🛡️ Guardian Logs")
    st.markdown(f'<div style="font-family: monospace; font-size: 0.7em; height: 200px; overflow-y: auto; color: #8b949e;">{get_latest_logs(20)}</div>', unsafe_allow_html=True)

# --- Secondary Controls ---
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🔥 Purge All Agents"):
        for a in agents: hive.delete_agent(a['id'])
        st.rerun()
with c2:
    if st.button("🔄 Full System Sync"): st.rerun()
with c3:
    if st.button("🗑️ Wipe Logs"):
        if os.path.exists('agent_oversight.log'): os.remove('agent_oversight.log')
        if os.path.exists('hive_chat.json'): os.remove('hive_chat.json')
        st.rerun()
