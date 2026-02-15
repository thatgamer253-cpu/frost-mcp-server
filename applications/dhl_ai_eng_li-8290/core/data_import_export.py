# core/data_import_export.py

import csv
import json
import logging
from typing import List, Dict
from utils.exceptions import DataImportExportError
from utils.helpers import create_backup, atomic_write

logger = logging.getLogger(__name__)

class DataImporter:
    def __init__(self):
        self.setup()

    def setup(self):
        """
        Setup any necessary resources for data import.
        """
        logger.info("DataImporter setup complete.")

    def import_from_csv(self, file_path: str) -> List[Dict[str, str]]:
        """
        Import candidate data from a CSV file.

        :param file_path: Path to the CSV file.
        :return: A list of dictionaries representing candidate data.
        """
        try:
            logger.info(f"Importing data from CSV file: {file_path}")
            with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = [row for row in reader]
            logger.info(f"Successfully imported {len(data)} records from CSV.")
            return data
        except Exception as e:
            logger.error(f"Failed to import data from CSV: {e}", exc_info=True)
            raise DataImportExportError("CSV import failed") from e

    def import_from_json(self, file_path: str) -> List[Dict[str, str]]:
        """
        Import candidate data from a JSON file.

        :param file_path: Path to the JSON file.
        :return: A list of dictionaries representing candidate data.
        """
        try:
            logger.info(f"Importing data from JSON file: {file_path}")
            with open(file_path, mode='r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
            logger.info(f"Successfully imported {len(data)} records from JSON.")
            return data
        except Exception as e:
            logger.error(f"Failed to import data from JSON: {e}", exc_info=True)
            raise DataImportExportError("JSON import failed") from e

class DataExporter:
    def __init__(self):
        self.setup()

    def setup(self):
        """
        Setup any necessary resources for data export.
        """
        logger.info("DataExporter setup complete.")

    def export_to_csv(self, data: List[Dict[str, str]], file_path: str):
        """
        Export candidate data to a CSV file.

        :param data: A list of dictionaries representing candidate data.
        :param file_path: Path to the CSV file.
        """
        try:
            logger.info(f"Exporting data to CSV file: {file_path}")
            create_backup(file_path)
            with atomic_write(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                if data:
                    writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            logger.info(f"Successfully exported {len(data)} records to CSV.")
        except Exception as e:
            logger.error(f"Failed to export data to CSV: {e}", exc_info=True)
            raise DataImportExportError("CSV export failed") from e

    def export_to_json(self, data: List[Dict[str, str]], file_path: str):
        """
        Export candidate data to a JSON file.

        :param data: A list of dictionaries representing candidate data.
        :param file_path: Path to the JSON file.
        """
        try:
            logger.info(f"Exporting data to JSON file: {file_path}")
            create_backup(file_path)
            with atomic_write(file_path, mode='w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=4)
            logger.info(f"Successfully exported {len(data)} records to JSON.")
        except Exception as e:
            logger.error(f"Failed to export data to JSON: {e}", exc_info=True)
            raise DataImportExportError("JSON export failed") from e