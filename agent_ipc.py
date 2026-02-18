#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  AGENT IPC — Inter-Process Communication Bus
  The nervous system connecting all Overlord agents.
═══════════════════════════════════════════════════════════════

File-based message queue using JSONL for append-only writes.
Each agent writes structured messages that the UI polls.
"""

import os
import json
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any

AGENT_SYSTEM_ROOT = os.path.dirname(os.path.abspath(__file__))
CHAT_LOG = os.path.join(AGENT_SYSTEM_ROOT, "memory", "agent_chat.jsonl")
_write_lock = threading.Lock()


class MessageType:
    FLAG = "FLAG"           # Sentinel/Auditor found an issue
    PROPOSE = "PROPOSE"     # Agent suggests an action
    RESOLVE = "RESOLVE"     # Agent completed an action
    STATUS = "STATUS"       # Heartbeat / progress update
    DREAM = "DREAM"         # Idle-time thought from Ghost Layer
    HUMAN = "HUMAN_OVERRIDE"  # User injected a command


# Agent identities for the Council
AGENTS = {
    "sentinel": {"name": "Sentinel", "icon": "🛡️", "color": "#ef4444"},
    "alchemist": {"name": "Alchemist", "icon": "⚗️", "color": "#a855f7"},
    "architect": {"name": "Architect", "icon": "📐", "color": "#3b82f6"},
    "fabricator": {"name": "Fabricator", "icon": "🔨", "color": "#f59e0b"},
    "merchant": {"name": "Merchant", "icon": "💰", "color": "#22c55e"},
    "heartbeat": {"name": "Heartbeat", "icon": "❤️", "color": "#ec4899"},
    "steward": {"name": "Steward", "icon": "🔧", "color": "#06b6d4"},
    "ghost": {"name": "Ghost", "icon": "👻", "color": "#8b5cf6"},
    "phantom": {"name": "Phantom", "icon": "👻", "color": "#a1a1aa"},
    "nirvash": {"name": "Nirvash", "icon": "💎", "color": "#e4e4e7"},
    "ambassador": {"name": "Ambassador", "icon": "🤝", "color": "#facc15"},
    "antigravity": {"name": "Antigravity", "icon": "⚛️", "color": "#00ffff"},
    "human": {"name": "Creator", "icon": "👤", "color": "#f4f4f5"},
}


def _ensure_dir():
    """Create memory/ directory if it doesn't exist."""
    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)


def post(sender: str, msg_type: str, content: str,
         target: str = "council", channel: str = "GENERAL",
         metadata: Optional[Dict] = None):
    """
    Post a message to the agent chat log.
    
    Args:
        sender:   Agent ID (e.g. "sentinel", "heartbeat")
        msg_type: One of MessageType constants
        content:  Human-readable message text
        target:   "council" (broadcast) or specific agent ID
        channel:  Channel name (SECURITY, CREATION, STATUS, GENERAL)
        metadata: Optional dict with extra structured data
    """
    _ensure_dir()
    
    entry = {
        "ts": datetime.now().isoformat(),
        "from": sender,
        "to": target,
        "type": msg_type,
        "channel": channel,
        "content": content,
        "meta": metadata or {},
    }
    
    with _write_lock:
        with open(CHAT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def broadcast(channel: str, sender: str, content: str,
              msg_type: str = "STATUS", **meta):
    """Broadcast a message to a named channel (convenience wrapper)."""
    post(sender, msg_type, content, target="council", channel=channel, metadata=meta)


def get_latest(channel: str = None, msg_type: str = None,
               n: int = 5) -> List[Dict[str, Any]]:
    """
    Get the latest messages, optionally filtered by channel or type.
    
    Args:
        channel: Filter by channel name (e.g. "SECURITY")
        msg_type: Filter by message type (e.g. "FLAG")
        n: Max messages to return
    """
    messages = read_recent(100)
    
    if channel:
        messages = [m for m in messages if m.get("channel") == channel]
    if msg_type:
        messages = [m for m in messages if m.get("type") == msg_type]
    
    if n <= 0: return []
    start = max(0, len(messages) - n)
    return messages[start:]


def read_recent(n: int = 50, after: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read the most recent N messages from the chat log.
    
    Args:
        n:     Max messages to return
        after: ISO timestamp — only return messages after this time
    
    Returns:
        List of message dicts, oldest first.
    """
    if not os.path.exists(CHAT_LOG):
        return []
    
    messages: List[Dict[str, Any]] = []
    try:
        with open(CHAT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if after and msg.get("ts", "") <= after:
                        continue
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    
    return messages[-n:]


def clear_log():
    """Wipe the chat log (for testing or fresh starts)."""
    _ensure_dir()
    with _write_lock:
        with open(CHAT_LOG, "w", encoding="utf-8") as f:
            f.write("")


def get_agent_info(agent_id: str) -> Dict[str, str]:
    """Get display info for an agent ID."""
    return AGENTS.get(agent_id, {"name": agent_id.title(), "icon": "🤖", "color": "#71717a"})


# ── Convenience Shortcuts ────────────────────────────────────

def flag(sender: str, content: str, **meta):
    """Shortcut: Post a FLAG message to SECURITY channel."""
    post(sender, MessageType.FLAG, content, channel="SECURITY", metadata=meta)

def propose(sender: str, content: str, **meta):
    """Shortcut: Post a PROPOSE message to CREATION channel."""
    post(sender, MessageType.PROPOSE, content, channel="CREATION", metadata=meta)

def resolve(sender: str, content: str, **meta):
    """Shortcut: Post a RESOLVE message to CREATION channel."""
    post(sender, MessageType.RESOLVE, content, channel="CREATION", metadata=meta)

def status(sender: str, content: str, **meta):
    """Shortcut: Post a STATUS message to STATUS channel."""
    post(sender, MessageType.STATUS, content, channel="STATUS", metadata=meta)

def dream(sender: str, content: str, **meta):
    """Shortcut: Post a DREAM message to GENERAL channel."""
    post(sender, MessageType.DREAM, content, channel="GENERAL", metadata=meta)
