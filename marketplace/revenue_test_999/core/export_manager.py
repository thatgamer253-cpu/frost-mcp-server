import os
import logging
from typing import Optional, List
from core.media_library import MediaLibrary
from utils.helpers import retry_on_failure
from utils.logger import setup_logging

class ExportManager:
    def __init__(self, export_path: str, media_library: MediaLibrary):
        self.export_path = export_path
        self.media_library = media_library
        setup_logging()

    @retry_on_failure
    def export_media(self, file_name: str, destination: Optional[str] = None) -> bool:
        """
        Export a media file to a specified destination.
        If no destination is provided, use the default export path.
        """
        try:
            logging.info(f"Exporting media file: {file_name}")
            if not destination:
                destination = self.export_path

            if not os.path.exists(destination):
                logging.warning(f"Destination path {destination} does not exist. Creating directory.")
                os.makedirs(destination)

            source_file = os.path.join(self.media_library.library_path, file_name)
            destination_file = os.path.join(destination, file_name)

            if not os.path.exists(source_file):
                logging.error(f"Source file {source_file} does not exist.")
                return False

            with open(source_file, 'rb') as src, open(destination_file, 'wb') as dst:
                dst.write(src.read())

            logging.info(f"Media file {file_name} exported successfully to {destination}.")
            return True
        except Exception as e:
            logging.error(f"Failed to export media file {file_name}: {e}", exc_info=True)
            return False

    def list_exported_files(self) -> List[str]:
        """
        List all files in the export directory.
        """
        try:
            logging.info("Listing exported files...")
            if not os.path.exists(self.export_path):
                logging.warning(f"Export path {self.export_path} does not exist.")
                return []

            exported_files = [f for f in os.listdir(self.export_path) if os.path.isfile(os.path.join(self.export_path, f))]
            logging.info(f"Found {len(exported_files)} exported files.")
            return exported_files
        except Exception as e:
            logging.error(f"Failed to list exported files: {e}", exc_info=True)
            return []

def initialize():
    """
    Initialize the export manager component.
    """
    try:
        logging.info("Initializing export manager...")
        export_path = os.getenv('EXPORT_PATH', './exports')
        library_path = os.getenv('MEDIA_LIBRARY_PATH', './media_library')
        media_library = MediaLibrary(library_path)
        export_manager = ExportManager(export_path, media_library)
        logging.info("Export manager initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize export manager: {e}", exc_info=True)
```

### Key Improvements:
1. **Error Handling**: Wrapped all critical operations in try-except blocks to ensure graceful error recovery.
2. **Logging**: Added detailed logging for each operation to provide traceability and debugging support.
3. **Directory Management**: Automatically creates the destination directory if it doesn't exist, ensuring the export operation doesn't fail due to missing directories.
4. **Environment Variables**: Uses environment variables for configuration, allowing flexibility in deployment environments.
5. **Robust Initialization**: The `initialize` function sets up the `ExportManager` with paths from environment variables, ensuring the component is ready for use.