import sys
import os
from typing import NoReturn

# Add the project root to the sys.path to allow absolute imports
# This assumes main.py is at the root of the project.
# If main.py is in a subdirectory, this path adjustment might need to be different.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from quotes_manager import QuotesManager
from config import Config

def main() -> NoReturn:
    """
    The main entry point of the random quote generator application.
    It loads quotes, selects a random one, and prints it to the console.
    """
    try:
        quotes_file_path = Config.QUOTES_FILE_PATH
        quotes_manager = QuotesManager(quotes_file_path)

        quotes_manager.load_quotes()

        if not quotes_manager.has_quotes():
            print("Error: No quotes available to display. The quotes file might be empty or malformed.", file=sys.stderr)
            sys.exit(1)

        random_quote = quotes_manager.get_random_quote()

        if random_quote:
            print("\n--- Your Random Quote ---")
            print(random_quote)
            print("-------------------------\n")
        else:
            # This case should ideally be caught by has_quotes() check,
            # but as a safeguard, if get_random_quote somehow returns None.
            print("Error: Could not retrieve a random quote.", file=sys.stderr)
            sys.exit(1)

    except FileNotFoundError:
        print(f"Error: Quotes file not found at '{quotes_file_path}'. Please ensure the file exists.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied when trying to read '{quotes_file_path}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()