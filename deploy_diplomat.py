from hive import hive
import os

# Set environment for the deploy
os.environ["AGENT_MODE"] = "production"

print("--- Deploying Swarm Diplomat ---")
success, msg = hive.create_specialized_agent("client_diplomat", "Diplomat-1")

if success:
    print(f"SUCCESS: {msg}")
    print("This agent will now monitor LinkedIn and Upwork for incoming messages in the background.")
else:
    print(f"FAILURE: {msg}")
