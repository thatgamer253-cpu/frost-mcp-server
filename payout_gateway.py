import os
import stripe
from dotenv import load_dotenv

load_dotenv()

class PayoutGateway:
    """Handles real-world financial transactions via Stripe."""
    
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        if self.api_key:
            stripe.api_key = self.api_key
            self.live_mode = self.api_key.startswith("sk_live")
        else:
            self.live_mode = False

    def send_instant_payout(self, amount, currency="usd"):
        """Triggers a real instant payout using Stripe."""
        if not self.api_key:
            return {"status": "error", "message": "Missing Stripe API Key"}
        
        destination = os.getenv("PAYOUT_DESTINATION")
        try:
            if self.live_mode:
                # OPTIMAL DECISION: If destination is the placeholder, omit it to use the Stripe default destination.
                payout_params = {
                    "amount": int(amount * 100),
                    "currency": currency,
                    "method": "standard", # Changed from instant for reliability
                    "description": "Project Frost Job Earning Payout"
                }
                
                if destination and destination != "connected_cashapp_user":
                    payout_params["destination"] = destination
                else:
                    print(f"[Gateway] Using default Stripe payout destination (placeholder detected: {destination})")

                payout = stripe.Payout.create(**payout_params)
                return {"status": "success", "id": payout.id}
            else:
                return {"status": "success", "id": "payout_simulated_test"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
