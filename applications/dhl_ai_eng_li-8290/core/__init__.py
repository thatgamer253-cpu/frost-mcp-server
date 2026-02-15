# core/__init__.py

from core.engine import initialize_engine
from core.database import initialize_database
from core.health_monitor import start_health_monitor
from core.logging import setup_logging
from core.nlp import initialize_nlp
from core.matching import initialize_matching
from core.remote_assessment import initialize_remote_assessment
from core.data_import_export import initialize_data_import_export

def initialize_core_components():
    """
    Initialize all core components required for the application.
    This includes setting up the engine, database, health monitoring,
    logging, NLP, matching, remote assessment, and data import/export.
    """
    setup_logging()
    initialize_engine()
    initialize_database()
    start_health_monitor()
    initialize_nlp()
    initialize_matching()
    initialize_remote_assessment()
    initialize_data_import_export()