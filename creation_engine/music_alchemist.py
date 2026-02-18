"""
Creation Engine — Music Alchemist Agent
Generative music and soundscape synthesis using ElevenLabs, Suno (via aggregator), and local MIDI synthesis.

The Music Alchemist handles:
  - Atmospheric soundscapes (ElevenLabs SFX)
  - Compositional MIDI (MidiUtil)
  - Melodic synthesis (Pydub / SciPy)
  - Final mixdown of audio tracks
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from .llm_client import log
except ImportError:
    def log(tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}] {msg}")

# ── Lazy SDK Loaders ────────────────────────────────────────

def _load_midiutil():
    try:
        from midiutil import MIDIFile
        return MIDIFile
    except ImportError:
        log("ALCHEMIST", "  ⚠ midiutil package missing. pip install midiutil")
        return None

def _load_pydub():
    try:
        from pydub import AudioSegment
        return AudioSegment
    except ImportError:
        log("ALCHEMIST", "  ⚠ pydub package missing. pip install pydub")
        return None

def _load_audiocraft():
    try:
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
        return MusicGen, audio_write
    except ImportError:
        # Don't log warning immediately, only if needed
        return None, None

# ═══════════════════════════════════════════════════════════
#  MUSIC ALCHEMIST AGENT
# ═══════════════════════════════════════════════════════════

class MusicAlchemistAgent:
    """Specialized agent for generative music and sound synthesis."""

    def __init__(self, api_key: Optional[str] = None):
        # Support both naming conventions
        self.elevenlabs_key = api_key or os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_API_KEY")
        self.midiutil = _load_midiutil()
        self.pydub = _load_pydub()
        
        # Skip heavy local models if requested to save CPU/VRAM
        if os.getenv("OVERLORD_NO_LOCAL_AUDIO") == "1":
            log("ALCHEMIST", "  🚫 Local MusicGen disabled via environment.")
            self.MusicGen, self.audio_write = None, None
        else:
            self.MusicGen, self.audio_write = _load_audiocraft()

        status_eleven = "READY" if self.elevenlabs_key else "UNAVAILABLE"
        status_musicgen = "READY (Local)" if self.MusicGen else "MISSING (pip install audiocraft)"
        status_midi = "READY" if self.midiutil else "UNAVAILABLE"
        
        log("ALCHEMIST", f"═══ Music Alchemist Status ═══")
        log("ALCHEMIST", f"  ElevenLabs SFX   {status_eleven}")
        log("ALCHEMIST", f"  MusicGen Local   {status_musicgen}")
        log("ALCHEMIST", f"  Legacy MIDI      {status_midi}")
        log("ALCHEMIST", f"══════════════════════════════")

    async def generate_ambient_track(self, prompt: str, duration: int = 30, 
                                     save_dir: str = "./assets", 
                                     filename: str = "ambient_track.mp3") -> Optional[str]:
        """Generate an ambient background track using ElevenLabs SFX or Local Synth."""
        log("ALCHEMIST", f"  🎵 Synthesizing ambient track: {prompt[:60]}...")
        
        # If ElevenLabs is available, use it for high-fidelity SFX/loops
        if self.elevenlabs_key:
            path = await self._generate_elevenlabs_sfx(prompt, duration, save_dir, filename)
            if path:
                return path
            log("ALCHEMIST", "  ⚠️ ElevenLabs failed. Trying local MusicGen...")
        
        # Try local MusicGen (AudioCraft)
        if self.MusicGen:
            path = await self._generate_musicgen_track(prompt, duration, save_dir, filename)
            if path:
                return path
            log("ALCHEMIST", "  ⚠️ MusicGen failed. Falling back to simple synthesis...")

        # Final Fallback: Simple Sine Wave
        log("ALCHEMIST", "  ℹ Creating fallback Waveform...")
        return self._generate_fallback_wave(prompt, duration, save_dir, filename)

    async def _generate_elevenlabs_sfx(self, prompt: str, duration: int, 
                                       save_dir: str, filename: str) -> Optional[str]:
        """Use ElevenLabs Sound Effects API."""
        try:
            import requests
            url = "https://api.elevenlabs.io/v1/sound-generation"
            headers = {
                "xi-api-key": self.elevenlabs_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": prompt,
                "duration_seconds": min(duration, 22), # ElevenLabs cap is ~22s per gen
                "prompt_influence": 0.3
            }
            
            os.makedirs(save_dir, exist_ok=True)
            output_path = os.path.join(save_dir, filename)
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                log("ALCHEMIST", f"    ✓ Saved: {output_path}")
                return output_path
            else:
                log("ALCHEMIST", f"    ✗ ElevenLabs API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            log("ALCHEMIST", f"    ✗ ElevenLabs generation failed: {e}")
            return None

    async def _generate_musicgen_track(self, prompt: str, duration: int, 
                                       save_dir: str, filename: str) -> Optional[str]:
        """Generate music using local MusicGen Small model."""
        log("ALCHEMIST", f"  🎹 MusicGen Local: Generating {duration}s clip for '{prompt[:20]}...'")
        try:
            # Run in thread to avoid blocking asyncio loop
            def _run_model():
                model = self.MusicGen.get_pretrained('facebook/musicgen-small')
                model.set_generation_params(duration=duration)
                wav = model.generate([prompt])
                
                # Save
                os.makedirs(save_dir, exist_ok=True)
                stem = os.path.splitext(filename)[0]
                # audio_write adds extension automatically
                self.audio_write(
                    os.path.join(save_dir, stem), 
                    wav[0].cpu(), 
                    model.sample_rate, 
                    strategy="loudness",
                    loudness_compressor=True
                )
                return os.path.join(save_dir, filename)

            # Offload heavy model work
            loop = asyncio.get_running_loop()
            path = await loop.run_in_executor(None, _run_model)
            
            log("ALCHEMIST", f"    ✓ MusicGen Created: {path}")
            return path
        except Exception as e:
            log("ALCHEMIST", f"    ✗ MusicGen Error: {e}")
            return None

    def _generate_fallback_wave(self, prompt: str, duration: int, 
                                 save_dir: str, filename: str) -> str:
        """Generates a simple atmospheric sine-wave drone (WAV) using standard library."""
        import wave
        import math
        import struct
        import random

        # Ensure correct extension
        filename = filename.rsplit('.', 1)[0] + ".wav"
        output_path = os.path.join(save_dir, filename)
        
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            sample_rate = 44100
            n_samples = int(duration * sample_rate)
            
            # Simple tonal palettes
            p_lower = prompt.lower()
            if "dark" in p_lower or "scary" in p_lower:
                freqs = [55.0, 110.0, 164.81] # A1, A2, E3 (Dark/Hollow)
                mod_rate = 0.2
            elif "happy" in p_lower or "upbeat" in p_lower:
                freqs = [261.63, 329.63, 392.00] # C4, E4, G4 (C Major)
                mod_rate = 2.0
            else:
                freqs = [196.00, 246.94, 293.66] # G3, B3, D4 (G Major / Neutral)
                mod_rate = 0.5

            with wave.open(output_path, 'w') as obj:
                obj.setnchannels(1) # Mono
                obj.setsampwidth(2) # 16-bit
                obj.setframerate(sample_rate)
                
                # Generate 1 second of audio to loop (optimization)
                # Adds a slight tremolo effect
                one_sec = []
                for i in range(sample_rate):
                    t = float(i) / sample_rate
                    sample = 0.0
                    for f in freqs:
                        # AM Modulation (Tremolo)
                        tremolo = 1.0 + 0.3 * math.sin(2 * math.pi * mod_rate * t)
                        sample += math.sin(2 * math.pi * f * t) * tremolo
                    
                    # Normalize and scale
                    sample = (sample / len(freqs)) * 0.3 # Keep it quiet/ambient
                    one_sec.append(int(sample * 32767))
                
                # Write loops
                n_loops = int(duration) + 1
                full_data = bytearray()
                packed_sec = struct.pack(f'{len(one_sec)}h', *one_sec)
                
                for _ in range(n_loops):
                    full_data.extend(packed_sec)
                
                # Trim
                final_bytes = full_data[:n_samples * 2] # 2 bytes per sample
                
                # Write
                obj.writeframes(final_bytes)
            
            log("ALCHEMIST", f"    ✓ Generated Fallback WAV ({len(freqs)} voices): {output_path}")
            return output_path
            
        except Exception as e:
            log("ALCHEMIST", f"    ✗ Fallback Wave synth failed: {e}")
            return ""

# ── Orchestrator Entry Point ────────────────────────────────

async def main():
    """Quick smoke test for the Music Alchemist Agent."""
    alchemist = MusicAlchemistAgent()
    track_path = await alchemist.generate_ambient_track(
        "A dark, cinematic industrial heartbeat with ethereal pads",
        duration=10
    )
    print(f"Music Task Result: {track_path}")

if __name__ == "__main__":
    asyncio.run(main())
