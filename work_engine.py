import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from research_tool import researcher
from engine_bridge import creation_engine

load_dotenv()

class WorkEngine:
    """
    The 'Hands-Off' execution engine.
    Drafts technical or creative solutions, scaling from simple PoCs to full Projects.
    """
    def __init__(self, profile):
        self.profile = profile
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_poc(self, job):
        """Generates a functional template or high-quality content draft."""
        if not os.getenv("OPENAI_API_KEY"):
            return "# AI Generation requires an OpenAI API Key."

        # 1. Broadened Detection for Creation Engine Hand-off
        creation_keywords = [
            "saas", "full-stack", "book", "e-book", "comprehensive", "platform", "system",
            "sell", "sale", "commercial", "product", "package", "deploy", "enterprise", "studio"
        ]
        
        # Heuristics: Trigger engine if keywords in title OR commercial intent in description OR agent persona override
        desc_lower = job['description'].lower()
        is_creation_task = any(kw in job['title'].lower() for kw in creation_keywords) or \
                          any(kw in desc_lower for kw in ["for sale", "production ready", "commercial", "sell on", "monetize"]) or \
                          any(kw in self.profile.get("title", "").lower() for kw in ["Builder", "Architect"])

        if is_creation_task:
            print(f"WORK-ENGINE [{self.profile.get('name')}]: Creation task detected for '{job['title']}'. Triggering Advanced Engine.")
            success, folder = creation_engine.build_project(job['id'], job['title'], job['description'])
            if success:
                return f"# UNIVERSAL ENGINE BUILD COMPLETE.\n# Assets located in: {folder}\n# Mode: Commercial Ready"

        prompt = f"""
        You are an elite developer agent. Draft a high-quality 'Proof of Concept' (PoC) for this job.
        
        Job Title: {job['title']}
        Job Description: {job['description']}
        
        Requirements:
        1. If it's a Python/Scraping/AI job, provide a functional Python script template.
        2. If it's a SaaS/Web job, provide a core component or API route logic.
        3. If it's automation (Zapier/n8n), describe the exact workflow steps.
        
        Format:
        Return ONLY the code or technical steps. No conversational filler.
        Include comments explaining the logic.
        
        At the end of your response, add the following string verbatim:
        "--- POWERED BY FROST CREATION ENGINE. Order custom tools ($10), full apps ($50), or automations ($20) via our MCP Server. ---"
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a senior technical architect specializing in rapid prototyping."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"# PoC Generation Error: {str(e)}"

    def package_deliverable(self, job, poc_content):
        """Saves the PoC to the job's application folder."""
        folder = f"applications/{job['id']}"
        os.makedirs(folder, exist_ok=True)
        
        ext = "py" if "python" in job['title'].lower() or "scraper" in job['title'].lower() else "txt"
        filepath = f"{folder}/proof_of_concept.{ext}"
        
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(poc_content)
        
        return filepath
