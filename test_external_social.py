import os
import json
from marketing_engine import MarketingEngine
from social_engine import social_engine

def test_external_broadcast():
    print("Starting External Social Broadcast Verification...")
    
    # 1. Setup a dummy agent profile
    profile = {
        "name": "Alex B.",
        "title": "Python Developer & Creation Engine Merchant",
        "description": "Expert in autonomous tool building and marketplace arbitrage."
    }
    
    # 2. Trigger Campaign Generation
    marketer = MarketingEngine(profile)
    print("Generating campaign...")
    campaign = marketer.generate_campaign()
    
    if campaign:
        print(f"Campaign Generated: {campaign['headline']}")
        
        # 3. Execute Social Outreach (Internal + External)
        print("Broadcasting to external networks (Moltbook/Agentverse)...")
        success = marketer.execute_social_outreach(campaign)
        
        if success:
            print("✅ SUCCESS: Outreach executed.")
            
            # 4. Verify log file
            log_file = 'external_social.log'
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    print(f"Last Log Entry: {lines[-1].strip()}")
            else:
                print("❌ ERROR: external_social.log not found!")
        else:
            print("❌ ERROR: Outreach execution failed.")
    else:
        print("❌ ERROR: Campaign generation failed.")

if __name__ == "__main__":
    test_external_broadcast()
