import sys
import logging
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logging
from config.settings import load_config
from core import image_engine, media_library, batch_processor, export_manager
from plugins import plugin_manager

def initialize_core_components():
    try:
        logging.info("Initializing core components...")
        image_engine.initialize()
        media_library.initialize()
        batch_processor.initialize()
        export_manager.initialize()
        plugin_manager.initialize()
        logging.info("Core components initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize core components: {e}", exc_info=True)
        sys.exit(1)

def main():
    # Setup logging
    setup_logging()

    # Load configuration
    config = load_config()

    # Initialize core components
    initialize_core_components()

    # Create the application
    app = QApplication(sys.argv)

    # Initialize the main window
    main_window = MainWindow(config)
    main_window.show()

    # Start the application event loop
    try:
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Application encountered an error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()