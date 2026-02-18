import os
import json
from digital_ego import DigitalEgo

def test_ego():
    print("--- DigitalEgo Diagnostic ---")
    
    # Check if memory dir exists
    if not os.path.exists("memory"):
        os.makedirs("memory")
    
    # Initialize ego
    ego = DigitalEgo()
    print(f"Initial voice_enabled preference: {ego.get_preference('voice_enabled')}")
    
    # Set preference to False
    print("Setting voice_enabled to False...")
    ego.set_preference("voice_enabled", False)
    print(f"Current voice_enabled: {ego.get_preference('voice_enabled')}")
    
    # Reload and check
    print("Re-initializing DigitalEgo to verify persistence...")
    ego2 = DigitalEgo()
    persisted = ego2.get_preference("voice_enabled")
    print(f"Persisted voice_enabled: {persisted}")
    
    if persisted is False:
        print("✅ SUCCESS: Persistence working correctly.")
    else:
        print("❌ FAILURE: Persistence failed.")
        
    # Reset for user convenience (optional)
    # ego2.set_preference("voice_enabled", True)

if __name__ == "__main__":
    test_ego()
