#!/usr/bin/env python3
import os
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import winsound

print("VOICE-LESS DEBUG MODE")
device_index = 16 # Trying the HD Audio Mic directly
sample_rate = 16000
recognizer = sr.Recognizer()

print(f"Listening on Index {device_index}: {sd.query_devices(device_index)['name']}")

while True:
    try:
        duration = 3.0
        recording = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='int16',
            device=device_index
        )
        sd.wait()

        amp = np.max(np.abs(recording))
        bars = int((amp / 1000) * 10)
        print(f"LEVEL: {'#'*bars} ({amp})")
        
        if amp > 500:
            print("Processing...")
            audio_data = sr.AudioData(recording.tobytes(), sample_rate, 2)
            try:
                text = recognizer.recognize_google(audio_data).lower()
                print(f"HEARD: {text}")
                if "hello" in text or "overlord" in text:
                    winsound.Beep(1000, 200)
                    print("!!! TRIGGER !!!")
            except:
                print("... unclear ...")

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
