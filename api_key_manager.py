import secrets
import hashlib
import json
import os
from datetime import datetime, timedelta

class APIKeyManager:
    """Manages API key generation and validation for marketplace services."""
    
    def __init__(self, keys_file="api_keys.json"):
        self.keys_file = keys_file
        self.keys = self._load_keys()
    
    def _load_keys(self):
        """Load existing API keys from file."""
        if os.path.exists(self.keys_file):
            with open(self.keys_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_keys(self):
        """Save API keys to file."""
        with open(self.keys_file, 'w') as f:
            json.dump(self.keys, f, indent=2)
    
    def generate_key(self, agent_id, service_id, billing_type="monthly"):
        """Generate a new API key for an agent."""
        # Generate secure random key
        raw_key = secrets.token_urlsafe(32)
        key = f"frost_{raw_key}"
        
        # Calculate expiration
        if billing_type == "monthly":
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        elif billing_type == "one_time":
            expires_at = None  # Lifetime access
        else:  # per_use
            expires_at = None
        
        # Store key metadata
        self.keys[key] = {
            "agent_id": agent_id,
            "service_id": service_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "billing_type": billing_type,
            "usage_count": 0,
            "active": True
        }
        
        self._save_keys()
        return key
    
    def validate_key(self, api_key, service_id):
        """Validate an API key for a specific service."""
        if api_key not in self.keys:
            return False, "Invalid API key"
        
        key_data = self.keys[api_key]
        
        # Check if key is active
        if not key_data.get("active", False):
            return False, "API key has been revoked"
        
        # Check if key is for the correct service
        if key_data["service_id"] != service_id:
            return False, "API key not valid for this service"
        
        # Check expiration for monthly subscriptions
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.now() > expires_at:
                return False, "API key has expired"
        
        # Increment usage count
        key_data["usage_count"] += 1
        self._save_keys()
        
        return True, "Valid"
    
    def revoke_key(self, api_key):
        """Revoke an API key."""
        if api_key in self.keys:
            self.keys[api_key]["active"] = False
            self._save_keys()
            return True
        return False
    
    def get_key_info(self, api_key):
        """Get information about an API key."""
        return self.keys.get(api_key)
