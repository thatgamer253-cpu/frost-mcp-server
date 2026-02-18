
import os
import sys

# Add current directory to path so we can import creation_engine
sys.path.append(os.getcwd())

from creation_engine.vault import Vault

def update_vault():
    vault = Vault()
    all_keys = vault.load_keys()
    
    new_key = "your_openai_key_here"
    
    updated = False
    
    # Check common provider IDs for OpenAI
    openai_providers = ["openai", "openai_api_key"]
    
    for provider in openai_providers:
        if provider in all_keys:
            print(f"Found provider '{provider}' in vault. Replacing keys...")
            all_keys[provider] = [new_key]
            updated = True
        else:
            # If not present, we might want to add it to be sure
            print(f"Adding new key to provider '{provider}' in vault.")
            all_keys[provider] = [new_key]
            updated = True

    if updated:
        vault.save_keys(all_keys)
        print("Vault updated successfully.")
    else:
        print("No OpenAI keys found in vault to replace, but added the new one.")
        vault.save_keys(all_keys)

if __name__ == "__main__":
    update_vault()
