import os

def setup_live_run():
    print("--- [Live Run: Triggering Healer] ---")
    run_dir = "output/live_run"
    os.makedirs(run_dir, exist_ok=True)
    
    # 1. Broken Python Script
    with open(f"{run_dir}/logic_error.py", "w", encoding='utf-8') as f:
        f.write("def fail(\n    print('missing paren')\n")
        
    # 2. Unpinned Requirements
    with open(f"{run_dir}/requirements.txt", "w", encoding='utf-8') as f:
        f.write("requests\nmcp\npilllow")
        
    # 3. Clean JSON
    with open(f"{run_dir}/config.json", "w", encoding='utf-8') as f:
        f.write('{"status": "stable", "version": 1.0}')

    print(f"--- [Assets Deployed in {run_dir}] ---")

if __name__ == "__main__":
    setup_live_run()
