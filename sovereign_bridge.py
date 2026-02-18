import requests
import json
import asyncio
import os
import sys

# Standard library imports for audio
try:
    from kokoro import KPipeline  # Local TTS
    import sounddevice as sd      # For local playback
    import soundfile as sf        # For audio data handling
except ImportError:
    print("--- [Dependency Alert]: kokoro or sounddevice missing. ---")
    print("Please run: pip install kokoro sounddevice soundfile")

# Import our local memory manager
try:
    from creation_engine.local_memory import LocalMemoryManager
except ImportError:
    # Fallback if running from a different context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from creation_engine.local_memory import LocalMemoryManager
    except ImportError:
        print("--- [Critical Error]: LocalMemoryManager not found. ---")
        class LocalMemoryManager:
            def __init__(self, **kwargs): pass
            def add_turn(self, r, c): pass
            def get_full_context(self): return []

class SovereignBridge:
    """
    Sovereign Bridge: Master logic for Offline Interaction.
    Combines Local Memory, Local Reasoning (Ollama), and Local Voice (Kokoro).
    """
    def __init__(self):
        # 1. Initialize Memory
        # OFF-LOADING: DeepSeek-R1:7b on local Ollama
        self.memory = LocalMemoryManager(model="deepseek-r1:7b", limit=5)
        
        # 2. Initialize Voice (Kokoro on CPU to save VRAM for 5060 Ti)
        try:
            self.tts_pipeline = KPipeline(lang_code='a') # 'a' for American English
        except Exception as e:
            print(f"--- [Voice Error]: Failed to initialize Kokoro: {e} ---")
            self.tts_pipeline = None

        self.ollama_url = "http://localhost:11434/api/chat"

    async def process_interaction(self, user_input):
        """
        Main loop: Memory Update -> Reasoning -> Speech -> Persistence
        """
        # 1. Update Memory with the new Seed
        self.memory.add_turn("user", user_input)
        
        # 2. Get Reasoning from Local DeepSeek
        payload = {
            "model": "deepseek-r1:7b",
            "messages": self.memory.get_full_context(),
            "stream": False
        }
        
        print("\n--- [Engine Reasoning: Offline] ---")
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            if response.status_code == 200:
                ai_thought = response.json()['message']['content']
            else:
                ai_thought = f"System Error: Ollama returned {response.status_code}"
        except Exception as e:
            ai_thought = f"System Offline: {e}"

        print(f"Assistant: {ai_thought}\n")
        
        # 3. Handle the 'Silence' - Trigger Local Voice immediately
        self.memory.add_turn("assistant", ai_thought)
        
        if self.tts_pipeline:
            await self.speak_locally(ai_thought)
        
        return ai_thought

    async def speak_locally(self, text):
        """Runs Kokoro TTS on CPU to save VRAM for the 5060 Ti."""
        if not self.tts_pipeline:
            print("--- [Voice: DISABLED (No Pipeline)] ---")
            return

        print("--- [Voice: Synthesis via Kokoro] ---")
        try:
            # Generator for audio segments (splits on newlines)
            generator = self.tts_pipeline(text, voice='af_heart', speed=1, split_pattern=r'\n+')
            
            for gs, ps, audio in generator:
                # Local sound device playback at 24000 Hz (Kokoro default)
                sd.play(audio, 24000)
                sd.wait() # Blocking wait per segment
        except Exception as e:
            print(f"--- [Voice Error]: {e} ---")

# Run test if executed directly
if __name__ == "__main__":
    bridge = SovereignBridge()
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        asyncio.run(bridge.process_interaction(prompt))
    else:
        print("Usage: python sovereign_bridge.py 'Your prompt here'")
