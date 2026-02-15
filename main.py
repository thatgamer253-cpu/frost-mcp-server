import os
import json
import time
from work_engine import WorkEngine
from auto_submitter import AutoSubmitter
from guardian import guardian
import marketing_engine

def load_all_profiles():
    profiles_dir = 'profiles'
    if not os.path.exists(profiles_dir):
        # Fallback to single profile if hive is not initialized
        if os.path.exists('profile_config.json'):
            with open('profile_config.json', 'r') as f:
                return [json.load(f)]
        return []
    
    profiles = []
    for filename in os.listdir(profiles_dir):
        if filename.endswith('.json'):
            with open(os.path.join(profiles_dir, filename), 'r') as f:
                try: 
                    p = json.load(f)
                    p['_filename'] = filename # Internal tracking
                    profiles.append(p)
                except: pass
    return profiles

def run_agent_loop(profile, submitter):
    guardian.log_activity(f"AGENT START: {profile.get('name')} [{profile.get('title')}]")
    is_closer = any(kw in profile.get("title", "") for kw in ["Diplomac", "Social", "Diplomat", "Merchant"])

    if is_closer:
        guardian.log_activity(f"[{profile.get('name')}] DIPLOMAT MODE: Checking messages & marketplace...")
        submitter.check_messages("LinkedIn")
        submitter.check_messages("Upwork")
        
        if "Merchant" in profile.get("title", ""):
            m_dir = 'marketplace'
            if os.path.exists(m_dir):
                items = os.listdir(m_dir)
                guardian.log_activity(f"[{profile.get('name')}] MERCHANT: Auditing marketplace ({len(items)} products total).")
                from revenue import RevenueManager
                rev_manager = RevenueManager()
                
                for item in items:
                    state_path = os.path.join(m_dir, item, 'state.json')
                    if os.path.exists(state_path):
                        try:
                            with open(state_path, 'r') as f:
                                st_data = json.load(f)
                            if st_data.get('current_phase') == "COMPLETE":
                                success, amount = rev_manager.process_marketplace_sale(item)
                                if success:
                                    guardian.log_activity(f"[{profile.get('name')}] MERCHANT: SALE CONFIRMED! Project {item} sold for ${amount:.2f}.")
                                    guardian.send_social_message(profile.get("name"), f"💰 MARKETPLACE SALE! Just finalized ${amount:.2f} for project '{item}'. Funds moved to Stripe Balance.")
                        except: pass
    
    # GLOBAL MARKETING: All agents promote marketplace services and the Creation Engine
    from marketing_engine import MarketingEngine
    marketer = MarketingEngine(profile)
    
    guardian.log_activity(f"[{profile.get('name')}] MARKETING: Generating outreach campaign...")
    try:
        campaign = marketer.generate_campaign()
        if campaign:
            marketer.execute_social_outreach(campaign)
    except Exception as e:
        guardian.log_activity(f"[{profile.get('name')}] MARKETING ERROR: {str(e)}")

def main():
    guardian.log_activity("--- Project Frost HIVE Mode Initialized [MARKETPLACE FOCUS] ---")
    submitter = AutoSubmitter()
    
    while True:
        profiles = load_all_profiles()
        if not profiles:
            guardian.log_activity("No profiles found. Swarm idle...")
            time.sleep(60)
            continue

        guardian.log_activity(f"HIVE UPDATE: {len(profiles)} agents active in swarm.")
        for profile in profiles:
            try:
                run_agent_loop(profile, submitter)
            except Exception as e:
                guardian.log_activity(f"HIVE CRITICAL: Agent {profile.get('name')} failed: {str(e)}", "CRITICAL")
            
            # Short breathe between agent cycles to avoid overloading system
            time.sleep(5)

        wait_time = 60 # FORCED LIVE VELOCITY
        guardian.log_activity(f"HIVE SLEEP: Cycle complete. Next sync in {wait_time}s.")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
