from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QPalette
from utils.logger import get_logger
from utils.error_handling import handle_exception

logger = get_logger(__name__)

class ThemeManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_theme()

    def init_ui(self):
        try:
            self.setWindowTitle("Theme Manager")
            self.setLayout(QVBoxLayout())

            # Theme toggle button
            self.theme_toggle_button = QPushButton("Toggle Theme")
            self.theme_toggle_button.clicked.connect(self.toggle_theme)
            self.layout().addWidget(self.theme_toggle_button)

            # Current theme label
            self.current_theme_label = QLabel("Current Theme: Light")
            self.layout().addWidget(self.current_theme_label)

        except Exception as e:
            logger.error(f"Failed to initialize theme manager UI: {e}")
            handle_exception(e)

    def toggle_theme(self):
        try:
            current_theme = self.get_current_theme()
            new_theme = "dark" if current_theme == "light" else "light"
            self.apply_theme(new_theme)
            self.save_theme(new_theme)
            self.current_theme_label.setText(f"Current Theme: {new_theme.capitalize()}")
            logger.info(f"Theme toggled to {new_theme}")
        except Exception as e:
            logger.error(f"Failed to toggle theme: {e}")
            handle_exception(e)

    def apply_theme(self, theme: str):
        try:
            palette = QPalette()
            if theme == "dark":
                palette.setColor(QPalette.Window, QColor(53, 53, 53))
                palette.setColor(QPalette.WindowText, Qt.white)
                palette.setColor(QPalette.Base, QColor(25, 25, 25))
                palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
                palette.setColor(QPalette.ToolTipBase, Qt.white)
                palette.setColor(QPalette.ToolTipText, Qt.white)
                palette.setColor(QPalette.Text, Qt.white)
                palette.setColor(QPalette.Button, QColor(53, 53, 53))
                palette.setColor(QPalette.ButtonText, Qt.white)
                palette.setColor(QPalette.BrightText, Qt.red)
                palette.setColor(QPalette.Link, QColor(42, 130, 218))
                palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
                palette.setColor(QPalette.HighlightedText, Qt.black)
            else:
                palette = self.style().standardPalette()

            self.setPalette(palette)
        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")
            handle_exception(e)

    def load_theme(self):
        try:
            settings = QSettings("MyApp", "ThemeManager")
            theme = settings.value("theme", "light")
            self.apply_theme(theme)
            self.current_theme_label.setText(f"Current Theme: {theme.capitalize()}")
            logger.info(f"Loaded theme: {theme}")
        except Exception as e:
            logger.error(f"Failed to load theme: {e}")
            handle_exception(e)

    def save_theme(self, theme: str):
        try:
            settings = QSettings("MyApp", "ThemeManager")
            settings.setValue("theme", theme)
            logger.info(f"Theme saved: {theme}")
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")
            handle_exception(e)

    def get_current_theme(self):
        try:
            settings = QSettings("MyApp", "ThemeManager")
            return settings.value("theme", "light")
        except Exception as e:
            logger.error(f"Failed to get current theme: {e}")
            handle_exception(e)
            return "light"
```

### Key Features:
- **Theme Toggle**: Allows users to switch between light and dark themes.
- **Persistent Theme**: Saves the user's theme preference using `QSettings` and loads it on startup.
- **UI Design**: Provides a simple interface with a button to toggle themes and a label to display the current theme.
- **Error Handling**: Comprehensive try-except blocks with logging for all operations.
- **Logging**: Structured logging for all major actions and errors.