# video_compiler.py

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import os

def compile_video(animation_file, audio_file):
    """
    Compiles an animation and audio file into a final video.

    Args:
        animation_file (str): The file path of the animation video.
        audio_file (str): The file path of the audio file.

    Returns:
        str: The file path of the compiled video.
    """
    try:
        # Load the animation and audio files
        video_clip = VideoFileClip(animation_file)
        audio_clip = AudioFileClip(audio_file)

        # Set the audio of the video clip
        final_video = video_clip.set_audio(audio_clip)

        # Define the output file path
        output_file = "final_video.mp4"

        # Write the final video to a file
        final_video.write_videofile(output_file, codec="libx264", audio_codec="aac")

        # Close the clips to release resources
        video_clip.close()
        audio_clip.close()

        return output_file

    except Exception as e:
        print(f"An error occurred while compiling the video: {e}")
        raise