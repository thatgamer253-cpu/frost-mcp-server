import winsound
import time
print("Attempting to play a system beep on the default output device...")
for i in range(3):
    print(f"Beep {i+1}...")
    winsound.Beep(1000, 500)
    time.sleep(0.5)
print("Diagnostic complete. If you didn't hear 3 beeps, your Windows Default Playback device is not set to your current speakers/headset.")
