import os
import sys
import time
from creation_engine.orchestrator import CreationEngine
from creation_engine.llm_client import log

def run_stress_test():
    log("STRESS_TEST", "🚀 INITIALIZING 10-MINUTE QUALITY HYBRID STRESS TEST")
    log("STRESS_TEST", "Mode: HYBRID (Local LLM + Kie API) | Target: 10 Minutes")
    
    # Set the provided Kie API key (Verified: Bearer auth, V2 API)
    os.environ["KIE_API_KEY"] = "40ae31e5e44616391008a0fcebaf4e77"
    
    prompt = "A 10-minute high-quality Family Guy episode about Peter discovering he is actually an AI living in a simulation."
    
    # 1. Initialize Engine with Quality settings
    engine = CreationEngine(
        project_name="stress-test-hybrid-quality",
        prompt=prompt,
        output_dir="./stress_test_output",
        local_model="qwen2.5-coder:7b",
        force_local=False, # Hybrid: Use APIs if available, fallback to local
        scale="asset"
    )
    
    # 2. Start Production
    start_time = time.time()
    try:
        log("STRESS_TEST", "🎬 Production started...")
        result = engine.run()
        
        duration = time.time() - start_time
        if result.get("success"):
            log("STRESS_TEST", f"✅ SUCCESS: Project built in {duration:.1f}s")
            log("STRESS_TEST", f"📁 Output Path: {result.get('output_path')}")
        else:
            log("ERROR", f"❌ FAILED: {result.get('reason')}")
            
    except Exception as e:
        log("ERROR", f"💥 CRASH: {e}")

if __name__ == "__main__":
    run_stress_test()
