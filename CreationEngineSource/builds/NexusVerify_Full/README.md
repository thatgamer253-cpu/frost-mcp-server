# Random Quote Generator

A simple Python command-line application that fetches and displays a random inspirational quote. This project demonstrates basic Python scripting, modular design, and local data management.

## Table of Contents

*   [Features](#features)
*   [Prerequisites](#prerequisites)
*   [Setup](#setup)
*   [Usage](#usage)
*   [Project Structure](#project-structure)
*   [Customizing Quotes](#customizing-quotes)
*   [Error Handling](#error-handling)

## Features

*   **Random Quote Selection**: Displays a different quote each time it's run.
*   **Local Data Source**: Quotes are stored locally, making it easy to add or modify.
*   **Modular Design**: Separates concerns into different modules (main logic, quote service, configuration, data).
*   **Basic Error Handling**: Gracefully handles scenarios where quotes cannot be retrieved.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.x**: The application is developed and tested with Python 3.

## Setup

Follow these steps to get the project up and running on your local machine.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/random_quote_generator.git
    cd random_quote_generator
    ```
    *(Note: Replace `https://github.com/your-username/random_quote_generator.git` with the actual repository URL if different.)*

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```

4.  **Install dependencies**:
    The `requirements.txt` file is currently empty, indicating no external libraries are strictly required beyond standard Python. However, if any were added in the future, this command would install them:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once the setup is complete, you can run the application from your terminal.

Simply execute the `main.py` script:

```bash
python main.py
```

Each time you run it, a new random quote will be displayed:

```
"The only way to do great work is to love what you do." - Steve Jobs
```

## Project Structure

*   `main.py`: The main entry point of the application. It initializes the quote service and prints a random quote.
*   `config.py`: Contains configuration settings, such as the name of the module and variable holding the quote data.
*   `quote_service.py`: (Not provided, but implied) This module would contain the `QuoteService` class responsible for loading quotes from the data source and selecting a random one.
*   `quotes_data.py`: (Not provided, but implied) This module is expected to store the actual list of quotes.
*   `requirements.txt`: Lists the Python dependencies required for the project.
*   `README.md`: This documentation file.

## Customizing Quotes

The quotes are expected to be stored in a Python file named `quotes_data.py` (as configured in `config.py`). This file should contain a list of dictionaries, where each dictionary represents a quote with `text` and `author` keys.

To add or modify quotes:

1.  Create a file named `quotes_data.py` in the project root if it doesn't exist.
2.  Define a list named `QUOTES` (as configured in `config.py`) within `quotes_data.py` in the following format:

    ```python
    # quotes_data.py
    QUOTES = [
        {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
        {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
        {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
        # Add more quotes here
        {"text": "Your new awesome quote here.", "author": "Your Name"}
    ]
    ```

The application will automatically load quotes from this file.

## Error Handling

The application includes basic error handling:

*   If no quotes can be retrieved (e.g., `quotes_data.py` is empty or malformed), an error message will be printed to `stderr`, and the program will exit with a non-zero status code.
*   Any unexpected exceptions during the execution will also be caught, an error message displayed, and the program will exit.