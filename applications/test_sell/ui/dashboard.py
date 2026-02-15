from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from utils.logger import get_logger
from core.data_processing import DataProcessing
from utils.config import load_config
from utils.error_handling import handle_exception
from utils.helpers import format_number
import random

logger = get_logger(__name__)

class Dashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.data_processor = DataProcessing()
        self.init_ui()
        self.load_data()
        self.setup_auto_refresh()

    def init_ui(self):
        try:
            self.setWindowTitle("Dashboard")
            self.setLayout(QVBoxLayout())

            # Create a grid layout for the dashboard cards
            grid_layout = QGridLayout()
            self.layout().addLayout(grid_layout)

            # Add dashboard cards
            self.total_users_card = self.create_dashboard_card("Total Users", "user_icon.png")
            self.active_sessions_card = self.create_dashboard_card("Active Sessions", "session_icon.png")
            self.error_rate_card = self.create_dashboard_card("Error Rate", "error_icon.png")
            self.data_processed_card = self.create_dashboard_card("Data Processed", "data_icon.png")

            grid_layout.addWidget(self.total_users_card, 0, 0)
            grid_layout.addWidget(self.active_sessions_card, 0, 1)
            grid_layout.addWidget(self.error_rate_card, 1, 0)
            grid_layout.addWidget(self.data_processed_card, 1, 1)

            # Add a refresh button
            refresh_button = QPushButton("Refresh")
            refresh_button.clicked.connect(self.load_data)
            self.layout().addWidget(refresh_button)

            # Add a last updated label
            self.last_updated_label = QLabel("Last updated: Never")
            self.layout().addWidget(self.last_updated_label)

        except Exception as e:
            logger.error(f"Failed to initialize UI: {e}")
            handle_exception(e)

    def create_dashboard_card(self, title: str, icon_filename: str) -> QFrame:
        try:
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setLayout(QVBoxLayout())

            # Load icon
            icon_path = self.config.get('ICON_DIR', '') + icon_filename
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # Title and value
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setObjectName("valueLabel")

            # Add to layout
            card.layout().addWidget(icon_label)
            card.layout().addWidget(title_label)
            card.layout().addWidget(value_label)

            return card
        except Exception as e:
            logger.error(f"Failed to create dashboard card for {title}: {e}")
            handle_exception(e)
            return QFrame()

    def load_data(self):
        try:
            logger.info("Loading dashboard data")
            # Simulate data loading
            total_users = random.randint(1000, 5000)
            active_sessions = random.randint(100, 500)
            error_rate = random.uniform(0, 5)
            data_processed = random.randint(10000, 50000)

            # Update UI
            self.update_dashboard_card(self.total_users_card, total_users)
            self.update_dashboard_card(self.active_sessions_card, active_sessions)
            self.update_dashboard_card(self.error_rate_card, f"{error_rate:.2f}%")
            self.update_dashboard_card(self.data_processed_card, format_number(data_processed))

            # Update last updated label
            self.last_updated_label.setText(f"Last updated: Just now")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            handle_exception(e)

    def update_dashboard_card(self, card: QFrame, value: str):
        try:
            value_label = card.findChild(QLabel, "valueLabel")
            if value_label:
                value_label.setText(str(value))
        except Exception as e:
            logger.error(f"Failed to update dashboard card: {e}")
            handle_exception(e)

    def setup_auto_refresh(self):
        try:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.load_data)
            self.timer.start(30000)  # Refresh every 30 seconds
        except Exception as e:
            logger.error(f"Failed to set up auto-refresh: {e}")
            handle_exception(e)