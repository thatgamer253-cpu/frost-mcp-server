# plugins/__init__.py

import logging
from .plugin_manager import initialize as initialize_plugin_manager

def initialize():
    """
    Initialize the plugins module.
    This function is responsible for setting up the plugin manager
    and ensuring all plugins are loaded and ready for use.
    """
    try:
        logging.info("Initializing plugins module...")
        initialize_plugin_manager()
        logging.info("Plugins module initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing plugins module: {e}", exc_info=True)
        raise