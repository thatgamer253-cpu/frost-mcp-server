import os
import sys
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ColorClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

def test_muxing():
    print("=== Testing MoviePy Audio/Video Muxing ===")
    
    # Create a 1-second dummy video
    clip = ColorClip(size=(640, 480), color=(255, 0, 0), duration=1)
    
    # Try to write it with dummy audio (if we had a dummy audio file)
    # Since we don't have a 1-second audio file ready, we'll try to write just the video first
    try:
        print("Writing video only...")
        clip.write_videofile("test_video_only.mp4", fps=24, logger=None)
        print("✅ Video only successful")
    except Exception as e:
        print(f"❌ Video only failed: {e}")

    # Now let's try with audio if possible
    # We can create a sine wave audio clip in MoviePy?
    # Or just check if ffmpeg is in path
    import subprocess
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        print(f"✅ FFmpeg found: {res.stdout.splitlines()[0]}")
    except FileNotFoundError:
        print("❌ FFmpeg NOT found in PATH")

if __name__ == "__main__":
    test_muxing()
