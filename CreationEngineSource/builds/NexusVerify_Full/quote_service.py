import random
import importlib
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import config

@dataclass
class Quote:
    """
    Represents a single inspirational quote with its text and author.
    """
    text: str
    author: str

class QuoteServiceError(Exception):
    """Base exception for errors in the QuoteService."""
    pass

class QuoteDataLoadError(QuoteServiceError):
    """Exception raised when there's an issue loading quote data."""
    pass

class NoQuotesAvailableError(QuoteServiceError):
    """Exception raised when no quotes are available after loading."""
    pass

class QuoteService:
    """
    Provides functionality to load quotes from a configured data source
    and retrieve a random quote.
    """
    def __init__(self) -> None:
        """
        Initializes the QuoteService and attempts to load quotes from
        the configured data module.
        Raises QuoteDataLoadError if quotes cannot be loaded.
        """
        self._quotes: List[Quote] = []
        self._load_quotes()

    def _load_quotes(self) -> None:
        """
        Loads quote data from the module and variable specified in config.py.
        Parses the raw data into a list of Quote objects.
        Raises QuoteDataLoadError on failure to load or parse data.
        """
        try:
            # Dynamically import the module containing the quote data
            quote_data_module = importlib.import_module(config.QUOTE_DATA_MODULE_NAME)
        except ModuleNotFoundError as e:
            raise QuoteDataLoadError(
                f"Quote data module '{config.QUOTE_DATA_MODULE_NAME}' not found. "
                f"Please ensure '{config.QUOTE_DATA_MODULE_NAME}.py' exists and is accessible."
            ) from e
        except Exception as e:
            # Catch any other unexpected errors during module import
            raise QuoteDataLoadError(
                f"An unexpected error occurred while importing module "
                f"'{config.QUOTE_DATA_MODULE_NAME}': {e}"
            ) from e

        try:
            # Get the variable containing the list of quotes from the module
            raw_quotes_data: Any = getattr(quote_data_module, config.QUOTE_DATA_VARIABLE_NAME)
        except AttributeError as e:
            raise QuoteDataLoadError(
                f"Quote data variable '{config.QUOTE_DATA_VARIABLE_NAME}' not found "
                f"in module '{config.QUOTE_DATA_MODULE_NAME}'. "
                f"Please ensure the variable is correctly named."
            ) from e
        except Exception as e:
            # Catch any other unexpected errors during attribute retrieval
            raise QuoteDataLoadError(
                f"An unexpected error occurred while accessing variable "
                f"'{config.QUOTE_DATA_VARIABLE_NAME}' in module "
                f"'{config.QUOTE_DATA_MODULE_NAME}': {e}"
            ) from e

        if not isinstance(raw_quotes_data, list):
            raise QuoteDataLoadError(
                f"Expected '{config.QUOTE_DATA_VARIABLE_NAME}' in "
                f"'{config.QUOTE_DATA_MODULE_NAME}' to be a list, "
                f"but got {type(raw_quotes_data).__name__}."
            )

        parsed_quotes: List[Quote] = []
        for i, quote_dict in enumerate(raw_quotes_data):
            if not isinstance(quote_dict, dict):
                # Log a warning or skip malformed entries instead of failing the whole load
                print(f"Warning: Quote entry at index {i} is not a dictionary. Skipping. "
                      f"Value: {quote_dict}", file=importlib.sys.stderr)
                continue

            try:
                text = quote_dict["text"]
                author = quote_dict.get("author", "Unknown") # Default author if missing
                parsed_quotes.append(Quote(text=text, author=author))
            except KeyError as e:
                # Log a warning or skip entries missing essential keys
                print(f"Warning: Quote entry at index {i} is missing required key '{e}'. Skipping. "
                      f"Entry: {quote_dict}", file=importlib.sys.stderr)
            except Exception as e:
                # Catch any other unexpected errors during parsing a single quote
                print(f"Warning: An unexpected error occurred while parsing quote entry at index {i}: {e}. "
                      f"Entry: {quote_dict}", file=importlib.sys.stderr)

        if not parsed_quotes:
            # If no quotes were successfully parsed, even if the raw list wasn't empty
            raise NoQuotesAvailableError(
                f"No valid quotes could be loaded from '{config.QUOTE_DATA_VARIABLE_NAME}' "
                f"in '{config.QUOTE_DATA_MODULE_NAME}'. "
                f"The data might be empty or malformed."
            )

        self._quotes = parsed_quotes

    def get_random_quote(self) -> Optional[Quote]:
        """
        Selects and returns a random quote from the loaded list.

        Returns:
            An Optional[Quote] object. Returns None if no quotes are available.
        """
        if not self._quotes:
            # This case should ideally be prevented by _load_quotes raising NoQuotesAvailableError,
            # but it acts as a safeguard if the list somehow becomes empty later or
            # if _load_quotes was modified not to raise for empty lists.
            return None
        return random.choice(self._quotes)

# Example of how to use (for testing purposes, not part of the main application flow)
if __name__ == "__main__":
    try:
        service = QuoteService()
        print("Quotes loaded successfully.")
        for _ in range(3):
            quote = service.get_random_quote()
            if quote:
                print(f"Random Quote: \"{quote.text}\" - {quote.author}")
            else:
                print("No quotes available.")
    except QuoteServiceError as e:
        print(f"Error initializing QuoteService: {e}", file=importlib.sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=importlib.sys.stderr)