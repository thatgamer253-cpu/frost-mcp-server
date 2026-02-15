QUOTE_DATA_MODULE_NAME: str = "quotes_data"
"""
The name of the Python module that contains the quote data.
This module is expected to be importable from the application's path.
For example, if your quotes are in 'quotes_data.py', this should be "quotes_data".
"""

QUOTE_DATA_VARIABLE_NAME: str = "QUOTES"
"""
The name of the variable within the `QUOTE_DATA_MODULE_NAME` that holds
the list of quote dictionaries.
For example, if `quotes_data.py` contains `QUOTES = [...]`, this should be "QUOTES".
"""

# Other potential configuration settings could be added here, for example:
# DEFAULT_AUTHOR_IF_MISSING: str = "Unknown"
# LOG_LEVEL: str = "INFO" # For a more complex application with logging
# CACHE_TTL_SECONDS: int = 3600 # If quotes were fetched from an external API and cached