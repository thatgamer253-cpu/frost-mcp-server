import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Verify Key Presence
key = os.getenv("STABILITY_API_KEY")
if not key:
    print("[ERROR] STABILITY_API_KEY not found in environment!")
    sys.exit(1)

print(f"[INFO] Stability Key Found: {key[:5]}...{key[-5:]}")

# Add core to path
sys.path.append(os.getcwd())

try:
    from core.media import MultimodalEngine
except ImportError as e:
    print(f"[ERROR] Failed to import MultimodalEngine: {e}")
    sys.exit(1)

def test_media():
    print("[INFO] Starting Multimodal Engine Test...")
    engine = MultimodalEngine()
    
    output_dir = os.path.join("output", "MediaTest2")
    os.makedirs(output_dir, exist_ok=True)
    
    # Test 1: Generate Visual DNA
    print("\n[TEST 1] SVD XL (Image Generation)...")
    prompt = "A futuristic sci-fi dashboard interface, neon blue and cyan, high tech, 8k resolution"
    image_path = engine.generate_visual_dna(prompt, output_dir)
    
    if not image_path:
        print("[FAIL] Visual DNA Generation Failed.")
        return
        
    print(f"[PASS] Image Generated: {image_path}")
    
    # Test 2: Generate Motion Proof
    print("\n[TEST 2] SVD (Video Generation)...")
    video_path = engine.generate_ux_motion(image_path, output_dir)
    
    if not video_path:
         print("[FAIL] Motion Proof Generation Failed.")
         return
         
    print(f"[PASS] Video Generated: {video_path}")
    print("\n[SUCCESS] MULTIMODAL TEST COMPLETED!")

if __name__ == "__main__":
    test_media()
