# error_handling.py

import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_error(exception):
    """
    Handles exceptions by logging the error details and stack trace.

    :param exception: The exception to handle.
    """
    try:
        error_message = str(exception)
        stack_trace = traceback.format_exc()
        
        # Log the error message and stack trace
        logging.error(f"Error: {error_message}")
        logging.error(f"Stack Trace: {stack_trace}")
        
    except Exception as log_exception:
        # If logging fails, print the error to standard output
        print(f"Logging failed: {log_exception}")
        print(f"Original error: {exception}")