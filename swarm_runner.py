import os
import time
import subprocess
from hive import hive
from guardian import guardian

class SwarmWatchdog:
    """
    Monitors the swarm and performs self-healing actions.
    """
    def __init__(self):
        self.processes = {} # agent_id -> process

    def deploy_swarm(self):
        guardian.log_activity("HIVE: Initializing Swarm Operations...")
        guardian.stabilize_environment()
        
        agents = hive.list_agents()
        for agent in agents:
            self.start_agent(agent)

    def start_agent(self, agent):
        guardian.log_activity(f"HIVE: Deploying Agent {agent['id']}...")
        env = os.environ.copy()
        env["FROST_PROFILE"] = agent['path']
        
        # Start in subprocess with explicit working directory
        p = subprocess.Popen(["python", "main.py"], env=env, stderr=subprocess.PIPE, text=True, cwd=os.getcwd())
        self.processes[agent['id']] = {"proc": p, "agent": agent}

    def heal_swarm(self):
        """Heartbeat loop that detects and repairs failures."""
        guardian.log_activity("WATCHDOG: Self-Healing heartbeat active.")
        while True:
            for agent_id, data in list(self.processes.items()):
                p = data["proc"]
                if p.poll() is not None:
                    # Agent Died!
                    error_output = p.stderr.read() if p.stderr else "Unknown Exit"
                    guardian.log_activity(f"SELF-HEAL: Agent {agent_id} CRASHED.", "CRITICAL")
                    
                    # AI Diagnosis
                    diagnosis = guardian.interpret_error_with_ai(error_output)
                    guardian.log_activity(f"AI DIAGNOSIS: {diagnosis}")
                    
                    # Restart
                    guardian.log_activity(f"SELF-HEAL: Restarting {agent_id}...")
                    self.start_agent(data["agent"])
            
            time.sleep(30)

if __name__ == "__main__":
    dog = SwarmWatchdog()
    dog.deploy_swarm()
    dog.heal_swarm()
