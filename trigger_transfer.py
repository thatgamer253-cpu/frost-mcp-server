from revenue import RevenueManager
import os

def main():
    print("--- Project Frost Transfer Protocol ---")
    rev_manager = RevenueManager()
    
    available = rev_manager.data.get('available_payout', 0)
    print(f"Current Available Balance: ${available:.2f}")
    
    if available <= 0:
        print("No funds available to transfer.")
        return

    print("Initiating transfer to Stripe...")
    success, message = rev_manager.request_payout()
    
    if success:
        print(f"SUCCESS: {message}")
        print(f"Updated Wallet (Paid): ${rev_manager.data.get('total_paid', 0)}")
    else:
        print(f"FAILED: {message}")
        print("\n[!] SAFETY NOTICE: If you see a 'PAYOUT_DESTINATION' error, please update your .env file with a valid Bank Account or Card ID.")

if __name__ == "__main__":
    main()
