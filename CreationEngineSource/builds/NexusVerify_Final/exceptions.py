class CalculatorError(Exception):
    """
    Base class for all custom exceptions in the calculator application.
    This allows for a single except block to catch all application-specific errors.
    """
    pass

class InvalidInputError(CalculatorError):
    """
    Exception raised when user input is malformed or cannot be parsed
    into a valid arithmetic expression or command.
    """
    def __init__(self, message: str = "Invalid input format. Please check your expression."):
        self.message = message
        super().__init__(self.message)

class UnsupportedOperatorError(CalculatorError):
    """
    Exception raised when an unsupported arithmetic operator is encountered
    in the user's expression.
    """
    def __init__(self, operator: str, message: str = "Unsupported operator"):
        self.operator = operator
        self.message = f"{message}: '{operator}'. Supported operators are +, -, *, /."
        super().__init__(self.message)

class DivisionByZeroError(CalculatorError):
    """
    Exception raised when an attempt is made to divide by zero.
    """
    def __init__(self, message: str = "Cannot divide by zero."):
        self.message = message
        super().__init__(self.message)