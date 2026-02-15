import psutil
import GPUtil
import time
import threading

class SystemMonitor:
    def __init__(self):
        self.cpu_usage = 0
        self.memory_usage = 0
        self.gpu_usage = 0
        self.monitoring = False

    def start_monitoring(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_system)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()

    def _monitor_system(self):
        while self.monitoring:
            try:
                self.cpu_usage = psutil.cpu_percent(interval=1)
                self.memory_usage = psutil.virtual_memory().percent
                gpus = GPUtil.getGPUs()
                if gpus:
                    self.gpu_usage = max(gpu.load * 100 for gpu in gpus)
                else:
                    self.gpu_usage = 0
            except Exception as e:
                print(f"Monitoring error: {e}")
            time.sleep(1)

    def get_cpu_usage(self):
        return self.cpu_usage

    def get_memory_usage(self):
        return self.memory_usage

    def get_gpu_usage(self):
        return self.gpu_usage