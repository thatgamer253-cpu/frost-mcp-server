import sys
import os

# Add Creator to path
creator_path = r"c:\Users\thatg\Desktop\Creator"
if creator_path not in sys.path:
    sys.path.append(creator_path)

try:
    from creation_engine.orchestrator import CreationEngine
    print("SUCCESS: Imported CreationEngine from Creator package.")
    
    # Try initializing a minimal engine
    engine = CreationEngine(
        project_name="test_bridge",
        prompt="Verify bridge",
        output_dir="./test_builds",
        model="gpt-4o"
    )
    print("SUCCESS: Initialized CreationEngine.")
    
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
