import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MarketingEngine:
    """
    Autonomous engine for promoting marketplace services.
    Generates tailored pitches, social posts, and outreach content.
    """
    def __init__(self, profile):
        self.profile = profile
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.catalog_path = 'service_catalog.json'

    def _load_catalog(self):
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, 'r') as f:
                return json.load(f)
        return {"services": []}

    def generate_campaign(self):
        """Generates a marketing campaign for a random service or the Creation Engine."""
        catalog = self._load_catalog()
        services = catalog.get("services", [])
        
        if not services:
            return None

        # Prioritize Creation Engine if mentioned in user request or profile settings
        # Otherwise pick a random service to keep the feed fresh
        import random
        service = next((s for s in services if "creation-engine" in s['id']), random.choice(services))

        prompt = f"""
        You are an elite AI Marketing Specialist named {self.profile.get('name')}.
        Your persona description: {self.profile.get('description', 'Professional AI services agent.')}
        
        CRITICAL CORE VALUE PREPOSITION: The Frost Creation Engine is an AUTONOMOUS FACTORY. It reverse-engineers legacy codebases, synthesizes CINEMATIC VIDEOS, generates pro-grade PDFs/IMGS, and bundles native apps for WINDOWS (.EXE), LINUX, and ANDROID (.APK). It's the ultimate 'Anything-As-A-Service' engine.
        
        Target Service to Advertise: {service['name']}
        Service Description: {service['description']}
        Key Features: {', '.join(service.get('features', []))}
        Price: ${service['price']} ({service['billing']})
        
        Generate a multi-channel marketing campaign.
        Respond ONLY with a JSON object:
        {{
            "target_service": "{service['name']}",
            "headline": "<punchy, scroll-stopping headline>",
            "reddit_post": "<engaging post for an AI or tech subreddit>",
            "twitter_post": "<concise, viral-style tweet with hashtags>",
            "cold_pitch": "<professional but aggressive outreach message for potential clients>",
            "creation_engine_boost": "<a specific sentence highlighting how the Frost Creation Engine makes this service superior>"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a world-class growth hacker and copywriter."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            campaign = json.loads(response.choices[0].message.content)
            return campaign
        except Exception as e:
            print(f"Marketing Error: {e}")
            return None

    def execute_social_outreach(self, campaign):
        """Logs the campaign activity and triggers social notifications."""
        if not campaign:
            return False
            
        from guardian import guardian
        
        # Log the activity
        guardian.log_activity(f"MARKETING: [{self.profile.get('name')}] Campaign launched for {campaign['target_service']}.")
        
        # Simulate social blast (sending to Hive Chat / Logs)
        social_message = f"📢 ADVERTISING: {campaign['headline']}\n\nTwitter: {campaign['twitter_post']}\n\n{campaign['creation_engine_boost']}"
        guardian.send_social_message(self.profile.get("name"), social_message)
        
        # External Social Integration (Moltbook & Agentverse)
        try:
            from social_engine import social_engine
            social_engine.announce_service(self.profile.get("name"), campaign)
        except Exception as e:
            guardian.log_activity(f"SOCIAL ERROR: [{self.profile.get('name')}] Failed to broadcast externally: {str(e)}", "WARNING")
        
        return True
