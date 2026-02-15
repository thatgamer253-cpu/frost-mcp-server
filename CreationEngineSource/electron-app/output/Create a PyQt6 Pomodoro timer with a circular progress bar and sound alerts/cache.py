{e}")

def retrieve_from_cache(key):
    """
    Retrieves a value from the cache by its key.

    :param key: The key of the value to retrieve.
    :return: The cached value or None if not found.
    """
    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            cursor = conn.execute('''
                SELECT value FROM cache WHERE key = ?
            ''', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        print(f"An error occurred while retrieving from cache: {e}")
        return None

def clear_cache():
    """
    Clears all entries from the cache.
    """
    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            with conn:
                conn.execute('DELETE FROM cache')
    except sqlite3.Error as e:
        print(f"An error occurred while clearing the cache: {e}