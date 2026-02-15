import os
import time
import subprocess
import socket
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class GuardianEngine:
    """
    Advanced reliability system for Project Frost.
    Handles self-healing, environment stabilization, and AI error analysis.
    """
    def __init__(self, log_file='agent_oversight.log'):
        self.log_file = log_file
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def log_activity(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        print(entry.strip())

    def check_port(self, port):
        """Checks if a port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def stabilize_environment(self):
        """Auto-repairs common environment issues."""
        self.log_activity("STABILIZER: Running environment audit...")
        
        # 1. Dependency Check (silent)
        try:
            subprocess.run(["pip", "install", "-r", "requirements.txt", "--quiet"], check=True)
        except:
            self.log_activity("STABILIZER: Warning - Dependency audit encountered an issue.", "WARNING")

        # 2. Workspace check
        os.makedirs('profiles', exist_ok=True)
        os.makedirs('applications', exist_ok=True)
        
        self.log_activity("STABILIZER: Environment is STABLE.")

    def send_social_message(self, agent_name, message):
        """Pushes a message to the Hive Chat system."""
        chat_file = 'hive_chat.json'
        chat_history = []
        if os.path.exists(chat_file):
            with open(chat_file, 'r') as f:
                try: chat_history = json.load(f)
                except: pass
        
        chat_history.append({
            "agent": agent_name,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # Keep only last 50 messages
        chat_history = chat_history[-50:]
        
        with open(chat_file, 'w') as f:
            json.dump(chat_history, f, indent=2)

    def interpret_error_with_ai(self, error_traceback):
        """Uses AI to explain a crash and suggest a fix."""
        if not os.getenv("OPENAI_API_KEY"):
            return "AI Analysis unavailable (Missing Key)."

        prompt = f"""
        A Project Frost agent process has crashed with the following error:
        {error_traceback}
        
        Explain exactly why it crashed and provide a 1-sentence 'Self-Heal' instruction for the orchestrator.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "You are a senior DevOps reliability engineer."},
                          {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return "AI failed to analyze crash."

# Singleton
guardian = GuardianEngine()
