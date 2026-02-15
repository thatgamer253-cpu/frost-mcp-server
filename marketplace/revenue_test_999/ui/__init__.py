# ui/__init__.py

import logging
from .main_window import MainWindow
from .plugin_manager_ui import PluginManagerUI
from .media_library_ui import MediaLibraryUI
from .dashboard_ui import DashboardUI
from .settings_ui import SettingsUI

def initialize_ui_components():
    """
    Initialize all UI components of the application.
    This function is responsible for setting up the main window and
    integrating all UI modules such as plugin manager, media library,
    dashboard, and settings.
    """
    try:
        logging.info("Initializing UI components...")
        
        # Initialize each UI component
        main_window = MainWindow()
        plugin_manager_ui = PluginManagerUI()
        media_library_ui = MediaLibraryUI()
        dashboard_ui = DashboardUI()
        settings_ui = SettingsUI()

        # Integrate UI components into the main window
        main_window.set_plugin_manager_ui(plugin_manager_ui)
        main_window.set_media_library_ui(media_library_ui)
        main_window.set_dashboard_ui(dashboard_ui)
        main_window.set_settings_ui(settings_ui)

        logging.info("UI components initialized successfully.")
        return main_window
    except Exception as e:
        logging.error(f"Error initializing UI components: {e}", exc_info=True)
        raise