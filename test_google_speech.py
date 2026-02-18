import speech_recognition as sr
import numpy as np

def test_recog():
    r = sr.Recognizer()
    # Create silent audio
    audio = sr.AudioData(np.zeros(16000*2, dtype='int16').tobytes(), 16000, 2)
    print("Testing Google Speech Recognition connectivity...")
    try:
        r.recognize_google(audio)
        print("Google API seems reachable (rejected silence as expected).")
    except sr.UnknownValueError:
        print("Google API reachable (Success: UnknownValue for silence).")
    except Exception as e:
        print(f"Connectivity check failed: {e}")

if __name__ == "__main__":
    test_recog()
