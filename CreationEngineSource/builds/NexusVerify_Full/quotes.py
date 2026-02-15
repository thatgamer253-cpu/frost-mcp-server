import random
import sys
from typing import Optional

try:
    from config import QUOTES
except ImportError as e:
    # This error indicates a problem with config.py itself or its location.
    # It's critical, so we print to stderr and exit.
    print(f"Error importing QUOTES from config.py: {e}", file=sys.stderr)
    print("Please ensure 'config.py' is present and contains a 'QUOTES' list.", file=sys.stderr)
    sys.exit(1)
except AttributeError:
    # This error indicates config.py was imported, but QUOTES was not found within it.
    print("Error: 'QUOTES' list not found in 'config.py'.", file=sys.stderr)
    print("Please ensure 'config.py' defines a list named 'QUOTES'.", file=sys.stderr)
    sys.exit(1)

def get_random_quote() -> Optional[str]:
    """
    Selects and retrieves a random inspirational quote from the available list.

    Returns:
        Optional[str]: A randomly selected quote string, or None if no quotes
                       are available or an error occurs.
    """
    if not isinstance(QUOTES, list):
        print("Error: QUOTES in config.py is not a list.", file=sys.stderr)
        return None

    if not QUOTES:
        print("Warning: No quotes found in the QUOTES list in config.py.", file=sys.stderr)
        return None

    try:
        return random.choice(QUOTES)
    except IndexError:
        # This should ideally not happen if the list is checked for emptiness,
        # but it's a safeguard against unexpected empty list scenarios.
        print("Error: Could not select a random quote. The QUOTES list might be empty.", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any other unexpected errors during random selection.
        print(f"An unexpected error occurred while getting a random quote: {e}", file=sys.stderr)
        return None