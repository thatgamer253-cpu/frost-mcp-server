import streamlit as st
import os
import time
from video_engine import FrostVideoEngine

st.set_page_config(page_title="Frost Video AI", page_icon="🎬", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ffffff; }
    .big-font { font-size: 3rem !important; font-weight: 800; color: #3b82f6; }
    .stTextArea textarea { background-color: #111; color: white; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<p class='big-font'>Frost Prompt-to-Video</p>", unsafe_allow_html=True)
st.write("Transform any concept into a cinematic cinematic sequence.")

with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    st.info("Required for autonomous generation.")

prompt = st.text_area("What's the vision?", placeholder="A futuristic city with flying neon cars and heavy rain...")
style = st.selectbox("Aesthetic Style", ["Cinematic", "Cyberpunk", "Ethereal", "Anime", "Dark Fantasy"])

if st.button("Forge Video"):
    if not prompt:
        st.error("Please enter a vision first.")
    elif not api_key:
        st.error("Please provide an OpenAI API Key in the sidebar.")
    else:
        with st.status("Forging Video...", expanded=True) as status:
            engine = FrostVideoEngine("./frost_outputs", api_key=api_key)
            
            st.write("🎬 Scripting scenes...")
            scenes = engine.generate_scene_descriptions(prompt)
            
            st.write("🖼️ Generating visual assets (DALL-E 3 HD)...")
            scene_images = engine.generate_images_for_scenes(scenes)
            
            st.write("✨ Applying cinematic motion...")
            # We use the existing engine render logic
            video_path = engine.assemble_video(scene_images, "frost_autonomous.mp4")
            
            status.update(label="Video Forged!", state="complete")
        
        st.success(f"Video ready: {video_path}")
        st.video(video_path)
