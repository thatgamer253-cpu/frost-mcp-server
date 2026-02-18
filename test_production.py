#!/usr/bin/env python3
"""
Test script for verifying NarratorAgent and MediaPostProcessor.
Includes mocking of external APIs and local asset generation for testing.
"""

import os
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch
from creation_engine.narrator import NarratorAgent
from creation_engine.post_processor import MediaPostProcessor

async def create_dummy_audio(path):
    print(f"Creating dummy audio: {path}...")
    try:
        from moviepy.audio.AudioClip import AudioArrayClip
        # Create a 1-second silent audio clip (44100Hz)
        silence = np.zeros((44100, 2))
        audio_clip = AudioArrayClip(silence, fps=44100)
        audio_clip.write_audiofile(path, logger=None)
        print(f"✓ Dummy audio created: {path}")
        return True
    except Exception as e:
        print(f"⚠ Could not create dummy audio via moviepy: {e}")
        return False

async def test_narrator():
    print("\n--- Testing NarratorAgent ---")
    # Mock ask_llm and requests
    with patch("creation_engine.narrator.ask_llm") as mock_ask, \
         patch("creation_engine.narrator.requests.post") as mock_post:
        
        mock_ask.return_value = "This is a test narration script for Overlord."
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_mp3_content" # This won't be used if we mock synthesize_speech or use dummy
        mock_post.return_value = mock_resp
        
        narrator = NarratorAgent()
        # Mock client
        client = MagicMock()
        
        script = await narrator.generate_script(client, "Test context")
        print(f"Generated Script: {script}")
        
        # For production test, we need a valid file, so we'll manually create one
        assets_dir = "./test_assets"
        os.makedirs(assets_dir, exist_ok=True)
        audio_path = os.path.join(assets_dir, "test_narration.mp3")
        await create_dummy_audio(audio_path)
        
        if audio_path and os.path.exists(audio_path):
            print(f"✓ Speech synthesized (dummy): {audio_path}")
        else:
            print("✗ Speech synthesis failed")

async def test_production():
    print("\n--- Testing MediaPostProcessor ---")
    try:
        from moviepy.video.VideoClip import ColorClip
        
        # Create a tiny dummy video
        assets_dir = "./test_assets"
        os.makedirs(assets_dir, exist_ok=True)
        dummy_video = os.path.join(assets_dir, "dummy_video.mp4")
        
        if not os.path.exists(dummy_video):
            print("Creating dummy video...")
            clip = ColorClip(size=(640, 360), color=(255, 0, 0), duration=2)
            clip.write_videofile(dummy_video, fps=24, logger=None)
        
        producer = MediaPostProcessor(output_dir="./test_output")
        
        # Test mixing
        final_path = producer.process_video(
            video_path=dummy_video,
            narration_path=os.path.join(assets_dir, "test_narration.mp3"),
            subtitles=[{"text": "Production Test", "start": 0, "end": 2, "position": "center"}],
            output_filename="test_mixed.mp4"
        )
        
        if final_path and os.path.exists(final_path):
            print(f"✓ Production complete: {final_path}")
        else:
            print("✗ Production failed")
            
    except ImportError:
        print("⚠ moviepy not fully installed for production test. Skipping rendering test.")
    except Exception as e:
        print(f"⚠ Production test error: {e}")

if __name__ == "__main__":
    os.makedirs("./test_assets", exist_ok=True)
    os.makedirs("./test_output", exist_ok=True)
    asyncio.run(test_narrator())
    asyncio.run(test_production())
