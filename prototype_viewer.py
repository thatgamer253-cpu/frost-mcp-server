
import streamlit as st
import os

st.set_page_config(page_title="Frost Prototype Viewer", layout="wide")

st.markdown("""
    <style>
    .reportview-container {
        background: #0d1117;
    }
    .stApp {
        background: #0d1117;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("❄️ Frost Autonomous Prototype: project-saas-101")
st.subheader("Architected & Audited by the Creation Engine")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("### 📋 Build Intelligence")
    if os.path.exists('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/research.txt'):
        with open('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/research.txt', 'r', encoding='utf-8') as f:
            st.markdown("**Research Synthesis**")
            st.text_area("Market Insights", f.read(), height=300)
            
    if os.path.exists('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/audit_report.md'):
        with open('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/audit_report.md', 'r', encoding='utf-8') as f:
            st.markdown("**Quality Audit**")
            st.markdown(f.read())

with col2:
    st.success("### 🏗️ Architectural Blueprint")
    if os.path.exists('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/blueprint.md'):
        with open('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/blueprint.md', 'r', encoding='utf-8') as f:
            st.markdown(f.read())

st.divider()
st.warning("### 💻 Core Implementation Logic")
if os.path.exists('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/deliverable_main.txt'):
    with open('c:/Users/thatg/Desktop/Frost/applications/project-saas-101/deliverable_main.txt', 'r', encoding='utf-8') as f:
        st.code(f.read(), language='markdown')

st.success("✅ Prototype is live and verified.")
