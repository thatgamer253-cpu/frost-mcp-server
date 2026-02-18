"""
Hardware Steward — GPU Telemetry & VRAM Management
Monitors hardware health to prevent crashes during intensive synthesis.
"""

import os
import subprocess
import time
import json
import logging

try:
    import pynvml
    HAS_NVML = True
except ImportError:
    HAS_NVML = False


class HardwareSteward:
    """GPU Telemetry & VRAM Management."""

    viz_active = True  # Class-level default

    def __init__(self):
        self.viz_active = True  # Primary instance flag
        self.gpu_count = 0
        self.initialized = False
        self.has_intel_npu = self._check_npu_presence()

        if HAS_NVML:
            try:
                pynvml.nvmlInit()
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                self.initialized = True
                self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                self.initialized = False

    def _check_npu_presence(self) -> bool:
        """Checks for Intel AI Boost NPU presence via PowerShell."""
        try:
            cmd = ["powershell", "-Command", "Get-PnpDevice | Where-Object { $_.FriendlyName -like '*AI Boost*' } | Select-Object -ExpandProperty Status"]
            # 0x08000000 = CREATE_NO_WINDOW
            output = subprocess.check_output(cmd, creationflags=0x08000000).decode().strip()
            return "OK" in output
        except:
            return False

    def monitor_and_throttle(self, threshold_gb, callback):
        """Monitors VRAM and triggers a callback to pause/resume visualizations."""
        if not hasattr(self, 'viz_active'):
             self.viz_active = True
             
        stats = self.get_gpu_stats()
        used_vram_gb = stats["vram_used"] / 1024.0
        
        if used_vram_gb > threshold_gb and self.viz_active:
            logging.warning(f"HardwareSentinel: VRAM Critical ({used_vram_gb:.1f}GB). Throttling Visuals...")
            self.viz_active = False
            callback(status="PAUSE")
        elif used_vram_gb < (threshold_gb * 0.8) and not self.viz_active:
            logging.info("HardwareSentinel: VRAM Stabilized. Resuming Visuals...")
            self.viz_active = True
            callback(status="RESUME")

    def is_pressured(self, threshold_vram_gb: float = 6.5, threshold_util: int = 70) -> bool:
        """
        Returns True if the system is under significant pressure (high VRAM or High Util).
        Used by autonomous agents to pause background 'heavy' thought.
        """
        stats = self.get_gpu_stats()
        used_gb = stats["vram_used"] / 1024.0
        util = stats["utilization"]
        
        # We consider 'pressured' if GPU util is high OR VRAM is near limit
        pressured = (used_gb > threshold_vram_gb) or (util > threshold_util)
        
        if pressured:
            logging.debug(f"HardwareSteward: Pressure detected (VRAM: {used_gb:.1f}GB, Util: {util}%)")
        
        return pressured

    def get_gpu_stats(self) -> dict:
        """Returns VRAM usage, Temperature, and Utilization."""
        stats = {
            "vram_total": 0,
            "vram_used": 0,
            "vram_free": 0,
            "temp": 0,
            "utilization": 0,
            "status": "OFFLINE",
            "sentinel_status": "STABLE",
            "npu_active": self.has_intel_npu
        }

        if self.initialized:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu

                used_gb = mem.used / 1024**3
                sentinel = "CRITICAL" if used_gb > 7.1 else "STABLE" # 7.1GB buffer for safety

                stats.update({
                    "vram_total": round(mem.total / 1024**2, 1),
                    "vram_used": round(mem.used / 1024**2, 1),
                    "vram_free": round(mem.free / 1024**2, 1),
                    "temp": temp,
                    "utilization": util,
                    "status": "STABLE" if temp < 80 else "HOT" if temp < 90 else "CRITICAL",
                    "sentinel_status": sentinel
                })
                return stats
            except Exception:
                pass

        # Fallback to nvidia-smi if NVML fails or isn't available
        return self._get_stats_via_smi()

    def _get_stats_via_smi(self) -> dict:
        """Execute nvidia-smi as fallback."""
        stats = {"vram_total": 0, "vram_used": 0, "vram_free": 0, "temp": 0, "utilization": 0, "status": "N/A"}
        try:
            # Query memory, temp, and utilization
            cmd = ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"]
            output = subprocess.check_output(cmd, creationflags=0x08000000).decode().strip()
            parts = [p.strip() for p in output.split(",")]
            
            if len(parts) >= 5:
                stats.update({
                    "vram_total": float(parts[0]),
                    "vram_used": float(parts[1]),
                    "vram_free": float(parts[2]),
                    "temp": float(parts[3]),
                    "utilization": float(parts[4]),
                    "status": "STABLE" if float(parts[3]) < 80 else "HOT"
                })
        except Exception:
            pass
        return stats

    def can_load_model(self, required_vram_mb: int) -> bool:
        """True if enough free VRAM is available."""
        stats = self.get_gpu_stats()
        # Leave a 500MB safety buffer for OS/GUI
        return (stats["vram_free"] - 500) >= required_vram_mb

    def vram_safety_check(self, threshold_gb: float = 7.2) -> str:
        """
        Check current VRAM usage (optimized for 5060 Ti / 8GB cards).
        Returns 'CPU' if usage is above threshold_gb, else 'GPU'.
        """
        try:
            import torch
            if torch.cuda.is_available():
                # Get current allocated vram in GB
                allocated = torch.cuda.memory_allocated() / (1024**3)
                if allocated > threshold_gb:
                    print(f"--- [SENTINEL ALERT]: VRAM Critical ({allocated:.1f}GB). Offloading TTS to CPU... ---")
                    return "CPU"
        except ImportError:
            pass

        # Fallback to NVML if torch isn't installed or cuda not available
        stats = self.get_gpu_stats()
        used_gb = stats["vram_used"] / 1024.0 # stats returns MB
        if used_gb > threshold_gb:
            print(f"--- [SENTINEL ALERT]: VRAM Critical ({used_gb:.1f}GB). Offloading TTS to CPU... ---")
            return "CPU"
            
        return "GPU"

    def purge_vram(self):
        """Attempts to clear cached models (Ollama specific)."""
        import requests
        try:
            # Tell Ollama to unload models
            # In some versions, unloading is handled by a DELETE or a zero-keepalive load
            # For now, we use a simple log entry or a subprocess kill if needed
            logging.info("HardwareSteward: Initiating VRAM Purge signal...")
            # subprocess.run(["ollama", "stop"], check=False) # Drastic measure
        except Exception:
            pass
