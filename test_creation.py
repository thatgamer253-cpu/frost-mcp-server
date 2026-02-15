import json
import os
from work_engine import WorkEngine

# Test Case: A complex 'SaaS' project that should trigger the Creation Engine.
print("--- TESTING CREATION ENGINE INTEGRATION ---")
profile = {"name": "Senior Architect Agent"}
worker = WorkEngine(profile)

complex_job = {
    "id": "project-saas-101",
    "title": "Build a SaaS Dashboard for AI Monitoring",
    "description": "We need a full-stack dashboard with real-time logs and metrics.",
    "platform": "Direct"
}

# This should trigger CreationEngine internally
result = worker.generate_poc(complex_job)
print(f"\nResult Summary:\n{result}")

# Check if the state file exists
state_file = "applications/project-saas-101/state.json"
if os.path.exists(state_file):
    print("\nState File Found! Build Phase History:")
    with open(state_file, 'r') as f:
        state = json.load(f)
        for h in state['history']:
            print(f"[{h['timestamp']}] {h['phase']}: {h['summary']}")
else:
    print("\nError: State file not found. Build likely failed.")
