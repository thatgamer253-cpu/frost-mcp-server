import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def check_balance():
    try:
        balance = stripe.Balance.retrieve()
        print("--- Stripe Live Balance ---")
        for type, value in balance.items():
            if isinstance(value, list):
                for item in value:
                    amount = item['amount'] / 100
                    print(f"{type.capitalize()} ({item['currency'].upper()}): ${amount:.2f}")
    except Exception as e:
        print(f"Error checking balance: {e}")

if __name__ == "__main__":
    check_balance()
