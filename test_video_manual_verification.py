import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Keys
LUMA_KEY = os.getenv("LUMA_API_KEY")
RUNWAY_KEY = os.getenv("RUNWAY_API_KEY")

def test_luma():
    print("\n--- Testing Luma Dream Machine ---")
    if not LUMA_KEY:
        print("SKIPPING: No Luma Key found.")
        return

    # Endpoint candidates based on research
    url = "https://api.lumalabs.ai/dream-machine/v1/generations" 
    
    headers = {
        "Authorization": f"Bearer {LUMA_KEY}",
        "Content-Type": "application/json"
    }
    
    # Simple text-to-video prompt to test auth
    payload = {
        "prompt": "A futuristic city with flying cars, cinematic lighting",
        "aspect_ratio": "16:9",
        "model": "ray-2" # Updating to current model
    }

    print(f"POST {url}")
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:200]}...")
        
        if resp.status_code == 200 or resp.status_code == 201:
            print("Luma Auth Success!")
            return True
        else:
            print(f"Luma Auth Failed: {resp.text}")
            return False
    except Exception as e:
        print(f"Luma Exception: {e}")
        return False

def test_runway():
    print("\n--- Testing Runway Gen-3 ---")
    if not RUNWAY_KEY:
        print("SKIPPING: No Runway Key found.")
        return

    # Correct endpoint from error message
    url = "https://api.dev.runwayml.com/v1/image_to_video" 
    
    headers = {
        "Authorization": f"Bearer {RUNWAY_KEY}",
        "X-Runway-Version": "2024-09-13",
        "Content-Type": "application/json"
    }
    
    payload = {
        "promptText": "A fast car driving down a neon road",
        "promptImage": "https://via.placeholder.com/1280x768.png", # Dummy image to satisfy validation
        "model": "gen3a_turbo", 
    }

    print(f"POST {url}")
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:200]}...")
        
        if resp.status_code == 200 or resp.status_code == 201:
            print("Runway Auth Success!")
            return True
        elif resp.status_code == 404:
             print("Runway Endpoint 404 (Incorrect URL)")
        else:
            print(f"Runway Auth Failed: {resp.text}")
            return False
    except Exception as e:
        print(f"Runway Exception: {e}")
        return False

if __name__ == "__main__":
    test_luma()
    test_runway()
