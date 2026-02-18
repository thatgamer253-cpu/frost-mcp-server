
import os
import sys

# Add the directory to sys.path to import agent_brain
sys.path.append(r"c:\Users\thatg\Desktop\Creator\electron-app")

try:
    from agent_brain import strip_fences, GoogleResearchAgent
    import requests
except ImportError as e:
    print(f"FAILED: Could not import agent_brain or dependencies: {e}")
    sys.exit(1)

def test_strip_fences():
    print("\n--- Testing strip_fences ---")
    
    # Case 1: Unclosed fence
    unclosed = "```python\ndef hello():\n    print('world')\n"
    stripped = strip_fences(unclosed)
    if "def hello():" in stripped and "```python" not in stripped:
        print("  ✓ Case 1 (Unclosed fence) passed")
    else:
        print(f"  ✗ Case 1 (Unclosed fence) failed: {repr(stripped)}")

    # Case 2: Normal fence
    normal = "```python\ndef hello():\n    print('world')\n```"
    stripped = strip_fences(normal)
    if "def hello():" in stripped and "```python" not in stripped:
        print("  ✓ Case 2 (Normal fence) passed")
    else:
        print(f"  ✗ Case 2 (Normal fence) failed")

    # Case 3: JSON fence
    json_text = "```json\n{\"id\": 1}\n```"
    stripped = strip_fences(json_text)
    if "{\"id\": 1}" in stripped:
        print("  ✓ Case 3 (JSON fence) passed")
    else:
        print(f"  ✗ Case 3 (JSON fence) failed")

def test_research_fallback():
    print("\n--- Testing GoogleResearchAgent Fallback ---")
    # We can't easily trigger a 403 because we don't want to use real keys
    # But we can verify the logging logic by mocking requests
    
    class MockClient:
        pass
    
    agent = GoogleResearchAgent(MockClient(), "gpt-4")
    agent.api_key = "invalid_key"
    agent.cse_id = "invalid_id"
    
    # This should log a warning and return empty string or memory
    print("  (Simulating research run with invalid keys)")
    result = agent.run_research("test prompt", "internal memory")
    if "internal memory" in result:
        print("  ✓ Research agent gracefully handled invalid keys and returned memory")
    else:
        print(f"  ✗ Research agent failed to return memory or crashed: {result}")

if __name__ == "__main__":
    test_strip_fences()
    test_research_fallback()
    print("\nVerification Complete.")
