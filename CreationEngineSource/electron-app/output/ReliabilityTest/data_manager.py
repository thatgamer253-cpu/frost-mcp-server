import sqlite3
from sqlite3 import Error
import os

class DataManager:
    def __init__(self, db_file='crypto_portfolio.db'):
        self.db_file = db_file
        self.connection = None
        self._create_connection()
        self._create_tables()

    def _create_connection(self):
        """Create a database connection to the SQLite database specified by db_file."""
        try:
            self.connection = sqlite3.connect(self.db_file)
        except Error as e:
            print(f"Error connecting to database: {e}")

    def _create_tables(self):
        """Create tables in the SQLite database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    date_added TEXT NOT NULL
                )
            ''')
            self.connection.commit()
        except Error as e:
            print(f"Error creating tables: {e}")

    def add_entry(self, symbol, amount, price, date_added):
        """Add a new entry to the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO portfolio (symbol, amount, price, date_added)
                VALUES (?, ?, ?, ?)
            ''', (symbol, amount, price, date_added))
            self.connection.commit()
        except Error as e:
            print(f"Error adding entry: {e}")

    def update_entry(self, entry_id, symbol, amount, price, date_added):
        """Update an existing entry in the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE portfolio
                SET symbol = ?, amount = ?, price = ?, date_added = ?
                WHERE id = ?
            ''', (symbol, amount, price, date_added, entry_id))
            self.connection.commit()
        except Error as e:
            print(f"Error updating entry: {e}")

    def delete_entry(self, entry_id):
        """Delete an entry from the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                DELETE FROM portfolio WHERE id = ?
            ''', (entry_id,))
            self.connection.commit()
        except Error as e:
            print(f"Error deleting entry: {e}")

    def fetch_all_entries(self):
        """Fetch all entries from the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM portfolio')
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching entries: {e}")
            return []

    def refresh_data(self):
        """Placeholder for refreshing data logic."""
        # This method can be expanded to include logic for refreshing data
        # from an external source or API.
        print("Data refreshed.")

    def __del__(self):
        """Ensure the database connection is closed when the DataManager is deleted."""
        if self.connection:
            self.connection.close()