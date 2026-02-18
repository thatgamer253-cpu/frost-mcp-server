import os
import sys

# Add Creator root to path for imports
creator_root = r"C:\Users\thatg\Desktop\Creator"
if creator_root not in sys.path:
    sys.path.append(creator_root)

from creation_engine.vault import Vault

def save_key():
    key = "your_stripe_sk_here"
    vault = Vault()
    vault.save_stripe_keys(key, "")
    print(f"Successfully saved Stripe Secret Key to Vault: {key[:10]}...")

if __name__ == "__main__":
    save_key()
