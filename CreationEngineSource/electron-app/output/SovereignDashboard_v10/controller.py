from PyQt5.QtCore import QTimer
from ui import SovereignSystemDashboardUI
from monitor import SystemMonitor
from database import DatabaseManager
import threading

class ApplicationController:
    def __init__(self, ui: SovereignSystemDashboardUI, monitor: SystemMonitor):
        self.ui = ui
        self.monitor = monitor
        self.database = DatabaseManager()
        self.monitor.start_monitoring()
        self._setup_ui_updates()

    def _setup_ui_updates(self):
        """Setup periodic updates for the UI based on monitoring data."""
        try:
            self._schedule_ui_update()
        except Exception as e:
            print(f"Error setting up UI updates: {e}")

    def _schedule_ui_update(self):
        """Schedule the UI update to run periodically."""
        self._update_ui()
        threading.Timer(5.0, self._schedule_ui_update).start()  # Update every 5 seconds

    def _update_ui(self):
        """Update the UI with the latest monitoring data."""
        try:
            cpu_usage = self.monitor.get_cpu_usage()
            memory_usage = self.monitor.get_memory_usage()
            gpu_usage = self.monitor.get_gpu_usage()

            self.ui.update_cpu_usage(cpu_usage)
            self.ui.update_memory_usage(memory_usage)
            self.ui.update_gpu_usage(gpu_usage)

            self.database.insert_usage_data(cpu_usage, memory_usage, gpu_usage)
        except Exception as e:
            print(f"Error updating UI: {e}")

    def shutdown(self):
        """Shutdown the application cleanly."""
        try:
            self.monitor.stop_monitoring()
            self.database.close_connection()
        except Exception as e:
            print(f"Error during shutdown: {e}")