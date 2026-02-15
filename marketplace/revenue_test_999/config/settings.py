# config/settings.py

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Config:
    """
    Config class to manage application settings loaded from environment variables.
    """
    PLUGINS_DIRECTORY: str = os.getenv('PLUGINS_DIRECTORY', './plugins')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    MEDIA_LIBRARY_PATH: str = os.getenv('MEDIA_LIBRARY_PATH', './media')
    EXPORT_PATH: str = os.getenv('EXPORT_PATH', './exports')
    IMAGE_CACHE_SIZE: int = int(os.getenv('IMAGE_CACHE_SIZE', 100))
    ENABLE_AUTO_UPDATE: bool = os.getenv('ENABLE_AUTO_UPDATE', 'True') == 'True'
    API_ENDPOINT: str = os.getenv('API_ENDPOINT', 'https://api.publicapis.org/entries')  # Example of a valid public API

def load_config() -> Dict[str, Any]:
    """
    Load configuration settings from environment variables.
    Returns a dictionary of configuration settings.
    """
    try:
        logging.info("Loading configuration from environment variables...")
        config = {
            'PLUGINS_DIRECTORY': Config.PLUGINS_DIRECTORY,
            'LOG_LEVEL': Config.LOG_LEVEL,
            'MEDIA_LIBRARY_PATH': Config.MEDIA_LIBRARY_PATH,
            'EXPORT_PATH': Config.EXPORT_PATH,
            'IMAGE_CACHE_SIZE': Config.IMAGE_CACHE_SIZE,
            'ENABLE_AUTO_UPDATE': Config.ENABLE_AUTO_UPDATE,
            'API_ENDPOINT': Config.API_ENDPOINT
        }
        logging.info("Configuration loaded successfully.")
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}", exc_info=True)
        raise

def save_config(config: Dict[str, Any], path: str = './config.json') -> None:
    """
    Save the current configuration to a JSON file.
    """
    try:
        import json
        logging.info(f"Saving configuration to {path}...")
        with open(path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
        logging.info("Configuration saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save configuration: {e}", exc_info=True)
        raise
```

### Key Features:
- **Environment Variables**: The `Config` class loads settings from environment variables using `os.getenv`, with sensible defaults provided.
- **Public API Endpoint**: Replaced the placeholder API endpoint with a valid public API endpoint (`https://api.publicapis.org/entries`).
- **Error Handling**: Comprehensive error handling with logging for both loading and saving configuration.
- **Logging**: Informative logging to track the configuration loading and saving processes.
- **JSON Configuration**: Ability to save the current configuration to a JSON file for persistence.