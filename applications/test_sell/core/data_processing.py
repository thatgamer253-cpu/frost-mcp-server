import re
import json
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from utils.error_handling import handle_exception

logger = get_logger(__name__)

class DataProcessing:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        """Clean text by removing unwanted characters and normalizing whitespace."""
        try:
            logger.info("Cleaning text data")
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
            cleaned_text = text.strip()
            logger.debug(f"Cleaned text: {cleaned_text[:50]}...")
            return cleaned_text
        except Exception as e:
            logger.error(f"Failed to clean text: {e}")
            handle_exception(e)
            return ""

    def normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data to ensure consistency."""
        try:
            logger.info("Normalizing data")
            normalized_data = {k.lower(): v for k, v in data.items()}
            logger.debug(f"Normalized data: {json.dumps(normalized_data, indent=2)}")
            return normalized_data
        except Exception as e:
            logger.error(f"Failed to normalize data: {e}")
            handle_exception(e)
            return {}

    def extract_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Extract specified keywords from the text."""
        try:
            logger.info("Extracting keywords from text")
            found_keywords = [keyword for keyword in keywords if keyword in text]
            logger.debug(f"Extracted keywords: {found_keywords}")
            return found_keywords
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            handle_exception(e)
            return []

    def process_json(self, json_data: str) -> Optional[Dict[str, Any]]:
        """Process JSON data and return a dictionary."""
        try:
            logger.info("Processing JSON data")
            data = json.loads(json_data)
            logger.debug(f"Processed JSON data: {json.dumps(data, indent=2)}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            handle_exception(e)
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing JSON: {e}")
            handle_exception(e)
            return None

    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """Summarize text to a specified maximum length."""
        try:
            logger.info("Summarizing text")
            if len(text) <= max_length:
                summary = text
            else:
                summary = text[:max_length].rsplit(' ', 1)[0] + '...'
            logger.debug(f"Text summary: {summary}")
            return summary
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            handle_exception(e)
            return ""

# Example usage
if __name__ == "__main__":
    processor = DataProcessing()
    sample_text = "This is a sample text with some keywords like Python and Data Processing."
    cleaned = processor.clean_text(sample_text)
    normalized = processor.normalize_data({"Name": "Alice", "AGE": 30})
    keywords = processor.extract_keywords(cleaned, ["Python", "Data"])
    json_data = processor.process_json('{"key": "value"}')
    summary = processor.summarize_text(sample_text, max_length=50)