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

def laser_submit():
    # Target a high-probability elite lead from scanner results
    target_url = "https://www.linkedin.com/jobs/view/4373229356"
    guardian.log_activity(f"LASER-LIVE: Targeting elite lead {target_url}...")
    
    # job object
    job = {
        "id": "li-9258",
        "title": "Applied AI Engineer",
        "company": "The Value Maximizer",
        "url": target_url,
        "platform": "LinkedIn",
        "description": "Applied AI Engineer role focused on deploying LLMs and automation workflows."
    }
    
    # 1. Load Profile
    profile_file = 'profiles/ai_strategist_1771146284.json'
    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    # 2. Generate Materials
    generator = MaterialGenerator(profile)
    letter = generator.generate_cover_letter(job)
    print("Cover Letter Generated.")
    
    # 3. Submit
    os.environ["AGENT_MODE"] = "production"
    submitter = AutoSubmitter(mode="production")
    
    print(f"Initiating Laser LinkedIn Submission for Applied AI Engineer...")
    # Inject a more robust selector override for this run
    success, msg = submitter.submit_proposal(job, letter)
    
    if success:
        print(f"SUCCESS: {msg}")
        guardian.log_activity(f"LASER-LIVE: [SUCCESS] Verified deployment for Applied AI Engineer.")
    else:
        print(f"FAILED: {msg}")
        # Take a screenshot specifically of the failure
        guardian.log_activity(f"LASER-LIVE: [FAILED] {msg}", "ERROR")

if __name__ == "__main__":
    laser_submit()
