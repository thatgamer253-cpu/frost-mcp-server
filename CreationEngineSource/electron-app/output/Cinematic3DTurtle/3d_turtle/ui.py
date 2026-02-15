from PyQt6.QtWidgets import QMainWindow, QDockWidget, QTextEdit, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from .log import setup_logging
from .widgets import CustomWidget

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Turtle Application")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup logging
        self.logger = setup_logging()
        
        # Initialize UI components
        self.initUI()
        
    def initUI(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Layout for central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Add a label to central widget
        label = QLabel("3D Turtle Graphics", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Add custom widget
        custom_widget = CustomWidget(self)
        layout.addWidget(custom_widget)
        
        # Setup dockable log widget
        self.log_dock = QDockWidget("Log", self)
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        self.log_dock.setWidget(self.log_text_edit)
        
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        
        # Example log message
        self.log_message("UI initialized successfully.")
        
    def log_message(self, message):
        try:
            self.logger.info(message)
            self.log_text_edit.append(message)
        except Exception as e:
            self.logger.error(f"Failed to log message: {e}")

# Ensure the module is ready for use
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    main_ui = MainUI()
    main_ui.show()
    sys.exit(app.exec())