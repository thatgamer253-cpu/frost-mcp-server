# ui.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt

class SovereignSystemDashboardUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sovereign System Dashboard")
        self.setGeometry(100, 100, 800, 600)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # CPU Usage Widget
        self.cpu_usage_label = QLabel("CPU Usage:")
        self.cpu_usage_bar = QProgressBar()
        self.cpu_usage_bar.setRange(0, 100)
        layout.addWidget(self.create_monitor_widget(self.cpu_usage_label, self.cpu_usage_bar))

        # Memory Usage Widget
        self.memory_usage_label = QLabel("Memory Usage:")
        self.memory_usage_bar = QProgressBar()
        self.memory_usage_bar.setRange(0, 100)
        layout.addWidget(self.create_monitor_widget(self.memory_usage_label, self.memory_usage_bar))

        # Disk Usage Widget
        self.disk_usage_label = QLabel("Disk Usage:")
        self.disk_usage_bar = QProgressBar()
        self.disk_usage_bar.setRange(0, 100)
        layout.addWidget(self.create_monitor_widget(self.disk_usage_label, self.disk_usage_bar))

        # GPU Usage Widget
        self.gpu_usage_label = QLabel("GPU Usage:")
        self.gpu_usage_bar = QProgressBar()
        self.gpu_usage_bar.setRange(0, 100)
        layout.addWidget(self.create_monitor_widget(self.gpu_usage_label, self.gpu_usage_bar))

        self.setLayout(layout)

    def create_monitor_widget(self, label, progress_bar):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(progress_bar)
        frame.setLayout(layout)
        return frame

    def update_cpu_usage(self, value):
        try:
            self.cpu_usage_bar.setValue(value)
        except Exception as e:
            print(f"Failed to update CPU usage: {e}")

    def update_memory_usage(self, value):
        try:
            self.memory_usage_bar.setValue(value)
        except Exception as e:
            print(f"Failed to update Memory usage: {e}")

    def update_disk_usage(self, value):
        try:
            self.disk_usage_bar.setValue(value)
        except Exception as e:
            print(f"Failed to update Disk usage: {e}")

    def update_gpu_usage(self, value):
        try:
            self.gpu_usage_bar.setValue(value)
        except Exception as e:
            print(f"Failed to update GPU usage: {e}")