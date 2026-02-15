import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

class FrostCore:
    """
    The central orchestrator for the Frost AI Development Platform.
    Manages job automation workflows and tool generation requests.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.config_path = os.path.join(workspace_root, "frost_config.json")
        self.state_path = os.path.join(workspace_root, "frost_state.json")
        self.config = self._load_config()
        self.state = self._load_state()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "version": "1.0.0",
            "provider_preferences": ["openai", "gemini", "anthropic"],
            "job_search_params": {
                "keywords": [],
                "locations": [],
                "distance": 25
            },
            "output_dir": os.path.join(self.workspace_root, "frost_outputs")
        }

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                return json.load(f)
        return {
            "sessions": [],
            "generated_tools": [],
            "job_matches": []
        }

    def save_state(self):
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    def log_event(self, event_type: str, details: Any):
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [FROST-{event_type}] {details}")

if __name__ == "__main__":
    # Internal test
    frost = FrostCore(os.getcwd())
    frost.log_event("INIT", "Frost Core successfully initialized.")
