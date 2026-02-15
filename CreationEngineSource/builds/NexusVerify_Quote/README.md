# Random Quote Generator

A simple Python command-line application that provides a dose of inspiration by displaying a random quote each time it's run. It's designed to be straightforward, easy to set up, and extensible.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Extending the Quote List](#extending-the-quote-list)
- [Project Structure](#project-structure)
- [Error Handling](#error-handling)
- [Contributing](#contributing)
- [License](#license)

## Features

*   **Random Selection**: Displays a different inspirational quote every time you run the application.
*   **Simple Interface**: A clean and direct command-line experience.
*   **Easy to Extend**: Add your favorite quotes by simply editing a text file.
*   **Configurable**: Quote file path is managed via a dedicated configuration file.
*   **Basic Error Handling**: Gracefully handles cases where the quotes file is missing or empty.

## Installation

Follow these steps to get the Random Quote Generator up and running on your local machine.

### Prerequisites

*   Python 3.6 or higher

### Steps

1.  **Clone the repository** (if applicable, assuming this project is part of a Git repository):
    ```bash
    git clone <repository-url>
    cd random_quote_generator
    ```
    If you've downloaded the files directly, navigate to the project's root directory.

2.  **(Optional) Create a virtual environment**:
    It's good practice to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    *   **On Linux/macOS**:
        ```bash
        source venv/bin/activate
        ```
    *   **On Windows**:
        ```bash
        venv\Scripts\activate
        ```

4.  **Install dependencies**:
    This project currently has no external Python dependencies, but it's good practice to run this command for future additions.
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once installed, running the application is simple:

1.  **Ensure your virtual environment is activated** (if you created one).
2.  **Run the main script**:
    ```bash
    python main.py
    ```

    You will see a random quote printed to your console.

    Example output:
    ```
    "The only way to do great work is to love what you do."
    ```

## Extending the Quote List

Adding new quotes to the generator is very easy:

1.  **Locate the quotes file**:
    The quotes are stored in `data/quotes.txt`.

2.  **Open the file**:
    Open `data/quotes.txt` using any text editor (e.g., Notepad, VS Code, Sublime Text, Vim).

3.  **Add your quote**:
    Type or paste your new quote on a **new line**. Each quote should occupy its own line in the file.

    Example `data/quotes.txt` content after adding a new quote:
    ```
    The only way to do great work is to love what you do.
    Believe you can and you're halfway there.
    The future belongs to those who believe in the beauty of their dreams.
    It always seems impossible until it's done.
    Success is not final, failure is not fatal: it is the courage to continue that counts.
    The best way to predict the future is to create it.
    Your time is limited, don't waste it living someone else's life.
    Strive not to be a success, but rather to be of value.
    The mind is everything. What you think you become.
    What you get by achieving your goals is not as important as what you become by achieving your goals.
    A new inspiring quote goes here!
    ```

4.  **Save the file**.

The next time you run `python main.py`, your new quote will be included in the random selection.

## Project Structure

```
random_quote_generator/
├── main.py                 # Main application entry point.
├── config.py               # Configuration settings (e.g., path to quotes file).
├── quotes_manager.py       # Logic for loading, managing, and selecting quotes.
├── data/
│   └── quotes.txt          # The text file containing all the quotes.
├── requirements.txt        # Lists Python dependencies.
└── README.md               # This documentation file.
```

## Error Handling

The application includes basic error handling:
*   If `data/quotes.txt` is not found, an error message will be printed to `stderr`, and the application will exit.
*   If `data/quotes.txt` is found but contains no valid quotes (e.g., it's empty or only contains whitespace lines), an error message will be printed, and the application will exit.

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests. You can also open an issue if you find a bug or have a feature request.

## License

This project is open-source and available under the [MIT License](LICENSE).