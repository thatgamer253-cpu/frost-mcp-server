import psutil
import time
import logging
from utils.logger import get_logger

logger = get_logger(__name__)

class HealthMonitor:
    def __init__(self, interval: int = 60):
        """
        Initialize the HealthMonitor with a specified interval for health checks.
        
        :param interval: Time in seconds between each health check.
        """
        self.interval = interval
        self.running = True

    def run(self):
        """
        Start the health monitoring loop. This function runs indefinitely in a separate thread.
        """
        logger.info("HealthMonitor started.")
        while self.running:
            try:
                self.log_system_health()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"HealthMonitor encountered an error: {e}", exc_info=True)

    def log_system_health(self):
        """
        Log the current system health metrics including CPU, memory, and disk usage.
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/')

            logger.info(f"System Health Check: CPU Usage: {cpu_usage}%, "
                        f"Memory Usage: {memory_info.percent}%, "
                        f"Disk Usage: {disk_usage.percent}%")

            if memory_info.percent > 85:
                logger.warning("High memory usage detected.")
            if disk_usage.percent > 90:
                logger.warning("High disk usage detected.")

        except Exception as e:
            logger.error(f"Failed to log system health: {e}", exc_info=True)

    def stop(self):
        """
        Stop the health monitoring loop.
        """
        self.running = False
        logger.info("HealthMonitor stopped.")
```

### Key Features:
- **System Health Monitoring**: Logs CPU, memory, and disk usage at regular intervals.
- **Configurable Interval**: Allows setting the interval for health checks.
- **Warning Alerts**: Logs warnings if memory usage exceeds 85% or disk usage exceeds 90%.
- **Graceful Error Handling**: Comprehensive try-except blocks with logging for all operations.
- **Structured Logging**: Uses a consistent logging format for all health check logs.
- **Thread-Safe Stop**: Provides a method to safely stop the monitoring loop.