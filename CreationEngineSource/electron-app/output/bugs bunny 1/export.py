import os
from moviepy import ImageSequenceClip

class AnimationExporter:
    def __init__(self, sprite_folder, output_file, fps=30):
        self.sprite_folder = sprite_folder
        self.output_file = output_file
        self.fps = fps
        self.sprites = []

    def load_sprites(self):
        try:
            for file_name in sorted(os.listdir(self.sprite_folder)):
                if file_name.endswith('.png'):
                    self.sprites.append(os.path.join(self.sprite_folder, file_name))
            if not self.sprites:
                raise ValueError("No sprites found in the specified folder.")
        except Exception as e:
            print(f"Error loading sprites: {e}")

    def export_to_video(self):
        try:
            if not self.sprites:
                self.load_sprites()
            clip = ImageSequenceClip(self.sprites, fps=self.fps)
            clip.write_videofile(self.output_file, codec='libx264')
        except Exception as e:
            print(f"Error exporting video: {e}")

def main():
    sprite_folder = 'path/to/character/sprites'
    output_file = 'output/animation.mp4'
    exporter = AnimationExporter(sprite_folder, output_file)
    exporter.export_to_video()

if __name__ == "__main__":
    main()