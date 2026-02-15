import os
from gtts import gTTS

def generate_audio(script_text, language='en'):
    """
    Generate audio from text using gTTS.
    Matches the signature expected by main.py
    """
    try:
        tts = gTTS(text=script_text, lang=language)
        filename = "script_audio.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"Error in generate_audio: {e}")
        # Fallback to an empty file if needed
        return None