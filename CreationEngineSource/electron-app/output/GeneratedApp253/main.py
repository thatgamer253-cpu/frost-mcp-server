import sys
from characters import generate_characters
from plot import generate_plot
from dialogue import generate_dialogue
from formatter import format_script

def main():
    try:
        if len(sys.argv) < 2:
            print("Usage: python main.py <script_title>")
            sys.exit(1)

        script_title = sys.argv[1]

        # Generate components of the script
        characters = generate_characters()
        plot = generate_plot()
        dialogue = generate_dialogue(characters)

        # Format the script
        script = format_script(script_title, characters, plot, dialogue)

        # Output the script
        print(script)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()