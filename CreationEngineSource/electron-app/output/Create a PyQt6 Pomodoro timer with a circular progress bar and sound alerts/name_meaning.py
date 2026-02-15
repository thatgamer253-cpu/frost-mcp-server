# name_meaning.py

import os
import requests
from utils import load_configuration

def get_name_meaning(name):
    """
    Retrieves the meaning of a given name using an external API.

    :param name: The name to retrieve the meaning for.
    :return: A string representing the meaning of the name.
    """
    try:
        config = load_configuration()
        api_url = config.get("NAME_MEANING_API_URL")
        api_key = os.getenv("NAME_MEANING_API_KEY")

        if not api_url or not api_key:
            raise ValueError("API URL or API Key not configured properly.")

        response = requests.get(api_url, params={"name": name, "api_key": api_key})
        response.raise_for_status()

        data = response.json()
        return data.get("meaning", "Unknown")
    except requests.exceptions.RequestException as e:
        return f"Error contacting the name meaning service: {e}"
    except Exception as e:
        return f"Error determining name meaning: {e}"