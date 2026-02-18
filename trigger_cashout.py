import os
import sys

# Add Creator root to path for imports
creator_root = r"C:\Users\thatg\Desktop\Creator"
if creator_root not in sys.path:
    sys.path.append(creator_root)

try:
    import agent_ipc as hub
    from agent_ipc import MessageType
    
    # OVERRIDE the log path to the real one
    hub.CHAT_LOG = os.path.join(creator_root, "memory", "agent_chat.jsonl")
    
    print(f"Broadcasting cash-out command to Ambassador at {hub.CHAT_LOG}...")
    hub.post("human", MessageType.PROPOSE, "cash out now", target="ambassador")
    print("Command dispatched successfully.")
    
    # Check if we can see the response
    import time
    time.sleep(2)
    recent = hub.read_recent(5)
    print("\nRecent Council Activity:")
    for msg in recent:
        print(f"[{msg.get('from')}] -> [{msg.get('to')}]: {msg.get('content')}")

except Exception as e:
    print(f"Error: {e}")
