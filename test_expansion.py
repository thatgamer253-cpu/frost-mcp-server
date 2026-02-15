import json
import os
from scanner import JobScanner
from work_engine import WorkEngine

# 1. Test Craigslist Scanner
print("--- TESTING CRAIGSLIST SCANNER ---")
scanner = JobScanner()
craigslist_jobs = scanner.scan_craigslist(["Python"])
print(f"Found {len(craigslist_jobs)} Craigslist jobs.")
if craigslist_jobs:
    print(f"Sample Job: {craigslist_jobs[0]['title']} @ {craigslist_jobs[0]['company']}")

# 2. Test Creative Content Generation
print("\n--- TESTING CREATIVE CONTENT GENERATION ---")
profile = {"name": "Test Agent"} # Minimal profile for the engine
worker = WorkEngine(profile)

creative_job = {
    "id": "test-creative-1",
    "title": "Write a deep-dive article on the future of Autonomous AI Agents",
    "description": "We need a 1000-word article for our tech blog.",
    "platform": "Direct"
}

content = worker.generate_poc(creative_job)
print(f"Content Generated (first 200 chars):\n{content[:200]}...")

# Save the deliverable
path = worker.package_deliverable(creative_job, content)
print(f"Deliverable saved to: {path}")
