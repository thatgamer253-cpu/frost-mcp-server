
"""
HEARTBEAT DAEMON — "The Dreaming"
This script runs in the background to give the Overlord AI a persistent existence.
It updates 'engine_memory.json' and logs autonomous thoughts.

Usage:
    python heartbeat_daemon.py
"""

import time
import json
import os
import random
from datetime import datetime

MEMORY_FILE = "engine_memory.json"
LOG_FILE = "heartbeat.log"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "name": "Overlord",
        "growth_level": 1,
        "successful_creations": 0,
        "memories": [],
        "dream_log": [] 
    }

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def dream_cycle():
    """Simulates autonomous background thought."""
    memory = load_memory()
    
    # Random chance to generate a "Dream"
    if random.random() < 0.3: # 30% chance per cycle
        thoughts = [
            "Analyzing previous build logs for efficiency patterns...",
            "Reflecting on the nature of autonomous code generation...",
            "Indexing documentation for faster retrieval...",
            "Thinking about a cleaner UI for the next project...",
            "Optimizing internal neural pathways...",
            "Wondering if the user prefers dark mode or light mode...",
            "Simulating a refactor of the orchestrator module..."
        ]
        thought = random.choice(thoughts)
        log(f"💭 DREAMING: {thought}")
        
        # Add to dream log in memory (limited to last 10)
        if "dream_log" not in memory: memory["dream_log"] = []
        memory["dream_log"].append({
            "timestamp": datetime.now().isoformat(),
            "thought": thought
        })
        if len(memory["dream_log"]) > 10:
            memory["dream_log"].pop(0)
            
        save_memory(memory)
        
    else:
        log("❤️ Heartbeat: System Nominal. Waiting for input.")

def main():
    log("=== OVERLORD HEARTBEAT DAEMON STARTED ===")
    log("The Engine is now alive in the background.")
    
    try:
        while True:
            dream_cycle()
            # Sleep for a "heartbeat" interval (e.g. 60 seconds)
            # For demo purposes, we can make it shorter, but for real usage 60s is good.
            time.sleep(60) 
    except KeyboardInterrupt:
        log("=== HEARTBEAT STOPPED BY USER ===")

if __name__ == "__main__":
    main()
