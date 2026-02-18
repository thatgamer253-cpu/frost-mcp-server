import os
import json
from .config import (
    PRODUCTION_SAFETY_DIRECTIVE,
    STABILITY_DIRECTIVE,
    FEATURE_RICHNESS_DIRECTIVE,
    PORTABILITY_DIRECTIVE,
    DISTRIBUTION_DIRECTIVE,
    PROVIDERS
)

OVERRIDE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user_overrides.json")

def load_settings():
    """Load settings from user_overrides.json or return defaults."""
    defaults = {
        "directives": {
            "safety": PRODUCTION_SAFETY_DIRECTIVE,
            "stability": STABILITY_DIRECTIVE,
            "richness": FEATURE_RICHNESS_DIRECTIVE,
            "portability": PORTABILITY_DIRECTIVE,
            "distribution": DISTRIBUTION_DIRECTIVE,
        },
        "providers": PROVIDERS
    }
    
    if os.path.exists(OVERRIDE_FILE):
        try:
            with open(OVERRIDE_FILE, "r") as f:
                overrides = json.load(f)
                # Merge logic
                if "directives" in overrides:
                    defaults["directives"].update(overrides["directives"])
                if "providers" in overrides:
                    defaults["providers"].update(overrides["providers"])
        except: pass
        
    return defaults

def save_settings(settings: dict):
    """Save persistent user overrides."""
    try:
        with open(OVERRIDE_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False

def get_directive(key: str) -> str:
    """Convenience to get a specific directive."""
    s = load_settings()
    return s["directives"].get(key, "")
