from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from utils.logger import get_logger
from utils.error_handling import handle_exception
import sys

logger = get_logger(__name__)

class NotificationType:
    SUCCESS = 'success'
    ERROR = 'error'
    INFO = 'info'
    WARNING = 'warning'

class Notification(QWidget):
    def __init__(self, message: str, notification_type: str = NotificationType.INFO, duration: int = 5000, parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self.init_ui()

    def init_ui(self):
        try:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setFixedSize(300, 100)

            layout = QVBoxLayout()
            self.setLayout(layout)

            # Icon and message
            icon_label = QLabel()
            icon_label.setPixmap(self.get_icon().pixmap(24, 24))
            message_label = QLabel(self.message)
            message_label.setWordWrap(True)

            # Layout for icon and message
            message_layout = QHBoxLayout()
            message_layout.addWidget(icon_label)
            message_layout.addWidget(message_label)
            layout.addLayout(message_layout)

            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(self.close_notification)
            layout.addWidget(close_button, alignment=Qt.AlignRight)

            # Auto-close timer
            QTimer.singleShot(self.duration, self.close_notification)

            self.show()
        except Exception as e:
            logger.error(f"Failed to initialize notification UI: {e}")
            handle_exception(e)

    def get_icon(self) -> QIcon:
        try:
            if self.notification_type == NotificationType.SUCCESS:
                return QIcon(":/icons/success.png")
            elif self.notification_type == NotificationType.ERROR:
                return QIcon(":/icons/error.png")
            elif self.notification_type == NotificationType.WARNING:
                return QIcon(":/icons/warning.png")
            else:
                return QIcon(":/icons/info.png")
        except Exception as e:
            logger.error(f"Failed to get icon for notification: {e}")
            handle_exception(e)
            return QIcon()

    def close_notification(self):
        try:
            self.close()
        except Exception as e:
            logger.error(f"Failed to close notification: {e}")
            handle_exception(e)

# Example usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    notification = Notification("This is a test notification", NotificationType.SUCCESS)
    sys.exit(app.exec_())
```

### Key Features:
- **Notification Types**: Supports different types of notifications (success, error, info, warning) with corresponding icons.
- **Auto-Close**: Notifications automatically close after a specified duration (default 5 seconds).
- **UI Design**: Frameless window with translucent background for a modern look.
- **Error Handling**: Comprehensive try-except blocks with logging for all operations.
- **Logging**: Structured logging for all major actions and errors.
- **Example Usage**: Demonstrates how to use the notification system with a test notification.