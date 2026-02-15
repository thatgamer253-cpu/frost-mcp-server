import sqlite3
from sqlite3 import Error
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_file='system_monitor.db'):
        self.db_file = db_file
        self.connection = None
        self._create_connection()
        self._create_tables()

    def _create_connection(self):
        """Create a database connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_file)
        except Error as e:
            print(f"Error connecting to database: {e}")

    def _create_tables(self):
        """Create tables for storing resource usage data."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS resource_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_usage REAL NOT NULL,
            memory_usage REAL NOT NULL,
            gpu_usage REAL NOT NULL
        );
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_sql)
        except Error as e:
            print(f"Error creating tables: {e}")

    def insert_usage_data(self, cpu_usage, memory_usage, gpu_usage):
        """Insert a new record into the resource_usage table."""
        insert_sql = """
        INSERT INTO resource_usage (timestamp, cpu_usage, memory_usage, gpu_usage)
        VALUES (?, ?, ?, ?);
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (timestamp, cpu_usage, memory_usage, gpu_usage))
            self.connection.commit()
        except Error as e:
            print(f"Error inserting data: {e}")

    def fetch_usage_data(self, limit=100):
        """Fetch the latest resource usage data."""
        fetch_sql = """
        SELECT * FROM resource_usage
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(fetch_sql, (limit,))
            rows = cursor.fetchall()
            return rows
        except Error as e:
            print(f"Error fetching data: {e}")
            return []

    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()