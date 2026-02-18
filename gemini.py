# gemini.py

import requests

def make_request(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Resource not found: {url}")
            return {
                "error": "Resource not found",
                "code": 404,
                "details": "The requested resource was not found. Please verify the endpoint and try again later."
            }  # Return a detailed user-friendly error message
        else:
            raise
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise