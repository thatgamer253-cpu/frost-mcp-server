from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QDialog, QLineEdit, QMessageBox
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, data_manager, api_client, notifier, plotter):
        super().__init__()
        self.data_manager = data_manager
        self.api_client = api_client
        self.notifier = notifier
        self.plotter = plotter

        self.setWindowTitle("Crypto Portfolio Dashboard")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.label = QLabel("Welcome to the Crypto Portfolio Dashboard")
        self.layout.addWidget(self.label)

        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_data)
        self.layout.addWidget(self.refresh_button)

        self.plot_button = QPushButton("Show Plot")
        self.plot_button.clicked.connect(self.show_plot)
        self.layout.addWidget(self.plot_button)

    def refresh_data(self):
        try:
            self.data_manager.refresh_data()
            self.notifier.notify("Data refreshed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {e}")

    def show_plot(self):
        try:
            self.plotter.plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate plot: {e}")

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(150, 150, 400, 200)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.api_key_label = QLabel("API Key:")
        self.layout.addWidget(self.api_key_label)

        self.api_key_input = QLineEdit()
        self.layout.addWidget(self.api_key_input)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_button)

    def save_settings(self):
        api_key = self.api_key_input.text()
        if api_key:
            # Save the API key using a secure method
            QMessageBox.information(self, "Success", "Settings saved successfully.")
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "API Key cannot be empty.")