import os
import json
import subprocess
from openai import OpenAI

# Initialize Client
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

class GlobalAgent:
    def __init__(self, project_name):
        self.project_name = project_name
        self.model = "gpt-4o"
        os.makedirs(project_name, exist_ok=True)

    def _ask_llm(self, system_role, user_content):
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip().strip('`').replace('python', '').replace('json', '').replace('dockerfile', '')

    def build_universal_package(self, user_prompt):
        # 1. ARCHITECTURE & DEPENDENCIES
        print(f"[*] Architecting: {user_prompt}")
        arch_system = "Senior Architect. Output ONLY JSON. Schema: {'files': [{'path': '...', 'task': '...'}], 'dependencies': ['...'], 'run_command': 'python main.py'}"
        plan = json.loads(self._ask_llm(arch_system, user_prompt))
        
        with open(os.path.join(self.project_name, "requirements.txt"), "w") as f:
            f.write("\n".join(plan.get('dependencies', [])))

        # 2. ENGINEERING & DEBUGGING
        file_list = [f['path'] for f in plan['files']]
        for file_spec in plan['files']:
            print(f"[*] Engineering: {file_spec['path']}")
            eng_system = f"Lead Dev. Context: {file_list}. Output ONLY raw code."
            code = self._ask_llm(eng_system, f"Write {file_spec['path']}: {file_spec['task']}")
            with open(os.path.join(self.project_name, file_spec['path']), "w") as f:
                f.write(code)

        # 3. DOCKERIZATION (The Cloud Module)
        print("[*] Generating Docker configuration...")
        docker_system = "DevOps Engineer. Create a Dockerfile for this Python project. Use a slim base image. Output ONLY the Dockerfile content."
        dockerfile_content = self._ask_llm(docker_system, f"Project Plan: {plan}")
        with open(os.path.join(self.project_name, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

        # 4. FINAL DOCUMENTATION
        doc_system = "Technical Writer. Create a README.md including Docker build/run instructions. Output ONLY markdown."
        readme = self._ask_llm(doc_system, f"Goal: {user_prompt}\nFiles: {file_list}")
        with open(os.path.join(self.project_name, "README.md"), "w") as f:
            f.write(readme)

        print(f"\n[COMPLETE] Your portable app is ready in ./{self.project_name}")
        print("[>] To run with Docker: 'docker build -t my-app . && docker run my-app'")

if __name__ == "__main__":
    agent = GlobalAgent("CloudReadyApp")
    agent.build_universal_package("A web scraper that takes a URL and returns all headers as a JSON file.")
