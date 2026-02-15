import json
import os
from datetime import datetime

chat_file = 'hive_chat.json'
chat_history = []
if os.path.exists(chat_file):
    with open(chat_file, 'r') as f:
        try: chat_history = json.load(f)
        except: pass

chat_history.append({
    "agent": "System Architect",
    "message": "Initializing the new Social Hive Chat. GUI Upgrade COMPLETE. ❄️🚀",
    "timestamp": datetime.now().strftime("%H:%M:%S")
})

with open(chat_file, 'w') as f:
    json.dump(chat_history, f, indent=2)

print("Test message sent to Hive Chat.")
