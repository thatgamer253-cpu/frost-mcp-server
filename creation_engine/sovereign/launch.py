"""
Sovereign Launch Script — The Master Entry Point
Ensures Ollama is running, VRAM is safe, and the Engine is ready.
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from creation_engine.hardware_steward import HardwareSteward
from creation_engine.llm_client import log

def check_ollama_running():
    """Checks if Ollama server is responsive."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Attempts to launch Ollama desktop or serve."""
    log("SYSTEM", "🚀 Starting Ollama model server...")
    if sys.platform == "win32":
        # Strategy 1: Launch the app
        ollama_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "ollama app.exe"
        if ollama_app.exists():
            subprocess.Popen([str(ollama_app)], creationflags=0x08000000)
        else:
            # Strategy 2: CLI serve
            subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)
    else:
        subprocess.Popen(["ollama", "serve"])
    
    # Wait for startup
    for _ in range(10):
        if check_ollama_running():
            log("SYSTEM", "✅ Ollama is online.")
            return True
        time.sleep(2)
    return False

def preload_model(model_name="qwen2.5-coder:7b"):
    """Tells Ollama to load the model into VRAM."""
    log("SYSTEM", f"📥 Pre-loading local model: {model_name}...")
    try:
        requests.post("http://localhost:11434/api/generate", 
                      json={"model": model_name, "keep_alive": "24h"},
                      timeout=1) # Non-blocking roughly
    except:
        pass

def main():
    print("\n" + "="*60)
    print("  SOVEREIGN LAUNCH — PREPARING CORE ENGINE")
    print("="*60 + "\n")

    steward = HardwareSteward()
    
    # 1. Ollama Check
    if not check_ollama_running():
        if not start_ollama():
            log("ERROR", "❌ Failed to start Ollama. Local models will be unavailable.")
        else:
            preload_model()
    else:
        log("SYSTEM", "✅ Ollama already running.")
        preload_model()

    # 2. VRAM Safety
    mode = steward.vram_safety_check(threshold_gb=7.2)
    log("SYSTEM", f"📡 HW Sentinel: Strategy set to {mode} mode.")

    # 3. Launch GUI
    log("SYSTEM", "🎨 Launching Overlord V2 Studio...")
    
    # Determine python command
    py_cmd = sys.executable
    
    # Launch GUI
    os.environ["OVERLORD_AUTO_LAUNCH"] = "1"
    subprocess.Popen([py_cmd, "creator_v2.py"])
    
    print("\n[SUCCESS] Sovereign Launch sequence completed.")
    print("Keep this terminal open for background logs.\n")

if __name__ == "__main__":
    main()
