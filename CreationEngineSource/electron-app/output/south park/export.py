import os
from PIL import Image
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

class Export:
    def __init__(self, animation_content, voice_content):
        self.animation_content = animation_content
        self.voice_content = voice_content

    def export_episode(self):
        try:
            # Load the voice audio file
            audio_clip = AudioFileClip(self.voice_content)

            # Load and concatenate animation clips
            video_clips = [VideoFileClip(scene) for scene in self.animation_content]
            final_video = concatenate_videoclips(video_clips, method="compose")

            # Set the audio to the final video
            final_video = final_video.set_audio(audio_clip)

            # Export the final video
            output_path = os.getenv('FINAL_VIDEO_OUTPUT_PATH', 'final_episode.mp4')
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

            # Clean up temporary files
            self.cleanup_temp_files()

            return output_path
        except Exception as e:
            print(f"Error exporting episode: {str(e)}")
            return None

    def cleanup_temp_files(self):
        try:
            # Remove temporary files if they exist
            if os.path.exists(self.voice_content):
                os.remove(self.voice_content)
            for scene in self.animation_content:
                if os.path.exists(scene):
                    os.remove(scene)
        except Exception as e:
            print(f"Error cleaning up temporary files: {str(e)}")