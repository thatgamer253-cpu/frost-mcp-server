# core/media_library.py

import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from utils.helpers import retry_on_failure
from utils.logger import setup_logging

class MediaLibrary:
    def __init__(self, library_path: str):
        self.library_path = library_path
        self.media_files = []
        self.metadata = {}
        setup_logging()

    def load_media_files(self):
        """
        Load media files from the library path.
        """
        try:
            logging.info("Loading media files...")
            if not os.path.exists(self.library_path):
                logging.warning(f"Library path {self.library_path} does not exist. Creating directory.")
                os.makedirs(self.library_path)

            self.media_files = [f for f in os.listdir(self.library_path) if os.path.isfile(os.path.join(self.library_path, f))]
            logging.info(f"Loaded {len(self.media_files)} media files.")
        except Exception as e:
            logging.error(f"Failed to load media files: {e}", exc_info=True)

    def get_metadata(self, file_name: str) -> Optional[Dict]:
        """
        Retrieve metadata for a specific media file.
        """
        try:
            return self.metadata.get(file_name)
        except Exception as e:
            logging.error(f"Failed to retrieve metadata for {file_name}: {e}", exc_info=True)
            return None

    def add_metadata(self, file_name: str, metadata: Dict):
        """
        Add or update metadata for a specific media file.
        """
        try:
            self.metadata[file_name] = metadata
            logging.info(f"Metadata for {file_name} updated.")
        except Exception as e:
            logging.error(f"Failed to update metadata for {file_name}: {e}", exc_info=True)

    def save_metadata(self):
        """
        Save metadata to a JSON file.
        """
        try:
            metadata_file = os.path.join(self.library_path, 'metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=4)
            logging.info("Metadata saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save metadata: {e}", exc_info=True)

    def load_metadata(self):
        """
        Load metadata from a JSON file.
        """
        try:
            metadata_file = os.path.join(self.library_path, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                logging.info("Metadata loaded successfully.")
            else:
                logging.warning("No metadata file found. Starting with empty metadata.")
        except Exception as e:
            logging.error(f"Failed to load metadata: {e}", exc_info=True)

    def tag_media(self, file_name: str, tags: List[str]):
        """
        Add tags to a specific media file.
        """
        try:
            if file_name not in self.metadata:
                self.metadata[file_name] = {}
            self.metadata[file_name]['tags'] = tags
            logging.info(f"Tags for {file_name} updated.")
        except Exception as e:
            logging.error(f"Failed to update tags for {file_name}: {e}", exc_info=True)

def initialize():
    """
    Initialize the media library component.
    """
    try:
        logging.info("Initializing media library...")
        library_path = os.getenv('MEDIA_LIBRARY_PATH', './media_library')
        media_library = MediaLibrary(library_path)
        media_library.load_media_files()
        media_library.load_metadata()
        logging.info("Media library initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize media library: {e}", exc_info=True)