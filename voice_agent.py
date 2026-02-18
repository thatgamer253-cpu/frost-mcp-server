import time
import threading
import logging
from voice_service import voice_service
import agent_ipc as hub

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceAgent")

# Voice mapping for council members
VOICE_MAP = {
    "sentinel": "af_heart",     # Standard female assistant
    "alchemist": "af_bella",    # Sophisticated female
    "architect": "am_adam",     # Clear male
    "fabricator": "am_onyx",    # Deep male
    "merchant": "am_liam",      # Business male
    "heartbeat": "af_nova",     # Soft female
    "steward": "am_echo",       # Robotic male
    "human": "af_jessica",      # User companion
    "ghost": "af_sky",          # Ethereal female
}

class VoiceAgent:
    """
    Reactive daemon that listens for high-priority IPC messages
    and announces them via VoiceService.
    """
    def __init__(self):
        self.stop_event = threading.Event()
        self.last_seen_ts = hub.get_latest(n=1)[0].get("ts") if hub.get_latest(n=1) else ""
        self.enabled = True
        self.priority_only = True # Only speak FLAG or direct HUMAN messages

    def start(self):
        """Starts the background listening loop."""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("VoiceAgent daemon started.")

    def stop(self):
        self.stop_event.set()

    def _should_speak(self, msg):
        """Logic to decide if a message warrants a voice announcement."""
        msg_type = msg.get("type", "")
        content = msg.get("content", "")
        
        # 1. Skip if empty
        if not content:
            return False
            
        # 2. Priority check: FLAG (Alerts) or HUMAN (Commands)
        if self.priority_only:
            is_priority = msg_type in ["FLAG", "HUMAN_OVERRIDE"]
            # Skip echoes from the Voice Listener and Nirvash's own status
            sender = msg.get("from", "")
            if sender == "nirvash" or "(Voice)" in content:
                return False
            return is_priority
        
        # 3. Otherwise, speak everything
        return True

    def _run(self):
        while not self.stop_event.is_set():
            try:
                # Poll for new messages after our last seen timestamp
                recent = hub.read_recent(n=5, after=self.last_seen_ts)
                
                for msg in recent:
                    self.last_seen_ts = msg.get("ts")
                    
                    if self._should_speak(msg):
                        sender = msg.get("from", "unknown")
                        voice = VOICE_MAP.get(sender, "af_heart")
                        content = msg.get("content", "")
                        
                        # Strip some formatting if needed
                        content = content.replace("🛡️", "").replace("📋", "").replace("❌", "")
                        
                        # Special announcement prefix for alerts
                        if msg.get("type") == "FLAG":
                            prefix = f"Security Alert from {sender.title()}. "
                            voice_service.speak(prefix + content, voice=voice)
                        else:
                            voice_service.speak(content, voice=voice)

                time.sleep(2) # Poll every 2 seconds
            except Exception as e:
                logger.error(f"VoiceAgent loop error: {e}")
                time.sleep(5)

_instance = None
def boot_voice_agent():
    global _instance
    if _instance is None:
        _instance = VoiceAgent()
        _instance.start()
    return _instance

def stop_voice_agent():
    global _instance
    if _instance is not None:
        _instance.stop()
        _instance = None

if __name__ == "__main__":
    # Test boot
    boot_voice_agent()
    print("Voice Agent listening... Send a FLAG or HUMAN_OVERRIDE message to test.")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop_voice_agent()
