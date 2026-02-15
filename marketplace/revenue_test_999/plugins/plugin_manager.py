# plugins/plugin_manager.py

import os
import logging
import importlib
from typing import List, Dict, Optional
from utils.helpers import retry_on_failure
from utils.logger import setup_logging

class PluginManager:
    def __init__(self, plugins_directory: str):
        self.plugins_directory = plugins_directory
        self.plugins = {}
        setup_logging()

    def discover_plugins(self) -> List[str]:
        """
        Discover all plugins in the specified directory.
        """
        try:
            logging.info("Discovering plugins...")
            if not os.path.exists(self.plugins_directory):
                logging.warning(f"Plugins directory {self.plugins_directory} does not exist. Creating directory.")
                os.makedirs(self.plugins_directory)

            plugin_files = [f for f in os.listdir(self.plugins_directory) if f.endswith('.py') and f != '__init__.py']
            logging.info(f"Discovered {len(plugin_files)} plugins.")
            return plugin_files
        except Exception as e:
            logging.error(f"Failed to discover plugins: {e}", exc_info=True)
            return []

    @retry_on_failure
    def load_plugin(self, plugin_name: str) -> Optional[object]:
        """
        Load a plugin by name.
        """
        try:
            logging.info(f"Loading plugin: {plugin_name}")
            module_name = f"plugins.{plugin_name.replace('.py', '')}"
            module = importlib.import_module(module_name)
            self.plugins[plugin_name] = module
            logging.info(f"Plugin {plugin_name} loaded successfully.")
            return module
        except Exception as e:
            logging.error(f"Failed to load plugin {plugin_name}: {e}", exc_info=True)
            return None

    def activate_plugin(self, plugin_name: str) -> bool:
        """
        Activate a plugin if it has an 'activate' method.
        """
        try:
            logging.info(f"Activating plugin: {plugin_name}")
            plugin = self.plugins.get(plugin_name)
            if plugin and hasattr(plugin, 'activate'):
                plugin.activate()
                logging.info(f"Plugin {plugin_name} activated successfully.")
                return True
            else:
                logging.warning(f"Plugin {plugin_name} does not have an activate method.")
                return False
        except Exception as e:
            logging.error(f"Failed to activate plugin {plugin_name}: {e}", exc_info=True)
            return False

    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        Deactivate a plugin if it has a 'deactivate' method.
        """
        try:
            logging.info(f"Deactivating plugin: {plugin_name}")
            plugin = self.plugins.get(plugin_name)
            if plugin and hasattr(plugin, 'deactivate'):
                plugin.deactivate()
                logging.info(f"Plugin {plugin_name} deactivated successfully.")
                return True
            else:
                logging.warning(f"Plugin {plugin_name} does not have a deactivate method.")
                return False
        except Exception as e:
            logging.error(f"Failed to deactivate plugin {plugin_name}: {e}", exc_info=True)
            return False

def initialize():
    """
    Initialize the plugin manager.
    """
    try:
        logging.info("Initializing plugin manager...")
        plugins_directory = os.getenv('PLUGINS_DIRECTORY', './plugins')
        plugin_manager = PluginManager(plugins_directory)
        plugin_files = plugin_manager.discover_plugins()
        for plugin_file in plugin_files:
            plugin_manager.load_plugin(plugin_file)
        logging.info("Plugin manager initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize plugin manager: {e}", exc_info=True)
```

### Key Features:
1. **Plugin Discovery**: Automatically discovers Python files in the plugins directory, excluding `__init__.py`.
2. **Plugin Loading**: Dynamically loads plugins using Python's `importlib`.
3. **Activation/Deactivation**: Supports activating and deactivating plugins if they implement `activate` and `deactivate` methods.
4. **Error Handling**: Comprehensive error handling with logging for all operations.
5. **Directory Management**: Ensures the plugins directory exists, creating it if necessary.
6. **Environment Configuration**: Uses environment variables for the plugins directory path, allowing flexible deployment configurations.