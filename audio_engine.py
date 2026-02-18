#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Audio Engine
  Vocal synthesis and audio manipulation.
  Provider: F5-TTS (Zero-shot Voice Cloning)
==============================================================
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

def _log(tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}]  {msg}", flush=True)

class F5TTSProvider:
    """F5-TTS via API (e.g., Hugging Face Inference or local server)."""

    NAME = "F5-TTS"
    ENV_KEY = "F5TTS_API_URL"

    def __init__(self, api_url=None):
        self.api_url = api_url or os.environ.get(self.ENV_KEY, "")

    @property
    def available(self):
        return bool(self.api_url)

    def speak(self, text, output_path, reference_audio=None):
        """Generate speech from text using F5-TTS zero-shot cloning."""
        if not self.api_url:
            raise RuntimeError("F5-TTS API URL not configured.")

        _log("F5TTS", f"Synthesizing: \"{text[:50]}...\"")
        
        payload = {
            "text": text,
        }
        if reference_audio:
            # Placeholder for handling reference audio (base64 or path)
            payload["reference_audio"] = reference_audio

        try:
            resp = requests.post(f"{self.api_url}/generate", json=payload, timeout=120)
            resp.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(resp.content)
                
            _log("F5TTS", f"  ✓ Saved: {os.path.basename(output_path)}")
            return output_path
        except Exception as e:
            _log("ERROR", f"F5-TTS synthesis failed: {e}")
            raise

class AudioEngine:
    """Unified interface for audio tasks."""

    def __init__(self, output_dir="./audio_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.f5tts = F5TTSProvider()

    def generate_speech(self, text, filename=None, reference_audio=None):
        """Generate a speech file."""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"speech_{ts}.wav"
        
        path = os.path.join(self.output_dir, filename)
        return self.f5tts.speak(text, path, reference_audio)

if __name__ == "__main__":
    engine = AudioEngine()
    if engine.f5tts.available:
        print("✓ Audio Engine (F5-TTS) Ready")
    else:
        print("✗ F5-TTS not configured. Set F5TTS_API_URL.")
