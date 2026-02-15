import streamlit as st
import os
import time
import pandas as pd
from frost_core import FrostCore
from job_automator import JobAutomator
from tool_generator import ToolGenerator

# Set page config for a premium feel
st.set_page_config(
    page_title="Frost AI | Automation Platform",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Premium Aesthetics
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stButton>button {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    .card {
        background-color: #1a1c24;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #2d2f39;
        margin-bottom: 1rem;
    }
    .header-text {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        background: -webkit-linear-gradient(#eee, #333);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize engines
@st.cache_resource
def get_frost_engines():
    core = FrostCore(os.getcwd())
    automator = JobAutomator(core)
    generator = ToolGenerator(os.path.join(os.getcwd(), "frost_tools"))
    return core, automator, generator

frost_core, job_automator, tool_generator = get_frost_engines()

# Sidebar Navigation
with st.sidebar:
    st.image("frost_platform_logo.png", width=200) if os.path.exists("frost_platform_logo.png") else st.title("❄️ FROST AI")
    st.markdown("---")
    menu = st.radio("Navigation", ["Command Center", "Job Automator", "Tool Forge", "Settings"])
    st.markdown("---")
    st.info("System Status: Online")

# Header
st.markdown("<h1 class='header-text'>Frost AI Development Platform</h1>", unsafe_allow_html=True)

if menu == "Command Center":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Matches", "124", "+12 today")
    with col2:
        st.metric("Tools Forged", "18", "+2 today")
    with col3:
        st.metric("Active Automations", "4", "Stable")
    
    st.markdown("### Recent Activity")
    st.markdown("""
        <div class='card'>
            <p>🔄 <b>Job Scraper:</b> 42 new matches found on LinkedIn</p>
            <p>🛠️ <b>Tool Forge:</b> 'resume_optimizer_v2' successfully deployed</p>
            <p>✅ <b>Application Bot:</b> Application submitted to 'OpenAI' for 'Senior Architect'</p>
        </div>
    """, unsafe_allow_html=True)

elif menu == "Job Automator":
    st.markdown("### 🔍 AI Job Search & Matching")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("Job Title / Keywords", "Senior Python Developer")
    with col2:
        location = st.text_input("Location", "Remote")
    
    if st.button("Run Scrapers"):
        with st.spinner("Frost is scouring the web..."):
            jobs = job_automator.search_jobs(query, location)
            time.sleep(2) # Animation effect
            st.session_state.jobs = jobs
            st.success(f"Found {len(jobs)} matches!")

    if "jobs" in st.session_state:
        for job in st.session_state.jobs:
            with st.container():
                st.markdown(f"""
                    <div class='card'>
                        <h4>{job['title']}</h4>
                        <p>🏢 {job['company']} | 📍 {job['location']}</p>
                        <p>{job['description']}</p>
                        <div style='display: flex; gap: 10px;'>
                            <span style='background-color: #1e3a8a; padding: 4px 8px; border-radius: 4px;'>Match Score: {job['score']}%</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Auto-Apply to {job['id']}", key=job['id']):
                    st.info(f"Initiating Frost Auto-Apply for {job['company']}...")

elif menu == "Tool Forge":
    st.markdown("### 🛠️ On-Demand Tool Forge")
    st.markdown("Generate custom AI-powered utilities using the Nexus Engine.")
    
    tool_desc = st.text_area("What do you want to build?", "Create a tool that pulls my latest GitHub commits and formats them into a professional LinkedIn post.")
    tool_name = st.text_input("Project Name", "linkedin_post_gen")

    if st.button("Forge Tool"):
        with st.status("Building Tool...", expanded=True) as status:
            st.write("Initializing Nexus Engine...")
            # In a real run, this would call tool_generator.generate_util
            # For UI demo, we simulate
            time.sleep(2)
            st.write("Architecting solution...")
            time.sleep(2)
            st.write("Generating code modules...")
            time.sleep(2)
            st.write("Verifying stability...")
            status.update(label="Build Complete!", state="complete", expanded=False)
        st.success(f"Tool '{tool_name}' is ready in your workspace!")

elif menu == "Settings":
    st.markdown("### Framework Settings")
    st.json(frost_core.config)
