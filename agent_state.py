#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  AGENT STATE — Global Shared Memory for the Overlord System
═══════════════════════════════════════════════════════════════

The State is the shared whiteboard that flows between all specialist
agents in the multi-agent graph. Each node reads from and writes to
this typed structure, ensuring every specialist sees the same world.

Persistence Layer:
  - Mem0 with Qdrant (vector) + Neo4j (graph) for long-term memory
  - Graceful degrade to in-memory dict when stores are unavailable

Usage:
    from agent_state import AgentState, memory, create_initial_state

    state = create_initial_state("MyProject", "Build a 3D engine")
    # Pass state through the agent graph...
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

# ── Logging ──────────────────────────────────────────────────
try:
    from creation_engine.llm_client import log
except ImportError:
    def log(tag: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}] {msg}")


# ═══════════════════════════════════════════════════════════════
#  AGENT STATE — The Shared Whiteboard
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """The shared whiteboard for the Overlord Agents.

    Every specialist node in the graph reads from and writes to
    this structure. Fields are grouped by responsibility:

      Identity:    project_name, user_id, prompt
      Blueprint:   blueprint (architecture plan from the Architect)
      Code:        code (filename -> source), final_exe_path
      Assets:      assets (list of generated media/3D paths)
      Security:    audit_report (from SecurityGuardian)
      Spatial:     spatial_manifest (from SpatialArchitect)
      Telemetry:   build_events (timestamped log), status
      Memory:      memory_context (retrieved from Mem0)
    """

    # ── Identity ─────────────────────────────────────────────
    project_name: str
    user_id: str
    prompt: str

    # ── Blueprint (Architect output) ─────────────────────────
    blueprint: Dict[str, Any]

    # ── Code (Engineer output) ───────────────────────────────
    code: Dict[str, str]             # filename -> source code
    final_exe_path: str              # path to bundled executable

    # ── Assets (Media Director + Spatial Architect output) ────
    assets: List[str]                # paths to generated media
    spatial_manifest: Dict[str, Any] # glTF world manifest

    # ── Security (SecurityGuardian output) ───────────────────
    audit_report: Dict[str, Any]

    # ── Telemetry ────────────────────────────────────────────
    build_events: List[Dict[str, Any]]
    status: str                      # "init" | "building" | "auditing" | "done" | "failed"

    # ── Memory (Mem0 context) ────────────────────────────────
    memory_context: List[Dict[str, Any]]


# ═══════════════════════════════════════════════════════════════
#  STATE FACTORY
# ═══════════════════════════════════════════════════════════════

def create_initial_state(
    project_name: str,
    prompt: str,
    user_id: str = "Donovan",
) -> AgentState:
    """Create a fresh AgentState with defaults for a new build.

    Args:
        project_name: Name of the project being built.
        prompt: The user's build directive.
        user_id: Owner identifier.

    Returns:
        A fully initialized AgentState dict.
    """
    return AgentState(
        project_name=project_name,
        user_id=user_id,
        prompt=prompt,
        blueprint={},
        code={},
        final_exe_path="",
        assets=[],
        spatial_manifest={},
        audit_report={},
        build_events=[{
            "timestamp": datetime.now().isoformat(),
            "node": "init",
            "status": "created",
            "data": {"project": project_name, "prompt": prompt[:100]},
        }],
        status="init",
        memory_context=[],
    )


def push_event(state: AgentState, node: str, status: str, data: Any = None) -> AgentState:
    """Append a build event to the state's telemetry log.

    This is the canonical way for any node to record what it did.
    """
    state["build_events"].append({
        "timestamp": datetime.now().isoformat(),
        "node": node,
        "status": status,
        "data": data,
    })
    return state


def save_state_snapshot(state: AgentState, output_dir: str = "") -> str:
    """Persist the current state to disk as JSON.

    Args:
        state: The current agent state.
        output_dir: Directory to save to (defaults to output/<project_name>).

    Returns:
        Path to the saved snapshot file.
    """
    if not output_dir:
        output_dir = os.path.join("output", state["project_name"])
    os.makedirs(output_dir, exist_ok=True)

    snapshot_path = os.path.join(output_dir, "state_snapshot.json")
    with open(snapshot_path, "w") as f:
        json.dump(dict(state), f, indent=2, default=str)

    return snapshot_path


