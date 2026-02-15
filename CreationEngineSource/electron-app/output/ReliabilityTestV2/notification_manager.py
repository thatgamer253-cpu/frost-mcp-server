from api_client import CoinGeckoAPIClient
import notify2

class NotificationManager:
    def __init__(self, app_name="Crypto Portfolio Dashboard"):
        self.app_name = app_name
        self.api_client = CoinGeckoAPIClient()
        notify2.init(app_name)

    def send_notification(self, title, message):
        """Send a desktop notification."""
        try:
            notification = notify2.Notification(title, message)
            notification.show()
        except Exception as e:
            print(f"Error sending notification: {e}")

    def check_price_change(self, crypto_id, threshold, vs_currency='usd'):
        """Check for significant price changes and notify the user."""
        try:
            current_price = self.api_client.get_current_price(crypto_id, vs_currency)
            if current_price is None:
                print("Failed to retrieve current price.")
                return

            # For demonstration, assume we have a method to get the previous price
            previous_price = self.get_previous_price(crypto_id, vs_currency)
            if previous_price is None:
                print("Failed to retrieve previous price.")
                return

            price_change = ((current_price - previous_price) / previous_price) * 100
            if abs(price_change) >= threshold:
                self.send_notification(
                    f"Significant Price Change for {crypto_id}",
                    f"The price has changed by {price_change:.2f}%"
                )
        except Exception as e:
            print(f"Error checking price change: {e}")

    def get_previous_price(self, crypto_id, vs_currency='usd'):
        """Mock method to get the previous price of a cryptocurrency."""
        # This should be replaced with actual logic to retrieve the previous price
        # For now, return a mock value
        return 100.0