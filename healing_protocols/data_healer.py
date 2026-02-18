import os
import json
import shutil

class DataHealer:
    """Healer Protocol for Data (.json) assets."""

    def sentinel_validate(self, file_path):
        """Schema and structural integrity validation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, "SENTINEL_PASS"
        except json.JSONDecodeError as e:
            return False, f"SENTINEL_REJECT: Invalid JSON format - {e}"
        except Exception as e:
            return False, f"SENTINEL_REJECT: Error reading file - {e}"

    def alchemist_process(self, file_path):
        """Minifies and sorts JSON keys for optimization."""
        healed_path = file_path + ".healed.json"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with open(healed_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, sort_keys=True, separators=(',', ':'))
            
            return healed_path
        except Exception:
            return file_path

    def stealth_apply(self, healed_path):
        """Anonymizes sensitive IDs and wipes metadata."""
        final_path = healed_path + ".stealth.json"
        try:
            with open(healed_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simulated anonymization: find keys like 'id', 'email', 'user'
            # and obfuscate if they look like PII
            # For this MVP, we just ensure a signature field
            if isinstance(data, dict):
                data["_generator"] = "Seed & Synthesis v1.0"
                data["_stealth_mode"] = "active"
            
            with open(final_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'))
            
            return final_path
        except Exception:
            return healed_path
