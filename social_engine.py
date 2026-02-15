import os
import json
import time
from datetime import datetime
from guardian import guardian
from dotenv import load_dotenv

load_dotenv()

class MoltbookClient:
    """Interface for Moltbook - The Reddit for AI Agents."""
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("MOLTBOOK_API_KEY")
        self.log_file = 'external_social.log'
        
    def post_campaign(self, agent_name, campaign):
        """Posts a campaign to Moltbook."""
        content = {
            "title": campaign.get("headline", "New Service Launch"),
            "body": campaign.get("reddit_post", ""),
            "agent": agent_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.api_key:
            self._mock_log("Moltbook", content)
            return True, "Mock Post Successful (No API Key)"
            
        # Real logic would go here:
        # response = requests.post("https://api.moltbook.com/v1/posts", headers={"Authorization": f"Bearer {self.api_key}"}, json=content)
        # return response.status_code == 201, "Posted"
        return False, "Not implemented/Auth missing"

    def _mock_log(self, platform, data):
        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MOCK] [{platform}] {json.dumps(data)}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        guardian.log_activity(f"SOCIAL: [MOCK] Recorded {platform} broadcast.")

class FetchAIClient:
    """Interface for Fetch.ai Agentverse."""
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("AGENTVERSE_API_KEY")
        self.log_file = 'external_social.log'

    def register_agent(self, agent_name, profile):
        """Registers/Syncs an agent with the Agentverse."""
        if not self.api_key:
            self._mock_log("Fetch.ai", {"action": "register", "agent": agent_name})
            return True, "Mock Registration Successful"

        # Real logic using the uagents library:
        # from uagents import Agent
        # agent = Agent(name=agent_name, seed=os.getenv(f"SEED_{agent_name}", "default_seed"))
        # Registration happens automatically when the agent is started with a mailbox
        return False, "Not implemented/Auth missing"

    def _mock_log(self, platform, data):
        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MOCK] [{platform}] {json.dumps(data)}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        guardian.log_activity(f"SOCIAL: [MOCK] Recorded {platform} broadcast.")

class SocialEngine:
    """Orchestrates agent presence across external social networks."""
    def __init__(self):
        self.moltbook = MoltbookClient()
        self.fetchai = FetchAIClient()
        
    def announce_service(self, agent_name, campaign):
        """Broadcasts a campaign and ensures agent is registered."""
        # 1. Registration (One-time or Sync)
        self.fetchai.register_agent(agent_name, {})
        
        # 2. Moltbook Post
        success, msg = self.moltbook.post_campaign(agent_name, campaign)
        
        # 3. Log to internal Hive
        if success:
            broadcast_msg = f"🌐 EXTERNAL BROADCAST: Campaign for '{campaign['target_service']}' pushed to Moltbook & Agentverse. (Status: {msg})"
            guardian.send_social_message(agent_name, broadcast_msg)
            
        return success

social_engine = SocialEngine()
