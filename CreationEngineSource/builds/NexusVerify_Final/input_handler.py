from exceptions import InvalidInputError

def get_user_input(prompt: str) -> str:
    """
    Prompts the user for input and returns the entered string.
    Performs basic sanitization by stripping leading/trailing whitespace.
    Handles EOF (Ctrl+D) and KeyboardInterrupt (Ctrl+C) by returning "exit"
    to allow the main loop to terminate gracefully.

    Args:
        prompt (str): The message to display to the user before awaiting input.

    Returns:
        str: The user's input string, stripped of leading/trailing whitespace.
             Returns "exit" if EOF or KeyboardInterrupt is detected.

    Raises:
        InvalidInputError: If the input is empty after stripping whitespace,
                           indicating no valid command or expression was entered.
    """
    try:
        user_input = input(prompt)
        stripped_input = user_input.strip()

        if not stripped_input:
            # If the input is empty after stripping, it's neither a command
            # nor a valid expression. Raise an error for the main loop to handle.
            raise InvalidInputError("Input cannot be empty. Please enter an expression or a command.")

        return stripped_input
    except EOFError:
        # Handle Ctrl+D (End-of-File) gracefully.
        # Treat it as an 'exit' command to allow the main application to terminate.
        return "exit"
    except KeyboardInterrupt:
        # Handle Ctrl+C (KeyboardInterrupt) gracefully.
        # Treat it as an 'exit' command to allow the main application to terminate.
        print("\nOperation interrupted.") # Provide immediate feedback
        return "exit"