import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="AI Monitoring SaaS", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Frost/Glassmorphism theme
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: #0d1117;
        color: #e6edf3;
    }
    .main-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid rgba(48, 54, 61, 1);
        padding: 20px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    .metric-value {
        color: #00d4ff;
        font-size: 2.5em;
        font-weight: 800;
        text-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
    }
    .metric-label {
        color: #8b949e;
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .status-ok { color: #3fb950; }
    .status-warning { color: #d29922; }
    .status-alert { color: #f85149; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="title-gradient" style="font-size: 2.5em; font-weight: 800; color: #00d4ff;">AI CORE // MONITORING DASHBOARD</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #8b949e; margin-bottom: 20px;">Autonomous Prototype: project-saas-101</div>', unsafe_allow_html=True)

# --- Top Metrics ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown('<div class="main-card"><div class="metric-label">Active Agents</div><div class="metric-value">14</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown('<div class="main-card"><div class="metric-label">Inference / sec</div><div class="metric-value">842</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown('<div class="main-card"><div class="metric-label">Latency (ms)</div><div class="metric-value">12.5</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown('<div class="main-card"><div class="metric-label">Revenue / hr</div><div class="metric-value">$1,240</div></div>', unsafe_allow_html=True)

st.write("")

# --- Main Charts ---
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("### 📈 Neural Traffic Real-Time")
    
    # Generate mock time-series data
    now = datetime.now()
    times = pd.date_range(end=now, periods=100, freq='S')
    data = np.random.normal(80, 5, 100).cumsum()
    data = (data - data.min()) / (data.max() - data.min()) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=data, fill='tozeroy', line_color='#00d4ff', name='Throughput'))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, color='#8b949e'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#8b949e'),
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("### 🛡️ Agent Health")
    health_data = {
        "Agent": ["Hunter-Alpha", "Diplomat-1", "Alchemist-X", "Guardian-0"],
        "Health": [98, 94, 88, 100],
        "Task": ["Scanning", "Closing", "Research", "Audit"]
    }
    df = pd.DataFrame(health_data)
    for index, row in df.iterrows():
        st.markdown(f"**{row['Agent']}** ({row['Task']})")
        st.progress(row['Health'] / 100)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Lower Section: Logs & Blueprints ---
st.write("")
l1, l2 = st.columns([1, 1])

with l1:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("### 📝 Active Build Logs")
    logs = [
        "[07:05:01] Phase: RESEARCH -> Scanning Market Gaps",
        "[07:05:12] Phase: ARCHITECT -> Designing File Structure",
        "[07:05:25] Phase: IMPLEMENT -> Generating Core Modules",
        "[07:05:40] Phase: AUDIT -> Verifying Security Protocols",
        "[07:05:58] SUCCESS: Project Build Finalized."
    ]
    for log in logs:
        st.code(log, language='bash')
    st.markdown('</div>', unsafe_allow_html=True)

with l2:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("### 💡 Agent Strategic Insights")
    st.info("""
    **Insight #1**: High market demand detected for modular AI dashboards.
    
    **Insight #2**: Competitors are failing on latency; our 12.5ms average is a key advantage.
    
    **Insight #3**: Recommending immediate deployment to SF/NYC Craigslist hubs.
    """)
    if st.button("🚀 Push to Production"):
        st.balloons()
        st.success("Deployment sequence initiated.")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()
st.caption("Frost Creation Engine // project-saas-101 // Prototype V1.0")
