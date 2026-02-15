import os
from typing import Final

class Config:
    """
    Configuration class for the random quote generator application.
    Stores paths and other static configuration variables.
    """

    # Determine the base directory of the project.
    # This assumes config.py is at the project root or a known relative path.
    # If config.py moves, this path calculation might need adjustment.
    _BASE_DIR: Final[str] = os.path.abspath(os.path.dirname(__file__))

    # Path to the file containing inspirational quotes.
    # It's located in the 'data' subdirectory relative to the project root.
    QUOTES_FILE_PATH: Final[str] = os.path.join(_BASE_DIR, 'data', 'quotes.txt')

    # You can add other configuration variables here, for example:
    # DEFAULT_ENCODING: Final[str] = 'utf-8'
    # MAX_QUOTE_LENGTH: Final[int] = 280 # For future features like tweet integration