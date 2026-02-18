import soundfile as sf
from kokoro_onnx import Kokoro
import numpy as np
import os
import requests

def download_file(url, filename):
    if not os.path.exists(filename):
        print(f"📥 Downloading {filename}...")
        r = requests.get(url, stream=True)
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ {filename} downloaded.")

try:
    # kokoro-onnx needs the onnx model and voices.bin
    # These are usually hosted on huggingface
    model_url = "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v0_19.onnx?download=true"
    voices_url = "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices.bin?download=true"
    
    download_file(model_url, "kokoro-v0_19.onnx")
    download_file(voices_url, "voices.bin")

    print("🚀 Initializing Kokoro-ONNX...")
    kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")

    text = "The Overlord Council is now offline-capable. Local ONNX test successful."
    
    print(f"🎙️ Generating speech: {text}")
    samples, sample_rate = kokoro.create(text, voice="af_heart", speed=1.0, lang="en-us")
    
    output_pf = "test_audio_onnx.wav"
    sf.write(output_pf, samples, sample_rate)
    print(f"💾 Saved to {output_pf}")

except Exception as e:
    print(f"❌ Error: {e}")
