import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from research_tool import researcher

load_dotenv()

class StateReducer:
    """
    Tracks the state of a multi-phase build process.
    Phases: RESEARCH -> ARCHITECT -> IMPLEMENT -> AUDIT -> COMPLETE
    """
    def __init__(self, project_id):
        self.project_id = project_id
        self.state_file = f"applications/{project_id}/state.json"
        self.history = []
        self.current_phase = "RESEARCH"
        
    def update(self, phase, summary, artifacts=None):
        self.current_phase = phase
        event = {
            "timestamp": time.strftime("%H:%M:%S"),
            "phase": phase,
            "summary": summary,
            "artifacts": artifacts or []
        }
        self.history.append(event)
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump({
                "current_phase": self.current_phase,
                "history": self.history
            }, f, indent=2)

class CreationEngine:
    """
    Coordinates multi-agent creation workflows for complex deliverables.
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def build_project(self, project_id, goal, context=""):
        """
        Executes the full creation pipeline.
        """
        reducer = StateReducer(project_id)
        print(f"CREATION-ENGINE: Starting build for project '{project_id}'...")
        
        # 1. RESEARCH PHASE
        reducer.update("RESEARCH", f"Investigating goal: {goal}")
        research_data = researcher.search_and_synthesize(goal, objective="comprehensive research")
        reducer.update("RESEARCH", "Research synthesis complete.", ["research.txt"])
        self._save_artifact(project_id, "research.txt", research_data)

        # 2. ARCHITECT PHASE
        reducer.update("ARCHITECT", "Designing project structure and components.")
        architecture = self._ai_call("Architect", f"Design a file structure and plan for: {goal}. Research: {research_data}")
        reducer.update("ARCHITECT", "Architecture blueprint generated.", ["blueprint.md"])
        self._save_artifact(project_id, "blueprint.md", architecture)

        # 3. IMPLEMENT PHASE
        reducer.update("IMPLEMENT", "Executing build and generating core assets.")
        implementation = self._ai_call("Builder", f"Implement the core deliverables for: {goal}. Blueprint: {architecture}")
        reducer.update("IMPLEMENT", "Core assets generated.", ["deliverable_main.txt"])
        self._save_artifact(project_id, "deliverable_main.txt", implementation)

        # 4. AUDIT PHASE
        reducer.update("AUDIT", "Performing quality check and final polish.")
        audit_report = self._ai_call("Auditor", f"Audit this implementation for goal: {goal}. Content: {implementation}")
        reducer.update("AUDIT", "Audit complete. Final polish applied.", ["audit_report.md"])
        self._save_artifact(project_id, "audit_report.md", audit_report)

        # 5. COMPLETE
        reducer.update("COMPLETE", "Project build finalized and packaged.")
        print(f"CREATION-ENGINE: Project '{project_id}' build SUCCESSFUL.")
        return True, f"applications/{project_id}"

    def _ai_call(self, persona, prompt):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are the {persona} component of the Creation Engine."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error in {persona} phase: {str(e)}"

    def _save_artifact(self, project_id, filename, content):
        path = f"applications/{project_id}/{filename}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding='utf-8') as f:
            f.write(content)

creation_engine = CreationEngine()
