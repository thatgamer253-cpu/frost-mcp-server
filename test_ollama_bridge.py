
import os
import sys
import time

# Ensure we can import from the relevant directories
sys.path.append(os.getcwd())

try:
    from engine_core import NexusEngine, PROVIDERS
except ImportError:
    print("Could not import NexusEngine from engine_core. Make sure you are running this from the Desktop/Creator directory.")
    sys.exit(1)

def test_ollama_connection():
    print("🧪 Testing Ollama Bridge...")

    # Check if Ollama is in the configuration
    if "ollama" not in PROVIDERS:
        print("❌ 'ollama' provider missing from engine_core.PROVIDERS")
        return

    print("✅ 'ollama' provider configuration found.")
    
    # Initialize Engine with an Ollama model
    # Note: The user might have different models pulled. 
    # Common ones: llama3, mistral, llama2. We'll try a generic one or let it fail with a helpful message.
    model_name = "ollama/llama3" 
    
    print(f"🔌 Initializing NexusEngine with model: {model_name}")
    engine = NexusEngine(
        project_name="ollama_test",
        model=model_name,
        output_dir="./test_output",
        use_docker=False # Disable docker for this quick connection test
    )

    prompt = "Reply with 'Ollama is online'."
    print(f"📤 Sending prompt: '{prompt}'")

    try:
        # We access the internal _ask method for a raw LLM test
        # In a real scenario, we'd use the full build pipeline, but this validates the bridge.
        response = engine._ask("You are a connection tester.", prompt)
        
        print("\n📥 Response received:")
        print("-" * 20)
        print(response)
        print("-" * 20)
        
        if response:
            print("\n✅ SUCCESS: verification complete. The engine can talk to Ollama.")
        else:
            print("\n⚠️ WARNING: Received empty response.")
            
    except Exception as e:
        print(f"\n❌ ERROR: Connection failed. Details: {e}")
        print("\nTroubleshooting:")
        print("1. Is Ollama running? (Try 'ollama serve' in a terminal)")
        print("2. Do you have the 'llama3' model pulled? (Try 'ollama pull llama3')")
        print("3. Is the Creation Engine utilizing the updated config?")

if __name__ == "__main__":
    test_ollama_connection()
