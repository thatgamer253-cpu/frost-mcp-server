import json
from error_handling import handle_error

def load_config(file_path):
    """
    Loads configuration settings from a JSON file.

    :param file_path: The path to the configuration file.
    :return: A dictionary containing the configuration settings.
    """
    try:
        with open(file_path, 'r') as config_file:
            config = json.load(config_file)
            return config
    except FileNotFoundError:
        handle_error(f"Configuration file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        handle_error(f"Error decoding JSON from the configuration file: {e}")
        return {}
    except Exception as e:
        handle_error(e)
        return {}

def save_config(file_path, config):
    """
    Saves configuration settings to a JSON file.

    :param file_path: The path to the configuration file.
    :param config: A dictionary containing the configuration settings to save.
    """
    try:
        with open(file_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
    except Exception as e:
        handle_error(e)

# Load the configuration file path from an environment variable
config_file_path = os.getenv('CONFIG_FILE_PATH', 'config.json')