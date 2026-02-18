import soundfile as sf
try:
    from kokoro import KPipeline
    import numpy as np
    import os

    print("🚀 Initializing Kokoro Pipeline...")
    # 'a' for American English
    pipeline = KPipeline(lang_code='a') 

    text = "The Overlord Council is now offline-capable. Local TTS test successful."
    
    # Generate audio
    # voice='af_heart' is a high quality female voice
    generator = pipeline(text, voice='af_heart', speed=1.1, split_pattern=r'\n+')
    
    for i, (gs, ps, audio) in enumerate(generator):
        print(f"✅ Generated segment {i}")
        sf.write(f'test_audio_{i}.wav', audio, 24000)
        print(f"💾 Saved to test_audio_{i}.wav")

except Exception as e:
    print(f"❌ Error: {e}")
