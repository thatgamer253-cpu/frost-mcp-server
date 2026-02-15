import os
import json
from work_engine import WorkEngine

def test_sell_trigger():
    # 1. Simulate a Hunter (non-builder) Agent
    hunter_profile = {
        "name": "Python Hunter",
        "title": "Python Scraper Architect", # No 'Builder' or 'Architect' keyword suffix for simple match
        "settings": {"strategy": "Machine Gun"}
    }
    
    worker = WorkEngine(hunter_profile)
    
    # 2. Case A: Simple Scraper (Should NOT trigger engine)
    simple_job = {
        "id": "test_simple",
        "title": "Simple Python Scraper",
        "description": "Scrape some data from a site."
    }
    print("Testing Simple Scraper (Hunter Persona)...")
    res_simple = worker.generate_poc(simple_job)
    if "BUILD COMPLETE" in res_simple:
        print("FAIL: Simple scraper triggered engine.")
    else:
        print("PASS: Simple scraper used standard PoC logic.")
        
    # 3. Case B: Commercial Product (Should trigger engine)
    sell_job = {
        "id": "test_sell",
        "title": "Build a Scraper for SALE",
        "description": "I want a commercial product that scrapes real estate data to sell on a shop."
    }
    print("\nTesting Commercial Scraper (Hunter Persona)...")
    # Note: This will attempt to run the engine if HAS_ADVANCED is true. 
    # We'll just check if it enters the 'Creation task detected' block.
    res_sell = worker.generate_poc(sell_job)
    
    if "BUILD COMPLETE" in res_sell or "Creation task detected" in str(res_sell):
        print("PASS: Commercial keyword triggered Creation Engine hand-off.")
    else:
        print("FAIL: Commercial keyword ignored.")

if __name__ == "__main__":
    test_sell_trigger()
