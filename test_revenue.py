import os
import json
from engine_bridge import creation_engine

def test_revenue_integration():
    print("Testing Cash Machine Revenue Integration...")
    
    project_id = "revenue_test_999"
    goal = "Build a commercial SaaS product for SALE"
    description = "A product to be sold on the marketplace."
    
    # We don't want to run the full engine, so we'll just check if record_job_start would be called.
    # Since we are testing the BRIDGE logic, we check for revenue_data.json existence.
    
    # Trigger the bridge (this will call record_job_start inside _run_advanced_build)
    # We use a try/except because we might terminate it or it might fail on the engine run,
    # but the revenue record happens BEFORE the engine run.
    
    print(f"Triggering build for {project_id}...")
    try:
        creation_engine.build_project(project_id, goal, description)
    except Exception as e:
        print(f"Engine catch (expected if offline): {e}")

    if os.path.exists('revenue_data.json'):
        with open('revenue_data.json', 'r') as f:
            data = json.load(f)
            print(f"SUCCESS: Revenue data found. Pending Income: ${data.get('pending_income')}")
            found = any(project_id in txn['id'] for txn in data.get('transactions', []))
            if found:
                print(f"PASS: Transaction {project_id} recorded.")
            else:
                print("FAIL: Transaction not found in log.")
    else:
        print("FAIL: revenue_data.json was not created.")

if __name__ == "__main__":
    test_revenue_integration()
