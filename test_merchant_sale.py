import os
import json
import time
from revenue import RevenueManager
from guardian import guardian

def test_merchant_sale():
    print("Testing Hive Merchant Sale Realization...")
    
    # 1. Setup Dummy Marketplace Project
    m_dir = 'marketplace/test_sale_123'
    os.makedirs(m_dir, exist_ok=True)
    
    state_data = {
        "current_phase": "COMPLETE",
        "history": [{"timestamp": "12:00:00", "phase": "COMPLETE", "summary": "Build successful"}]
    }
    with open(os.path.join(m_dir, 'state.json'), 'w') as f:
        json.dump(state_data, f)
        
    # 2. Setup Pending Transaction
    rev_manager = RevenueManager()
    # Reset/Ensure clean start for test if needed, but we'll just add
    rev_manager.record_job_start("test_sale_123", "Marketplace", 299.0)
    
    print("Initial State: Pending Income recorded.")
    
    # 3. Simulate Merchant Loop
    # We'll just run the logic block from main.py
    items = os.listdir('marketplace')
    for item in items:
        if item == 'test_sale_123':
            state_path = os.path.join('marketplace', item, 'state.json')
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    st_data = json.load(f)
                if st_data.get('current_phase') == "COMPLETE":
                    print(f"Merchant: Found completed project {item}. Processing sale...")
                    success, amount = rev_manager.process_marketplace_sale(item)
                    if success:
                        print(f"PASS: Merchant finalized sale of ${amount:.2f} for {item}.")
                    else:
                        print(f"FAIL: Merchant failed to finalize sale for {item}.")

    # 4. Verify Final Balance
    with open('revenue_data.json', 'r') as f:
        final_data = json.load(f)
        print(f"Final Available Payout: ${final_data.get('available_payout')}")
        if final_data.get('available_payout') >= 299.0:
            print("VERIFICATION SUCCESSFUL: Funds moved to Available Payout.")
        else:
            print("VERIFICATION FAILED: Funds not found in Available Payout.")

if __name__ == "__main__":
    test_merchant_sale()
