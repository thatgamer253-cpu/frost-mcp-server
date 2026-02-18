import os
import sys
from datetime import datetime

# Add Creator root to path for imports
creator_root = r"C:\Users\thatg\Desktop\Creator"
if creator_root not in sys.path:
    sys.path.append(creator_root)

try:
    from creation_engine.stripe_service import StripeService
    import agent_ipc as hub
    
    # Override log path for IPC
    hub.CHAT_LOG = os.path.join(creator_root, "memory", "agent_chat.jsonl")
    
    print("Initiating Specific Payout Protocol: $200.00 USD...")
    
    stripe = StripeService()
    if not stripe.is_configured():
        print("Error: Stripe is not configured with a Secret Key.")
        sys.exit(1)
        
    # Trigger the payout
    amount = 200.00
    description = f"Nexus OS - Targeted Payout (${amount}) - {datetime.now().strftime('%Y-%m-%d')}"
    
    hub.broadcast("BOUNTY", "ambassador", f"💰 **Targeted Payout Initiated**: Requesting settlement of ${amount:.2f} from internal reserves.", msg_type="STATUS")
    
    result = stripe.create_payout(amount, description=description)
    
    if result.get("success"):
        msg = f"✅ **Targeted Payout Successful**: {result['payout_id']}. Status: {result['status']}. Arrival: {result['arrival_date']}"
        print(msg)
        hub.broadcast("BOUNTY", "ambassador", msg, msg_type="RESOLVE")
        
        # Log it locally
        stripe.log_payout(amount)
        
        # Note: We don't archive the revenue_events.log here because we only cashed out a partial amount
        # This is a 'manual override' payout.
    else:
        err = f"❌ **Payout Failed**: {result.get('error')}"
        print(err)
        hub.broadcast("BOUNTY", "ambassador", err, msg_type="FLAG")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
