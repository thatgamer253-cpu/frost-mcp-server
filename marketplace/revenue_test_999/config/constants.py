# config/constants.py

"""
This module defines constant values used throughout the application.
These constants are intended to provide a single source of truth for
configuration keys, default paths, and other fixed values.
"""

# Default paths
DEFAULT_CONFIG_PATH = './config.json'
DEFAULT_PLUGINS_DIRECTORY = './plugins'
DEFAULT_MEDIA_LIBRARY_PATH = './media'
DEFAULT_EXPORT_PATH = './exports'

# Logging
DEFAULT_LOG_LEVEL = 'INFO'

# Image processing
DEFAULT_IMAGE_CACHE_SIZE = 100

# Feature toggles
ENABLE_AUTO_UPDATE = True

# API Endpoints
PUBLIC_API_ENDPOINT = 'https://api.publicapis.org/entries'

# UI Settings
UI_THEME_LIGHT = 'light'
UI_THEME_DARK = 'dark'

# Health Monitoring
HEALTH_CHECK_INTERVAL = 60  # in seconds

# Backup and Restore
BACKUP_EXTENSION = '.bak'
TEMP_EXTENSION = '.tmp'

# Watchdog/Sentinel
DISK_USAGE_WARNING_THRESHOLD = 90  # in percentage
MEMORY_USAGE_WARNING_THRESHOLD = 85  # in percentage

# Structured Logging
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
```

This file defines constants that are used throughout the application to ensure consistency and maintainability. It includes default paths, logging settings, feature toggles, API endpoints, UI settings, health monitoring intervals, backup and restore settings, and structured logging formats. These constants provide a centralized location for configuration keys and fixed values, making it easier to manage and update the application's configuration.