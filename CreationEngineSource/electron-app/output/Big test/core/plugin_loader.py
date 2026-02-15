import os
import importlib.util
import logging
from core.base_tool import BaseTool

class PluginLoader:
    def __init__(self, plugins_directory):
        self.plugins_directory = plugins_directory
        self.logger = logging.getLogger(__name__)

    def load_plugins(self):
        plugins = []
        try:
            self.logger.info(f"Loading plugins from directory: {self.plugins_directory}")
            for filename in os.listdir(self.plugins_directory):
                if filename.endswith('.py') and not filename.startswith('__'):
                    plugin_path = os.path.join(self.plugins_directory, filename)
                    plugin = self._load_plugin(plugin_path)
                    if plugin:
                        plugins.append(plugin)
            self.logger.info("Plugins loaded successfully.")
        except Exception as e:
            self.logger.error("Error occurred while loading plugins.", exc_info=True)
            raise
        return plugins

    def _load_plugin(self, plugin_path):
        try:
            self.logger.info(f"Loading plugin from path: {plugin_path}")
            module_name = os.path.splitext(os.path.basename(plugin_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, type) and issubclass(attribute, BaseTool) and attribute is not BaseTool:
                    self.logger.info(f"Plugin {attribute_name} loaded successfully.")
                    return attribute()
        except Exception as e:
            self.logger.error(f"Error loading plugin from {plugin_path}", exc_info=True)
            return None