# ═══════════════════════════════════════════════════════════════
#  MEM0 PERSISTENCE LAYER
# ═══════════════════════════════════════════════════════════════

_memory = None  # Lazy singleton


def _init_memory():
    """Initialize Mem0 with Qdrant vector + Neo4j graph store.

    Falls back to in-memory mode if either store is unavailable.
    """
    global _memory

    # Already initialized
    if _memory is not None:
        return _memory

    try:
        from mem0 import Memory

        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")

        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": qdrant_host,
                    "port": qdrant_port,
                },
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": neo4j_url,
                    "username": neo4j_user,
                    "password": neo4j_pass,
                },
            },
        }

        _memory = Memory.from_config(config)
        log("MEMORY", "  Mem0 initialized (Qdrant + Neo4j)")
        return _memory

    except ImportError:
        log("MEMORY", "  mem0 not installed — using in-memory fallback")
        return None
    except Exception as e:
        log("MEMORY", f"  Mem0 init failed ({e}) — using in-memory fallback")
        return None


def get_memory():
    """Get the Mem0 memory instance (lazy init)."""
    return _init_memory()


def remember(content: str, user_id: str = "Donovan",
             metadata: Optional[Dict] = None) -> bool:
    """Store a memory in the persistent vector+graph store.

    Args:
        content: Text content to remember.
        user_id: User the memory belongs to.
        metadata: Optional metadata dict.

    Returns:
        True if stored successfully, False otherwise.
    """
    mem = get_memory()
    if mem is None:
        log("MEMORY", f"  [fallback] Would remember: {content[:60]}...")
        return False

    try:
        mem.add(content, user_id=user_id, metadata=metadata or {})
        log("MEMORY", f"  Stored: {content[:60]}...")
        return True
    except Exception as e:
        log("MEMORY", f"  Store failed: {e}")
        return False


def recall(query: str, user_id: str = "Donovan",
           limit: int = 5) -> List[Dict[str, Any]]:
    """Search memories relevant to a query.

    Args:
        query: Search query string.
        user_id: User whose memories to search.
        limit: Max number of results.

    Returns:
        List of memory dicts with content and metadata.
    """
    mem = get_memory()
    if mem is None:
        log("MEMORY", f"  [fallback] Would recall for: {query[:60]}...")
        return []

    try:
        results = mem.search(query, user_id=user_id, limit=limit)
        log("MEMORY", f"  Recalled {len(results)} memories for: {query[:40]}...")
        return results
    except Exception as e:
        log("MEMORY", f"  Recall failed: {e}")
        return []


def hydrate_state_with_memory(state: AgentState) -> AgentState:
    """Enrich state with relevant memories from past builds.

    Searches Mem0 for memories relevant to the current prompt
    and injects them into state['memory_context'].
    """
    memories = recall(state["prompt"], user_id=state["user_id"])
    state["memory_context"] = memories
    if memories:
        push_event(state, "memory", "hydrated", {
            "count": len(memories),
        })
    return state


# ═══════════════════════════════════════════════════════════════
#  CLI VERIFICATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log("STATE", "=== AgentState Verification ===")

    # Create initial state
    state = create_initial_state("TestProject", "Build a 3D holographic studio")
    log("STATE", f"  Project: {state['project_name']}")
    log("STATE", f"  Status:  {state['status']}")
    log("STATE", f"  Events:  {len(state['build_events'])}")

    # Push some events
    push_event(state, "architect", "planned", {"files": 5})
    push_event(state, "engineer", "generated", {"lines": 200})
    push_event(state, "media", "rendered", {"assets": ["video.mp4"]})
    state["status"] = "building"

    log("STATE", f"  Events after updates: {len(state['build_events'])}")

    # Try memory
    log("STATE", "")
    log("STATE", "--- Memory Layer ---")
    state = hydrate_state_with_memory(state)
    log("STATE", f"  Memory context: {len(state['memory_context'])} entries")

    # Save snapshot
    path = save_state_snapshot(state)
    log("STATE", f"  Snapshot saved: {path}")

    log("STATE", "")
    log("STATE", "=== Verification Complete ===")
