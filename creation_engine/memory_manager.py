import json
import os
import logging
import threading
from collections import deque

class MemoryManager:
    """
    Sovereign Memory Manager: Implements Hybrid Pruning with JSON persistence.
    Feature 1: Sliding Window (High-Definition Recall)
    Feature 2: Rolling Summary (VRAM Compression)
    Feature 3: JSON Persistence (Across Restart Continuity)
    Feature 4: Evolutionary Memory (Learned Constraints & Personality)
    """
    def __init__(self, memory_file="engine_memory.json", limit=5, llm_callback=None):
        self.memory_file = memory_file
        self.limit = limit
        self.llm_callback = llm_callback
        self.lock = threading.Lock()
        self.logger = logging.getLogger("MemoryManager")
        self.load_memory()

    def load_memory(self):
        with self.lock:
            if os.path.exists(self.memory_file):
                try:
                    with open(self.memory_file, 'r') as f:
                        self.data = json.load(f)
                        # Convert list back to deque for short_term
                        self.short_term = deque(self.data.get("short_term", []), maxlen=self.limit)
                        self.compressed_summary = self.data.get("compressed_summary", "The beginning of the saga.")
                        self.learned_constraints = self.data.get("learned_constraints", [])
                        self.personality_profile = self.data.get("personality_profile", {})
                except Exception as e:
                    self.logger.error(f"Memory Load Error: {e}")
                    self.short_term = deque(maxlen=self.limit)
                    self.compressed_summary = "Memories lost in the flicker. Re-syncing."
                    self.learned_constraints = []
                    self.personality_profile = {}
            else:
                self.short_term = deque(maxlen=self.limit)
                self.compressed_summary = "The beginning of the saga."
                self.learned_constraints = []
                self.personality_profile = {}
                self.data = {"short_term": [], "compressed_summary": self.compressed_summary}

    def add_interaction(self, role, content):
        with self.lock:
            # If about to overflow, summarize the outbound turn
            if len(self.short_term) >= self.limit:
                outbound_turn = self.short_term[0]
                self._async_compress(outbound_turn)
            
            self.short_term.append({"role": role, "content": content})
            self.save_memory()

    def _async_compress(self, turn):
        """Phase B: Context Pruning via LLM Summary."""
        if not self.llm_callback:
            return

        def _task():
            try:
                self.logger.info("--- [Memory Manager]: Pruning and compressing old context... ---")
                prompt = f"Existing History Summary: {self.compressed_summary}\n\nNewly archived interaction: {turn['role'].upper()}: {turn['content']}\n\nUpdate the summary to include the essence of the new interaction. Keep it extremely concise (1-2 sentences)."
                
                new_summary = self.llm_callback(prompt)
                if new_summary:
                    with self.lock:
                        self.compressed_summary = new_summary
                        self.save_memory()
                    self.logger.info("🧠 Memory compressed and persisted.")
            except Exception as e:
                self.logger.error(f"Compression Failure: {e}")

        threading.Thread(target=_task, daemon=True).start()

    def save_memory(self):
        # We don't need the lock here if called from within a locked context
        export_data = {
            "short_term": list(self.short_term),
            "compressed_summary": self.compressed_summary,
            "learned_constraints": getattr(self, "learned_constraints", []),
            "personality_profile": getattr(self, "personality_profile", {})
        }
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(export_data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Memory Save Error: {e}")

    def get_full_context(self):
        """Returns the formatted history for prompt injection."""
        with self.lock:
            history = f"CHRONICLE SUMMARY:\n{self.compressed_summary}\n\nRECENT RECALL:\n"
            for turn in self.short_term:
                history += f"{turn['role'].upper()}: {turn['content']}\n"
            return history
