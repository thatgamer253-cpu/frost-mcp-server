# core/__init__.py

import logging
from .image_engine import initialize as initialize_image_engine
from .media_library import initialize as initialize_media_library
from .batch_processor import initialize as initialize_batch_processor
from .export_manager import initialize as initialize_export_manager

def initialize():
    """
    Initialize all core components of the application.
    This function is responsible for setting up the core modules
    such as image engine, media library, batch processor, and export manager.
    """
    try:
        logging.info("Initializing core module components...")
        initialize_image_engine()
        initialize_media_library()
        initialize_batch_processor()
        initialize_export_manager()
        logging.info("Core module components initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing core module components: {e}", exc_info=True)
        raise