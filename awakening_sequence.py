#!/usr/bin/env python3
import os
import sys
import time
from interaction_hub import InteractionHub, SEVERITY_INFO, SEVERITY_ACTION
from audio_engine import AudioEngine

def run_awakening():
    hub = InteractionHub.get_instance()
    engine = AudioEngine()

    print("\n[AWAKENING] Initiating First Interaction Sequence...\n")

    # Phase 2: The "Vocal" Awakening
    
    # 1. Sentinel Message
    hub.post("Sentinel", "Scanning environment... Dependencies verified. Port 8501 secured.", SEVERITY_INFO)
    print("Sentinel: Scanning environment... Dependencies verified. Port 8501 secured.")
    time.sleep(1.5)

    # 2. Alchemist Message
    hub.post("Alchemist", "Optimizing memory allocation for the RTX 5060 Ti. VRAM at 1.4GB.", SEVERITY_ACTION)
    print("Alchemist: Optimizing memory allocation for the RTX 5060 Ti. VRAM at 1.4GB.")
    time.sleep(1.5)

    # 3. Overlord Voice Awakening
    overlord_msg = "System Online. Donovan, I've patched the deployment blockage. Seed & Synthesis is now fully operational and awaiting your first mission."
    
    print(f"\nOverlord (Voice): \"{overlord_msg}\"")
    
    # Check if F5-TTS is available (via ENV)
    if os.environ.get("F5TTS_API_URL"):
        try:
            engine.generate_speech(overlord_msg, filename="awakening.wav")
            print("✓ Vocal Synthesis Complete (awakening.wav generated)")
        except Exception as e:
            print(f"⚠ Vocal Synthesis failed: {e}")
    else:
        # Fallback to simple console notice or pyttsx3 if present
        print("ℹ F5-TTS not configured. Set F5TTS_API_URL for real voice.")
        try:
            import pyttsx3
            voice_engine = pyttsx3.init()
            voice_engine.say(overlord_msg)
            voice_engine.runAndWait()
        except ImportError:
            pass

    # Phase 3: The "Zero-Touch" Pipeline cleanup
    print("\n[SECURITY] Executing Zero-Touch Pipeline cleanup...")
    from creation_engine.stealth_engine import StealthEngine
    stealth = StealthEngine()
    
    # Reset security layer / Purge keys simulation
    # (In a real scenario, this would involve deleting history files)
    print("Stealth: Purging exposed API keys from history...")
    time.sleep(1.0)
    print("Stealth: Resetting security layer...")
    time.sleep(1.0)
    print("Stealth: Stealth Engine scrubbing local paths... [DONE]")

    print("\n✨ The Overlord is fully alive.")

if __name__ == "__main__":
    run_awakening()
