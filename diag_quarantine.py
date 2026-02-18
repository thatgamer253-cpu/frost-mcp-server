from healing_protocols.python_healer import PythonHealer
from healing_protocols.data_healer import DataHealer
import os

def diag():
    py_healer = PythonHealer()
    data_healer = DataHealer()
    
    print("--- [Diagnostic: Quarantined Assets] ---")
    
    # 1. Check requirements.txt
    req_path = "quarantine/requirements.txt"
    if os.path.exists(req_path):
        valid, reason = py_healer.sentinel_validate(req_path)
        print(f"requirements.txt: {valid} | {reason}")
        
    # 2. Check data.json
    json_path = "quarantine/data.json"
    if os.path.exists(json_path):
        valid, reason = data_healer.sentinel_validate(json_path)
        print(f"data.json: {valid} | {reason}")

if __name__ == "__main__":
    diag()
