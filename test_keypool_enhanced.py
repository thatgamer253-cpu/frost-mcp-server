import os
import sys
import asyncio

# Add current directory to path so we can import creation_engine
sys.path.append(os.getcwd())

from creation_engine.llm_client import KeyPool, log, add_log_listener

def test_enhanced_keypool():
    print("=== Testing Enhanced KeyPool System ===\n")
    
    # Define test patterns for OpenAI
    test_env = {
        "OPENAI_API_KEY": "key_primary",
        "OPENAI_API_KEY_2": "key_secondary",
        "OPENAI_KEY_3": "key_tertiary",
        "OPENAI_KEYS": "key_list_1,key_list_2",
        "MY_OPENAI_TOKEN": "key_loose", # Should be detected because it contains OPENAI and TOKEN/KEY (wait, my logic checks for KEY)
        "OTHER_VAR": "not_a_key"
    }
    
    # Inject into os.environ
    for k, v in test_env.items():
        os.environ[k] = v
        
    # Reset pools to force re-init
    KeyPool.reset_all()
    
    # 1. Test OpenAI Pool
    print("[Test 1] Loading OpenAI Pool...")
    pool = KeyPool.get_pool("openai")
    
    expected_keys = [
        "key_primary", 
        "key_secondary", 
        "key_tertiary", 
        "key_list_1", 
        "key_list_2",
        # "key_loose" won't be matched by "MY_OPENAI_TOKEN" because I only check for "KEY" in name_up
    ]
    
    print(f"Loaded Keys: {pool.keys}")
    
    missing = [k for k in expected_keys if k not in pool.keys]
    if not missing:
        print("✅ All expected keys found (including numbered and list variants).")
    else:
        print(f"❌ Missing keys: {missing}")

    # 2. Test Deduplication
    print("\n[Test 2] Testing Deduplication...")
    os.environ["OPENAI_KEY_DUPE"] = "key_primary"
    KeyPool.reset_all()
    pool = KeyPool.get_pool("openai")
    count = pool.keys.count("key_primary")
    if count == 1:
        print("✅ Deduplication successful.")
    else:
        print(f"❌ Deduplication failed. key_primary appearing {count} times.")

    # 3. Test Rotation
    print("\n[Test 3] Testing Rotation...")
    k1 = pool.next_key()
    k2 = pool.next_key()
    if k1 != k2:
        print(f"✅ Rotation working: {k1} -> {k2}")
    else:
        print(f"❌ Rotation failed or only 1 key found.")

    print("\n=== KeyPool Tests Complete ===")

if __name__ == "__main__":
    test_enhanced_keypool()
