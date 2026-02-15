import json
import os
from revenue import RevenueManager

def finalize_all():
    print("Finalizing all pending revenue...")
    rev_manager = RevenueManager()
    
    # We'll collect all pending project IDs
    pending_ids = []
    for txn in rev_manager.data["transactions"]:
        if txn["status"] == "Pending":
            # Extract project ID from TXN- prefix
            project_id = txn["id"].replace("TXN-", "")
            pending_ids.append(project_id)
    
    if not pending_ids:
        print("No pending transactions found.")
        return

    for pid in pending_ids:
        print(f"Finalizing {pid}...")
        success, amount = rev_manager.process_marketplace_sale(pid)
        if success:
            print(f"SUCCESS: {pid} finalized for ${amount:.2f}")
        else:
            print(f"FAIL: Could not finalize {pid}")

    print(f"New Available Payout: ${rev_manager.data['available_payout']:.2f}")

if __name__ == "__main__":
    finalize_all()
