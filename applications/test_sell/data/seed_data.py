import os
import json
from typing import List, Dict, Any
from utils.logger import get_logger
from utils.error_handling import handle_exception

logger = get_logger(__name__)

class SeedData:
    def __init__(self, seed_file: str = "data/demo_data.json"):
        self.seed_file = seed_file
        self.data = self.load_seed_data()

    def load_seed_data(self) -> List[Dict[str, Any]]:
        """Load seed data from a JSON file."""
        try:
            if not os.path.exists(self.seed_file):
                logger.warning(f"Seed file {self.seed_file} does not exist. Generating default seed data.")
                return self.generate_default_seed_data()

            with open(self.seed_file, 'r') as file:
                data = json.load(file)
                logger.info(f"Seed data loaded successfully from {self.seed_file}.")
                return data
        except Exception as e:
            logger.error(f"Failed to load seed data: {e}", exc_info=True)
            handle_exception(e)
            return self.generate_default_seed_data()

    def generate_default_seed_data(self) -> List[Dict[str, Any]]:
        """Generate default seed data if no seed file is found."""
        default_data = [
            {"id": 1, "name": "Demo Item 1", "description": "This is a demo item.", "value": 100},
            {"id": 2, "name": "Demo Item 2", "description": "This is another demo item.", "value": 200},
            {"id": 3, "name": "Demo Item 3", "description": "Yet another demo item.", "value": 300},
            # Add more realistic demo data as needed
        ]
        logger.info("Default seed data generated.")
        return default_data

    def save_seed_data(self, data: List[Dict[str, Any]]) -> None:
        """Save seed data to a JSON file."""
        try:
            with open(self.seed_file, 'w') as file:
                json.dump(data, file, indent=4)
                logger.info(f"Seed data saved successfully to {self.seed_file}.")
        except Exception as e:
            logger.error(f"Failed to save seed data: {e}", exc_info=True)
            handle_exception(e)

    def get_seed_data(self) -> List[Dict[str, Any]]:
        """Get the current seed data."""
        return self.data

# Example usage
if __name__ == "__main__":
    seed_data_manager = SeedData()
    seed_data = seed_data_manager.get_seed_data()
    logger.info(f"Loaded Seed Data: {seed_data}")
```

### Key Features:
- **Data Loading**: Loads seed data from a JSON file, with error handling and logging.
- **Default Data Generation**: Generates default seed data if the file is missing or unreadable.
- **Data Saving**: Provides functionality to save seed data back to a file.
- **Logging**: Uses structured logging for all operations, including errors and warnings.
- **Error Handling**: Comprehensive try-except blocks with logging and error handling for robustness.
- **Example Usage**: Demonstrates how to use the `SeedData` class to load and log seed data.