import pyttsx3
print("Testing pyttsx3 on all available voices at max volume.")
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('volume', 1.0)
    engine.setProperty('rate', 180)
    
    for i, voice in enumerate(voices):
        print(f"Testing Voice {i}: {voice.name}")
        engine.setProperty('voice', voice.id)
        engine.say(f"I am speaking using voice index {i}. My name is {voice.name}. Can you hear this?")
    
    engine.runAndWait()
    print("Test finished.")
except Exception as e:
    print(f"Error: {e}")
