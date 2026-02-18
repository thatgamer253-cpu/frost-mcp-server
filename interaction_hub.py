#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
  INTERACTION HUB — The Sovereign State Dialogue Bus
  Real-time agent-to-agent communication layer
═══════════════════════════════════════════════════════════

Agents post natural-language messages to the Hub. The GUI
subscribes for live updates, creating a conversational feed:

  Sentinel: "I've detected a memory leak in the Prism module."
  Alchemist: "Creating a Shadow Sandbox to test a new GC routine."
  Judge: "Gauntlet passed. Prism module upgraded. 0% downtime."
"""

import os
import json
import threading
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional


# ── Severity Levels ──────────────────────────────────────────
SEVERITY_INFO    = "INFO"      # Routine status update
SEVERITY_WARNING = "WARNING"   # Potential issue detected
SEVERITY_ACTION  = "ACTION"    # Agent is taking action
SEVERITY_VERDICT = "VERDICT"   # Final judgment / pass-fail

# ── Agent Avatars (for GUI rendering) ────────────────────────
AGENT_AVATARS = {
    "Architect":  "🏗️",
    "Fabricator": "⚙️",
    "Alchemist":  "🧪",
    "Sentinel":   "🛡️",
    "Judge":      "⚖️",
    "Merchant":   "💰",
    "Healer":     "🩹",
    "System":     "🔧",
}


class InteractionMessage:
    """A single message in the agent dialogue stream."""

    def __init__(self, agent_name: str, message: str,
                 severity: str = SEVERITY_INFO,
                 context: Optional[Dict[str, Any]] = None):
        self.agent_name = agent_name
        self.message = message
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now()
        self.avatar = AGENT_AVATARS.get(agent_name, "🤖")

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "avatar": self.avatar,
            "message": self.message,
            "severity": self.severity,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_display(self) -> str:
        """Human-readable format for terminal/log output."""
        ts = self.timestamp.strftime("%H:%M:%S")
        return f"[{ts}] {self.avatar} {self.agent_name}: {self.message}"

    def __repr__(self):
        return f"<InteractionMessage {self.agent_name}: {self.message[:40]}...>"


class InteractionHub:
    """Singleton event bus for agent-to-agent dialogue.

    Thread-safe. Agents call hub.post() to emit messages.
    The GUI calls hub.subscribe() to receive live updates.

    Usage:
        hub = InteractionHub.get_instance()
        hub.post("Sentinel", "Memory leak detected in Prism module.", "WARNING")
        hub.subscribe(lambda msg: print(msg.to_display()))
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._messages: List[InteractionMessage] = []
        self._subscribers: List[Callable[[InteractionMessage], None]] = []
        self._msg_lock = threading.Lock()
        self._log_path = os.path.join("logs", "interaction_hub.log")
        os.makedirs("logs", exist_ok=True)

    @classmethod
    def get_instance(cls) -> "InteractionHub":
        """Return the singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        with cls._lock:
            cls._instance = None

    def post(self, agent_name: str, message: str,
             severity: str = SEVERITY_INFO,
             context: Optional[Dict[str, Any]] = None):
        """Post a message to the Interaction Hub.

        Args:
            agent_name: Who is speaking (Sentinel, Alchemist, Judge, etc.)
            message: Natural-language dialogue
            severity: INFO, WARNING, ACTION, VERDICT
            context: Optional metadata (file paths, metrics, etc.)
        """
        msg = InteractionMessage(agent_name, message, severity, context)

        with self._msg_lock:
            self._messages.append(msg)

        # Persist to log file
        self._write_log(msg)

        # Notify all subscribers (GUI, etc.)
        for callback in self._subscribers:
            try:
                callback(msg)
            except Exception:
                pass  # Never let a subscriber crash the pipeline

    def subscribe(self, callback: Callable[[InteractionMessage], None]):
        """Register a callback to receive live messages.

        Args:
            callback: Function that accepts an InteractionMessage.
                      Will be called from the posting thread.
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Remove a subscriber callback."""
        self._subscribers = [s for s in self._subscribers if s != callback]

    def get_history(self, limit: int = 50) -> List[InteractionMessage]:
        """Get the most recent messages."""
        with self._msg_lock:
            return list(self._messages[-limit:])

    def get_history_for_agent(self, agent_name: str,
                               limit: int = 20) -> List[InteractionMessage]:
        """Get messages from a specific agent."""
        with self._msg_lock:
            filtered = [m for m in self._messages if m.agent_name == agent_name]
            return filtered[-limit:]

    def clear(self):
        """Clear the message history (new build session)."""
        with self._msg_lock:
            self._messages.clear()

    def _write_log(self, msg: InteractionMessage):
        """Append message to the persistent log file."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(msg.to_display() + "\n")
        except Exception:
            pass

    def export_session(self) -> List[dict]:
        """Export the full session as JSON-serializable dicts."""
        with self._msg_lock:
            return [m.to_dict() for m in self._messages]


# ── Module-level convenience ─────────────────────────────────

def hub() -> InteractionHub:
    """Shortcut to get the singleton hub instance."""
    return InteractionHub.get_instance()
