#!/usr/bin/env python3
import time
import sys
import os
import threading

# Ensure local imports work
sys.path.append(os.getcwd())

from council_agents import boot_council, stop_council

def main():
    print("🛸 LAUNCHING THE SOVEREIGN FLEET...")
    print("Engaging Ambassador, Healer, Alchemist, and the Autonomous Engine.")
    
    # Boot the council (this starts all agents as daemon threads)
    agents = boot_council()
    
    print("\n✅ FLEET ACTIVE. AGENTS ARE ON THEIR OWN.")
    print("💰 Monitoring Global Market for commercial engagements...")
    print("🧪 Healer set to Sandbox/Peer-Review mode.")
    print("⚗️ Alchemist watching for system stabilization opportunities.")
    
    try:
        # Keep the main thread alive while agents work in background
        while True:
            # Check revenue events every 30 seconds to show update in console
            if os.path.exists("revenue_events.log"):
                with open("revenue_events.log", "r") as f:
                    lines = f.readlines()
                    if lines:
                        last = lines[-1]
                        print(f"📊 [Update] Last Revenue Event: {last.strip()}")
            
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 SHUTTING DOWN FLEET...")
        stop_council()
        print("Fleet Grounded.")

if __name__ == "__main__":
    main()
