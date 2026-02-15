import streamlit as st
import os

st.set_page_config(page_title="Project Frost - DEBUG", layout="wide")

st.title("❄️ Project Frost - Debug Mode")
st.write("If you can see this, Streamlit is working correctly.")

st.header("Checklist")
st.write(f"Current Directory: {os.getcwd()}")
st.write(f"Profile Exists: {os.path.exists('profile_config.json')}")
st.write(f"Logs Exist: {os.path.exists('agent_oversight.log')}")

if st.button("Reload App"):
    st.rerun()
