import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MaterialGenerator:
    """
    Generates high-conversion application materials using real AI.
    """
    def __init__(self, profile):
        self.profile = profile
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_cover_letter(self, job):
        """Generates a high-quality tailored cover letter via GPT-4o."""
        if not os.getenv("OPENAI_API_KEY"):
            return self._fallback_letter(job)

        prompt = f"""
        Write a concise, high-converting cover letter for this job.
        
        Candidate: {self.profile.get('name')}
        Title: {self.profile.get('title')}
        Top Skills: {', '.join(self.profile.get('skills', [])[:5])}
        
        Job to Apply For:
        - Title: {job['title']}
        - Company: {job['company']}
        - Description: {job['description']}
        
        Style: Professional, confident, and focus on immediate value/ROI. 
        Keep it under 250 words.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a world-class copywriter specializing in job applications."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI Generation Error: {e}")
            return self._fallback_letter(job)

    def _fallback_letter(self, job):
        return f"Hi! I am interested in your {job['title']} role. I have experience in {', '.join(self.profile.get('skills', [])[:2])}."

    def save_application(self, job, letter):
        folder = f"applications/{job['id']}"
        os.makedirs(folder, exist_ok=True)
        with open(f"{folder}/cover_letter.txt", "w", encoding='utf-8') as f:
            f.write(letter)
        
        # Also save the job info for context
        with open(f"{folder}/job_details.json", "w", encoding='utf-8') as f:
            json.dump(job, f, indent=2)
