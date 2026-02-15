# core/database.py

import logging
import os
import psycopg2
from psycopg2 import pool, OperationalError, InterfaceError
from contextlib import contextmanager
from utils.exceptions import DatabaseConnectionError
from utils.helpers import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.connection_pool = None

    def initialize(self):
        """
        Initialize the database connection pool.
        """
        try:
            logger.info("Initializing database connection pool...")
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self._build_dsn()
            )
            if self.connection_pool:
                logger.info("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
            raise DatabaseConnectionError("Database connection pool initialization failed") from e

    def _build_dsn(self) -> str:
        """
        Build the DSN (Data Source Name) for PostgreSQL connection.
        """
        try:
            dsn = (
                f"dbname={os.getenv('DB_NAME')} "
                f"user={os.getenv('DB_USER')} "
                f"password={os.getenv('DB_PASSWORD')} "
                f"host={os.getenv('DB_HOST', 'localhost')} "
                f"port={os.getenv('DB_PORT', '5432')}"
            )
            logger.debug(f"DSN built: {dsn}")
            return dsn
        except KeyError as e:
            logger.error(f"Missing environment variable for DSN: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Missing environment variable for DSN: {e}")

    @contextmanager
    def get_connection(self):
        """
        Get a database connection from the pool.
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except (OperationalError, InterfaceError) as e:
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise DatabaseConnectionError("Failed to get database connection") from e
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def close_all_connections(self):
        """
        Close all connections in the pool.
        """
        try:
            logger.info("Closing all database connections...")
            self.connection_pool.closeall()
            logger.info("All database connections closed.")
        except Exception as e:
            logger.error(f"Failed to close database connections: {e}", exc_info=True)

@retry_with_exponential_backoff(max_retries=3)
def initialize_database():
    """
    Initialize the database connection.
    """
    db_connection = DatabaseConnection()
    db_connection.initialize()
    return db_connection
```

### Key Features:
- **Environment Variables**: Uses environment variables for database credentials, ensuring security and flexibility.
- **Connection Pooling**: Implements a connection pool using `psycopg2.pool.SimpleConnectionPool` for efficient database access.
- **Error Handling**: Includes comprehensive error handling with specific exceptions and logging.
- **Retry Logic**: Uses a retry decorator to handle transient failures during initialization.
- **Context Management**: Provides a context manager for safely acquiring and releasing database connections.
- **Logging**: Structured logging is used throughout to provide detailed information about the database operations.