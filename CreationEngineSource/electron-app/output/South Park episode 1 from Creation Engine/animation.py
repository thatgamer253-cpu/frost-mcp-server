# animation.py

from manim import Scene, Text, FadeIn, FadeOut, Write
import os

def create_animation(script):
    """
    Creates an animation based on the provided script using the Manim library.

    Args:
        script (str): The script for which to create the animation.

    Returns:
        str: The file path of the created animation video.
    """
    try:
        # Define a custom scene class
        class ScriptScene(Scene):
            def construct(self):
                # Split the script into lines
                lines = script.split('\n')
                for line in lines:
                    # Create a text object for each line
                    text = Text(line)
                    # Add the text to the scene with an animation
                    self.play(Write(text))
                    self.wait(2)
                    self.play(FadeOut(text))

        # Define the output file path
        output_file = "script_animation.mp4"

        # Render the scene
        scene = ScriptScene()
        scene.render()

        # Move the output file to the desired location
        os.rename(scene.renderer.file_writer.movie_file_path, output_file)

        return output_file

    except Exception as e:
        print(f"An error occurred while creating the animation: {e}")
        raise