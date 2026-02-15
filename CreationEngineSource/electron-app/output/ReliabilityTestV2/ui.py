import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog, QFormLayout, QLineEdit, QDialogButtonBox
from PyQt6.QtCore import Qt

class CryptoPortfolioDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crypto Portfolio Dashboard")
        self.setGeometry(100, 100, 800, 600)
        
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        
        self.label = QLabel("Welcome to Crypto Portfolio Dashboard", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.settings_button = QPushButton("Settings", self)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.layout.addWidget(self.settings_button)
        
    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(150, 150, 400, 300)
        
        self.layout = QFormLayout(self)
        
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setText(os.getenv('API_KEY', ''))
        self.layout.addRow("API Key:", self.api_key_input)
        
        self.api_secret_input = QLineEdit(self)
        self.layout.addRow("API Secret:", self.api_secret_input)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)