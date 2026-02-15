from dotenv import load_dotenv
import os
from script_generator import generate_script
from animation import create_animation
from audio import generate_audio
from video_compiler import compile_video

load_dotenv()

def main():
    try:
        # Get user input
        script_topic = input("Enter the topic for the script: ").strip()

        # Generate script
        script = generate_script(script_topic)
        print("Script generated successfully.")

        # Create animation
        animation_file = create_animation(script)
        print("Animation created successfully.")

        # Generate audio
        audio_file = generate_audio(script, "en")  # Assuming the function requires a language parameter
        print("Audio generated successfully.")

        # Compile video
        video_file = compile_video(animation_file, audio_file)
        print(f"Video compiled successfully: {video_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()