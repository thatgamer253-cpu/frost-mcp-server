import os
import json
import time
from scanner import JobScanner
from intelligence import JobEvaluator
from generator import MaterialGenerator
from work_engine import WorkEngine
from auto_submitter import AutoSubmitter
from guardian import guardian

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

def run_agent_loop(profile, scanner, submitter):
    guardian.log_activity(f"AGENT START: {profile.get('name')} [{profile.get('title')}]")
    evaluator = JobEvaluator(profile)
    generator = MaterialGenerator(profile)
    worker = WorkEngine(profile)

    strat_name = profile.get("settings", {}).get("strategy", "Standard")
    is_closer = any(kw in profile.get("title", "") for kw in ["Diplomac", "Social", "Diplomat", "Merchant"])

    if is_closer:
        guardian.log_activity(f"[{profile.get('name')}] DIPLOMAT MODE: Checking messages & closing...")
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

        # CLOSER PROTOCOL: Process saved leads
        filename = 'found_jobs.json'
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    saved_jobs = json.load(f)
                
                applied_file = 'applied_ledger.json'
                applied = []
                if os.path.exists(applied_file):
                    with open(applied_file, 'r') as f:
                        try: applied = json.load(f)
                        except: pass

                leads = [j for j in saved_jobs if (j.get('score', 0) >= 85 or j.get('manual_push')) and j['id'] not in applied]
                if leads:
                    guardian.log_activity(f"[{profile.get('name')}] DIPLOMAT: Found {len(leads)} fresh elite leads.")
                    for job in leads[:2]: # Small batch per agent
                        # 1. Generate Material
                        guardian.log_activity(f"[{profile.get('name')}] Closing lead '{job['title']}'...")
                        letter = generator.generate_cover_letter(job)
                        generator.save_application(job, letter)
                        
                        # 2. Generate Proof of Concept (The 'Work' / Engine Hand-off)
                        poc = worker.generate_poc(job)
                        poc_path = worker.package_deliverable(job, poc)
                        
                        # 3. Auto-Submit
                        success, msg = submitter.submit_proposal(job, letter, poc_path)
                        guardian.log_activity(f"[{profile.get('name')}] DIPLOMAT STATUS: {msg}")
            except Exception as e:
                guardian.log_activity(f"[{profile.get('name')}] DIPLOMAT ERROR: {str(e)}", "WARNING")
    else:
        guardian.log_activity(f"[{profile.get('name')}] HUNTER MODE: Starting scan for {strat_name} strategy...")
        try:
            jobs = scanner.scan_all(profile)
            for job in jobs:
                score, reasoning = evaluator.evaluate(job)
                saved = evaluator.save_interesting_job(job, score, reasoning)
                if saved and score >= 85:
                    guardian.log_activity(f"[{profile.get('name')}] identified elite match: {job['title']}")
                    guardian.send_social_message(profile.get("name"), f"🚀 Found ELITE match: {job['title']} ({score}%)")
        except Exception as e:
            guardian.log_activity(f"[{profile.get('name')}] SCANNER ERROR: {str(e)}")

def main():
    guardian.log_activity("--- Project Frost HIVE Mode Initialized ---")
    scanner = JobScanner()
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
                run_agent_loop(profile, scanner, submitter)
            except Exception as e:
                guardian.log_activity(f"HIVE CRITICAL: Agent {profile.get('name')} failed: {str(e)}", "CRITICAL")
            
            # Short breathe between agent cycles to avoid overloading system
            time.sleep(5)

        wait_time = 60 # FORCED LIVE VELOCITY
        guardian.log_activity(f"HIVE SLEEP: Cycle complete. Next sync in {wait_time}s.")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
