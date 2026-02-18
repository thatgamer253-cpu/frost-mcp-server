import pyttsx3
import winsound
import os
import time

def test_manual_playback():
    print("Initializing pyttsx3...")
    engine = pyttsx3.init()
    text = "This is a direct wave playback test. Checking for audio output."
    filename = "test_output.wav"
    
    if os.path.exists(filename):
        os.remove(filename)
        
    print(f"Saving speech to {filename}...")
    engine.save_to_file(text, filename)
    engine.runAndWait()
    
    # Wait a bit for file to be ready
    time.sleep(1)
    
    if os.path.exists(filename):
        print(f"File created ({os.path.getsize(filename)} bytes). Playing via winsound...")
        winsound.PlaySound(filename, winsound.SND_FILENAME)
        print("Playback finished.")
    else:
        print("Failed to create WAV file.")

if __name__ == "__main__":
    test_manual_playback()
