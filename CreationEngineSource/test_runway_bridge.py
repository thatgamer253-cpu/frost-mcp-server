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

def test_runway_bridge():
    print("Testing Runway Gen-3 with PixelBridge...")
    
    # We explicitly instantiate with ONLY Runway key to force its usage logic if logic prioritizes Luma
    # But wait, our engine tries Luma first. 
    # To test Runway specifically, we can temporarily Unset Luma env var or hack the instance.
    
    # Hack: Initialize and then clear luma key to force Runway path
    engine = MultimodalEngine()
    engine.luma_key = None # Force fallback to Runway
    
    if not engine.runway_key:
        print("FAIL: Runway Key not detected by Engine.")
        return

    output_dir = os.path.join("output", "RunwayTest")
    os.makedirs(output_dir, exist_ok=True)
    
    # We NEED a real image for Runway. 
    # Let's generate one or use a dummy. Runway is smart, random noise might fail modulation.
    # Let's try to simple "text-to-image" via SDXL first if possible, or use a solid color.
    
    dummy_image = os.path.join(output_dir, "test_input.png")
    
    # Create a simple red square using minimal python (no PIL dependency if possible)
    # Actually, we can just write random bytes and hope, OR we can use the "generate_visual_dna" method logic first!
    
    print("Generating base image for video using SDXL...")
    image_path = engine.generate_visual_dna("A cyberpunk city", output_dir)
    
    if not image_path:
        print("FAIL: Could not generate base image for Runway test.")
        return

    print(f"\n--- Triggering Runway Generation (Source: {image_path}) ---")
    video_path = engine.generate_ux_motion(image_path, output_dir)
    
    if video_path and os.path.exists(video_path):
        print(f"PASS: Runway Video successfully generated at: {video_path}")
    else:
        print("FAIL: Runway Video generation returned None or file missing.")

if __name__ == "__main__":
    test_runway_bridge()
