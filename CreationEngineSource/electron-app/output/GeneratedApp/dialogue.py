# dialogue.py

import pyttsx3

class Dialogue:
    def __init__(self, text):
        self.text = text
        self.engine = pyttsx3.init()
        self.configure_engine()

    def configure_engine(self):
        try:
            # Set properties for the speech engine
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 1)  # Volume 0.0 to 1.0
        except Exception as e:
            print(f"Error configuring text-to-speech engine: {e}")

    def speak(self):
        try:
            self.engine.say(self.text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error during text-to-speech conversion: {e}")

    def update_text(self, new_text):
        self.text = new_text

    def stop_speaking(self):
        try:
            self.engine.stop()
        except Exception as e:
            print(f"Error stopping the speech engine: {e}")