import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui import MainUI
from logging import setup_logging

def main():
    # Initialize logging
    setup_logging()

    # Create the application instance
    app = QApplication(sys.argv)

    # Set up the main window
    try:
        main_window = QMainWindow()
        ui = MainUI(main_window)
        main_window.show()
    except Exception as e:
        print(f"Failed to initialize the main window: {e}")
        sys.exit(1)

    # Execute the application
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Application execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()