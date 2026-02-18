import sys
import os
import json
import argparse
from creation_engine.orchestrator import CreationEngine
from creation_engine.llm_client import log, divider

# --- CONFIGURATION ---
MANIFEST_PATH = "task_manifest.json"
MEMORY_PATH = "engine_memory.json"

def launch_synthesis(seed_prompt, project_id, output_dir):
    """Feeds the Seed into the Synthesis Engine."""
    log("SYSTEM", f"--- [Seed & Synthesis] Initializing Project: {project_id} ---")
    
    # Save the manifest for recursive tracking
    manifest = {
        "project_id": project_id,
        "iteration": 1,
        "seed": seed_prompt,
        "status": "executing"
    }
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=4)

    # Initialize Engine
    engine = CreationEngine(
        project_name=project_id,
        prompt=seed_prompt,
        output_dir=output_dir,
        max_fix_cycles=3
    )

    try:
        summary = engine.run()
        
        if summary.get("success"):
            log("SYSTEM", "--- [Success] Task Finalized. Package Ready. ---")
            update_logic_vault(project_id, "SUCCESS")
            
            # Consolidated Handoff Package
            print(json.dumps({
                "status": "FINALIZED",
                "project": project_id,
                "output": summary.get("project_path"),
                "run_cmd": summary.get("run_command")
            }, indent=2))
        else:
            log("ERROR", "--- [Failure] Self-Correction Triggered. ---")
            handle_ghost_recursion(summary.get("error", "Unknown error"), manifest)

    except Exception as e:
        log("ERROR", f"Fatal Engine Error: {e}")

def handle_ghost_recursion(error_log, manifest):
    """Analyzing the failure and notifying the Architect."""
    log("SYSTEM", f"Analyzing Stack Trace for Iteration {manifest['iteration']}...")
    
    crash_log = "crash_report.log"
    with open(crash_log, "w", encoding="utf-8") as f:
        f.write(error_log)
    
    log("SYSTEM", f"Crash report saved to {crash_log}. Architect notified for recursive repair.")

def update_logic_vault(project_id, status):
    """Persists successful patterns to the Logic Vault."""
    memory = {}
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, 'r') as f:
                memory = json.load(f)
        except: pass
    
    memory[project_id] = {
        "status": status,
        "timestamp": "2026-02-16",
        "protocol": "Seed & Synthesis v1"
    }
    
    with open(MEMORY_PATH, 'w') as f:
        json.dump(memory, f, indent=4)
    log("SYSTEM", "Logic Vault updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=str, required=True)
    parser.add_argument("--project", type=str, default="Synthesis_Alpha")
    parser.add_argument("--output", type=str, default="./output")
    args = parser.parse_args()
    
    launch_synthesis(args.seed, args.project, args.output)
