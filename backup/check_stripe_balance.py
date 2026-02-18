import os
import sys

# Add Creator root to path for imports
creator_root = r"C:\Users\thatg\Desktop\Creator"
if creator_root not in sys.path:
    sys.path.append(creator_root)

try:
    from creation_engine.stripe_service import StripeService
    
    stripe = StripeService()
    if not stripe.is_configured():
        print("Error: Stripe not configured.")
        sys.exit(1)
        
    print("Checking real-world Stripe balance...")
    balance = stripe.get_balance()
    
    if "error" in balance:
        print(f"Failed to fetch balance: {balance['error']}")
    else:
        print(f"Available: {balance['available']} {balance['currency'].upper()}")
        print(f"Pending: {balance['pending']} {balance['currency'].upper()}")

except Exception as e:
    print(f"Error: {e}")
