import requests

class CoinGeckoAPIClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        pass

    def get_current_price(self, crypto_id, vs_currency='usd'):
        """Fetch the current price of a cryptocurrency."""
        try:
            response = requests.get(f"{self.BASE_URL}/simple/price", params={
                'ids': crypto_id,
                'vs_currencies': vs_currency
            })
            response.raise_for_status()
            data = response.json()
            return data.get(crypto_id, {}).get(vs_currency)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching current price: {e}")
            return None

    def get_historical_price(self, crypto_id, date, vs_currency='usd'):
        """Fetch the historical price of a cryptocurrency on a specific date."""
        try:
            response = requests.get(f"{self.BASE_URL}/coins/{crypto_id}/history", params={
                'date': date,
                'localization': 'false'
            })
            response.raise_for_status()
            data = response.json()
            market_data = data.get('market_data', {})
            return market_data.get('current_price', {}).get(vs_currency)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching historical price: {e}")
            return None