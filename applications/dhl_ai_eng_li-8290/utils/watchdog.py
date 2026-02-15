# utils/watchdog.py

import logging
import threading
import psutil
import time
from typing import Optional

logger = logging.getLogger(__name__)

class Watchdog:
    def __init__(self, check_interval: int = 60, disk_threshold: int = 90, memory_threshold: int = 85):
        """
        Initialize the Watchdog for monitoring system resources.

        :param check_interval: Interval in seconds between checks.
        :param disk_threshold: Disk usage percentage threshold to trigger warnings.
        :param memory_threshold: Memory usage percentage threshold to trigger warnings.
        """
        self.check_interval = check_interval
        self.disk_threshold = disk_threshold
        self.memory_threshold = memory_threshold
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """
        Start the watchdog monitoring in a separate thread.
        """
        if self._thread is None:
            self._thread = threading.Thread(target=self._monitor, daemon=True)
            self._thread.start()
            logger.info("Watchdog started.")

    def stop(self):
        """
        Stop the watchdog monitoring.
        """
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join()
            self._thread = None
            logger.info("Watchdog stopped.")

    def _monitor(self):
        """
        Monitor system resources and log warnings if thresholds are exceeded.
        """
        while not self._stop_event.is_set():
            try:
                self._check_disk_usage()
                self._check_memory_usage()
            except Exception as e:
                logger.error(f"Error during system resource check: {e}", exc_info=True)
            time.sleep(self.check_interval)

    def _check_disk_usage(self):
        """
        Check the disk usage and log a warning if the threshold is exceeded.
        """
        disk_usage = psutil.disk_usage('/')
        if disk_usage.percent > self.disk_threshold:
            logger.warning(f"Disk usage is high: {disk_usage.percent}% used.")

    def _check_memory_usage(self):
        """
        Check the memory usage and log a warning if the threshold is exceeded.
        """
        memory_info = psutil.virtual_memory()
        if memory_info.percent > self.memory_threshold:
            logger.warning(f"Memory usage is high: {memory_info.percent}% used.")

def start_watchdog():
    """
    Initialize and start the system resource watchdog.
    """
    watchdog = Watchdog()
    watchdog.start()
```

### Explanation:
- **Watchdog Class**: This class is responsible for monitoring system resources such as disk and memory usage.
- **Initialization**: The class is initialized with configurable thresholds for disk and memory usage, as well as a check interval.
- **Start/Stop Methods**: These methods manage the lifecycle of the monitoring thread.
- **Monitoring Logic**: The `_monitor` method runs in a separate thread, periodically checking system resources and logging warnings if thresholds are exceeded.
- **Error Handling**: The monitoring loop is wrapped in a try-except block to ensure that any errors are logged and do not crash the thread.
- **Logging**: Uses structured logging to report the status of system resources and any warnings.
- **Start Function**: The `start_watchdog` function is a convenient entry point to initialize and start the watchdog.