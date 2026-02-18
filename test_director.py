"""Live test: Fire a Luma Ray-2 cinematic generation via MediaDirectorAgent."""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from creation_engine.media_director import MediaDirectorAgent

async def test():
    director = MediaDirectorAgent()
    
    # 1. Fire generation
    prompt = "A futuristic AI engine rendering holographic code in a dark command center, cinematic lighting, 4K"
    gen_id = await director.generate_cinematic_asset(prompt)
    print(f"\nGENERATION_ID: {gen_id}")
    
    if not gen_id:
        print("FAIL: Generation was not submitted.")
        return
    
    # 2. Poll for completion and download
    save_dir = os.path.join("output", "DirectorTest")
    os.makedirs(save_dir, exist_ok=True)
    
    video_path = await director.poll_luma_generation(gen_id, save_dir, "cinematic_test.mp4")
    
    if video_path and os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"\nSUCCESS: Video downloaded to {video_path} ({size_mb:.1f} MB)")
    else:
        print("\nFAIL: Video download failed or timed out.")

if __name__ == "__main__":
    asyncio.run(test())
