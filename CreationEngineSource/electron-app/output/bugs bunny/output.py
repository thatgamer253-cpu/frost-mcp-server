import os
from dotenv import load_dotenv

load_dotenv()

def save_script(title, plot):
    """
    Save the generated script to a file.

    :param title: The title of the script.
    :param plot: The complete plot of the script.
    """
    try:
        # Ensure the output directory exists
        output_dir = os.getenv('OUTPUT_DIR', 'scripts')
        os.makedirs(output_dir, exist_ok=True)

        # Define the file path
        file_path = os.path.join(output_dir, f"{title.replace(' ', '_')}.txt")

        # Write the plot to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(plot)

        print(f"Script saved successfully at {file_path}")
    except Exception as e:
        print(f"An error occurred while saving the script: {e}")