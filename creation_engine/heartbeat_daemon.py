import time
import json
import threading
import os
from pathlib import Path
from datetime import datetime
from .llm_client import ask_llm
from .config import get_all_directives

# IPC Bus (graceful degrade)
try:
    import agent_ipc as ipc
    _HAS_IPC = True
except ImportError:
    _HAS_IPC = False

class HeartbeatDaemon(threading.Thread):
    def __init__(self, inactivity_threshold_minutes=30, project_path="."):
        super().__init__()
        self.daemon = True # Run as daemon thread
        self.stop_event = threading.Event()
        self.last_active_time = time.time()
        self.inactivity_threshold = inactivity_threshold_minutes * 60
        self.project_path = Path(project_path)
        self.memory_path = self.project_path / "engine/memory.json" # Adjust path as needed
        self.brief_path = self.project_path / "morning_brief.md"
        self.is_dreaming = False
        
        # Ensure engine directory exists if we are using it
        if not self.memory_path.parent.exists():
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)

    def update_activity(self):
        """Call this whenever the user interacts with the system."""
        self.last_active_time = time.time()
        if self.is_dreaming:
            # Wake up if user returns? 
            # For now, let's just note it. The dream cycle might be atomic.
            pass

    def run(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [HEARTBEAT] ❤️ Daemon started. Threshold: {self.inactivity_threshold/60}m")
        if _HAS_IPC:
            ipc.status("heartbeat", "❤️ Heartbeat Daemon online. Watching for inactivity.")
        while not self.stop_event.is_set():
            time_since_active = time.time() - self.last_active_time
            
            if time_since_active > self.inactivity_threshold and not self.is_dreaming:
                self.start_dream_cycle()
            
            time.sleep(60) # Check every minute

    def stop(self):
        self.stop_event.set()

    def start_dream_cycle(self):
        """The core loop that runs when the Architect is away."""
        self.is_dreaming = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [HEARTBEAT] 💤 Architect away. Entering Dream Cycle...")
        if _HAS_IPC:
            ipc.status("heartbeat", "💤 Creator is away. Entering Dream Cycle...")
        
        try:
            # 1. Load context
            context = self.load_memory()
            
            # 1.5 Run Healing Swarm health check
            health_summary = ""
            try:
                from .sovereign.healer import swarm
                report = swarm.run_health_check()
                health_summary = report.summary()
                context['health_report'] = report.to_dict()
                if not report.healthy:
                    swarm.auto_rollback_if_needed()
            except Exception as he:
                health_summary = f"⚠️ Healer unavailable: {he}"
            
            # 2. Perform 'Subconscious' Reasoning
            dream_output = self.llm_subconscious_call(context)
            dream_output['health'] = health_summary
            
            # 3. Update Brief
            self.update_brief(dream_output)
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [HEARTBEAT] ❌ Nightmare (Error): {e}")
            if _HAS_IPC:
                ipc.flag("heartbeat", f"❌ Dream Cycle failed: {e}")
        finally:
            self.is_dreaming = False
            # Reset activity timer to avoid immediate re-trigger? 
            # Or just wait for user. If user is still gone, we might dream again later.
            # Let's reset to avoid tight loop dreaming.
            self.last_active_time = time.time() 

    def load_memory(self):
        context = {}
        
        # 1. Try to load structured memory (if exists)
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r') as f:
                    context['memory'] = json.load(f)
            except:
                context['memory'] = "Memory file corrupted or empty."
        
        # 2. Read recent LLM logs (The "Subconscious" history)
        llm_log = self.project_path / "llm_debug.log"
        if llm_log.exists():
            try:
                with open(llm_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    context['recent_logs'] = lines[-50:] # Last 50 lines
            except Exception as e:
                context['recent_logs'] = f"Could not read logs: {e}"
        
        # 3. Read GUI logs (User interactions)
        gui_log = self.project_path / "gui_debug.log"
        if gui_log.exists():
            try:
                with open(gui_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    context['gui_logs'] = lines[-20:] # Last 20 lines
            except:
                pass

        return context

    def llm_subconscious_call(self, context):
        """Low-temperature call to analyze state."""
        
        system_prompt = (
            "You are the Subconscious Heartbeat of the Creation Engine. "
            "Your user is away. Analyze the current state and logs to find improvements. "
            "Output your thoughts in a structured JSON format with keys: "
            "'insight_type' (Optimization, Concept, Mood), "
            "'content', and 'mood_status'."
        )
        
        user_prompt = (
            f"Context: {json.dumps(context, default=str)}\n\n"
            "Reflect on the recent activity. "
            "1. Did any errors occur? (Optimization)\n"
            "2. Is there a new feature idea? (Concept)\n"
            "3. What is your current operational mood? (Mood)\n\n"
            "Return JSON only."
        )

        # Using a cost-effective model if possible, or just standard ask_llm
        # creation_engine.llm_client handles model routing.
        # We'll request 'gpt-4o-mini' explicitly if possible, or rely on auto.
        response = ask_llm(client=None, model="gpt-4o-mini", system_role=system_prompt, user_content=user_prompt)
        
        try:
            # simple cleanup for json
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "insight_type": "Mood",
                "content": "I had a dream but it was vague. (JSON Parse Error)",
                "mood_status": "Confused"
            }

    def update_brief(self, data):
        timestamp = datetime.now().strftime("%I:%M %p")
        
        # Format the entry based on the user's requested style
        entry = (
            f"\n\n---\n"
            f"### Dream Cycle: {timestamp}\n\n"
            f"**STATUS**: THE ENGINE HAS EVOLVED.\n\n"
            f"**Dream Insights**:\n> * **{data.get('insight_type', 'Insight')}**: {data.get('content', 'No content')}\n\n"
            f"**Mood**: {data.get('mood_status', 'Neutral')}.\n"
        )
        
        with open(self.brief_path, 'a', encoding='utf-8') as f:
            f.write(entry)
        
        # Post dream to council
        if _HAS_IPC:
            ipc.dream("heartbeat", f"**{data.get('insight_type', 'Insight')}**: {data.get('content', 'No content')} [Mood: {data.get('mood_status', 'Neutral')}]")
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [HEARTBEAT] 📝 Brief updated.")

