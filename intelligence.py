import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class JobEvaluator:
    """
    Evaluates jobs using real AI (OpenAI GPT-4o) against the user's profile.
    """
    def __init__(self, profile):
        self.profile = profile
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def evaluate(self, job):
        """
        Uses LLM to perform a deep ATS-style match analysis.
        """
        if not os.getenv("OPENAI_API_KEY"):
            return self._fallback_evaluate(job)

        prompt = f"""
        Analyze the following job for a candidate profile.
        
        Candidate Profile:
        - Title: {self.profile.get('title')}
        - Skills: {', '.join(self.profile.get('skills', []))}
        - Preferences: {json.dumps(self.profile.get('preferences', {}))}
        
        Job Details:
        - Title: {job['title']}
        - Platform: {job['platform']}
        - Description: {job['description']}
        
        Respond ONLY with a JSON object:
        {{
            "score": <0-100 integer based on match probability>,
            "reasoning": "<short sentence explaining why>",
            "custom_keywords": ["found", "relevant", "keywords"]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert ATS (Applicant Tracking System) and career coach."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("score", 50), data.get("reasoning", "AI analysis complete.")
        except Exception as e:
            print(f"AI Evaluation Error: {e}")
            return self._fallback_evaluate(job)

    def _fallback_evaluate(self, job):
        """Simple keyword matching if AI fails/unavailable."""
        score = 40
        matches = []
        desc = job["description"].lower()
        skills = self.profile.get("skills", [])
        for skill in skills:
            if skill.lower() in desc:
                score += 10
                matches.append(skill)
        return min(score, 100), f"Keyword matches: {', '.join(matches[:3])}"

    def save_interesting_job(self, job, score, reasoning):
        """Saves jobs that passed the threshold and prevents duplicates."""
        filename = 'found_jobs.json'
        ledger_file = 'applied_ledger.json'
        
        # Load Applied Ledger
        applied = []
        if os.path.exists(ledger_file):
            with open(ledger_file, 'r') as f:
                try: 
                    applied = json.load(f)
                except: 
                    pass
        
        if job['id'] in applied:
            return False 

        # Load existing interesting jobs
        interesting_jobs = []
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    interesting_jobs = json.load(f)
                except:
                    pass
        
        if any(j['id'] == job['id'] or j.get('url') == job.get('url') for j in interesting_jobs):
            return True

        job['score'] = score
        job['reasoning'] = reasoning
        interesting_jobs.append(job)
        
        with open(filename, 'w') as f:
            json.dump(interesting_jobs, f, indent=2)
        return True
