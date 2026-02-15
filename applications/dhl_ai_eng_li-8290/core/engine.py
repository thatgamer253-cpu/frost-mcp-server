# core/engine.py

from typing import Optional
import logging
from core.database import DatabaseConnection
from core.nlp import NLPProcessor
from core.matching import Matcher
from core.remote_assessment import RemoteAssessment
from core.data_import_export import DataImporter, DataExporter
from utils.exceptions import EngineInitializationError
from utils.helpers import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

class Engine:
    def __init__(self):
        self.db_connection: Optional[DatabaseConnection] = None
        self.nlp_processor: Optional[NLPProcessor] = None
        self.matcher: Optional[Matcher] = None
        self.remote_assessment: Optional[RemoteAssessment] = None
        self.data_importer: Optional[DataImporter] = None
        self.data_exporter: Optional[DataExporter] = None

    def initialize(self):
        try:
            logger.info("Initializing engine components...")
            self.db_connection = self._initialize_database()
            self.nlp_processor = self._initialize_nlp()
            self.matcher = self._initialize_matching()
            self.remote_assessment = self._initialize_remote_assessment()
            self.data_importer = self._initialize_data_import_export()
            self.data_exporter = self.data_importer  # Assuming same instance for import/export
            logger.info("Engine components initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}", exc_info=True)
            raise EngineInitializationError("Engine initialization failed") from e

    @retry_with_exponential_backoff(max_retries=3)
    def _initialize_database(self) -> DatabaseConnection:
        logger.debug("Initializing database connection...")
        db_connection = DatabaseConnection()
        db_connection.connect()
        logger.debug("Database connection established.")
        return db_connection

    def _initialize_nlp(self) -> NLPProcessor:
        logger.debug("Initializing NLP processor...")
        nlp_processor = NLPProcessor()
        nlp_processor.setup()
        logger.debug("NLP processor initialized.")
        return nlp_processor

    def _initialize_matching(self) -> Matcher:
        logger.debug("Initializing matcher...")
        matcher = Matcher()
        matcher.setup()
        logger.debug("Matcher initialized.")
        return matcher

    def _initialize_remote_assessment(self) -> RemoteAssessment:
        logger.debug("Initializing remote assessment...")
        remote_assessment = RemoteAssessment()
        remote_assessment.setup()
        logger.debug("Remote assessment initialized.")
        return remote_assessment

    def _initialize_data_import_export(self) -> DataImporter:
        logger.debug("Initializing data import/export...")
        data_importer = DataImporter()
        data_importer.setup()
        logger.debug("Data import/export initialized.")
        return data_importer

def initialize_engine():
    """
    Initialize the main engine for processing candidate data and job descriptions.
    """
    engine = Engine()
    engine.initialize()