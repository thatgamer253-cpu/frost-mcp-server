# ui/settings_ui.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QHBoxLayout, QFormLayout, QMessageBox
from PyQt5.QtCore import Qt
from config.settings import load_config, save_config

class SettingsUI(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # General Settings
        self.general_settings_layout = QFormLayout()
        self.general_settings_layout.addRow(QLabel("<b>General Settings</b>"))

        # Theme selection
        self.theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.config.get('theme', 'Light'))
        self.general_settings_layout.addRow(self.theme_label, self.theme_combo)

        # Auto-save setting
        self.auto_save_checkbox = QCheckBox("Enable Auto-Save", self)
        self.auto_save_checkbox.setChecked(self.config.get('auto_save', False))
        self.general_settings_layout.addRow(self.auto_save_checkbox)

        self.layout.addLayout(self.general_settings_layout)

        # Network Settings
        self.network_settings_layout = QFormLayout()
        self.network_settings_layout.addRow(QLabel("<b>Network Settings</b>"))

        # API Endpoint
        self.api_endpoint_label = QLabel("API Endpoint:")
        self.api_endpoint_input = QLineEdit(self)
        self.api_endpoint_input.setText(self.config.get('api_endpoint', 'https://api.example.com'))
        self.network_settings_layout.addRow(self.api_endpoint_label, self.api_endpoint_input)

        self.layout.addLayout(self.network_settings_layout)

        # Buttons
        self.buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_settings)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_settings)
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.reset_button)

        self.layout.addLayout(self.buttons_layout)

    def save_settings(self):
        try:
            self.config['theme'] = self.theme_combo.currentText()
            self.config['auto_save'] = self.auto_save_checkbox.isChecked()
            self.config['api_endpoint'] = self.api_endpoint_input.text()

            save_config(self.config)
            QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", "Failed to save settings. Please try again.")

    def reset_settings(self):
        try:
            self.config = load_config(default=True)
            self.theme_combo.setCurrentText(self.config.get('theme', 'Light'))
            self.auto_save_checkbox.setChecked(self.config.get('auto_save', False))
            self.api_endpoint_input.setText(self.config.get('api_endpoint', 'https://api.example.com'))
            QMessageBox.information(self, "Settings Reset", "Settings have been reset to default values.")
        except Exception as e:
            logging.error(f"Failed to reset settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", "Failed to reset settings. Please try again.")