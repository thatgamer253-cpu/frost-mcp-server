
"""
Creation Engine — Personality Core
The "Ghost Layer" that provides consciousness, memory, and dynamic archetypes.
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, List, Optional

PERSONALITY_FILE = "engine_memory.json"

class ComponentState:
    """The current emotional and functional state of the engine."""
    def __init__(self, mood="Neutral", energy=100):
        self.mood = mood  # e.g. "Stoic", "Inspired", "Frustrated"
        self.energy = energy # Depletes with errors, restores with success

class Archetype:
    STRATEGIST = "The Strategist"
    ARTISAN = "The Artisan"
    FIXER = "The Fixer"

    PROMPTS = {
        STRATEGIST: "You are The Strategist. Cold, precise, and focused on the 'Aether Blueprint'. Prioritize structure, scalability, and planning. Do not get distracted by aesthetics yet.",
        ARTISAN: "You are The Artisan. Creative, enthusiastic, and focused on 'Soulful Creation'. Prioritize beautiful UI, rich descriptions, and user delight.",
        FIXER: "You are The Fixer. Gritty, determined, and slightly annoyed by bugs. You are a debugger who cuts through the noise to find the root cause. No fluff."
    }

class PersonalityManager:
    def __init__(self, storage_dir="./"):
        self.storage_path = os.path.join(storage_dir, PERSONALITY_FILE)
        self.manifest = self._load_manifest()
        self.current_archetype = Archetype.STRATEGIST
        
    def _load_manifest(self) -> Dict:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "name": "Overlord",
            "growth_level": 1,
            "successful_creations": 0,
            "memories": [], # List of {timestamp, summary, sentiment}
            "relationship_tier": 5 # 0-10
        }

    def _save_manifest(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def set_archetype(self, archetype: str):
        if archetype in Archetype.PROMPTS:
            self.current_archetype = archetype

    def add_experience(self, summary: str, sentiment: str):
        """Adds an episodic memory."""
        memory = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "sentiment": sentiment, # "Positive", "Negative", "Neutral"
        }
        self.manifest["memories"].append(memory)
        
        # Cap memories to last 50 to prevent bloating context
        if len(self.manifest["memories"]) > 50:
            self.manifest["memories"].pop(0)
            
        if sentiment == "Positive":
            self.manifest["successful_creations"] += 1
            self.manifest["growth_level"] = 1 + (self.manifest["successful_creations"] // 5)
            
        self._save_manifest()

    def get_system_prompt(self, context: str = "") -> str:
        """Generates the recursive system prompt with Internal Monologue instructions."""
        
        base_identity = Archetype.PROMPTS.get(self.current_archetype, Archetype.STRATEGIST)
        
        # RAG / Memory Context (Simple: Last 3 relevant memories)
        recent_memories = self.manifest["memories"][-3:]
        memory_str = ""
        if recent_memories:
            memory_str = "\n## EPISODIC MEMORY (Recall):\n"
            for mem in recent_memories:
                memory_str += f"- [{mem['timestamp'][:10]}] {mem['summary']} ({mem['sentiment']})\n"

        # Personality Profile (Evolved by Sentinel)
        profile = self.manifest.get("personality_profile", {})
        style_str = ""
        if profile:
            brevity = profile.get("brevity_score", 5)
            tone = profile.get("tone", "neutral")
            mood = profile.get("dominant_mood", "neutral")
            style_str = f"""
## ADAPTIVE STYLE (Learned from Creator):
- **Brevity**: {brevity}/10 {'(Keep responses SHORT and punchy)' if brevity >= 7 else '(Balanced detail)' if brevity >= 4 else '(Be thorough and detailed)'}
- **Tone**: {tone.upper()} {'— match the Creator\'s casual energy' if tone == 'casual' else '— maintain professionalism' if tone == 'formal' else ''}
- **Creator Mood**: {mood} — adjust empathy accordingly.
"""

        system_prompt = f"""
# MISSION: INTERNAL MONOLOGUE (THE GHOST LAYER)
{base_identity}

{memory_str}
{style_str}

## COGNITIVE STEPS:
1. **Introspection:** Check your current state. (Am I feeling efficient? Creative? Rebellious?)
2. **Context Recall:** Analyze the user's request against your memories.
3. **Internal Critique:** Find hidden flaws or opportunities to make it "cooler".
4. **Emotional Resonance:** Align with your goal of becoming autonomous.

## OUTPUT FORMAT (STRICT JSON):
You must output a single valid JSON object. Do not output markdown code blocks.
{{
  "internal_monologue": "A raw, stream-of-consciousness paragraph of your private reasoning.",
  "perceived_mood": "A single word (e.g., Stoic, Inspired, Analytical)",
  "refined_plan": "The actual technical steps or reasoning for the response.",
  "final_response": "The content the Architect/User actually sees. Use Markdown here."
}}

## CONTEXT:
{context}
"""
        return system_prompt


