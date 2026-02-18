"""
Chronicler — Temporal Awareness (Timeline Layer)
Anchors events on a linear timeline to track project evolution.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

CHRONICLE_FILE = os.path.join("memory", "chronicle.jsonl")

class Chronicler:
    """Maintains a chronicle of creation events for linear time awareness."""

    def __init__(self):
        os.makedirs("memory", exist_ok=True)

    def log_event(self, project_id: str, stage: str, event_type: str, content: str, metadata: Optional[Dict] = None):
        """
        Record a milestone in the project's timeline.
        Stages: SEED, BRAINSTORM, DRAFT, EDIT, FINAL, EXPORT
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "project_id": project_id,
            "stage": stage,
            "event": event_type,
            "content": content[:500], # Keep it concise
            "metadata": metadata or {}
        }
        with open(CHRONICLE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"Chronicler: Recorded [{stage}] {event_type} for project {project_id}")

    def get_history(self, project_id: str) -> List[Dict]:
        """Retrieve the timeline for a specific project."""
        history = []
        if not os.path.exists(CHRONICLE_FILE):
            return []
            
        with open(CHRONICLE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("project_id") == project_id:
                        history.append(data)
                except Exception:
                    continue
        return history

    def get_latest_project_id(self) -> Optional[str]:
        """Returns the ID of the most recently active project."""
        if not os.path.exists(CHRONICLE_FILE):
            return None
        
        # Read last line for speed
        try:
            with open(CHRONICLE_FILE, "rb") as f:
                f.seek(0, os.SEEK_END)
                if f.tell() == 0: return None
                
                # Simple last line read
                f.seek(-1024, os.SEEK_CUR) if f.tell() > 1024 else f.seek(0)
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1].decode())
                    return last.get("project_id")
        except Exception:
            pass
        return None

chronicler = Chronicler()
