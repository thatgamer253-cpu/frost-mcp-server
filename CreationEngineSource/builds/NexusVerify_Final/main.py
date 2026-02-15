import sys
from typing import NoReturn

import config
import calculator_logic
import input_handler
import output_handler
from exceptions import CalculatorError, InvalidInputError, UnsupportedOperatorError, DivisionByZeroError

def run_calculator() -> NoReturn:
    """
    Main function to run the calculator application.
    It orchestrates the user interaction, input parsing, calculation,
    and result display, handling various errors gracefully.
    It distinguishes between interactive and non-interactive (e.g., piped input)
    modes to provide appropriate behavior and prevent indefinite blocking.
    """
    output_handler.display_message(config.WELCOME_MESSAGE)
    output_handler.display_message(config.HELP_MESSAGE)

    is_interactive = sys.stdin.isatty()

    if not is_interactive:
        # Non-interactive mode: Process input line by line from stdin until EOF.
        # This prevents indefinite blocking if input_handler.get_user_input
        # were to block on an empty non-interactive stream.
        output_handler.display_message("Running in non-interactive mode. Processing input from stdin...")
        for line in sys.stdin:
            user_input = line.strip()

            if not user_input:
                # Skip empty lines in non-interactive mode.
                # If an empty line should signal an exit, this logic would need adjustment.
                continue

            try:
                if user_input.lower() in config.EXIT_COMMANDS:
                    output_handler.display_message("Exit command received in non-interactive mode. Exiting.")
                    sys.exit(0)
                elif user_input.lower() in config.HELP_COMMANDS:
                    output_handler.display_message(config.HELP_MESSAGE)
                    continue

                # Attempt to parse the user's expression
                num1, operator, num2 = input_handler.parse_expression(user_input)

                # Perform the calculation
                result = calculator_logic.calculate(num1, operator, num2)

                # Display the result
                output_handler.display_result(result)

            except (InvalidInputError, UnsupportedOperatorError, DivisionByZeroError) as e:
                output_handler.display_error(str(e))
                sys.exit(1) # Exit with a non-zero status code to indicate an error in non-interactive mode
            except CalculatorError as e:
                output_handler.display_error(f"An unexpected calculator error occurred: {e}")
                sys.exit(1)
            except Exception as e:
                output_handler.display_error(f"An unexpected system error occurred: {e}")
                sys.exit(1)
        
        # If the loop finishes, it means EOF was reached on stdin.
        output_handler.display_message("End of input detected (non-interactive). Exiting calculator. Goodbye!")
        sys.exit(0)

    else:
        # Interactive mode: Loop indefinitely, prompting the user for input.
        while True:
            try:
                user_input = input_handler.get_user_input(config.PROMPT_MESSAGE)

                if user_input.lower() in config.EXIT_COMMANDS:
                    output_handler.display_message("Exiting calculator. Goodbye!")
                    sys.exit(0)
                elif user_input.lower() in config.HELP_COMMANDS:
                    output_handler.display_message(config.HELP_MESSAGE)
                    continue

                # Attempt to parse the user's expression
                num1, operator, num2 = input_handler.parse_expression(user_input)

                # Perform the calculation
                result = calculator_logic.calculate(num1, operator, num2)

                # Display the result
                output_handler.display_result(result)

            except EOFError:
                # Handle end-of-file condition (e.g., when Ctrl+D is pressed in interactive mode).
                output_handler.display_message("\nEnd of input detected. Exiting calculator. Goodbye!")
                sys.exit(0)
            except (InvalidInputError, UnsupportedOperatorError, DivisionByZeroError) as e:
                # Catch specific calculator-related errors and display user-friendly messages.
                # In interactive mode, we display the error and continue the loop.
                output_handler.display_error(str(e))
            except CalculatorError as e:
                # Catch any other custom CalculatorError that might arise.
                output_handler.display_error(f"An unexpected calculator error occurred: {e}")
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully.
                output_handler.display_message("\nKeyboardInterrupt detected. Exiting calculator. Goodbye!")
                sys.exit(0)
            except Exception as e:
                # Catch any other unexpected system errors.
                output_handler.display_error(f"An unexpected system error occurred: {e}")

if __name__ == "__main__":
    run_calculator()