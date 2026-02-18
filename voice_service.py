import os
import threading
import queue
import time
import soundfile as sf
import numpy as np
import logging
import asyncio
from typing import Optional, List, Dict
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceService")

try:
    from kokoro_onnx import Kokoro
except Exception as e:
    logger.error(f"Failed to import Kokoro-ONNX: {e}. DLL issues or missing deps.")
    Kokoro = None

class VoiceService:
    """
    Thread-safe voice service using Kokoro-ONNX for offline TTS with Edge-TTS fallback.
    Maintains a queue of speech tasks to prevent audio overlap.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VoiceService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.model_path = "kokoro-v0_19.onnx"
        self.voices_path = "voices.bin"
        self.kokoro: Optional[Kokoro] = None
        self.speech_queue = queue.Queue()
        self.is_playing = False
        self.enabled = True
        
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        logger.info(f"Voice Service {'enabled' if enabled else 'disabled'}.")
        
        # Audio device
        try:
            import sounddevice as sd
            self.sd = sd
            
            # Diagnostic Check
            try:
                device_info = sd.query_devices(kind='output')
                if not device_info:
                    logger.warning("⚠️ No output audio devices found. TTS will be silent.")
                else:
                    logger.info(f"🔊 Audio Output: {device_info['name']}")
            except Exception:
                logger.warning("Could not query audio devices.")

        except ImportError:
            logger.warning("sounddevice not installed. Audio playback will be skipped.")
            self.sd = None

        self._start_worker()
        self._initialized = True

    def _start_worker(self):
        """Starts the background worker that processes the speech queue."""
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _lazy_init(self) -> bool:
        """Initialize Kokoro only when needed."""
        if self.kokoro is not None:
            return True
        
        # Check for espeak-ng (required by phonemizer backend of Kokoro)
        import shutil
        if shutil.which("espeak-ng") is None and not os.path.exists(r"C:\Program Files\eSpeak NG\espeak-ng.exe"):
            logger.warning("espeak-ng not found. Kokoro TTS disabled. Using Edge-TTS fallback.")
            return False

        if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
            logger.warning("Local TTS Model files missing. Will attempt fallback to Edge-TTS.")
            return False

        try:
            if Kokoro is None:
                raise ImportError("Kokoro module not available")
            logger.info("Initializing Kokoro-ONNX...")
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            return True
        except Exception as e:
            logger.error(f"Failed to load Kokoro: {e}. Falling back to Edge-TTS.")
            return False

    def speak(self, text: str, voice: str = "af_heart", speed: float = 1.0):
        """Queue a text-to-speech task."""
        if not self.enabled or not text:
            return
        
        # Clean text for phonemizer (Kokoro can be picky)
        text = text.replace("*", "").replace("_", "").replace("#", "").strip()
        if not text: return

        logger.info(f"Queuing speech: [{voice}] {text[:50]}...")
        self.speech_queue.put({
            "text": text,
            "voice": voice,
            "speed": speed
        })

    def _speech_worker(self):
        """Background thread processing the speech queue."""
        while True:
            try:
                task = self.speech_queue.get()
                if not self.enabled:
                    self.speech_queue.task_done()
                    continue

                self.is_playing = True
                try:
                    text = task["text"]
                    voice = task["voice"]
                    speed = task["speed"]

                    success = False
                    # 1. Try Local Kokoro
                    if self._lazy_init():
                        try:
                            samples, sample_rate = self.kokoro.create(
                                text, voice=voice, speed=speed, lang="en-us"
                            )
                            if self.sd:
                                self.sd.play(samples, sample_rate)
                                self.sd.wait()
                                success = True
                        except Exception as e:
                            logger.error(f"Kokoro Synthesis Error: {e}")

                    # 2. Fallback to Edge-TTS if Kokoro failed or missing
                    if not success:
                        try:
                            logger.info("Attempting Edge-TTS fallback...")
                            import edge_tts
                            import tempfile
                            
                            # Edge voice mapping
                            edge_voice = "en-US-AndrewNeural" if "am_" in voice else "en-US-EmmaNeural"
                            
                            async def _edge_speak():
                                communicate = edge_tts.Communicate(text, edge_voice, rate=f"+{int((speed-1)*100)}%")
                                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                                    tmp_path = tf.name
                                await communicate.save(tmp_path)
                                
                                data, fs = sf.read(tmp_path)
                                if self.sd:
                                    try:
                                        self.sd.play(data, fs)
                                        self.sd.wait()
                                    except Exception as e:
                                        logger.error(f"Playback Error: {e}")
                                os.unlink(tmp_path)

                            asyncio.run(_edge_speak())
                            success = True
                        except ImportError:
                            logger.error("edge-tts not installed. Cannot fallback.")
                        except Exception as e:
                            logger.error(f"Edge-TTS Error: {e}")

                except Exception as e:
                    logger.error(f"Worker task error: {e}")
                finally:
                    self.is_playing = False
                    self.speech_queue.task_done()

            except Exception as e:
                logger.error(f"Worker loop exception: {e}")
                time.sleep(1)

voice_service = VoiceService()

if __name__ == "__main__":
    # Test script
    vs = VoiceService()
    vs.speak("Initializing tactical voice protocols. Sentinel is active.", voice="af_heart")
    vs.speak("System health at 98 percent. No anomalies detected.", voice="am_adam")
    time.sleep(10)
