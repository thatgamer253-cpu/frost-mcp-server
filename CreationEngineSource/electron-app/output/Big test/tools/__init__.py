import os
import logging
from .state_manager import StateManager
from .plugin_loader import PluginLoader
from .task_manager import TaskManager
from .error_handler import ErrorHandler

# Initialize logging for the tools module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Define the directory where plugins are stored
PLUGINS_DIRECTORY = os.path.join(os.path.dirname(__file__), 'plugins')

# Initialize core components
state_manager = StateManager(db_path='path/to/db', logger=logger)
plugin_loader = PluginLoader(plugins_directory=PLUGINS_DIRECTORY)
task_manager = TaskManager(state_manager=state_manager, plugin_loader=plugin_loader)

def initialize_tools():
    """
    Initialize the tools module by loading plugins and preparing tasks.
    """
    try:
        logger.info("Initializing tools module.")
        
        # Load plugins
        plugins = plugin_loader.load_plugins()
        logger.info(f"Loaded {len(plugins)} plugins.")
        
        # Load tasks from plugins
        task_manager.load_tasks_from_plugins()
        logger.info("Tasks loaded from plugins successfully.")
        
    except Exception as e:
        ErrorHandler.handle_exception(e)
        logger.error("An error occurred during tools initialization.", exc_info=True)

# Initialize tools when the module is imported
initialize_tools()