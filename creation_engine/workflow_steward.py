"""
Workflow Steward — Observation & Preference Learning (Sense Layer)
Monitors how the user interacts with the engine to infer priorities and constraints.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from monologue_hub import hub as awareness_hub


PATTERNS_FILE = os.path.join("memory", "workflow_patterns.jsonl")
CONSTRAINTS_FILE = os.path.join("memory", "permanent_constraints.json")

class WorkflowSteward:
    """Observes workflow patterns to update internal engine priorities."""

    def __init__(self):
        os.makedirs("memory", exist_ok=True)

    def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """Log a user action or workflow event."""
        entry = {
            "ts": datetime.now().isoformat(),
            "type": activity_type,
            "details": details
        }
        with open(PATTERNS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        # If it's a manual edit, we might want to analyze it immediately
        if activity_type == "manual_edit":
            self._analyze_manual_edit(details)

    def _analyze_manual_edit(self, details: Dict[str, Any]):
        """
        Analyze what the user changed after an AI generation.
        Details should contain: {'file': str, 'before': str, 'after': str}
        """
        # In a real implementation, we would diff these and look for patterns.
        # For now, we log the intent.
        pass

    def update_preferences(self, key: str, value: str, rationale: str):
        """Update the permanent constraints based on learned behavior."""
        if not os.path.exists(CONSTRAINTS_FILE):
            data = {"permanent_rules": [], "prohibited_patterns": [], "user_preferences": []}
        else:
            with open(CONSTRAINTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        if "user_preferences" not in data:
            data["user_preferences"] = []
            
        # Add or update preference
        updated = False
        for pref in data["user_preferences"]:
            if pref.get("key") == key:
                pref["value"] = value
                pref["rationale"] = rationale
                pref["updated_at"] = datetime.now().isoformat()
                updated = True
                break
                
        if not updated:
            data["user_preferences"].append({
                "key": key,
                "value": value,
                "rationale": rationale,
                "updated_at": datetime.now().isoformat()
            })
            
        with open(CONSTRAINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        print(f"WorkflowSteward: Updated preference '{key}' -> '{value}'")

    def get_summary(self) -> str:
        """Returns a human-readable summary of learned workflow patterns."""
        if not os.path.exists(PATTERNS_FILE):
            return "No workflow data collected yet."
        # Simple analysis of the last 100 entries could go here
        return "Detecting patterns in manual edits and task duration..."

workflow_steward = WorkflowSteward()
