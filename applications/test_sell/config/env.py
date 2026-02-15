import os
from typing import Dict, Any

class Config:
    """Environment-specific configuration management."""
    
    def __init__(self):
        self.config = self.load_environment_config()

    def load_environment_config(self) -> Dict[str, Any]:
        """Load configuration based on the current environment."""
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        config_map = {
            'development': self.development_config,
            'testing': self.testing_config,
            'production': self.production_config
        }
        return config_map.get(environment, self.development_config)()

    def development_config(self) -> Dict[str, Any]:
        """Configuration for development environment."""
        return {
            'DEBUG': True,
            'DATABASE_URI': 'sqlite:///dev.db',
            'API_URL': 'https://dev.api.yourdomain.com',
            'LOG_LEVEL': 'DEBUG',
            'CACHE_TIMEOUT': 300
        }

    def testing_config(self) -> Dict[str, Any]:
        """Configuration for testing environment."""
        return {
            'DEBUG': False,
            'DATABASE_URI': 'sqlite:///test.db',
            'API_URL': 'https://test.api.yourdomain.com',
            'LOG_LEVEL': 'INFO',
            'CACHE_TIMEOUT': 300
        }

    def production_config(self) -> Dict[str, Any]:
        """Configuration for production environment."""
        return {
            'DEBUG': False,
            'DATABASE_URI': os.getenv('DATABASE_URI', 'postgresql://user:password@prod.db.yourdomain.com/dbname'),
            'API_URL': 'https://api.yourdomain.com',
            'LOG_LEVEL': 'WARNING',
            'CACHE_TIMEOUT': 600
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

# Example usage
if __name__ == "__main__":
    config = Config()
    print("Current Environment Configuration:")
    for key, value in config.config.items():
        print(f"{key}: {value}")
```

### Key Features:
- **Environment Detection**: Automatically detects the environment (`development`, `testing`, `production`) using the `ENVIRONMENT` environment variable.
- **Environment-Specific Configurations**: Provides distinct configurations for development, testing, and production environments.
- **Secure Defaults**: Uses environment variables for sensitive information like `DATABASE_URI` in production.
- **Dynamic Configuration Loading**: Loads the appropriate configuration based on the current environment.
- **Fallback Mechanism**: Defaults to development configuration if the environment is not specified or recognized.
- **Configuration Access**: Provides a `get` method to access configuration values with a default fallback.