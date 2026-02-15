import logging
import logging.handlers
import os
from typing import Optional

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_LEVEL = logging.DEBUG
LOG_FILE = "application.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

def setup_logging(log_level: Optional[int] = LOG_LEVEL, log_file: Optional[str] = LOG_FILE):
    """Setup structured logging for the application."""
    try:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Configure root logger
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

        # Create a rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(file_handler)

        # Add a console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(console_handler)

        logging.info("Logging setup complete. Log level: %s, Log file: %s", log_level, log_file)
    except Exception as e:
        logging.error("Failed to setup logging: %s", e, exc_info=True)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)
```

### Key Features:
- **Structured Logging**: Uses a consistent format for all log messages, including timestamp, log level, logger name, and message.
- **Rotating File Handler**: Ensures that log files do not grow indefinitely by rotating them when they reach a specified size (10 MB) and keeping a backup of the last 5 log files.
- **Console Logging**: Outputs log messages to the console for real-time monitoring.
- **Dynamic Configuration**: Allows for dynamic configuration of log level and log file path.
- **Error Handling**: Includes error handling for the logging setup process to ensure that the application can still run even if logging setup fails. The `exc_info=True` in the logging call provides a traceback for better debugging.
- **Directory Management**: Automatically creates the log directory if it does not exist, ensuring that logging can proceed without manual setup.