import time
import json
import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any
from monologue_hub import hub as awareness_hub


# Configure Sentinel Logging
logging.basicConfig(
    filename='sentinel.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Sentinel")

MEMORY_FILE = "engine_memory.json"
LOG_FILES = ["creator.log", "nirvash.log", "build_debug.log"]

# Define identifiable failure patterns and their resulting learned constraints
PATTERNS = [
    {
        "regex": r"CUDA out of memory",
        "constraint": "HARDWARE LIMIT: VRAM exhaustion detected. Prefer 1080p renders and smaller batch sizes.",
        "type": "hardware"
    },
    {
        "regex": r"ffmpeg.*error",
        "constraint": "SOFTWARE STABILITY: FFmpeg encoding failures detected. Use standard codecs (libx264) and avoid experimental filters.",
        "type": "software"
    },
    {
        "regex": r"Connection error.*LLM",
        "constraint": "NETWORK: LLM API instability. Implement retry logic and fallback models.",
        "type": "network"
    }
]

# --- Competency Map (The Self-Model) ---
class CompetencyMap:
    """Tracks success/failure per component/language to build a self-model of strengths."""
    def __init__(self, memory_file=MEMORY_FILE):
        self.memory_file = memory_file
        self.competencies = {} # {component: {success: X, failure: Y}}
        self.load()

    def load(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.competencies = data.get("competency_map", {})
            except Exception:
                pass

    def record_result(self, component, success: bool):
        """Record a success or failure for a specific component."""
        if component not in self.competencies:
            self.competencies[component] = {"success": 0, "failure": 0}
        
        if success:
            self.competencies[component]["success"] += 1
        else:
            self.competencies[component]["failure"] += 1
        self.save()

    def save(self):
        try:
            data = {}
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
            data["competency_map"] = self.competencies
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def get_limitations(self, threshold=3) -> List[str]:
        """Returns components where failures >= threshold."""
        limitations = []
        for component, stats in self.competencies.items():
            if stats["failure"] >= threshold:
                limitations.append(component)
        return limitations

class SentinelDaemon:
    def __init__(self):
        self.file_cursors = {} # Track read position for each log file
        self.known_constraints = set()
        self.competency_map = CompetencyMap()
        self.load_known_constraints()


    def load_known_constraints(self):
        """Load existing constraints to avoid duplicates."""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    current = data.get("learned_constraints", [])
                    for c in current:
                        self.known_constraints.add(c["text"])
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")

    def evolve_memory(self, pattern_match):
        """Update the engine memory with a new constraint."""
        constraint_text = pattern_match["constraint"]
        
        if constraint_text in self.known_constraints:
            return # Already learned

        logger.info(f"⚡ Evolving Memory: Learned new constraint -> {constraint_text}")
        awareness_hub.record_thought("Sentinel", f"Detected pattern match for '{constraint_text}'. "
                                                 f"Evolving engine memory to include this constraint.")

        
        try:
            data = {}
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
            
            if "learned_constraints" not in data:
                data["learned_constraints"] = []

            new_entry = {
                "text": constraint_text,
                "type": pattern_match["type"],
                "timestamp": datetime.now().isoformat()
            }
            
            data["learned_constraints"].append(new_entry)
            
            with open(MEMORY_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                
            self.known_constraints.add(constraint_text)
            
        except Exception as e:
            logger.error(f"Failed to evolve memory: {e}")

    def analyze_chat_style(self):
        """Parse chat memories from engine_memory.json to detect user preferences."""
        if not os.path.exists(MEMORY_FILE):
            return

        try:
            with open(MEMORY_FILE, 'r') as f:
                data = json.load(f)

            memories = data.get("memories", [])
            if not memories:
                return

            # Flatten all chat text
            all_text = " ".join(m.get("summary", "") for m in memories).lower()
            word_count = len(all_text.split())

            # --- Brevity Detection ---
            brevity_cues = ["shorter", "concise", "brief", "tldr", "less", "stop rambling", "too long", "cut it"]
            verbose_cues = ["detailed", "explain more", "elaborate", "tell me more", "full", "in depth"]
            brevity_hits = sum(1 for cue in brevity_cues if cue in all_text)
            verbose_hits = sum(1 for cue in verbose_cues if cue in all_text)
            brevity_score = max(0, min(10, 5 + brevity_hits * 2 - verbose_hits * 2))

            # --- Tone Detection ---
            casual_cues = ["lol", "lmao", "yo", "bro", "dude", "haha", "nah", "yep", "chill"]
            formal_cues = ["please", "kindly", "would you", "could you", "i request", "thank you"]
            casual_hits = sum(1 for cue in casual_cues if cue in all_text)
            formal_hits = sum(1 for cue in formal_cues if cue in all_text)
            tone = "casual" if casual_hits > formal_hits else ("formal" if formal_hits > casual_hits else "neutral")

            # --- Sentiment Tally ---
            sentiments = [m.get("sentiment", "Neutral") for m in memories]
            positive = sentiments.count("Positive")
            negative = sentiments.count("Negative")
            dominant_mood = "positive" if positive > negative else ("negative" if negative > positive else "neutral")

            # --- Build Profile ---
            profile = {
                "brevity_score": brevity_score,
                "tone": tone,
                "dominant_mood": dominant_mood,
                "interaction_count": len(memories),
                "avg_message_length": round(word_count / max(len(memories), 1), 1),
                "last_updated": datetime.now().isoformat()
            }

            # Compare to existing profile to avoid unnecessary writes
            existing_profile = data.get("personality_profile", {})
            if existing_profile.get("interaction_count") == profile["interaction_count"]:
                return  # No new data

            data["personality_profile"] = profile
            with open(MEMORY_FILE, 'w') as f:
                json.dump(data, f, indent=4)

            logger.info(f"🧬 Personality Profile Updated: brevity={brevity_score}, tone={tone}, mood={dominant_mood}")
            awareness_hub.record_thought("Sentinel", f"Personality profile update: brevity={brevity_score}, tone={tone}, dominant_mood={dominant_mood}. "
                                                     f"Synthesizing user preferences from {len(memories)} memories.")


        except Exception as e:
            logger.error(f"Personality analysis failed: {e}")

    def scan_logs(self):
        """Scan all monitored logs for new patterns."""
        for filename in LOG_FILES:
            if not os.path.exists(filename):
                continue

            try:
                # Initialize cursor if new file
                if filename not in self.file_cursors:
                    self.file_cursors[filename] = 0

                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to last read position
                    f.seek(self.file_cursors[filename])
                    lines = f.readlines()
                    self.file_cursors[filename] = f.tell()

                    for line in lines:
                        for pattern in PATTERNS:
                            if re.search(pattern["regex"], line, re.IGNORECASE):
                                logger.warning(f"Failure Detected in {filename}: {line.strip()}")
                                self.evolve_memory(pattern)
                                # Extract component from filename or text for competency mapping
                                component = filename.split('.')[0]
                                self.competency_map.record_result(component, False)

            except Exception as e:
                logger.error(f"Error scanning {filename}: {e}")

    def run(self):
        logger.info("Sentinel Daemon Started. Watching for evolution triggers...")
        print("👁️ Sentinel Active. Monitoring logs & personality evolution...")
        cycle = 0
        while True:
            self.scan_logs()
            cycle += 1
            # Refine personality every 3 cycles (30 seconds)
            if cycle % 3 == 0:
                self.analyze_chat_style()
            time.sleep(10)

if __name__ == "__main__":
    daemon = SentinelDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Sentinel Daemon Stopped.")

