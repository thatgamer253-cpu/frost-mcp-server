import sys
from typing import Union

def display_message(message: str) -> None:
    """
    Displays a general informational message to the user.

    Args:
        message (str): The message string to be displayed.
    """
    print(message)

def display_result(result: Union[int, float]) -> None:
    """
    Displays the result of a calculation to the user.
    Formats the result to avoid excessive decimal places for integers
    but retains precision for floats.

    Args:
        result (Union[int, float]): The numerical result of the calculation.
    """
    # If the result is an integer (e.g., 5.0), display it without the .0
    if isinstance(result, float) and result.is_integer():
        print(f"Result: {int(result)}")
    else:
        print(f"Result: {result}")

def display_error(error_message: str) -> None:
    """
    Displays an error message to the user.
    Error messages are typically printed to standard error for better separation
    from standard output, though for simple CLI apps, printing to stdout with
    a clear prefix is also common. Here, we'll use stdout with a prefix for
    user-friendliness.

    Args:
        error_message (str): The error message string to be displayed.
    """
    print(f"Error: {error_message}", file=sys.stderr) # Using sys.stderr for proper error stream output