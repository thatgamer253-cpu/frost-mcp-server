import os
from gtts import gTTS

class Voice:
    def __init__(self, script_content):
        self.script_content = script_content

    def generate_voice(self):
        try:
            # Generate voice using gTTS
            tts = gTTS(text=self.script_content, lang='en')
            voice_file_path = os.getenv('VOICE_FILE_PATH', 'output_voice.mp3')
            tts.save(voice_file_path)
            return voice_file_path
        except Exception as e:
            print(f"Error generating voice: {str(e)}")
            return None