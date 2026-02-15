import os
import json
import sys

# Set encoding for Windows stdout
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

from engine_bridge import creation_engine
from generator import MaterialGenerator

def main():
    # Target Lead: AI Engineer (Python, Gen AI) at DHL
    # We found two versions, li-8655 and li-8290. Using li-8290 (Score 85).
    lead_id = "li-8290"
    
    if not os.path.exists('found_jobs.json'):
        print("found_jobs.json not found.")
        return

    with open('found_jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)
        
    job = next((j for j in jobs if j['id'] == lead_id), None)
    
    if not job:
        print(f"Lead {lead_id} not found in found_jobs.json")
        return

    print(f"INITIATING CLOSING PROTOCOL: {job['title']} @ {job['company']}")
    
    # 1. Load Profile
    profile_path = 'profile_config.json'
    if not os.path.exists(profile_path):
        print("profile_config.json not found.")
        return

    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    generator = MaterialGenerator(profile)
    
    # 2. Generate Cover Letter
    print("Generating Cover Letter...")
    letter = generator.generate_cover_letter(job)
    generator.save_application(job, letter)
    
    # 3. Trigger Universal Engine (via Bridge)
    project_id = f"dhl_ai_eng_{lead_id}"
    goal = f"Build a {job['title']} Proof of Concept"
    description = f"Job Title: {job['title']}\nCompany: {job['company']}\nURL: {job['url']}\nRequirements: {job.get('reasoning', 'Expert AI and Python automation.')}"
    
    print(f"Triggering Universal Engine for {project_id}...")
    success, path = creation_engine.build_project(project_id, goal, description)
    
    if success:
        print(f"SUCCESS: Universal Engine build complete at: {path}")
        print("Note: Materials are ready in the applications folder.")
    else:
        print(f"FAILED: Engine error: {path}")

if __name__ == "__main__":
    main()
