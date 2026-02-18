import os
import time
import sys
import subprocess
from .llm_client import log, ask_llm

# Windows-specific: suppress console windows for background processes
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

class DeploymentManager:
    """
    Handles Continuous Agentic Deployment.
    - Manages Docker containers.
    - Monitors logs for errors.
    - Auto-patches configuration files (docker-compose.yml).
    """
    def __init__(self, project_path):
        self.project_path = project_path
    
    def deploy(self):
        log("DEPLOY", "🚀 Starting Continuous Agentic Deployment...")
        
        # 1. Check for docker-compose
        compose_file = os.path.join(self.project_path, "docker-compose.yml")
        if not os.path.exists(compose_file):
            log("DEPLOY", "  ⚠ No docker-compose.yml found. Skipping deployment.")
            return {"success": False, "reason": "No compose file"}

        # 2. Attempt Deploy
        log("DEPLOY", "  🐳 Running docker-compose up --build...")
        try:
            # Using subprocess to run docker-compose
            # Run in detached mode to not block, but for agentic deployment we might want to attach 
            # and monitor for a bit. 
            # Let's run detached and then tail logs.
            subprocess.run(["docker-compose", "up", "-d", "--build"], 
                           cwd=self.project_path, check=True, timeout=300,
                           creationflags=CREATE_NO_WINDOW)
            
            # 3. Monitor Health
            log("DEPLOY", "  Values checked. Monitoring logs for stability (10s)...")
            time.sleep(10)
            
            # Get logs
            logs = subprocess.run(["docker-compose", "logs", "--tail", "50"], 
                                  cwd=self.project_path, capture_output=True, text=True,
                                  creationflags=CREATE_NO_WINDOW).stdout
            
            if "error" in logs.lower() or "exception" in logs.lower() or "exited with code" in logs.lower():
                log("DEPLOY", "❌ Deployment Unstable! Analyzing logs...")
                self._heal_deployment(logs)
                return {"success": False, "reason": "Unstable deployment"}
            
            log("DEPLOY", "✅ Deployment Stable.")
            return {"success": True}
            
        except subprocess.CalledProcessError as e:
            log("DEPLOY", f"❌ Deployment Failed: {e}")
            return {"success": False, "reason": str(e)}
        except Exception as e:
            log("DEPLOY", f"❌ Deployment Error: {e}")
            return {"success": False, "reason": str(e)}

    def _heal_deployment(self, error_logs):
        """
        Agentic Self-Healing: Analyze logs and patch docker-compose or code.
        """
        log("DEPLOY", "🩹 Attempting Self-Healing...")
        # TODO: Implement LLM analysis of logs to suggest fixes
        # For now, just log the intent.
        pass
