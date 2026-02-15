import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Add core to path
sys.path.append(os.getcwd())

try:
    from core.media import MultimodalEngine
except ImportError as e:
    print(f"Failed to import MultimodalEngine: {e}")
    sys.exit(1)

def test_video_generation():
    print("Testing Luma Video Integration through MultimodalEngine...")
    engine = MultimodalEngine()
    
    if not engine.luma_key:
        print("FAIL: Luma Key not detected by Engine.")
        return

    output_dir = os.path.join("output", "VideoTest")
    os.makedirs(output_dir, exist_ok=True)
    
    # Fake image path (Luma in text-to-video mode doesn't strictly need it, but the method signature does)
    # We will pass a dummy path, knowing _generate_luma ignores it for now in favor of text-to-video
    dummy_image = os.path.join(output_dir, "dummy_dna.png") 
    with open(dummy_image, "w") as f: f.write("dummy")

    print("\n--- Triggering Motion Generation ---")
    video_path = engine.generate_ux_motion(dummy_image, output_dir)
    
    if video_path and os.path.exists(video_path):
        print(f"PASS: Video successfully generated at: {video_path}")
    else:
        print("FAIL: Video generation returned None or file missing.")

if __name__ == "__main__":
    test_video_generation()
