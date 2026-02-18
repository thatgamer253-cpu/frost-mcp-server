
import os
import sys
import json
from creation_engine.orchestrator import CreationEngine

def main():
    # mission: 15 seconds South Park short about the Epstein files in 720P
    prompt = "15 second South Park short about the Epstein files, 720p, cut-out animation style, snowy background, paper textures"
    project_name = "SouthPark_Epstein_Short_720p"
    output_dir = os.path.join(os.getcwd(), "output")
    
    # Force local if requested
    force_local = os.environ.get("OVERLORD_FORCE_LOCAL", "1") == "1"
    
    # Disable heavy local audio to prevent CPU 100% hits
    os.environ["OVERLORD_NO_LOCAL_AUDIO"] = "1"
    
    print(f"🚀 MISSION INITIATED: {project_name}")
    print(f"📝 PROMPT: {prompt}")
    
    engine = CreationEngine(
        project_name=project_name,
        prompt=prompt,
        output_dir=output_dir,
        scale="asset",
        platform="movie",
        force_local=force_local
    )
    
    # Run production
    result = engine.run()
    
    print("\n" + "="*50)
    print("🎬 PRODUCTION REPORT")
    print("="*50)
    if result.get("success"):
        print(f"✅ SUCCESS: Project built at {result.get('project_path')}")
        files = result.get("written_files", {})
        for f in files:
            if ".mp4" in f:
                print(f"🎥 FINAL ASSET: {f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
    print("="*50)

if __name__ == "__main__":
    main()
