import sys
from PyQt6.QtWidgets import QApplication
from ui import MainWindow
from data_manager import DataManager
from api_client import APIClient
from notifier import Notifier
from plotter import Plotter

def main():
    try:
        # Initialize the application
        app = QApplication(sys.argv)

        # Initialize components
        data_manager = DataManager()
        api_client = APIClient()
        notifier = Notifier()
        plotter = Plotter()

        # Initialize the main window
        main_window = MainWindow(data_manager, api_client, notifier, plotter)
        main_window.show()

        # Start the main event loop
        sys.exit(app.exec_())

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()