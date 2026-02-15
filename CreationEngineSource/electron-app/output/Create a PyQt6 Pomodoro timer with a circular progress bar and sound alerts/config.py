import configparser
import os

def load_config():
    """
    Loads and parses the configuration file.

    :return: A dictionary containing configuration sections and their key-value pairs.
    """
    config = configparser.ConfigParser()
    config_file = 'config.ini'

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

    config.read(config_file)
    configuration = {section: dict(config.items(section)) for section in config.sections()}
    return configuration

def validate_name_format(name):
    """
    Validates the format of a given name.

    :param name: The name to validate.
    :return: True if the name is valid, False otherwise.
    """
    # Example validation: name must be alphabetic and between 1 and 50 characters
    return name.isalpha() and 1 <= len(name) <= 50