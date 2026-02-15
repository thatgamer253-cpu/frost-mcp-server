import json
import os

def find_upwork_elite():
    if not os.path.exists('found_jobs.json'):
        print("found_jobs.json missing")
        return
        
    with open('found_jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)
        
    upwork_elite = [j for j in jobs if j.get('platform') == 'Upwork' and j.get('score', 0) >= 80]
    
    print(f"Found {len(upwork_elite)} Upwork elite jobs:")
    for j in upwork_elite[:10]:
        print(f"ID: {j['id']} | Title: {j['title']} | Score: {j['score']}")
        print(f"URL: {j['url']}\n")

if __name__ == "__main__":
    find_upwork_elite()
