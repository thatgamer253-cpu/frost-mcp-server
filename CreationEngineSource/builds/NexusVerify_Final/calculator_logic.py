import math
from typing import Union

from exceptions import DivisionByZeroError, UnsupportedOperatorError
from config import SUPPORTED_OPERATORS

def add(num1: Union[int, float], num2: Union[int, float]) -> float:
    """
    Performs addition of two numbers.

    Args:
        num1 (Union[int, float]): The first number.
        num2 (Union[int, float]): The second number.

    Returns:
        float: The sum of num1 and num2.
    """
    return float(num1 + num2)

def subtract(num1: Union[int, float], num2: Union[int, float]) -> float:
    """
    Performs subtraction of two numbers.

    Args:
        num1 (Union[int, float]): The number to subtract from.
        num2 (Union[int, float]): The number to subtract.

    Returns:
        float: The difference between num1 and num2.
    """
    return float(num1 - num2)

def multiply(num1: Union[int, float], num2: Union[int, float]) -> float:
    """
    Performs multiplication of two numbers.

    Args:
        num1 (Union[int, float]): The first number.
        num2 (Union[int, float]): The second number.

    Returns:
        float: The product of num1 and num2.
    """
    return float(num1 * num2)

def divide(num1: Union[int, float], num2: Union[int, float]) -> float:
    """
    Performs division of two numbers.

    Args:
        num1 (Union[int, float]): The dividend.
        num2 (Union[int, float]): The divisor.

    Returns:
        float: The quotient of num1 divided by num2.

    Raises:
        DivisionByZeroError: If num2 is zero.
    """
    if num2 == 0:
        raise DivisionByZeroError("Cannot divide by zero.")
    return float(num1 / num2)

def calculate(num1: Union[int, float], num2: Union[int, float], operator: str) -> float:
    """
    Performs an arithmetic calculation based on the given numbers and operator.

    Args:
        num1 (Union[int, float]): The first operand.
        num2 (Union[int, float]): The second operand.
        operator (str): The arithmetic operator (+, -, *, /).

    Returns:
        float: The result of the calculation.

    Raises:
        UnsupportedOperatorError: If the provided operator is not supported.
        DivisionByZeroError: If division by zero is attempted.
    """
    if operator not in SUPPORTED_OPERATORS:
        raise UnsupportedOperatorError(f"Operator '{operator}' is not supported.")

    if operator == '+':
        return add(num1, num2)
    elif operator == '-':
        return subtract(num1, num2)
    elif operator == '*':
        return multiply(num1, num2)
    elif operator == '/':
        return divide(num1, num2)
    else:
        # This case should ideally be caught by the SUPPORTED_OPERATORS check,
        # but included for robustness.
        raise UnsupportedOperatorError(f"Operator '{operator}' is not recognized.")