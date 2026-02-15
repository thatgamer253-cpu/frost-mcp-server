from core.scraper_engine import ScraperEngine
from core.data_processing import DataProcessing
from utils.logger import get_logger
from utils.error_handling import handle_exception
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)

class PluginTemplate:
    def __init__(self):
        self.scraper_engine = ScraperEngine()
        self.data_processor = DataProcessing()

    def scrape_and_process(self, url: str, dynamic: bool = False, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Scrape content from a URL and process it.

        :param url: The URL to scrape.
        :param dynamic: Whether to use dynamic content fetching.
        :param headers: Optional headers for the request.
        :return: Processed data as a dictionary.
        """
        try:
            logger.info(f"Starting scrape for URL: {url}")
            content = self.scraper_engine.scrape(url, dynamic, headers)
            if content:
                logger.info("Scraping successful, processing content")
                processed_data = self.data_processor.process_json(content)
                return processed_data if processed_data else {}
            else:
                logger.warning("No content retrieved from scraping")
                return {}
        except Exception as e:
            logger.error(f"Error in scrape_and_process: {e}")
            handle_exception(e)
            return {}

    def extract_and_clean_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """
        Extract and clean keywords from text.

        :param text: The text to process.
        :param keywords: List of keywords to extract.
        :return: List of extracted keywords.
        """
        try:
            logger.info("Extracting and cleaning keywords")
            cleaned_text = self.data_processor.clean_text(text)
            extracted_keywords = self.data_processor.extract_keywords(cleaned_text, keywords)
            return extracted_keywords
        except Exception as e:
            logger.error(f"Error in extract_and_clean_keywords: {e}")
            handle_exception(e)
            return []

# Example usage
if __name__ == "__main__":
    plugin = PluginTemplate()
    url = "https://www.example.com"
    keywords = ["example", "test", "scrape"]
    processed_data = plugin.scrape_and_process(url, dynamic=True)
    if processed_data:
        logger.info(f"Processed Data: {processed_data}")
    extracted_keywords = plugin.extract_and_clean_keywords("Sample text with example and test keywords.", keywords)
    logger.info(f"Extracted Keywords: {extracted_keywords}")
```

### Key Features:
- **Scraping and Processing**: Combines scraping and data processing in a single method.
- **Keyword Extraction**: Provides a method to extract and clean keywords from text.
- **Error Handling**: Comprehensive try-except blocks with logging for all operations.
- **Logging**: Structured logging for all major actions and errors.
- **Modular Design**: Uses `ScraperEngine` and `DataProcessing` for modular functionality.
- **Example Usage**: Demonstrates how to use the plugin with example URLs and keywords.