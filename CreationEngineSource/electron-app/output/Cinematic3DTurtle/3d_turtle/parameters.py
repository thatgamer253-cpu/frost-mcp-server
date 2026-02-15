import json
import os

class Parameters:
    def __init__(self, config_file='config.json'):
        """
        Initialize the Parameters class, loading settings from a configuration file.
        
        :param config_file: Path to the configuration file.
        """
        self.config_file = config_file
        self.settings = {
            "window_width": 800,
            "window_height": 600,
            "background_color": [0, 0, 0],
            "gravity": 9.81,
            "friction": 0.1,
            "shader_paths": {
                "vertex_shader": "assets/shaders/vertex_shader.glsl",
                "fragment_shader": "assets/shaders/fragment_shader.glsl"
            }
        }
        self.load_settings()

    def load_settings(self):
        """
        Load settings from the configuration file. If the file does not exist, use default settings.
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    self.settings.update(json.load(file))
            else:
                self.save_settings()  # Save default settings if file doesn't exist
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """
        Save the current settings to the configuration file.
        """
        try:
            with open(self.config_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_setting(self, key, default=None):
        """
        Retrieve a setting value by key.
        
        :param key: The key of the setting to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the setting or the default value.
        """
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """
        Set a setting value by key.
        
        :param key: The key of the setting to set.
        :param value: The value to set for the key.
        """
        self.settings[key] = value
        self.save_settings()