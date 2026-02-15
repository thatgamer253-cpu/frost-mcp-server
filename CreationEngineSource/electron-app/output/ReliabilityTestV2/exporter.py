import csv
from datetime import datetime, timedelta
from api_client import CoinGeckoAPIClient
from data_manager import DataManager

class Exporter:
    def __init__(self, api_client: CoinGeckoAPIClient, data_manager: DataManager):
        self.api_client = api_client
        self.data_manager = data_manager

    def export_portfolio_to_csv(self, file_path='portfolio.csv'):
        """Export the current portfolio to a CSV file."""
        try:
            portfolio = self.data_manager.get_portfolio()
            with open(file_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Cryptocurrency', 'Amount', 'Current Price (USD)', 'Total Value (USD)'])

                for crypto in portfolio:
                    crypto_name = crypto[1]
                    if crypto_name:
                        current_price = self.api_client.get_current_price(crypto_name)
                        if current_price is not None:
                            total_value = crypto['amount'] * current_price
                            writer.writerow([crypto_name, crypto['amount'], current_price, total_value])

            print(f"Portfolio successfully exported to {file_path}")
        except Exception as e:
            print(f"Error exporting portfolio to CSV: {e}")

    def export_historical_prices_to_csv(self, crypto_id, start_date, end_date, file_path='historical_prices.csv'):
        """Export historical prices of a cryptocurrency to a CSV file."""
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            current_date = start_date_obj

            with open(file_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Date', 'Price (USD)'])

                while current_date <= end_date_obj:
                    date_str = current_date.strftime('%d-%m-%Y')
                    price = self.api_client.get_historical_price(crypto_id, date_str)
                    if price is not None:
                        writer.writerow([current_date.strftime('%Y-%m-%d'), price])
                    current_date += timedelta(days=1)

            print(f"Historical prices successfully exported to {file_path}")
        except Exception as e:
            print(f"Error exporting historical prices to CSV: {e}")