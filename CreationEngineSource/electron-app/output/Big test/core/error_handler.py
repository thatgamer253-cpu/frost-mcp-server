import logging
import traceback

class ErrorHandler:
    @staticmethod
    def handle_exception(exception):
        """
        Handle exceptions by logging the error details and attempting recovery if possible.

        :param exception: The exception to handle.
        """
        logger = logging.getLogger(__name__)
        logger.error("An exception occurred: %s", str(exception))
        logger.debug("Exception traceback: %s", traceback.format_exc())

        # Attempt to recover from specific known exceptions
        if isinstance(exception, FileNotFoundError):
            ErrorHandler._handle_file_not_found(exception)
        elif isinstance(exception, ConnectionError):
            ErrorHandler._handle_connection_error(exception)
        else:
            logger.error("Unhandled exception type: %s", type(exception).__name__)

    @staticmethod
    def _handle_file_not_found(exception):
        """
        Handle FileNotFoundError by logging and suggesting corrective actions.

        :param exception: The FileNotFoundError to handle.
        """
        logger = logging.getLogger(__name__)
        logger.warning("File not found: %s. Please check the file path.", exception.filename)

    @staticmethod
    def _handle_connection_error(exception):
        """
        Handle ConnectionError by logging and suggesting corrective actions.

        :param exception: The ConnectionError to handle.
        """
        logger = logging.getLogger(__name__)
        logger.warning("Connection error occurred. Please check your network settings and try again.")
        
    @staticmethod
    def log_warning(message):
        """
        Log a warning message.

        :param message: The warning message to log.
        """
        logger = logging.getLogger(__name__)
        logger.warning(message)

    @staticmethod
    def log_info(message):
        """
        Log an informational message.

        :param message: The informational message to log.
        """
        logger = logging.getLogger(__name__)
        logger.info(message)