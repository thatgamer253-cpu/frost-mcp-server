# ui/media_library_ui.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QPushButton, QHBoxLayout, QComboBox, QProgressBar, QAbstractItemView
from PyQt5.QtCore import Qt, QTimer
from core.media_library import MediaLibrary
from utils.helpers import retry_on_failure

class MediaLibraryUI(QWidget):
    def __init__(self, media_library: MediaLibrary):
        super().__init__()
        self.media_library = media_library
        self.init_ui()
        self.load_media_files()
        self.setup_auto_refresh()

    def init_ui(self):
        self.setWindowTitle("Media Library")
        self.layout = QVBoxLayout(self)

        # Search and filter bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search media files...")
        self.search_bar.textChanged.connect(self.filter_media_files)
        self.layout.addWidget(self.search_bar)

        # Media files table
        self.media_table = QTableWidget(self)
        self.media_table.setColumnCount(3)
        self.media_table.setHorizontalHeaderLabels(["File Name", "Tags", "Last Modified"])
        self.media_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.media_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layout.addWidget(self.media_table)

        # Pagination controls
        self.pagination_layout = QHBoxLayout()
        self.page_size_combo = QComboBox(self)
        self.page_size_combo.addItems(["10", "25", "50"])
        self.page_size_combo.currentIndexChanged.connect(self.update_pagination)
        self.pagination_layout.addWidget(QLabel("Items per page:"))
        self.pagination_layout.addWidget(self.page_size_combo)
        self.layout.addLayout(self.pagination_layout)

        # Export buttons
        self.export_layout = QHBoxLayout()
        self.export_csv_button = QPushButton("Export CSV", self)
        self.export_csv_button.clicked.connect(self.export_to_csv)
        self.export_json_button = QPushButton("Export JSON", self)
        self.export_json_button.clicked.connect(self.export_to_json)
        self.export_layout.addWidget(self.export_csv_button)
        self.export_layout.addWidget(self.export_json_button)
        self.layout.addLayout(self.export_layout)

        # Status bar
        self.status_bar = QLabel(self)
        self.layout.addWidget(self.status_bar)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar)

    def load_media_files(self):
        try:
            self.media_library.load_media_files()
            self.media_library.load_metadata()
            self.populate_media_table()
            self.status_bar.setText(f"Loaded {len(self.media_library.media_files)} media files.")
        except Exception as e:
            logging.error(f"Failed to load media files: {e}", exc_info=True)
            self.status_bar.setText("Error loading media files.")

    def populate_media_table(self):
        self.media_table.setRowCount(0)
        for file_name in self.media_library.media_files:
            metadata = self.media_library.get_metadata(file_name)
            tags = ", ".join(metadata.get('tags', [])) if metadata else "No tags"
            last_modified = metadata.get('last_modified', 'Unknown') if metadata else 'Unknown'

            row_position = self.media_table.rowCount()
            self.media_table.insertRow(row_position)
            self.media_table.setItem(row_position, 0, QTableWidgetItem(file_name))
            self.media_table.setItem(row_position, 1, QTableWidgetItem(tags))
            self.media_table.setItem(row_position, 2, QTableWidgetItem(last_modified))

    def filter_media_files(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.media_table.rowCount()):
            item = self.media_table.item(row, 0)
            self.media_table.setRowHidden(row, search_text not in item.text().lower())

    def update_pagination(self):
        # Placeholder for pagination logic
        pass

    def export_to_csv(self):
        # Placeholder for CSV export logic
        pass

    def export_to_json(self):
        # Placeholder for JSON export logic
        pass

    def setup_auto_refresh(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_media_library)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    @retry_on_failure
    def refresh_media_library(self):
        try:
            self.load_media_files()
            self.status_bar.setText("Media library refreshed.")
        except Exception as e:
            logging.error(f"Failed to refresh media library: {e}", exc_info=True)
            self.status_bar.setText("Error refreshing media library.")
```

### Explanation of Fixes:
- **Syntax Error**: The original code had a syntax error likely due to a missing or misplaced character. The corrected code ensures all methods and logic are properly closed and structured.
- **Auto-Refresh Logic**: The `setup_auto_refresh` method now correctly connects the timer to the `refresh_media_library` method.
- **Error Handling**: Ensured that all try-except blocks are correctly implemented to handle exceptions and log errors.
- **UI Initialization**: Ensured that all UI components are properly initialized and connected to their respective slots or methods.