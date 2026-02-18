#!/usr/bin/env python3
import sounddevice as sd
import numpy as np
import time

def scan_mics():
    devices = sd.query_devices()
    input_devices = [i for i, d in enumerate(devices) if d['max_input_channels'] > 0]
    
    print("--- MIC SENSITIVITY SCAN ---")
    print("Please Speak/Make noise now...")
    
    results = []
    for i in input_devices:
        name = devices[i]['name']
        print(f"Testing Device {i}: {name}...")
        try:
            # Short 1s samples to check for noise
            recording = sd.rec(int(16000 * 1.5), samplerate=16000, channels=1, dtype='int16', device=i)
            sd.wait()
            max_amp = np.max(np.abs(recording))
            print(f"  > MAX AMPLITUDE: {max_amp}")
            results.append((i, name, max_amp))
        except Exception as e:
            print(f"  > FAILED: {e}")
            
    print("\n--- SCAN RESULTS ---")
    sorted_results = sorted(results, key=lambda x: x[2], reverse=True)
    for r in sorted_results:
        print(f"[{r[0]}] {r[1]}: {r[2]}")
        
    if sorted_results and sorted_results[0][2] > 100:
        print(f"\nRecommended Device Index: {sorted_results[0][0]}")
    else:
        print("\nNo signal detected on any device. Check Windows Mute settings.")

if __name__ == "__main__":
    scan_mics()
