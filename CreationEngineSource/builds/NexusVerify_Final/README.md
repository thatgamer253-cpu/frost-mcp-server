# Simple Python Calculator

A basic command-line calculator application built with Python, designed to perform fundamental arithmetic operations. This project demonstrates modular design, robust error handling, and a user-friendly interactive interface.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [How to Run](#how-to-run)
- [Usage](#usage)
- [Error Handling](#error-handling)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Basic Arithmetic Operations**: Supports addition (`+`), subtraction (`-`), multiplication (`*`), and division (`/`).
- **Interactive CLI**: Engage with the calculator directly from your terminal.
- **Robust Error Handling**: Catches and gracefully handles various issues such as invalid input, unsupported operators, and division by zero.
- **Help Command**: Provides on-demand instructions within the application.
- **Exit Command**: Allows users to gracefully quit the calculator.
- **Modular Design**: Code is organized into distinct modules for better maintainability and readability.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.x**: The project is developed and tested with Python 3.8+.

## Installation

1.  **Clone the repository** (or download the project files):

    ```bash
    git clone https://github.com/your-username/simple-python-calculator.git
    cd simple-python-calculator
    ```
    *(Note: Replace `https://github.com/your-username/simple-python-calculator.git` with the actual repository URL if available.)*

2.  **Install dependencies**:
    This project has minimal dependencies. If `requirements.txt` contains any, install them using pip:

    ```bash
    pip install -r requirements.txt
    ```
    *(As of now, `requirements.txt` is empty, indicating no external libraries are strictly required beyond standard Python.)*

## How to Run

Navigate to the project's root directory and execute the `main.py` file:

```bash
python main.py
```

## Usage

Once the calculator is running, you will see a welcome message and a prompt. Enter your arithmetic expressions or commands.

### Examples:

-   **Addition**:
    ```
    Enter expression > 5 + 3
    Result: 8.0
    ```

-   **Subtraction**:
    ```
    Enter expression > 10 - 4.5
    Result: 5.5
    ```

-   **Multiplication**:
    ```
    Enter expression > 6 * 7
    Result: 42.0
    ```

-   **Division**:
    ```
    Enter expression > 20 / 4
    Result: 5.0
    ```

-   **Help Command**:
    ```
    Enter expression > help

    Enter an arithmetic expression (e.g., '2 + 3', '10 / 2').
    Supported operations: +, -, *, /
    Type 'help' for this message again.
    Type 'exit' or 'quit' to close the calculator.
    ```

-   **Exit Command**:
    ```
    Enter expression > exit
    Exiting calculator. Goodbye!
    ```

## Error Handling

The calculator is designed to handle common errors gracefully:

-   **Invalid Input**: If you enter non-numeric values or malformed expressions.
    ```
    Enter expression > hello world
    Error: Invalid input format. Please enter a valid arithmetic expression.
    ```

-   **Unsupported Operator**: If you use an operator not recognized by the calculator.
    ```
    Enter expression > 5 ^ 2
    Error: Unsupported operator: ^. Supported operators are +, -, *, /.
    ```

-   **Division by Zero**:
    ```
    Enter expression > 10 / 0
    Error: Division by zero is not allowed.
    ```

## Project Structure

-   `main.py`: The entry point of the application. It orchestrates the flow, handles user interaction, and manages error handling.
-   `config.py`: Stores global configuration settings, constants, user interface messages, and supported commands/operators.
-   `calculator_logic.py`: Contains the core business logic for performing arithmetic calculations.
-   `input_handler.py`: Responsible for handling user input, including parsing and validation of expressions.
-   `output_handler.py`: Manages all output to the console, displaying messages, results, and errors.
-   `exceptions.py`: Defines custom exception classes specific to the calculator, enhancing error clarity and handling.
-   `requirements.txt`: Lists the project's Python dependencies.
-   `README.md`: This file, providing an overview and instructions for the project.

## Contributing

Contributions are welcome! If you have suggestions for improvements, bug fixes, or new features, please feel free to:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/YourFeature`).
6.  Open a Pull Request.

## License

This project is open-source and available under the [MIT License](LICENSE).