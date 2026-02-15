import os
import json

def pivot_profiles():
    profiles_dir = 'profiles'
    if not os.path.exists(profiles_dir):
        print("Profiles directory not found.")
        return

    for filename in os.listdir(profiles_dir):
        if filename.endswith('.json'):
            path = os.path.join(profiles_dir, filename)
            try:
                with open(path, 'r') as f:
                    profile = json.load(f)
                
                # Update Title
                base_title = profile.get('title', '').split('|')[0].strip()
                profile['title'] = f"{base_title} | Expert Creation Engine Merchant"
                
                # Update Strategy & Focus
                if 'settings' not in profile:
                    profile['settings'] = {}
                
                profile['settings']['strategy'] = "Merchant"
                profile['settings']['marketing_focus'] = "Creation Engine"
                
                # Broaden marketing keywords
                if 'platforms' in profile:
                    for platform in profile['platforms']:
                        profile['platforms'][platform]['keywords'] = [
                            "SaaS Builder", 
                            "AI Automation", 
                            "Direct Sales", 
                            "Marketplace Service",
                            "Creation Engine",
                            "Enterprise AI"
                        ]
                
                with open(path, 'w') as f:
                    json.dump(profile, f, indent=2)
                
                print(f"Updated profile: {filename}")
            except Exception as e:
                print(f"Failed to update {filename}: {e}")

if __name__ == "__main__":
    pivot_profiles()
