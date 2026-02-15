import sqlite3
from sqlite3 import Error
import os

class DataManager:
    def __init__(self, db_file=None):
        self.db_file = db_file or os.getenv('DATABASE_PATH', 'portfolio.db')
        self.connection = None
        self._connect_to_db()

    def _connect_to_db(self):
        """Establish a connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_file)
            self._create_tables()
        except Error as e:
            print(f"Error connecting to database: {e}")

    def _create_tables(self):
        """Create necessary tables if they do not exist."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crypto_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    purchase_date TEXT NOT NULL
                )
            ''')
            self.connection.commit()
        except Error as e:
            print(f"Error creating tables: {e}")

    def add_crypto(self, crypto_name, amount, purchase_price, purchase_date):
        """Add a new cryptocurrency to the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO portfolio (crypto_name, amount, purchase_price, purchase_date)
                VALUES (?, ?, ?, ?)
            ''', (crypto_name, amount, purchase_price, purchase_date))
            self.connection.commit()
        except Error as e:
            print(f"Error adding crypto: {e}")

    def get_portfolio(self):
        """Retrieve the entire cryptocurrency portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM portfolio')
            return cursor.fetchall()
        except Error as e:
            print(f"Error retrieving portfolio: {e}")
            return []

    def update_crypto(self, crypto_id, crypto_name, amount, purchase_price, purchase_date):
        """Update an existing cryptocurrency in the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE portfolio
                SET crypto_name = ?, amount = ?, purchase_price = ?, purchase_date = ?
                WHERE id = ?
            ''', (crypto_name, amount, purchase_price, purchase_date, crypto_id))
            self.connection.commit()
        except Error as e:
            print(f"Error updating crypto: {e}")

    def delete_crypto(self, crypto_id):
        """Delete a cryptocurrency from the portfolio."""
        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM portfolio WHERE id = ?', (crypto_id,))
            self.connection.commit()
        except Error as e:
            print(f"Error deleting crypto: {e}")

    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()