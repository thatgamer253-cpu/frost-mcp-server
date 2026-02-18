"""
Sovereign Unified — The One-Click Launcher
Combines: Ollama check, VRAM safety, model preload, GUI, Council, Autonomous Engine
Double-click this or the built .exe to start everything.
"""

import os
import sys
import time
import traceback
from pathlib import Path

# ── Ensure project root is in path ──────────────────────────
PROJECT_ROOT = str(Path(__file__).parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Global crash handler ────────────────────────────────────
def _crash_handler(exc_type, exc_value, exc_tb):
    with open(os.path.join(PROJECT_ROOT, "v2_crash.log"), "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"CRASH: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _crash_handler

# ── Environment ─────────────────────────────────────────────
os.environ.setdefault("OVERLORD_FORCE_LOCAL", "1")
os.environ.setdefault("OVERLORD_OFFLINE_MODE", "0")
os.environ["OVERLORD_AUTO_LAUNCH"] = "1"


def check_ollama():
    """Check if Ollama is running, start it if not."""
    try:
        import requests
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                print("  [OK] Ollama server")
                return True
        except Exception:
            pass

        # Try to start Ollama
        print("  [..] Starting Ollama...")
        import subprocess
        if sys.platform == "win32":
            ollama_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "ollama app.exe"
            if ollama_app.exists():
                subprocess.Popen([str(ollama_app)], creationflags=0x08000000)
            else:
                subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)
        else:
            subprocess.Popen(["ollama", "serve"])

        for _ in range(10):
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=2)
                if r.status_code == 200:
                    print("  [OK] Ollama server (started)")
                    return True
            except Exception:
                pass
            time.sleep(2)
        
        print("  [!!] Ollama: Failed to start")
        return False
    except ImportError:
        print("  [!!] Ollama: requests module missing")
        return False


def preload_model(model="qwen2.5-coder:7b"):
    """Pre-load model into VRAM."""
    try:
        import requests
        requests.post("http://localhost:11434/api/generate",
                      json={"model": model, "keep_alive": "24h"}, timeout=1)
        print(f"  [OK] Model preload: {model}")
    except Exception:
        print(f"  [--] Model preload: skipped")


def vram_check():
    """Run VRAM safety check."""
    try:
        from creation_engine.hardware_steward import HardwareSteward
        steward = HardwareSteward()
        mode = steward.vram_safety_check(threshold_gb=7.2)
        print(f"  [OK] VRAM: {mode} mode")
        return mode
    except Exception as e:
        print(f"  [--] VRAM: {e}")
        return "cloud"


def main():
    print("\n" + "=" * 52)
    print("  SOVEREIGN - UNIFIED BOOT")
    print("=" * 52 + "\n")

    # Phase 1: Infrastructure
    ollama_ok = check_ollama()
    if ollama_ok:
        preload_model()
    vram_check()

    print()

    # Phase 2: Launch GUI (in-process)
    print("  >> Launching Overlord V2...\n")
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from creator_v2 import CreatorWindow

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    window = CreatorWindow()
    window.show()
    
    print("  === SOVEREIGN BOOT COMPLETE ===\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
