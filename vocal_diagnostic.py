#!/usr/bin/env python3
import pyttsx3
import sounddevice as sd
import time

def test_voice():
    print("Listing Speakers and Output Devices...")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            print(f"  [{i}] {dev['name']}")

    print("\nAttempting to initialize Vocal Bridge (pyttsx3)...")
    try:
        engine = pyttsx3.init()
        rate = engine.getProperty('rate')
        engine.setProperty('rate', 150)
        
        print(f"Default Voice Rate: {rate}")
        print("Speaking: 'Testing Overlord Vocal Cords. Can you hear me?'")
        
        engine.say("Testing Overlord Vocal Cords. Can you hear me?")
        engine.runAndWait()
        print("Done.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_voice()
