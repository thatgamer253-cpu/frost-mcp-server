#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Visual Auditor
  Local UI/UX verification using Qwen2.5-VL via Ollama.
  Compares rendered output against Architectural blueprints.
==============================================================
"""

import os
import json
import time
from typing import Dict, List, Any, Optional

try:
    from local_overlord import log
except ImportError:
    def log(tag, msg):
        print(f"[{tag}] {msg}")

class VisualAuditor:
    """Performs visual red-teaming and UI verification."""

    AUDIT_PROMPT = """
    You are the 'Overlord Visual Sentinel.'
    Analyze the provided screenshot(s) of a generated application.
    Compare the visual output against the Architectural Blueprint below.
    
    ARCHITECTURAL BLUEPRINT:
    {blueprint}
    
    MISSION: 
    Identify any visual discrepancies, missing UI elements, broken layouts, 
    or UX failures. Focus on accessibility, responsiveness, and brand consistency.
    
    Output ONLY valid JSON with this schema:
    {{
        "verdict": "VIBE_VERIFIED | VISUAL_FAIL",
        "findings": [
            {{
                "element": "e.g., Submit Button",
                "issue": "e.g., Missing from the sidebar",
                "severity": "CRITICAL | MEDIUM | LOW"
            }}
        ],
        "ux_score": 0-100,
        "summary": "Overall visual assessment."
    }}
    """

    def __init__(self, local_overlord=None):
        self.overlord = local_overlord
        self.model = "qwen2.5vl:7b"

    def audit_screenshot(self, screenshot_path: str, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Audit a single screenshot against a project blueprint."""
        if not os.path.exists(screenshot_path):
            return {"error": f"Screenshot not found: {screenshot_path}"}

        log("VISUAL", f"Auditing UI screenshot: {os.path.basename(screenshot_path)}")
        
        prompt = self.AUDIT_PROMPT.format(blueprint=json.dumps(blueprint, indent=2))
        
        if self.overlord:
            raw_response = self.overlord._ask_local_vision(prompt, [screenshot_path], model=self.model)
            try:
                # Strip any potential markdown fences
                if "```" in raw_response:
                    raw_response = raw_response.split("```")[1]
                    if raw_response.startswith("json"):
                        raw_response = raw_response[4:]
                
                return json.loads(raw_response.strip())
            except Exception as e:
                log("ERROR", f"Failed to parse visual audit response: {e}")
                return {
                    "verdict": "PARSE_ERROR",
                    "summary": f"Could not parse AI response: {raw_response}",
                    "findings": [],
                    "ux_score": 0
                }
        else:
            return {"error": "LocalOverlord not provided to VisualAuditor."}

    def batch_audit(self, screenshot_paths: List[str], blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a multi-view audit of the application."""
        # Simple implementation: use first screenshot or combine? 
        # For now, we'll just process the first one for simplicity.
        return self.audit_screenshot(screenshot_paths[0], blueprint)

if __name__ == "__main__":
    # Test stub
    from local_overlord import LocalOverlord
    ov = LocalOverlord("TestProject")
    va = VisualAuditor(ov)
    # result = va.audit_screenshot("test_ui.png", {"project_name": "Test", "files": []})
    # print(json.dumps(result, indent=2))
