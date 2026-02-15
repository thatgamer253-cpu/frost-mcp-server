from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QHBoxLayout
from PyQt5.QtCore import Qt
from utils.logger import get_logger
from utils.error_handling import handle_exception
from core.data_processing import DataProcessing
from typing import List, Dict, Any

logger = get_logger(__name__)

class SearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_processor = DataProcessing()
        self.init_ui()

    def init_ui(self):
        try:
            self.setWindowTitle("Search Interface")
            self.setLayout(QVBoxLayout())

            # Search bar
            search_layout = QHBoxLayout()
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Enter search query...")
            search_button = QPushButton("Search")
            search_button.clicked.connect(self.perform_search)
            search_layout.addWidget(self.search_input)
            search_layout.addWidget(search_button)
            self.layout().addLayout(search_layout)

            # Filter dropdown
            self.filter_dropdown = QComboBox()
            self.filter_dropdown.addItems(["All", "Category 1", "Category 2", "Category 3"])
            self.layout().addWidget(self.filter_dropdown)

            # Results table
            self.results_table = QTableWidget()
            self.results_table.setColumnCount(3)
            self.results_table.setHorizontalHeaderLabels(["ID", "Name", "Description"])
            self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.layout().addWidget(self.results_table)

            # Status label
            self.status_label = QLabel("Enter a query and press 'Search'")
            self.layout().addWidget(self.status_label)

        except Exception as e:
            logger.error(f"Failed to initialize search interface UI: {e}")
            handle_exception(e)

    def perform_search(self):
        try:
            query = self.search_input.text()
            filter_category = self.filter_dropdown.currentText()
            logger.info(f"Performing search with query: {query} and filter: {filter_category}")

            # Simulate data retrieval
            results = self.mock_search(query, filter_category)
            self.populate_results_table(results)

            self.status_label.setText(f"Found {len(results)} results for '{query}'")
        except Exception as e:
            logger.error(f"Failed to perform search: {e}")
            handle_exception(e)

    def populate_results_table(self, results: List[Dict[str, Any]]):
        try:
            self.results_table.setRowCount(len(results))
            for row_index, result in enumerate(results):
                self.results_table.setItem(row_index, 0, QTableWidgetItem(str(result.get("id", ""))))
                self.results_table.setItem(row_index, 1, QTableWidgetItem(result.get("name", "")))
                self.results_table.setItem(row_index, 2, QTableWidgetItem(result.get("description", "")))
        except Exception as e:
            logger.error(f"Failed to populate results table: {e}")
            handle_exception(e)

    def mock_search(self, query: str, category: str) -> List[Dict[str, Any]]:
        # This is a mock function to simulate search results
        try:
            logger.info("Mocking search results")
            # Example mock data
            mock_data = [
                {"id": 1, "name": "Item 1", "description": "Description of item 1"},
                {"id": 2, "name": "Item 2", "description": "Description of item 2"},
                {"id": 3, "name": "Item 3", "description": "Description of item 3"},
            ]
            # Filter mock data based on query and category
            filtered_data = [item for item in mock_data if query.lower() in item["name"].lower()]
            if category != "All":
                filtered_data = [item for item in filtered_data if category in item["name"]]
            return filtered_data
        except Exception as e:
            logger.error(f"Error in mock_search: {e}")
            handle_exception(e)
            return []