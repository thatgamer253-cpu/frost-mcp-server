import sounddevice as sd
import numpy as np

def callback(indata, frames, time, status):
    pass

print("Host APIs:")
print(sd.query_hostapis())

print("\nScanning devices with callback...")
devices = sd.query_devices()

for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"Testing Device {i}: {dev['name']} (API: {dev['hostapi']})")
        for sr in [16000, 44100, 48000]:
            try:
                with sd.InputStream(device=i, channels=1, samplerate=sr, callback=callback):
                    print(f"  ✅ Works at {sr}Hz")
            except Exception as e:
                print(f"  ❌ Failed at {sr}Hz: {e}")
