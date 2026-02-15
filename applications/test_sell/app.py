import sys
import threading
from PyQt5.QtWidgets import QApplication
from ui.alternate_window import AlternateWindow as MainWindow  # Assuming 'ui/alternate_window.py' exists
from utils.logger import setup_logging
from utils.config import load_config
from utils.health_monitor import HealthMonitor
from utils.error_handling import handle_exception

def start_health_monitor():
    """Start the health monitoring in a separate thread."""
    health_monitor = HealthMonitor()
    health_thread = threading.Thread(target=health_monitor.run, daemon=True)
    health_thread.start()

def main():
    """Main entry point for the application."""
    # Setup logging
    setup_logging()

    # Load configuration
    config = load_config()

    # Global exception handler
    sys.excepthook = handle_exception

    # Start health monitoring
    start_health_monitor()

    # Initialize the application
    app = QApplication(sys.argv)
    main_window = MainWindow(config)
    main_window.show()

    # Start the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()