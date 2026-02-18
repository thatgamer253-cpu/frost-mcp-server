import os
import sys

# Add Creator root to path for imports
creator_root = r"C:\Users\thatg\Desktop\Creator"
if creator_root not in sys.path:
    sys.path.append(creator_root)

try:
    from council_agents import AmbassadorAgent
    import agent_ipc as hub
    
    # Override log path
    hub.CHAT_LOG = os.path.join(creator_root, "memory", "agent_chat.jsonl")
    
    print("Initiating Force Payout Protocol via AmbassadorAgent...")
    
    # We don't start it as a thread, just call the method
    ambassador = AmbassadorAgent(project_root=creator_root)
    
    # The protocol checks the Vault and calls StripeService
    ambassador._cash_out_protocol()
    
    print("\nProtocol execution complete. Check agent_chat.jsonl and revenue_events.log for results.")

except Exception as e:
    print(f"Error during force payout: {e}")
    import traceback
    traceback.print_exc()
