# plugins/sample_plugin.py

import logging
from core.media_library import MediaLibrary

class SamplePlugin:
    def __init__(self, media_library: MediaLibrary):
        self.media_library = media_library
        logging.info("SamplePlugin initialized with media library.")

    def activate(self):
        """
        Activate the plugin. This method is called when the plugin is loaded.
        """
        try:
            logging.info("Activating SamplePlugin...")
            # Example action: Tag all media files with 'sample'
            for file_name in self.media_library.media_files:
                self.media_library.tag_media(file_name, ['sample'])
            logging.info("SamplePlugin activated successfully.")
        except Exception as e:
            logging.error(f"Failed to activate SamplePlugin: {e}", exc_info=True)

    def deactivate(self):
        """
        Deactivate the plugin. This method is called when the plugin is unloaded.
        """
        try:
            logging.info("Deactivating SamplePlugin...")
            # Example action: Remove 'sample' tag from all media files
            for file_name in self.media_library.media_files:
                metadata = self.media_library.get_metadata(file_name)
                if metadata and 'tags' in metadata:
                    metadata['tags'] = [tag for tag in metadata['tags'] if tag != 'sample']
                    self.media_library.add_metadata(file_name, metadata)
            logging.info("SamplePlugin deactivated successfully.")
        except Exception as e:
            logging.error(f"Failed to deactivate SamplePlugin: {e}", exc_info=True)

def initialize(media_library: MediaLibrary):
    """
    Initialize the SamplePlugin with the given media library.
    """
    try:
        logging.info("Initializing SamplePlugin...")
        plugin = SamplePlugin(media_library)
        logging.info("SamplePlugin initialized successfully.")
        return plugin
    except Exception as e:
        logging.error(f"Failed to initialize SamplePlugin: {e}", exc_info=True)
        return None
```

### Explanation:
- **SamplePlugin Class**: This class demonstrates how to extend the application's functionality by interacting with the `MediaLibrary`. It tags media files with 'sample' when activated and removes the tag when deactivated.
- **Activate/Deactivate Methods**: These methods perform actions on the media library, showcasing how plugins can modify application data.
- **Error Handling**: Each method includes try-except blocks to ensure robust error handling and logging.
- **Initialization**: The `initialize` function sets up the plugin, ensuring it is ready for use with the provided `MediaLibrary` instance.