import asyncio
import os
import sys
from creation_engine.media_director import MediaDirectorAgent
from creation_engine.music_alchemist import MusicAlchemistAgent

async def test_local_media():
    print("=== Testing Local Media Fallback ===")
    
    # Clear API keys to force fallback
    os.environ["LUMAAI_API_KEY"] = ""
    os.environ["RUNWAY_API_KEY"] = ""
    os.environ["KIE_API_KEY"] = ""
    os.environ["ELEVENLABS_API_KEY"] = ""
    os.environ["ELEVEN_API_KEY"] = ""
    
    save_dir = "./test_assets_local"
    os.makedirs(save_dir, exist_ok=True)
    
    # 1. Test Local Video Fallback
    director = MediaDirectorAgent()
    print("\n[Video] Attempting local cinematic video...")
    video_path = await director.create_cinematic_video(
        "A futuristic computer terminal with glowing code", 
        save_dir=save_dir, 
        filename="local_test_video.mp4"
    )
    
    if video_path and os.path.exists(video_path):
        print(f"✅ Local Video Generated: {video_path}")
    else:
        print("❌ Local Video Generation Failed")

    # 2. Test Local Music Fallback
    alchemist = MusicAlchemistAgent()
    print("\n[Music] Attempting local MIDI fallback (Dark Mood)...")
    music_path = await alchemist.generate_ambient_track(
        "A dark, haunting atmosphere with deep bass",
        duration=10,
        save_dir=save_dir,
        filename="local_test_music.mp3"
    )
    
    if music_path and os.path.exists(music_path):
        print(f"✅ Local Music Generated: {music_path}")
    else:
        # Check if .mid was generated instead
        mid_path = music_path.replace(".mp3", ".mid") if music_path else os.path.join(save_dir, "local_test_music.mid")
        if os.path.exists(mid_path):
            print(f"✅ Local MIDI Generated: {mid_path}")
        else:
            print("❌ Local Music Generation Failed")

    print("\n=== Local Media Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_local_media())
