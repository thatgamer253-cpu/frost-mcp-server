import sqlite3
from contextlib import closing

class StateManager:
    def __init__(self, db_path, logger):
        self.db_path = db_path
        self.logger = logger

    def set_task_status(self, task_name, status):
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                with conn:
                    conn.execute('''
                        INSERT INTO task_status (task_name, status) VALUES (?, ?)
                        ON CONFLICT(task_name) DO UPDATE SET status=excluded.status
                    ''', (task_name, status))
            self.logger.info(f"Task '{task_name}' status set to '{status}'.")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to set status for task '{task_name}'.", exc_info=True)
            raise

    def get_task_status(self, task_name):
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.execute('''
                    SELECT status FROM task_status WHERE task_name = ?
                ''', (task_name,))
                result = cursor.fetchone()
                status = result[0] if result else None
            self.logger.info(f"Retrieved status for task '{task_name}': '{status}'.")
            return status
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get status for task '{task_name}'.", exc_info=True)
            raise

    def delete_task_status(self, task_name):
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                with conn:
                    conn.execute('''
                        DELETE FROM task_status WHERE task_name = ?
                    ''', (task_name,))
            self.logger.info(f"Task '{task_name}' status deleted.")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete status for task '{task_name}'.", exc_info=True)
            raise