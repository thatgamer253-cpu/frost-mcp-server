import os
import json
from datetime import datetime

class AwarenessHub:
    def __init__(self):
        # Ensure we use an absolute path for the logic_vault directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_path = os.path.join(base_dir, "logic_vault", "internal_monologue.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def record_thought(self, agent_name, thought_content):
        """
        Records an agent's internal reasoning to the hidden thought channel.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {agent_name.upper()}: {thought_content}\n"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry)
            print(f"Awareness Update: {agent_name} is thinking...")
        except Exception as e:
            print(f"Failed to record thought: {e}")

# Global instance for easy access
hub = AwarenessHub()

if __name__ == "__main__":
    # Test cases
    hub.record_thought("Sentinel", "VRAM is at 88%. I am delaying the code-scrub to prioritize the Unreal render.")
    hub.record_thought("Alchemist", "Donovan's last three 'Seeds' were dark-themed. I am shifting the synthesis palette to Noir.")
