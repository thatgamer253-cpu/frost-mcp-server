import os
import sys
from creation_engine.memory.mem0_integration import get_memory

def test_memory():
    print("Testing Memory Integration...")
    
    # Mock project path
    project_path = os.path.join(os.getcwd(), "output", "TestProject")
    mem = get_memory(project_path)
    
    # 1. Add a memory
    print("  + Adding memory: 'User prefers dark mode and no pickle serialization.'")
    mem.add("User prefers dark mode.", user_id="Tester")
    mem.add("Do not use pickle for serialization; use JSON instead.", user_id="Tester")
    
    # 2. Search
    print("  Searching for 'pickle'...")
    results = mem.search("pickle")
    
    print(f"  Found {len(results['results'])} results.")
    for res in results['results']:
        print(f"    - {res['memory']} (Score: {res['score']})")

    if len(results['results']) > 0:
        print("Memory System Operational.")
    else:
        print("Memory Search Failed.")

if __name__ == "__main__":
    test_memory()
