import stripe
import os
from dotenv import load_dotenv

load_dotenv()

def find_destination():
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY not found in .env")
        return

    stripe.api_key = api_key
    
    print(f"Checking Stripe account for valid payout destinations...")
    try:
        # Check External Accounts (Bank Accounts and Cards)
        # Note: In a real scenario, this might need more specific queries depending on account type.
        # But for an instant payout, we usually look for 'bank_account' or 'card'.
        
        # We start by getting the Account Info
        account = stripe.Account.retrieve()
        print(f"Account ID: {account.id}")
        
        # List External Accounts
        external_accounts = stripe.Account.list_external_accounts(account.id, object="bank_account")
        print("\n--- BANK ACCOUNTS ---")
        for acc in external_accounts.data:
            print(f"ID: {acc.id} | Status: {acc.status} | Bank: {acc.bank_name} | Payouts: {acc.default_for_currency}")

        external_accounts_cards = stripe.Account.list_external_accounts(account.id, object="card")
        print("\n--- CARDS ---")
        for card in external_accounts_cards.data:
            print(f"ID: {card.id} | Brand: {card.brand} | Last4: {card.last4} | Payouts: {card.default_for_currency}")

    except Exception as e:
        print(f"Error retrieving from Stripe: {e}")

if __name__ == "__main__":
    find_destination()
