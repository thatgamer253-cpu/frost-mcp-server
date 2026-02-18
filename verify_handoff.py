import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_self_healing():
    print("Testing Self-Healing Paths...")
    from creation_engine.packaging import OneHandoffPackager
    
    # Create a dummy project structure
    test_dir = Path("test_project_bundle")
    test_dir.mkdir(exist_ok=True)
    
    asset_dir = test_dir / "assets"
    asset_dir.mkdir(exist_ok=True)
    
    # Create a dummy code file with an absolute path
    code_file = test_dir / "main.py"
    abs_path = str(test_dir.absolute()).replace("\\", "/")
    content = f'image_path = "{abs_path}/assets/image.png"\n'
    code_file.write_text(content)
    
    print(f"  Created file with absolute path: {abs_path}")
    
    # Run packager
    packager = OneHandoffPackager(str(test_dir), "TestBundle")
    packager._apply_self_healing()
    
    # Check if healed
    healed_content = code_file.read_text()
    if 'image_path = "./assets/image.png"' in healed_content:
         print("  [PASS] Path was healed to relative.")
    else:
         print(f"  [FAIL] Path was not healed correctly. Content: {healed_content}")

def test_upscale_integration():
    print("\nTesting Upscale Integration...")
    # NOTE: This only tests that the call is routed correctly, not the actual AI output
    from media_engine import MediaEngine
    engine = MediaEngine()
    
    # Mocking would be better, but we'll just check if the method exists
    if hasattr(engine, 'post_process_video'):
        print("  [PASS] MediaEngine has post_process_video.")
    else:
        print("  [FAIL] MediaEngine missing post_process_video.")

if __name__ == "__main__":
    test_self_healing()
    test_upscale_integration()
