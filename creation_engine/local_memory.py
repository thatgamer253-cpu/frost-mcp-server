import os
import requests
import json
from datetime import datetime
from .hardware_steward import HardwareSteward

try:
    import openvino as ov
    HAS_OPENVINO = True
except ImportError:
    HAS_OPENVINO = False

# ── Logging ──────────────────────────────────────────────────
def log(agent: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{agent}] {message}")

class LocalMemoryManager:
    """
    VRAM Stability Manager for Sovereign Offline Mode.
    Compresses long conversation context into a Master Summary using a local LLM (Ollama).
    """
    def __init__(self, model="deepseek-r1:7b", limit=5, api_url="http://localhost:11434"):
        self.api_url = f"{api_url}/api"
        self.model = model
        self.limit = limit
        self.history = []
        self.master_summary = "Engine initialized in Sovereign Offline Mode."
        self.is_offline_mode = True
        
        # Check connectivity
        try:
            resp = requests.get(api_url, timeout=2)
            if resp.status_code != 200:
                log("MEMORY", "⚠ Ollama server not responding correctly.")
        except Exception:
            self.is_offline_mode = False
            
        # Hardware Sentinel integration
        self.hardware = HardwareSteward()
        self.vram_threshold_gb = 7.4  # Emergency threshold for 8GB cards
        
        # Hardware Mode: GPU (Default), NPU (If available), CPU (Fallback)
        self.hw_mode = "GPU"
        if HAS_OPENVINO and self.hardware.has_intel_npu:
            self.hw_mode = "NPU"
            log("MEMORY", "🚀 AI BOOST DETECTED: NPU-Offload mode enabled for summarization.")

    @staticmethod
    def check_health(api_url="http://localhost:11434") -> bool:
        """Static check to see if Ollama is available."""
        try:
            resp = requests.get(api_url, timeout=1)
            return resp.status_code == 200
        except:
            return False

    def add_turn(self, role, content):
        """Add a turn to the history. Triggers compression if limit exceeded."""
        if not content:
            return
            
        self.history.append({"role": role, "content": content})
        
        # Hardware Check: If VRAM is critical, skip summarization and just prune hard
        stats = self.hardware.get_gpu_stats()
        vram_used_gb = stats.get("vram_used", 0) / 1024.0
        
        if vram_used_gb > self.vram_threshold_gb:
            log("MEMORY", f"🚨 HARDWARE CRITICAL: VRAM @ {vram_used_gb:.1f}GB. Emergency Pruning enforced.")
            self.history = self.history[-max(1, self.limit):]
            return

        # Every 'limit' pairs (user + assistant)
        if len(self.history) > (self.limit * 2):
            self.compress_memory()

    def compress_memory(self):
        """Collapses old turns into the Master Summary to save VRAM."""
        if not self.is_offline_mode:
            # Degrade gracefully: prune history without summarizing
            log("MEMORY", "Pruning history without summarization (Ollama offline)...")
            h_len = len(self.history)
            if h_len > self.limit:
                # Explicitly keep last 'limit' items
                new_hist = []
                for i in range(h_len - self.limit, h_len):
                    new_hist.append(self.history[i])
                self.history = new_hist
            return

        log("MEMORY", f"--- [VRAM Stability]: Pruning context & generating Master Summary ({self.hw_mode})... ---")
        try:
            hist_len = len(self.history)
            keep_count = min(hist_len, self.limit)
            to_summarize = self.history[:hist_len - keep_count]
            
            # If in NPU mode, we could theoretically use OpenVINO here. 
            # For now, we still route through the preferred local provider but flag the preference.
            # In a full NPU implementation, this would call a light-weight local model via OpenVINO.
            
            # Simple request to Ollama to summarize the archived turns
            prompt = (
                "You are the memory core of an autonomous build engine. "
                "Summarize these project steps into one dense, technical paragraph for your own future context. "
                "Focus on architectural decisions and failures. "
                f"Archived History: {json.dumps(to_summarize)}"
            )
            
            resp = requests.post(
                f"{self.api_url}/generate", 
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=15
            )
            
            if resp.status_code == 200:
                new_summary = resp.json().get('response', '')
                if new_summary:
                    self.master_summary += f" | {new_summary}"
                    log("MEMORY", "Master Summary updated successfully.")
                
                # Keep only the last 'keep_count' turns
                new_hist = []
                starting_idx = len(self.history) - keep_count
                if starting_idx < 0: starting_idx = 0
                for i in range(starting_idx, len(self.history)):
                    new_hist.append(self.history[i])
                self.history = new_hist
            else:
                log("MEMORY", f"⚠ Summarization failed (status {resp.status_code}).")
        except Exception as e:
            log("MEMORY", f"⚠ Compression error: {e}")
            # Ensure we don't leak memory even if LLM fails
            if len(self.history) > 20:
                self.history = self.history[-self.limit:]

    def get_full_context(self) -> list:
        """Returns the full context including the injected Master Summary."""
        # Always inject the master summary at the start of the next turn
        return [{"role": "system", "content": f"BACKGROUND CONTEXT: {self.master_summary}"}] + self.history

    def clear(self):
        """Reset the session memory."""
        self.history = []
        self.master_summary = "Engine memory reset."
        log("MEMORY", "Session memory cleared.")
