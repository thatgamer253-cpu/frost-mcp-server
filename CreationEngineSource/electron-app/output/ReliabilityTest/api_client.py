import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

class APIClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        pass

    def get_coin_data(self, coin_id):
        """Fetch data for a specific coin from CoinGecko."""
        endpoint = f"{self.BASE_URL}/coins/{coin_id}"
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
        except HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except RequestException as req_err:
            print(f"An error occurred: {req_err}")
        return None

    def get_market_data(self, vs_currency='usd', order='market_cap_desc', per_page=100, page=1):
        """Fetch market data for all coins."""
        endpoint = f"{self.BASE_URL}/coins/markets"
        params = {
            'vs_currency': vs_currency,
            'order': order,
            'per_page': per_page,
            'page': page,
            'sparkline': False
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except RequestException as req_err:
            print(f"An error occurred: {req_err}")
        return None