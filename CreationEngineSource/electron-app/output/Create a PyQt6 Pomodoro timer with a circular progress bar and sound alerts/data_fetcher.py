import requests
import os
import configparser
from utils import load_configuration

class DataFetcher:
    api_endpoints = {
        "name_analysis": "https://api.publicapis.org/entries"  # Example public API for demonstration
    }

    def fetch_data_from_api(self, endpoint_key, params=None):
        """
        Fetches data from an external API based on the endpoint key.

        :param endpoint_key: The key to identify the API endpoint in the configuration.
        :param params: Optional parameters to pass to the API.
        :return: The response data from the API or an error message.
        """
        try:
            endpoint = self.api_endpoints.get(endpoint_key)
            if not endpoint:
                raise ValueError(f"API endpoint for '{endpoint_key}' not found in configuration.")

            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    def fetch_data_from_database(self, query):
        """
        Mock function to fetch data from a database.

        :param query: The database query to execute.
        :return: Mocked database response.
        """
        try:
            # Mock database interaction
            # In a real scenario, this would involve actual database connection and query execution
            return {"data": "Mocked database response for query: " + query}
        except Exception as e:
            return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    fetcher = DataFetcher()
    api_result = fetcher.fetch_data_from_api("name_analysis", {"title": "API"})