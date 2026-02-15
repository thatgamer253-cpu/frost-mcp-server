import json
import os

def deduplicate_jobs():
    filename = 'found_jobs.json'
    if not os.path.exists(filename):
        print("found_jobs.json not found.")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        try:
            jobs = json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
            return

    original_count = len(jobs)
    unique_urls = set()
    deduplicated_jobs = []

    for job in jobs:
        url = job.get('url')
        if url and url not in unique_urls:
            unique_urls.add(url)
            # Normalize ID if it's missing or random (optional, but good for consistency)
            deduplicated_jobs.append(job)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(deduplicated_jobs, f, indent=2)

    print(f"De-duplication complete.")
    print(f"Original: {original_count}")
    print(f"Unique: {len(deduplicated_jobs)}")
    print(f"Removed: {original_count - len(deduplicated_jobs)}")

if __name__ == "__main__":
    deduplicate_jobs()
