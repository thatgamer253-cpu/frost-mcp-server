# core/logging.py

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = os.getenv('LOG_FILE', 'app.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

def setup_logging():
    """
    Configures the logging for the application with a rotating file handler.
    """
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    # Create a rotating file handler
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    file_handler.setLevel(LOG_LEVEL)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Log the startup banner
    log_startup_banner(logger)

def log_startup_banner(logger):
    """
    Logs a startup banner with application details.
    """
    logger.info("==========================================")
    logger.info("Application Startup")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info(f"Log File: {LOG_FILE}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Version: {os.getenv('APP_VERSION', '1.0.0')}")
    logger.info(f"Startup Time: {datetime.now().strftime(DATE_FORMAT)}")
    logger.info("==========================================")
```

### Key Features:
- **Rotating File Handler**: Uses `RotatingFileHandler` to manage log files, ensuring that logs do not consume excessive disk space by rotating when they reach 10 MB, keeping up to 5 backups.
- **Environment Configuration**: Reads log file path, log level, and other configurations from environment variables, allowing flexibility across different environments.
- **Structured Logging**: Implements a consistent log format with timestamps, log levels, and logger names.
- **Console and File Logging**: Logs are output to both the console and a file, ensuring visibility during development and persistence in production.
- **Startup Banner**: Logs a startup banner with key application details, providing a clear log entry for when the application starts.