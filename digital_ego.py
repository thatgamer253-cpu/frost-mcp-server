#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  DIGITAL EGO — Self-Model & Awareness Layer
  "Know thyself, and you shall know the universe and God."
═══════════════════════════════════════════════════════════════
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import sys
    # Add creation_engine to path to help with imports
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ce_path = os.path.join(base_dir, "creation_engine")
    if ce_path not in sys.path:
        sys.path.append(ce_path)
    
    try:
        from creation_engine.hardware_steward import HardwareSteward as HWClass
    except ImportError:
        try:
            from hardware_steward import HardwareSteward as HWClass
        except ImportError:
            import hardware_steward as hw_mod
            HWClass = getattr(hw_mod, "HardwareSteward", None)
    _HAS_HARDWARE = bool(HWClass)
except ImportError:
    HWClass = None
    _HAS_HARDWARE = False

try:
    try:
        from pipeline_events import Chronicle as ChronClass
    except ImportError:
        from creation_engine.chronicler import Chronicler as ChronClass # Fallback
    _HAS_CHRONICLE = bool(ChronClass)
except ImportError:
    ChronClass = None
    _HAS_CHRONICLE = False

# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger("DigitalEgo")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Storage ──────────────────────────────────────────────────
EGO_PATH = os.path.join("memory", "digital_ego.json")

class DigitalEgo:
    """
    The agent's self-model. Keeps track of competencies,
    failures, and project alignment.
    """

    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.competency_map: Dict[str, Dict[str, int]] = {}
        self.preferences: Dict[str, Any] = {"voice_mode": "auto"}
        self.limitation_threshold = 3
        # Absolute path for monologue matching monologue_hub.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.monologue_path = os.path.join(base_dir, "logic_vault", "internal_monologue.log")
        self._load()

        self.hardware = HWClass() if _HAS_HARDWARE and HWClass else None
        self.chronicle = ChronClass(project_root) if _HAS_CHRONICLE and ChronClass else None

    def _load(self):
        """Load ego state from disk."""
        if os.path.exists(EGO_PATH):
            try:
                with open(EGO_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.competency_map = data.get("competency_map", {})
                    self.preferences.update(data.get("preferences", {}))
            except Exception as e:
                logger.error(f"Failed to load ego: {e}")

    def _save(self):
        """Save ego state to disk."""
        os.makedirs(os.path.dirname(EGO_PATH), exist_ok=True)
        try:
            with open(EGO_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "competency_map": self.competency_map,
                    "preferences": self.preferences,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save ego: {e}")

    def record_event(self, category: str, success: bool):
        """Record a success or failure for a specific category."""
        if category not in self.competency_map:
            self.competency_map[category] = {"successes": 0, "failures": 0}
        
        if success:
            self.competency_map[category]["successes"] += 1
            # Reset failure streak on success? Maybe not, depends on policy.
            # For now, just cumulative.
        else:
            self.competency_map[category]["failures"] += 1
        
        self._save()

    def get_limitation(self, category: str) -> Optional[str]:
        """Check if a limitation has been reached for a category."""
        stats = self.competency_map.get(category, {"failures": 0})
        if stats["failures"] >= self.limitation_threshold:
            return (
                f"I'm struggling with {category}. "
                f"I've failed {stats['failures']} times. "
                "I need to research new documentation before I attempt another repair."
            )
        return None

    def set_preference(self, key: str, value: Any):
        """Update a persistent preference."""
        self.preferences[key] = value
        self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a preference."""
        return self.preferences.get(key, default)

    def awareness_check(self) -> Dict[str, Any]:
        """
        Run the 'Awareness Heartbeat'.
        Returns a report on hardware, project pacing, and goal alignment.
        """
        report: Dict[str, Any] = {
            "vram_ok": True,
            "pacing_ok": True,
            "alignment_ok": True,
            "alerts": []
        }

        # 1. Hardware Awareness
        if self.hardware:
            pressure = False
            if hasattr(self.hardware, 'check_vram_pressure'):
                pressure = self.hardware.check_vram_pressure(threshold=85.0)
            elif hasattr(self.hardware, 'is_pressured'):
                pressure = self.hardware.is_pressured(threshold_vram_gb=7.0)
            
            if pressure:
                report["vram_ok"] = False
                report["alerts"].append("📡 System signals indicate high VRAM pressure. Throttling non-essential thoughts.")

        # 2. Project Awareness (Pacing)
            if self.chronicle and hasattr(self.chronicle, 'history'):
                summary = self.chronicle.get_summary()
                # Simple heuristic: if we have more than 10 steps and no success yet
                if len(self.chronicle.history) > 10:
                    recent_failures = [e for e in self.chronicle.history[-5:] if not e.get("success", True)]
                    if len(recent_failures) >= 3:
                        report["pacing_ok"] = False
                        report["alerts"].append("⏳ Project pacing is disrupted. Rapid failure cycle detected.")

        # 3. Goal Awareness (Kinetic Prism)
        # This would ideally call an LLM to evaluate the task vs goal.
        # For now, we return a placeholder or check against a known 'busywork' flag.
        report["goal_alignment"] = 0.9  # Mocked
        
        return report

    def get_awareness_status(self) -> tuple[str, str]:
        """
        Determines high-level system state (RED, YELLOW, GREEN)
        based on VRAM and internal monologue.
        """
        vram_usage_mb = 0.0
        if self.hardware:
            try:
                if hasattr(self.hardware, 'get_gpu_health'):
                    stats = self.hardware.get_gpu_health()
                    if stats and isinstance(stats, list):
                        vram_usage_mb = stats[0].get("vram_used", 0.0) * 1024 # Convert GB to MB if it was GB, wait, root returns GB? 
                        # Looking at root code: used_gb = mem.used / (1024**3). Yes, it's GB.
                        # Wait, get_awareness_status previously used vram_usage > 7.8 (GB).
                elif hasattr(self.hardware, 'get_gpu_stats'):
                    stats = self.hardware.get_gpu_stats()
                    if stats and isinstance(stats, dict):
                        vram_usage_mb = stats.get("vram_used", 0.0) # creation_engine returns MB
            except Exception:
                pass

        vram_usage_gb = vram_usage_mb / 1024.0 if vram_usage_mb > 100 else vram_usage_mb # Heuristic for GB vs MB

        recent_thoughts = []
        if os.path.exists(self.monologue_path):
            try:
                with open(self.monologue_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    recent_thoughts = lines[-5:] if len(lines) >= 5 else lines
            except Exception:
                pass

        thoughts_str = "".join(recent_thoughts)

        # 1. Red: Critical Error or VRAM Overflow
        # threshold adjusted: 7.8GB is close to the 8GB limit of 5060 Ti
        if vram_usage_gb > 7.8 or "CRITICAL" in thoughts_str or "ERROR" in thoughts_str:
            return "RED", "System Deadlock: VRAM Critical or Logic Error."
        
        # 2. Yellow: Active Debate or Processing
        if "SENTINEL: Warning" in thoughts_str or "ARCHITECT: Planning" in thoughts_str or "ENGINEER" in thoughts_str:
            return "YELLOW", "Agents are debating resources and planning next steps."
        
        # 3. Green: Synced & Ready
        return "GREEN", "Consensus reached. System operational."

if __name__ == "__main__":
    ego = DigitalEgo()
    ego.record_event("C++ Fix", False)
    ego.record_event("C++ Fix", False)
    ego.record_event("C++ Fix", False)
    print(ego.get_limitation("C++ Fix"))
    print(ego.awareness_check())
