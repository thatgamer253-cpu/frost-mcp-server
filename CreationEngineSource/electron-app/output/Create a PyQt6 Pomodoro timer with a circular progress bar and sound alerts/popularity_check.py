# popularity_check.py

import requests
import os
from utils import load_configuration

def check_name_popularity(name):
    """
    Checks the popularity of a given name using an external API.

    :param name: The name to check.
    :return: A string representing the popularity of the name.
    """
    try:
        config = load_configuration()
        api_url = config.get("NAME_POPULARITY_API_URL")
        api_key = os.getenv("NAME_POPULARITY_API_KEY")

        if not api_url or not api_key:
            raise ValueError("API URL or API Key not configured properly.")

        response = requests.get(api_url, params={"name": name, "api_key": api_key})
        response.raise_for_status()

        data = response.json()
        return data.get("popularity", "Unknown")
    except requests.exceptions.RequestException as e:
        return f"Error contacting the name popularity service: {e}"
    except Exception as e:
        return f"Error determining name popularity: {e}"