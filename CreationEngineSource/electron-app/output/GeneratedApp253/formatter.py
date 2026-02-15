def format_script(title, characters, plot, dialogue):
    try:
        # Format the title
        formatted_title = f"Title: {title}\n\n"

        # Format the characters
        formatted_characters = "Characters:\n" + "\n".join(str(character) for character in characters) + "\n\n"

        # Format the plot
        formatted_plot = (
            "Plot:\n"
            f"Setting: {plot['setting']}\n"
            f"Conflict: {plot['conflict']}\n"
            f"Resolution: {plot['resolution']}\n\n"
        )

        # Format the dialogue
        formatted_dialogue = "Dialogue:\n" + "\n".join(dialogue) + "\n"

        # Combine all parts into the final script
        formatted_script = (
            formatted_title +
            formatted_characters +
            formatted_plot +
            formatted_dialogue
        )

        return formatted_script

    except Exception as e:
        print(f"An error occurred while formatting the script: {e}")
        return "Script formatting failed."