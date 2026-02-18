from monologue_hub import hub
import os

def verify():
    print("Testing AwarenessHub...")
    hub.record_thought("Verifier", "System check initiated. Validating cross-module awareness.")
    
    log_path = hub.log_path
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            print("\n--- Current Monologue Log Content ---")
            print(content)
            print("------------------------------------")
            
            if "VERIFIER: System check initiated" in content:
                print("\n✅ Verification SUCCESS: Thought successfully recorded.")
            else:
                print("\n❌ Verification FAILED: Thought not found in log.")
    else:
        print(f"\n❌ Verification FAILED: Log file not found at {log_path}")

if __name__ == "__main__":
    verify()
