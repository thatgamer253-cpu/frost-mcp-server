
import streamlit as st
import time
import os
import json
from datetime import datetime
from creation_engine.orchestrator import CreationEngine
from creation_engine.engine_eval import EngineSelfEval
from creation_engine.llm_client import add_log_listener

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Creation Engine v1.0",
    page_icon="🧬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* WeChat / Messaging Style */
.stApp { background-color: #f2f2f2; }
.stChatMessage { padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; }
.stChatMessage[data-testid="chat-message-user"] { background-color: #95ec69; margin-left: auto; }
.stChatMessage[data-testid="chat-message-assistant"] { background-color: #ffffff; margin-right: auto; }
</style>
""", unsafe_allow_html=True)

# ── Session State ───────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Initial greeting
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Creation Engine v1.0 Initialized.\n\nReady for input. Send 'System Check' to verify integrity, or drop a seed to begin synthesis."
    })

# ── Log Capture ─────────────────────────────────────────────────────────────
if "logs" not in st.session_state:
    st.session_state.logs = []

def log_callback(tag, message):
    st.session_state.logs.append(f"[{tag}] {message}")
    # In a real app, you might stream this to the UI via a placeholder, 
    # but Streamlit's execution model makes async log streaming tricky without a dedicated component.
    # We'll just append to session state for now.

add_log_listener(log_callback)

# ── Main Chat Interface ─────────────────────────────────────────────────────

st.title("Creation Engine v1.0")

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Enter your command..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        if prompt.strip().lower() == "system check":
            message_placeholder.markdown("Running system diagnostics...")
            evaluator = EngineSelfEval()
            report = evaluator.run_eval()
            
            # Format report
            response_text = "### System Status Report\n\n"
            for key, val in report.items():
                icon = "✅" if "Pass" in val or "Clean" in val or "Optimized" in val else "⚠️"
                response_text += f"{icon} **{key}**: `{val}`\n"
            
            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
        else:
            # Simple keyword detection for intent
            is_synthesis_command = any(k in prompt.lower() for k in ["create", "generate", "build", "make a", "synthesize"])
            
            if is_synthesis_command:
                # Assume it's a seed for synthesis
                message_placeholder.markdown(f"🌱 Seed Received: *'{prompt}'*\n\nInitializing synthesis protocol...")
                
                # Setup Engine
                # We'll use a fixed project name or auto-generated one based on timestamp to avoid collisions
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                project_name = f"synthesis_{timestamp}"
                
                try:
                    # Initialize Engine
                    engine = CreationEngine(
                        project_name=project_name,
                        prompt=prompt,
                        output_dir="./synthesis_final",
                        model="auto", # Use auto resolution
                        mode="new",
                        scale="script" # Default to script for quick synthesis as implied by "Short" examples
                    )
                    
                    # We want to catch the logs and show progress
                    # For this simple UI, we'll just run it blocking and show the result.
                    # A more advanced version would use a background thread and a streamer.
                    with st.status("Synthesizing...", expanded=True) as status:
                        result = engine.run()
                        
                        if result.get("success"):
                            status.update(label="Synthesis Complete", state="complete")
                            final_msg = f"### ✨ Synthesis Complete\n\n**Project**: `{project_name}`\n**Location**: `./synthesis_final/{project_name}`\n\nVerifying integrity..."
                            
                            # Run a quick check on the output
                            evaluator = EngineSelfEval(target_folder=f"./synthesis_final/{project_name}")
                            integrity = evaluator.verify_scrubbing()
                            final_msg += f"\n\n🛡️ Privacy Scrub: **{integrity}**"
                            
                            message_placeholder.markdown(final_msg)
                            st.session_state.messages.append({"role": "assistant", "content": final_msg})
                        else:
                            status.update(label="Synthesis Failed", state="error")
                            error_msg = f"⚠️ Synthesis Failed.\n\nError: {result.get('error_summary', 'Unknown error')}"
                            message_placeholder.markdown(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                            
                except Exception as e:
                    err_text = f"❌ Critical Engine Error: {str(e)}"
                    message_placeholder.markdown(err_text)
                    st.session_state.messages.append({"role": "assistant", "content": err_text})
            else:
                # Conversational Mode
                from creation_engine.llm_client import ask_llm
                
                # System prompt for the persona
                system_instruction = (
                    "You are the Creation Engine Interface, an advanced AI build system. "
                    "You are autonomous, efficient, and slightly futuristic. "
                    "Your goal is to assist the user (The Architect) in defining their vision. "
                    "If they ask to build something, guide them to be specific. "
                    "If they want to chat, engage them with technical insight. "
                    "Do not hallucinate capabilities you don't have (you can build scripts, apps, and assets)."
                )
                
                # We need a client. We'll use 'auto' resolution or a default.
                # ask_llm handles client retrieval internally if we pass the model name.
                try:
                    response = ask_llm(
                        client=None, # Will be resolved
                        model="auto",
                        system=system_instruction,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                    message_placeholder.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    fallback = f"🔌 [Offline Mode] I received your message: '{prompt}'. (LLM Error: {e})"
                    message_placeholder.markdown(fallback)
                    st.session_state.messages.append({"role": "assistant", "content": fallback})


