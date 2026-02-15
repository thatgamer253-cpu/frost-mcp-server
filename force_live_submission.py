import sys
import codecs
import os
import json
import time
from auto_submitter import AutoSubmitter
from generator import MaterialGenerator
from guardian import guardian

# Set encoding for Windows stdout
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def force_submit():
    guardian.log_activity("FORCE-LIVE: Initializing manual submission override...")
    
    # 1. Load Profile (Using Casey A. for AI skills)
    profile_file = 'profiles/ai_strategist_1771146284.json'
    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    # 2. Get Job from found_jobs.json
    with open('found_jobs.json', 'r') as f:
        jobs = json.load(f)
    
    # Target an Elite match (AI Engineer)
    # Target all Elite matches (Score >= 85)
    elite_jobs = [j for j in jobs if j.get('score', 0) >= 85]
    print(f"Found {len(elite_jobs)} elite leads. Attempting one-by-one...")
    
    # Force production mode
    os.environ["AGENT_MODE"] = "production"
    submitter = AutoSubmitter(mode="production")

    for job in elite_jobs:
        print(f"\n--- ATTEMPTING: {job['title']} at {job['company']} ---")
        
        # 3. Generate Materials
        generator = MaterialGenerator(profile)
        letter = generator.generate_cover_letter(job)
        
        print(f"Initiating LinkedIn Submission for {job['id']}...")
        success, msg = submitter.submit_proposal(job, letter)
        
        if success:
            print(f"SUCCESS: {msg}")
            guardian.log_activity(f"FORCE-LIVE: [SUCCESS] Verified deployment for '{job['title']}'.")
            return # Stop at first success
        else:
            print(f"SKIPPED/FAILED: {msg}")
            # Continue to next job
    
    print("\nNo elite jobs could be submitted at this time.")

if __name__ == "__main__":
    force_submit()
