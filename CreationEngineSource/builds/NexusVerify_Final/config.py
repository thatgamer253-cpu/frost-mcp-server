# config.py

"""
Configuration settings and constants for the simple_python_calculator project.
This file centralizes various messages, supported operations, and other
application-wide parameters.
"""

# --- User Interface Messages ---
WELCOME_MESSAGE: str = "Welcome to the Simple Python Calculator!"
HELP_MESSAGE: str = """
Enter an arithmetic expression (e.g., '2 + 3', '10 / 2').
Supported operations: +, -, *, /
Type 'help' for this message again.
Type 'exit' or 'quit' to close the calculator.
"""
PROMPT_MESSAGE: str = "Enter expression > "

# --- Commands ---
EXIT_COMMANDS: list[str] = ["exit", "quit", "q"]
HELP_COMMANDS: list[str] = ["help", "h", "?"]

# --- Supported Operations ---
# This dictionary maps operator symbols to their string names for potential
# future use (e.g., displaying supported operations dynamically).
# The actual logic for operations is in calculator_logic.py.
SUPPORTED_OPERATORS: dict[str, str] = {
    "+": "addition",
    "-": "subtraction",
    "*": "multiplication",
    "/": "division",
}

# --- Error Messages ---
INVALID_INPUT_FORMAT_MESSAGE: str = (
    "Invalid input format. Please enter a valid arithmetic expression "
    "(e.g., '2 + 3')."
)
UNSUPPORTED_OPERATOR_MESSAGE: str = (
    "Unsupported operator '{operator}'. Supported operators are: {supported_ops}."
)
DIVISION_BY_ZERO_MESSAGE: str = "Error: Division by zero is not allowed."
GENERIC_CALCULATOR_ERROR_MESSAGE: str = "An unexpected calculator error occurred: {error_detail}"

# --- Calculation Settings ---
# Number of decimal places for floating-point results.
# Set to None for no specific rounding, or an integer for fixed precision.
DECIMAL_PRECISION: int | None = 4