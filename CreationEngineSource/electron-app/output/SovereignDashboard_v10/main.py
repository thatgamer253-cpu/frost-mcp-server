import sys
from PyQt5.QtWidgets import QApplication
from ui import SovereignSystemDashboardUI
from monitor import SystemMonitor
from controller import ApplicationController

def main():
    try:
        app = QApplication(sys.argv)
        ui = SovereignSystemDashboardUI()
        monitor = SystemMonitor()
        controller = ApplicationController(ui, monitor)

        ui.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()