#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Narrator Agent
  Vocal synthesis and script generation.
  Leverages ElevenLabs (Primary) and F5-TTS (Secondary).
==============================================================
"""

import os
import sys
import json
import asyncio
import requests
from typing import Optional, List, Dict
from datetime import datetime

# Import shared utilities from agent_brain
try:
    from agent_brain import log, ask_llm, get_cached_client
except ImportError:
    # Fallback log if not in the same directory
    def log(tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}]  {msg}", flush=True)

class NarratorAgent:
    """Agent responsible for generating narration scripts and synthesized voiceovers."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
        self.f5tts_url = os.environ.get("F5TTS_API_URL")
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Default: Rachel

    async def generate_script(self, client, context: str, target_duration: int = 30) -> str:
        """Generate a concise narration script based on the project context."""
        log("NARRATOR", f"📜 Generating narration script (target: {target_duration}s)...")
        
        system_prompt = (
            "You are a professional project narrator. Write a concise, engaging spoken script "
            f"that lasts approximately {target_duration} seconds when spoken (roughly {target_duration * 2.5} words). "
            "Use a confident, professional tone. Do NOT use markdown, code, or bullet points. "
            "Output ONLY the narration text, nothing else."
        )
        
        try:
            script = await asyncio.to_thread(ask_llm, client, self.model, system_prompt, context)
            script = script.strip().strip('\"').strip("'")
            log("NARRATOR", f"  📝 Script generated: \"{script[:60]}...\"")
            return script
        except Exception as e:
            log("ERROR", f"  Script generation failed: {e}")
            return f"This project showcases a professional build focusing on {context[:50]}."

    async def synthesize_speech(self, text: str, save_dir: str, filename: str = "narration.mp3") -> Optional[str]:
        """Synthesize speech using ElevenLabs (primary) or F5-TTS (fallback)."""
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, filename)

        # 1. Try ElevenLabs
        if self.elevenlabs_key:
            log("NARRATOR", "🎤 Synthesizing via ElevenLabs...")
            result = await self._synthesize_elevenlabs(text, output_path)
            if result:
                return result
            log("NARRATOR", "  ⚠️ ElevenLabs failed. Checking F5-TTS fallback...")

        # 2. Try F5-TTS Fallback
        if self.f5tts_url:
            log("NARRATOR", "🎤 Synthesizing via F5-TTS (Fallback)...")
            result = await self._synthesize_f5tts(text, output_path)
            if result:
                return result

        log("ERROR", "❌ No voice synthesis providers available or all failed.")
        return None

    async def _synthesize_elevenlabs(self, text: str, output_path: str) -> Optional[str]:
        """Internal helper for ElevenLabs TTS."""
        api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }

        try:
            response = await asyncio.to_thread(requests.post, api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                log("NARRATOR", f"  ✓ ElevenLabs success: {os.path.basename(output_path)}")
                return output_path
            else:
                log("WARN", f"  ElevenLabs error {response.status_code}: {response.text[:100]}")
        except Exception as e:
            log("ERROR", f"  ElevenLabs request failed: {e}")
        return None

    async def _synthesize_f5tts(self, text: str, output_path: str) -> Optional[str]:
        """Internal helper for F5-TTS fallback."""
        try:
            payload = {"text": text}
            # Note: Extension might need to change to .wav depending on provider
            resp = await asyncio.to_thread(requests.post, f"{self.f5tts_url}/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                log("NARRATOR", f"  ✓ F5-TTS success: {os.path.basename(output_path)}")
                return output_path
        except Exception as e:
            log("ERROR", f"  F5-TTS fallback failed: {e}")
        return None

if __name__ == "__main__":
    # Quick test
    async def test():
        narrator = NarratorAgent()
        # Mock client for test
        pass
    
    # asyncio.run(test())
    print("✓ Narrator Agent Module Loaded")
