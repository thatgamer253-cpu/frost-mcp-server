import os
from pydub import AudioSegment
from pydub.playback import play
from pydub.exceptions import CouldntDecodeError

class SoundManager:
    def __init__(self, sound_directory):
        self.sound_directory = sound_directory
        self.sounds = {}
        self.load_sounds()

    def load_sounds(self):
        try:
            for filename in os.listdir(self.sound_directory):
                if filename.endswith('.mp3') or filename.endswith('.wav'):
                    sound_name = os.path.splitext(filename)[0]
                    sound_path = os.path.join(self.sound_directory, filename)
                    try:
                        self.sounds[sound_name] = AudioSegment.from_file(sound_path)
                    except CouldntDecodeError:
                        print(f"Error decoding sound file: {sound_path}")
        except FileNotFoundError:
            print(f"Sound directory not found: {self.sound_directory}")

    def play_sound(self, sound_name):
        if sound_name in self.sounds:
            try:
                play(self.sounds[sound_name])
            except Exception as e:
                print(f"Error playing sound {sound_name}: {e}")
        else:
            print(f"Sound {sound_name} not found.")

    def stop_sound(self, sound_name):
        # PyDub does not support stopping a sound once it starts playing.
        # This method is a placeholder for future implementation if needed.
        print(f"Stopping sound is not supported for {sound_name}.")

    def list_sounds(self):
        return list(self.sounds.keys())