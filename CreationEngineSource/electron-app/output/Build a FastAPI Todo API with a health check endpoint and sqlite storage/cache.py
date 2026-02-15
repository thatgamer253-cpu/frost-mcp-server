import sqlite3
import os
from error_handling import handle_error

class Cache:
    def __init__(self, settings):
        """
        Initializes the Cache with the given settings.

        :param settings: A dictionary containing cache settings, including the database file path.
        """
        self.db_path = settings.get('db_path', 'cache.db')
        self._initialize_database()

    def _initialize_database(self):
        """
        Initializes the SQLite database and creates necessary tables if they do not exist.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            handle_error(e)

    def set(self, key, value):
        """
        Sets a key-value pair in the cache.

        :param key: The key for the cache entry.
        :param value: The value to be cached.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)
                ''', (key, value))
                conn.commit()
        except sqlite3.Error as e:
            handle_error(e)

    def get(self, key):
        """
        Retrieves a value from the cache by key.

        :param key: The key for the cache entry.
        :return: The cached value or None if the key does not exist.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM cache WHERE key = ?', (key,))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            handle_error(e)
            return None

    def delete(self, key):
        """
        Deletes a key-value pair from the cache.

        :param key: The key for the cache entry to delete.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()
        except sqlite3.Error as e:
            handle_error(e)

    def clear(self):
        """
        Clears all entries from the cache.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache')
                conn.commit()
        except sqlite3.Error as e:
            handle_error(e)