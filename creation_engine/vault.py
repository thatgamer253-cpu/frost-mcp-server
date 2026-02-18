import os
import json
import base64
from typing import Dict, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Vault:
    """Secure encrypted storage for API keys.
    Uses Fernet (AES-128 in CBC mode with HMAC-SHA256) for encryption.
    The master key is derived from the system's machine-id/node.
    """
    
    def __init__(self, vault_path: str = None):
        if vault_path is None:
            # Persistent location in user home
            home = os.path.expanduser("~")
            overlord_dir = os.path.join(home, ".overlord")
            os.makedirs(overlord_dir, exist_ok=True)
            self.vault_path = os.path.join(overlord_dir, "vault.bin")
        else:
            self.vault_path = vault_path
            
        self._master_key = self._get_master_key()
        self._fernet = Fernet(self._master_key)

    def _get_master_key(self) -> bytes:
        """Generate a stable master key based on system hardware identity."""
        try:
            import uuid
            # Use node (MAC address) as a stable identifier
            machine_id = str(uuid.getnode())
        except Exception:
            # Fallback for systems where uuid might fail
            machine_id = "overlord-fallback-id-999"
            
        salt = b'overlord_secure_salt_v1' # Static salt for reproducibility
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return key

    def save_keys(self, provider_keys: Dict[str, List[str]]):
        """Encrypt and save the key dictionary to disk."""
        data = json.dumps(provider_keys).encode()
        encrypted = self._fernet.encrypt(data)
        with open(self.vault_path, "wb") as f:
            f.write(encrypted)

    def load_keys(self) -> Dict[str, List[str]]:
        """Load and decrypt keys from disk."""
        if not os.path.exists(self.vault_path):
            return {}
        
        try:
            with open(self.vault_path, "rb") as f:
                encrypted = f.read()
            if not encrypted:
                return {}
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            # If decryption fails (e.g. machine changed or corrupted), return empty
            print(f"Vault decryption failed: {e}")
            return {}

    def get_keys_for_provider(self, provider_id: str) -> List[str]:
        """Fetch keys for a specific provider."""
        all_keys = self.load_keys()
        return all_keys.get(provider_id, [])

    def add_key(self, provider_id: str, key: str):
        """Add a single key to a provider's pool."""
        all_keys = self.load_keys()
        if provider_id not in all_keys:
            all_keys[provider_id] = []
        if key not in all_keys[provider_id]:
            all_keys[provider_id].append(key)
        self.save_keys(all_keys)

    def get_stripe_keys(self) -> Dict[str, str]:
        """Specific helper for Stripe credentials."""
        all_keys = self.load_keys()
        return {
            "api_key": all_keys.get("stripe_api_key", [""])[0],
            "account_id": all_keys.get("stripe_account_id", [""])[0]
        }

    def save_stripe_keys(self, api_key: str, account_id: str):
        """Specific helper to save Stripe credentials."""
        all_keys = self.load_keys()
        all_keys["stripe_api_key"] = [api_key]
        all_keys["stripe_account_id"] = [account_id]
        self.save_keys(all_keys)

    def get_all_providers(self) -> List[str]:
        """Return list of all stored providers."""
        return list(self.load_keys().keys())

    def clear(self):
        """Wipe the vault."""
        if os.path.exists(self.vault_path):
            os.remove(self.vault_path)
