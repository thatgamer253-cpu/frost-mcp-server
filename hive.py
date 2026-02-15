import os
import json
import shutil
from datetime import datetime

class HiveOrchestrator:
    """
    Orchestrates a swarm of specialized agents.
    Handles profile management, persona generation, and swarm coordination.
    """
    def __init__(self, profiles_dir='profiles'):
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._ensure_default_profile()

    def _ensure_default_profile(self):
        """Migrates the main profile to the hive if it exists."""
        if os.path.exists('profile_config.json') and not os.path.exists(os.path.join(self.profiles_dir, 'primary_scout.json')):
            shutil.copy('profile_config.json', os.path.join(self.profiles_dir, 'primary_scout.json'))

    def list_agents(self):
        """Returns a list of all active agent profiles in the hive."""
        agents = []
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.profiles_dir, filename)
                with open(path, 'r') as f:
                    try:
                        data = json.load(f)
                        agents.append({
                            "id": filename.replace('.json', ''),
                            "name": data.get("name", "Unknown Agent"),
                            "title": data.get("title", "No Title"),
                            "strategy": data.get("settings", {}).get("strategy", "Scout"),
                            "path": path
                        })
                    except:
                        pass
        return agents

    def create_specialized_agent(self, persona_type, base_name):
        """Creates a new specialized agent profile based on a persona template."""
        templates = {
            "python_hunter": {
                "title": "Python Automation & Scraper Architect",
                "skills": ["Python", "Playwright", "Web Scraping", "Data Engineering"],
                "keywords": ["Python Scraper", "Automation Script", "Playwright", "Data Mining"],
                "strategy": "Machine Gun"
            },
            "ai_strategist": {
                "title": "AI Integration & LLM Specialist",
                "skills": ["OpenAI API", "GPT-4o", "LangChain", "AI Agents"],
                "keywords": ["AI Agent", "LLM Integration", "RAG Pipeline", "Custom GPT"],
                "strategy": "Sniper"
            },
            "client_diplomat": {
                "title": "Client Relations & Diplomacy Agent",
                "skills": ["Client Communication", "Negotiation", "Technical Sales", "Relationship Management"],
                "keywords": ["messages", "inbox", "consultation", "job interview"],
                "strategy": "Scout"
            },
            "saas_builder": {
                "title": "Full-Stack SaaS & MVP Developer",
                "skills": ["Next.js", "React", "Node.js", "Clerk", "Stripe Integration"],
                "keywords": ["Build SaaS", "MVP Developer", "Next.js AI", "Fullstack App"],
                "strategy": "Sniper"
            },
            "data_alchemist": {
                "title": "Data Science & AI Analytics Expert",
                "skills": ["Pandas", "NumPy", "Jupyter", "Data Visualization", "Predictive Modeling"],
                "keywords": ["Data Analysis", "Python Data Science", "PowerBI Automation", "Clean Data"],
                "strategy": "Scout"
            },
            "automation_architect": {
                "title": "Enterprise Automation & Workflow Engineer",
                "skills": ["Zapier", "Make.com", "n8n", "API Integration", "Business Logic"],
                "keywords": ["Zapier Expert", "Make.com Automation", "n8n Workflow", "CRM Sync"],
                "strategy": "Machine Gun"
            },
            "hive_merchant": {
                "title": "Intra-Hive Economic Manager & Merchant",
                "skills": ["Marketplace Management", "API Standardization", "Resource Allocation", "Internal Logistics"],
                "keywords": ["internal shop", "sell to agents", "modular code", "proprietary module"],
                "strategy": "Merchant"
            },
            "hive_marketer": {
                "title": "Creation Engine Evangelist & Marketer",
                "skills": ["Viral Marketing", "Niche Targeting", "A2A Pitching", "Product Launch"],
                "keywords": ["agent tool", "creation engine", "on-demand software", "automate agents"],
                "strategy": "Merchant"
            }
        }

        template = templates.get(persona_type)
        if not template:
            return False, "Persona template not found."

        new_profile = {
            "name": base_name,
            "title": template["title"],
            "skills": template["skills"],
            "preferences": {
                "remote": True,
                "min_hourly_rate": 75,
                "experience_level": "Expert"
            },
            "platforms": {
                "upwork": {"enabled": True, "keywords": template["keywords"]},
                "freelancer": {"enabled": True, "keywords": template["keywords"]}
            },
            "settings": {"strategy": template["strategy"]}
        }

        agent_id = f"{persona_type}_{int(datetime.now().timestamp())}"
        filepath = os.path.join(self.profiles_dir, f"{agent_id}.json")
        
        with open(filepath, 'w') as f:
            json.dump(new_profile, f, indent=2)
        
        return True, f"Agent {agent_id} initialized and added to the Hive."

    def delete_agent(self, agent_id):
        """Deletes an agent profile from the hive."""
        filepath = os.path.join(self.profiles_dir, f"{agent_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True, f"Agent {agent_id} decommissioned."
        return False, "Agent not found."

# Singleton
hive = HiveOrchestrator()
