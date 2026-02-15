import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ResearchTool:
    """
    Enables agents to perform deep research and data synthesis using the internet.
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def search_and_synthesize(self, query, objective="article"):
        """
        Searches the web and synthesizes findings into a structured document.
        """
        print(f"RESEARCH: Investigating '{query}' for {objective} creation...")
        
        # Simplified research: Using DuckDuckGo or similar (mocking search results for the demo)
        # In a real scenario, this would use a Search API or Playwright to sweep Google/Bing.
        
        # Simulated raw data points found for common 'Jack of All Trades' tasks
        raw_data = f"""
        - Current Market Trends: High demand for modular AI agents and specialized content.
        - Strategic Insights: Companies are moving away from monolithic platforms toward niche automation.
        - Emerging Tech: LLMs are becoming the backbone of autonomous creative workflows.
        - Pricing: Professional articles on tech are fetching $500-$1000 per piece.
        """

        prompt = f"""
        You are a Research Alchemist. Use the following raw findings to create a high-quality {objective}.
        
        Query: {query}
        Findings:
        {raw_data}
        
        Objective: Produce a comprehensive {objective} that is ready for publishing.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a world-class researcher and content strategist."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Research Synthesis Failed: {str(e)}"

researcher = ResearchTool()
