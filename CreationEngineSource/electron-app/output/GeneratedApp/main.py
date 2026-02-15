import os
from dotenv import load_dotenv
from cli import handle_cli
from gui import launch_gui
from image_generator import generate_image, ImageGenerationError
from style_filter import apply_style_filter
from scene_composer import compose_scene
from exporter import export_scene

def main():
    # Load environment variables
    load_dotenv()

    try:
        # Handle command-line interface
        handle_cli()

        # Launch the graphical user interface
        launch_gui()

        # Example workflow
        prompt = "A serene landscape with mountains"
        image_data = generate_image(prompt)
        styled_image = apply_style_filter(image_data, "vintage")
        scene = compose_scene(styled_image)
        export_scene(scene, "output/scene.png")

    except ImageGenerationError as e:
        print(f"Image generation failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()