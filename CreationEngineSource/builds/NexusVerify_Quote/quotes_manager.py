import os
import random
from typing import List

class QuotesManager:
    """
    Manages the loading and selection of quotes from a text file.

    Quotes are expected to be stored one per line in the specified text file.
    Empty lines or lines containing only whitespace will be ignored.
    """

    def __init__(self, quotes_file_path: str) -> None:
        """
        Initializes the QuotesManager with the path to the quotes file.

        Args:
            quotes_file_path: The absolute or relative path to the text file
                              containing quotes.

        Raises:
            TypeError: If quotes_file_path is not a string.
            ValueError: If quotes_file_path is an empty string.
        """
        if not isinstance(quotes_file_path, str):
            raise TypeError("quotes_file_path must be a string.")
        if not quotes_file_path:
            raise ValueError("quotes_file_path cannot be empty.")

        self._quotes_file_path: str = quotes_file_path
        self._quotes: List[str] = []
        self._is_loaded: bool = False

    def load_quotes(self) -> None:
        """
        Loads quotes from the specified file into memory.
        Each non-empty line in the file is considered a quote.
        Existing loaded quotes will be cleared before loading new ones.

        Raises:
            FileNotFoundError: If the quotes file does not exist or is not a regular file.
            PermissionError: If there are insufficient permissions to read the file.
            IOError: For other input/output errors during file reading.
            RuntimeError: For any other unexpected errors during the loading process.
        """
        if not os.path.exists(self._quotes_file_path):
            raise FileNotFoundError(f"Quotes file not found: '{self._quotes_file_path}'")
        if not os.path.isfile(self._quotes_file_path):
            raise FileNotFoundError(f"Path is not a file: '{self._quotes_file_path}'")

        self._quotes.clear()  # Clear any previously loaded quotes
        try:
            with open(self._quotes_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line:  # Only add non-empty lines
                        self._quotes.append(stripped_line)
            self._is_loaded = True
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied to read quotes file: '{self._quotes_file_path}'. Details: {e}"
            ) from e
        except IOError as e:
            raise IOError(
                f"Error reading quotes file: '{self._quotes_file_path}'. Details: {e}"
            ) from e
        except Exception as e:
            # Catch any other unexpected errors during file processing
            raise RuntimeError(
                f"An unexpected error occurred while loading quotes from '{self._quotes_file_path}'. Details: {e}"
            ) from e

    def has_quotes(self) -> bool:
        """
        Checks if any quotes have been loaded and are available.

        Returns:
            True if there is at least one quote loaded, False otherwise.
        """
        return len(self._quotes) > 0

    def get_random_quote(self) -> str:
        """
        Selects and returns a random quote from the loaded list.

        This method assumes that `load_quotes()` has been called successfully
        and `has_quotes()` returns True. It is recommended to check `has_quotes()`
        before calling this method to prevent errors.

        Returns:
            A randomly selected quote string.

        Raises:
            RuntimeError: If quotes have not been loaded yet, or if the list of
                          quotes is empty after loading.
        """
        if not self._is_loaded:
            raise RuntimeError("Quotes have not been loaded. Call load_quotes() first.")
        if not self._quotes:
            # This case should ideally be prevented by checking has_quotes() externally,
            # but as a safeguard, an error is raised.
            raise RuntimeError("No quotes available to select from. The quotes list is empty.")

        return random.choice(self._quotes)