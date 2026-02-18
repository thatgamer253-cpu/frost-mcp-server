import os
import json
import time
from datetime import datetime
from ..llm_client import log, ask_llm, get_cached_client

class Mem0Adapter:
    """
    Adapter for Mem0-style memory. 
    Implements a Knowledge Graph-like interface for persistent state.
    """
    def __init__(self, memory_dir):
        self.memory_path = os.path.join(memory_dir, "knowledge_graph.json")
        os.makedirs(memory_dir, exist_ok=True)
        self.memory = self._load()

    def _load(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"nodes": [], "relationships": [], "history": []}

    def _save(self):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    def search(self, query, user_id="Donovan"):
        """
        Simulate a semantic search on the graph.
        Returns relevant 'memories' based on query keywords for now.
        """
        results = []
        q_lower = query.lower()
        for node in self.memory["nodes"]:
            if any(tag in q_lower for tag in node.get("tags", [])) or node.get("content", "").lower() in q_lower:
                results.append({"memory": node["content"], "score": 1.0})
        
        # If no graph nodes found, fallback to history search
        if not results:
            for entry in self.memory["history"]:
                if any(word in entry["text"].lower() for word in q_lower.split()):
                    results.append({"memory": entry["text"], "score": 0.5})
        
        return {"results": results[:10]}

    def add(self, text, user_id="Donovan", metadata=None):
        """Add a memory node or history entry."""
        entry = {
            "id": f"mem_{int(time.time()*1000)}",
            "content": text,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "metadata": metadata or {}
        }
        self.memory["nodes"].append(entry)
        self.memory["history"].append({"text": text, "ts": time.time()})
        self._save()
        log("MEMORY", f"Stored new memory: {text[:50]}...")

memory = None

def get_memory(project_path):
    global memory
    if memory is None:
        memory_dir = os.path.join(os.path.dirname(project_path), "memory")
        memory = Mem0Adapter(memory_dir)
    return memory
