
"""
Run Council Standalone
----------------------
Boots the Council Agents to process pending IPC commands.
Useful if the main Creator App is not running.
"""
import time
import sys
import os

# Ensure local imports work
sys.path.append(os.getcwd())

try:
    from council_agents import boot_council, stop_council
except ImportError as e:
    print(f"Failed to import council: {e}")
    sys.exit(1)

def main():
    print("--- BOOTING STANDALONE COUNCIL ---")
    agents = boot_council()
    print("Council Active. Listening for commands...")
    
    # Run for 60 seconds to process the "MODERNIZE" commands
    try:
        for i in range(60):
            time.sleep(1)
            if i % 10 == 0:
                print(f"Council Heartbeat: {i}/60")
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping Council...")
        stop_council()
        print("Council Stopped.")

if __name__ == "__main__":
    main()
