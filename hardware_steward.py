#!/usr/bin/env python3
import time
import logging

try:
    import pynvml
    PNVML_AVAILABLE = True
except ImportError:
    PNVML_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HardwareSteward")

class HardwareSteward:
    def __init__(self):
        self.viz_active = False
        self.gpu_count = 0
        self._initialize_nvml()

    def _initialize_nvml(self):
        """Initialize pynvml if available."""
        if not PNVML_AVAILABLE:
            logger.warning("pynvml not installed. GPU monitoring disabled.")
            return

        try:
            pynvml.nvmlInit()
            self.gpu_count = pynvml.nvmlDeviceGetCount()
            logger.info(f"VRAM Empathy Active: Found {self.gpu_count} GPU(s).")
        except pynvml.NVMLError as e:
            logger.error(f"Failed to initialize NVML: {e}")
            self.gpu_count = 0

    def get_gpu_health(self):
        """
        Returns a list of dictionaries containing health stats for each GPU.
        Each dict has: index, name, vram_used, vram_total, vram_percent, temperature.
        """
        if not PNVML_AVAILABLE or self.gpu_count == 0:
            return []

        gpu_stats = []
        try:
            for i in range(self.gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Convert to GB for readability
                used_gb = mem.used / (1024**3)
                total_gb = mem.total / (1024**3)
                percent = (mem.used / mem.total) * 100

                gpu_stats.append({
                    "index": i,
                    "name": name,
                    "vram_used": round(used_gb, 2),
                    "vram_total": round(total_gb, 2),
                    "vram_percent": round(percent, 1),
                    "temperature": temp
                })
        except pynvml.NVMLError as e:
            logger.error(f"Error reading GPU stats: {e}")
            
        return gpu_stats

    def check_vram_pressure(self, threshold=90.0):
        """Returns True if any GPU is under high VRAM pressure."""
        stats = self.get_gpu_health()
        for gpu in stats:
            if gpu["vram_percent"] > threshold:
                logger.warning(f"HIGH VRAM PRESSURE detected on GPU {gpu['index']} ({gpu['name']}): {gpu['vram_percent']}%")
                return True
        return False

    def __del__(self):
        """Shutdown NVML on destruction."""
        if PNVML_AVAILABLE and self.gpu_count > 0:
            try:
                pynvml.nvmlShutdown()
            except pynvml.NVMLError:
                pass

if __name__ == "__main__":
    steward = HardwareSteward()
    while True:
        health = steward.get_gpu_health()
        print(f"\rGPU Health: {health}", end="", flush=True)
        time.sleep(2)