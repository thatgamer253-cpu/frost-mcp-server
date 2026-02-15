import os
import requests
from error_handling import handle_error
from dotenv import load_dotenv

load_dotenv()

def analyze_name(name):
    """
    Analyzes a given name for its origin, popularity trends, and personality traits.

    :param name: The name to analyze.
    :return: A dictionary containing the analysis results.
    """
    try:
        origin = lookup_name_origin(name)
        popularity = get_popularity_trends(name)
        traits = analyze_personality_traits(name)

        return {
            "origin": origin,
            "popularity": popularity,
            "traits": traits
        }
    except Exception as e:
        handle_error(e)
        return None

def lookup_name_origin(name):
    """
    Looks up the origin of a given name.

    :param name: The name to look up.
    :return: A string describing the origin of the name.
    """
    try:
        # Mock API call to a public endpoint for name origin
        api_endpoint = os.getenv("NAME_ORIGIN_API_ENDPOINT", "https://api.nationalize.io")
        response = requests.get(f"{api_endpoint}/?name={name}")
        response.raise_for_status()
        data = response.json()
        if data['country']:
            return data['country'][0]['country_id']
        return "Unknown"
    except requests.RequestException as e:
        handle_error(e)
        return "Error fetching origin"

def get_popularity_trends(name):
    """
    Retrieves popularity trends for a given name.

    :param name: The name to analyze.
    :return: A dictionary with year as keys and popularity score as values.
    """
    try:
        # Mock API call to a public endpoint for name popularity
        api_endpoint = os.getenv("NAME_POPULARITY_API_ENDPOINT", "https://api.agify.io")
        response = requests.get(f"{api_endpoint}/?name={name}")
        response.raise_for_status()
        data = response.json()
        return {"age": data.get("age", "Unknown")}
    except requests.RequestException as e:
        handle_error(e)
        return {"error": "Error fetching popularity trends"}

def analyze_personality_traits(name):
    """
    Analyzes personality traits associated with a given name.

    :param name: The name to analyze.
    :return: A list of personality traits.
    """
    try:
        # Mock analysis based on name length and characters
        traits = []
        if len(name) % 2 == 0:
            traits.append("Balanced")
        else:
            traits.append("Creative")

        if 'a' in name.lower():
            traits.append("Adventurous")
        if 'e' in name.lower():
            traits.append("Empathetic")

        return traits
    except Exception as e:
        handle_error(e)
        return ["Error analyzing traits"]