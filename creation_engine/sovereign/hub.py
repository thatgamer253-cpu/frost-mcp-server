"""
Sovereign Module — Agent Hub (Message Broker)
Lightweight in-process Pub/Sub system for agent cross-talk.

Design: Thread-safe deque-based channels with ring buffers.
No external dependencies (no Redis, no MQTT).

Usage:
    from creation_engine.sovereign.hub import hub

    hub.broadcast("SECURITY", "Sentinel", "Detected exposed API key in config.py")
    latest = hub.get_latest("SECURITY")
"""

import json
import time
import os
import threading
from collections import deque
from datetime import datetime
from pathlib import Path


# ── Channel Definitions ─────────────────────────────────────

class Channel:
    SECURITY  = "SECURITY"   # Sentinel / Stealth
    CREATION  = "CREATION"   # Architect / Engineer / Alchemist
    SYSTEM    = "SYSTEM"     # Core Engine lifecycle events
    BOUNTY    = "BOUNTY"     # Scout Agent / Revenue updates
    HEALING   = "HEALING"    # Medic / Healer reports
    COUNCIL   = "COUNCIL"    # Human ↔ Agent conversation
    DREAM     = "DREAM"      # Heartbeat dream cycle outputs

    ALL = [SECURITY, CREATION, SYSTEM, BOUNTY, HEALING, COUNCIL, DREAM]


# ── Message Schema ───────────────────────────────────────────

class HubMessage:
    """Standardized message packet for inter-agent communication."""

    def __init__(self, sender: str, content: str, msg_type: str = "STATUS",
                 channel: str = Channel.SYSTEM, priority: int = 0,
                 metadata: dict = None):
        self.timestamp = datetime.now().isoformat()
        self.ts = self.timestamp  # Alias for GUI compatibility
        self.sender = sender
        self.content = content
        self.msg_type = msg_type   # FLAG, PROPOSE, RESOLVE, STATUS, DREAM, HUMAN_OVERRIDE
        self.channel = channel
        self.priority = priority   # 0=normal, 1=important, 2=critical
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "ts": self.timestamp,
            "from": self.sender,
            "content": self.content,
            "type": self.msg_type,
            "channel": self.channel,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HubMessage":
        msg = cls(
            sender=data.get("from", "unknown"),
            content=data.get("content", ""),
            msg_type=data.get("type", "STATUS"),
            channel=data.get("channel", Channel.SYSTEM),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )
        msg.timestamp = data.get("ts", msg.timestamp)
        msg.ts = msg.timestamp
        return msg


# ── The Hub ──────────────────────────────────────────────────

class AgentHub:
    """
    In-process message broker for agent cross-talk.

    Thread-safe. Each channel is a ring buffer (deque) holding
    the last N messages. Subscribers are notified synchronously
    on the publishing thread.
    """

    def __init__(self, buffer_size: int = 100, persist_path: str = None):
        self._lock = threading.Lock()
        self._buffer_size = buffer_size
        self._persist_path = persist_path or os.path.join("logs", "hub_transcript.jsonl")

        # Initialize all channels
        self.channels = {}
        for ch in Channel.ALL:
            self.channels[ch] = deque(maxlen=buffer_size)

        # Subscriber registry: channel -> [callback(HubMessage)]
        self._subscribers = {ch: [] for ch in Channel.ALL}

        # Stats
        self._total_messages = 0

    # ── Publishing ───────────────────────────────────────────

    def broadcast(self, channel: str, sender: str, content: str,
                  msg_type: str = "STATUS", priority: int = 0,
                  metadata: dict = None):
        """
        Post a message to a channel. All subscribers are notified.
        This is the primary API matching the user's blueprint.
        """
        if channel not in self.channels:
            # Auto-create channel if it doesn't exist
            with self._lock:
                self.channels[channel] = deque(maxlen=self._buffer_size)
                self._subscribers[channel] = []

        msg = HubMessage(
            sender=sender,
            content=content,
            msg_type=msg_type,
            channel=channel,
            priority=priority,
            metadata=metadata,
        )

        with self._lock:
            self.channels[channel].append(msg)
            self._total_messages += 1

        # Persist to disk (append-only log)
        self._persist(msg)

        # Notify subscribers (outside lock to avoid deadlocks)
        for callback in self._subscribers.get(channel, []):
            try:
                callback(msg)
            except Exception as e:
                print(f"[HUB] Subscriber error on {channel}: {e}")

        # Console echo
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [HUB/{channel}] {sender}: {content[:80]}")

        return msg

    # ── Subscribing ──────────────────────────────────────────

    def subscribe(self, channel: str, callback):
        """Register a callback(HubMessage) for a channel."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback):
        """Remove a subscriber."""
        if channel in self._subscribers:
            self._subscribers[channel] = [
                cb for cb in self._subscribers[channel] if cb != callback
            ]

    # ── Reading ──────────────────────────────────────────────

    def get_latest(self, channel: str):
        """Get the most recent message from a channel. Returns dict or None."""
        if channel in self.channels and self.channels[channel]:
            return self.channels[channel][-1].to_dict()
        return None

    def get_log(self, channel: str = None, limit: int = 20,
                after: str = None) -> list:
        """
        Get recent messages as dicts.
        If channel is None, returns from ALL channels merged and sorted.
        If after (ISO timestamp) is provided, only returns messages after that time.
        """
        with self._lock:
            if channel:
                messages = list(self.channels.get(channel, []))
            else:
                messages = []
                for ch_msgs in self.channels.values():
                    messages.extend(ch_msgs)
                messages.sort(key=lambda m: m.timestamp)

        # Filter by timestamp
        if after:
            messages = [m for m in messages if m.timestamp > after]

        # Limit
        messages = messages[-limit:]

        return [m.to_dict() for m in messages]

    # ── Persistence ──────────────────────────────────────────

    def _persist(self, msg: HubMessage):
        """Append message to both Hub transcript and agent_ipc JSONL."""
        # Hub's own log
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict(), default=str) + "\n")
        except Exception:
            pass

        # Also write through agent_ipc so the Council panel picks it up
        try:
            ipc_log = os.path.join("memory", "agent_chat.jsonl")
            os.makedirs(os.path.dirname(ipc_log), exist_ok=True)
            entry = {
                "ts": msg.timestamp,
                "from": msg.sender,
                "to": "council",
                "type": msg.msg_type,
                "content": msg.content,
                "meta": msg.metadata,
            }
            with open(ipc_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def load_transcript(self, limit: int = 100) -> list:
        """Load recent messages from the persisted transcript."""
        if not os.path.exists(self._persist_path):
            return []
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]
        except Exception:
            return []

    # ── Diagnostics ──────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return hub statistics for the morning brief."""
        stats = {
            "total_messages": self._total_messages,
            "channels": {},
        }
        for ch_name, ch_deque in self.channels.items():
            stats["channels"][ch_name] = {
                "count": len(ch_deque),
                "subscribers": len(self._subscribers.get(ch_name, [])),
                "latest": ch_deque[-1].to_dict() if ch_deque else None,
            }
        return stats

    def get_digest(self) -> str:
        """Human-readable summary for the morning brief."""
        lines = [f"📡 **Hub Activity**: {self._total_messages} total messages"]
        for ch_name, ch_deque in self.channels.items():
            if ch_deque:
                latest = ch_deque[-1]
                lines.append(
                    f"  - **{ch_name}** ({len(ch_deque)} msgs) "
                    f"→ Latest: {latest.sender}: {latest.content[:60]}"
                )
        return "\n".join(lines)


# ── Global Singleton ─────────────────────────────────────────
# All agents import this single instance.

hub = AgentHub()
