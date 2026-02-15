#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Media Engine
  Unified interface for AI image generation and video processing.
  Providers: Flux 2.0, Adobe Firefly, Midjourney, Ideogram,
             HandBrake (transcoding), GStreamer (streaming)
==============================================================
"""

import os
import sys
import json
import time
import shutil
import subprocess
import requests
import base64
import tempfile
from datetime import datetime

# Force UTF-8 encoding for Windows pipes (cp1252 fix)
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


# ── Helpers ──────────────────────────────────────────────────

def _log(tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}]  {msg}", flush=True)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _save_image_from_url(url, output_path):
    """Download an image from a URL and save to disk."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path


def _save_image_from_b64(b64_data, output_path):
    """Decode base64 image data and save to disk."""
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(b64_data))
    return output_path


# ══════════════════════════════════════════════════════════════
#  IMAGE GENERATION PROVIDERS
# ══════════════════════════════════════════════════════════════

class FluxProvider:
    """Flux 2.0 via fal.ai REST API."""

    NAME = "Flux 2.0"
    ENV_KEY = "FLUX_API_KEY"
    BASE_URL = "https://fal.run/fal-ai/flux-pro/v2"

    def __init__(self):
        self.api_key = os.environ.get(self.ENV_KEY, "")

    @property
    def available(self):
        return bool(self.api_key)

    def generate(self, prompt, output_path, width=1024, height=1024, **kwargs):
        """Generate an image using Flux 2.0 Pro via fal.ai."""
        _log("FLUX", f"Generating: {prompt[:60]}…")

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "safety_tolerance": "2",
        }
        payload.update(kwargs)

        resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # fal.ai returns images array with url field
        image_url = data.get("images", [{}])[0].get("url", "")
        if not image_url:
            raise RuntimeError(f"Flux API returned no image URL: {data}")

        _save_image_from_url(image_url, output_path)
        _log("FLUX", f"  ✓ Saved: {os.path.basename(output_path)}")
        return output_path


class FireflyProvider:
    """Adobe Firefly via official Adobe Firefly Services API."""

    NAME = "Adobe Firefly"
    ENV_CLIENT_ID = "FIREFLY_CLIENT_ID"
    ENV_CLIENT_SECRET = "FIREFLY_CLIENT_SECRET"
    TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
    GENERATE_URL = "https://firefly-api.adobe.io/v3/images/generate"

    def __init__(self):
        self.client_id = os.environ.get(self.ENV_CLIENT_ID, "")
        self.client_secret = os.environ.get(self.ENV_CLIENT_SECRET, "")
        self._token = None
        self._token_expiry = 0

    @property
    def available(self):
        return bool(self.client_id and self.client_secret)

    def _get_token(self):
        """Obtain an OAuth access token from Adobe IMS."""
        if self._token and time.time() < self._token_expiry:
            return self._token

        resp = requests.post(self.TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid,AdobeID,firefly_enterprise,firefly_api,ff_apis"
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
        return self._token

    def generate(self, prompt, output_path, width=1024, height=1024, **kwargs):
        """Generate an image using Adobe Firefly."""
        _log("FIREFLY", f"Generating: {prompt[:60]}…")

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": self.client_id,
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "n": 1,
            "size": {"width": width, "height": height},
        }
        payload.update(kwargs)

        resp = requests.post(self.GENERATE_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Firefly returns outputs array with base64 or url
        outputs = data.get("outputs", [])
        if not outputs:
            raise RuntimeError(f"Firefly API returned no outputs: {data}")

        image_data = outputs[0]
        if "image" in image_data and "url" in image_data["image"]:
            _save_image_from_url(image_data["image"]["url"], output_path)
        elif "base64" in image_data:
            _save_image_from_b64(image_data["base64"], output_path)
        else:
            raise RuntimeError(f"Firefly: unexpected output format: {image_data}")

        _log("FIREFLY", f"  ✓ Saved: {os.path.basename(output_path)}")
        return output_path


class MidjourneyProvider:
    """Midjourney via unofficial proxy API (piapi.ai or similar)."""

    NAME = "Midjourney"
    ENV_KEY = "MIDJOURNEY_API_KEY"
    BASE_URL = "https://api.piapi.ai/api/v1/task"

    def __init__(self):
        self.api_key = os.environ.get(self.ENV_KEY, "")

    @property
    def available(self):
        return bool(self.api_key)

    def generate(self, prompt, output_path, **kwargs):
        """Generate an image using Midjourney via proxy API."""
        _log("MIDJOURNEY", f"Generating: {prompt[:60]}…")

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Step 1: Submit the imagine task
        payload = {
            "model": "midjourney",
            "task_type": "imagine",
            "input": {
                "prompt": prompt,
                "aspect_ratio": kwargs.get("aspect_ratio", "1:1"),
                "process_mode": kwargs.get("process_mode", "fast"),
            }
        }

        resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        task_data = resp.json()

        task_id = task_data.get("data", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError(f"Midjourney: no task_id returned: {task_data}")

        # Step 2: Poll for completion
        _log("MIDJOURNEY", "  Waiting for generation…")
        status_url = f"{self.BASE_URL}/{task_id}"
        for _ in range(60):  # 5 min max
            time.sleep(5)
            status_resp = requests.get(status_url, headers=headers, timeout=30)
            status_resp.raise_for_status()
            status_data = status_resp.json()

            task_status = status_data.get("data", {}).get("status", "")
            if task_status == "completed":
                image_url = status_data["data"].get("output", {}).get("image_url", "")
                if not image_url:
                    # Try alternative response structure
                    image_urls = status_data["data"].get("output", {}).get("image_urls", [])
                    image_url = image_urls[0] if image_urls else ""

                if not image_url:
                    raise RuntimeError(f"Midjourney: completed but no image URL: {status_data}")

                _save_image_from_url(image_url, output_path)
                _log("MIDJOURNEY", f"  ✓ Saved: {os.path.basename(output_path)}")
                return output_path

            elif task_status == "failed":
                raise RuntimeError(f"Midjourney generation failed: {status_data}")

        raise TimeoutError("Midjourney generation timed out after 5 minutes.")


class IdeogramProvider:
    """Ideogram via official API."""

    NAME = "Ideogram"
    ENV_KEY = "IDEOGRAM_API_KEY"
    BASE_URL = "https://api.ideogram.ai/generate"

    def __init__(self):
        self.api_key = os.environ.get(self.ENV_KEY, "")

    @property
    def available(self):
        return bool(self.api_key)

    def generate(self, prompt, output_path, width=1024, height=1024, **kwargs):
        """Generate an image using Ideogram."""
        _log("IDEOGRAM", f"Generating: {prompt[:60]}…")

        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Map dimensions to closest aspect ratio
        aspect = "ASPECT_1_1"
        ratio = width / height if height else 1
        if ratio > 1.4:
            aspect = "ASPECT_16_9"
        elif ratio < 0.7:
            aspect = "ASPECT_9_16"
        elif ratio > 1.2:
            aspect = "ASPECT_4_3"
        elif ratio < 0.85:
            aspect = "ASPECT_3_4"

        payload = {
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": kwargs.get("aspect_ratio", aspect),
                "model": kwargs.get("model", "V_2"),
                "magic_prompt_option": "AUTO",
            }
        }

        resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        images = data.get("data", [])
        if not images:
            raise RuntimeError(f"Ideogram API returned no images: {data}")

        image_url = images[0].get("url", "")
        if not image_url:
            raise RuntimeError(f"Ideogram: no URL in response: {images[0]}")

        _save_image_from_url(image_url, output_path)
        _log("IDEOGRAM", f"  ✓ Saved: {os.path.basename(output_path)}")
        return output_path


# ══════════════════════════════════════════════════════════════
#  VIDEO PROCESSING ENGINES
# ══════════════════════════════════════════════════════════════

class HandBrakeEngine:
    """Video transcoding via HandBrakeCLI."""

    NAME = "HandBrake"

    # Common presets for quick access
    PRESETS = {
        "default": "Fast 1080p30",
        "web": "Gmail Large 3 Minutes 720p30",
        "hq": "HQ 1080p30 Surround",
        "4k": "HQ 2160p60 4K HEVC Surround",
        "fast": "Very Fast 720p30",
        "mobile": "Android 720p30",
    }

    def __init__(self):
        self.cli_path = shutil.which("HandBrakeCLI")
        if not self.cli_path:
            # Also check common Windows install paths
            common_paths = [
                r"C:\Program Files\HandBrake\HandBrakeCLI.exe",
                r"C:\Program Files (x86)\HandBrake\HandBrakeCLI.exe",
            ]
            for p in common_paths:
                if os.path.isfile(p):
                    self.cli_path = p
                    break

    @property
    def available(self):
        return bool(self.cli_path)

    def transcode(self, input_path, output_path, preset="default",
                  extra_args=None):
        """Transcode a video file using HandBrakeCLI.
        
        Args:
            input_path:  Source video file
            output_path: Destination file (extension determines container)
            preset:      Preset name (key from PRESETS dict or raw HandBrake preset)
            extra_args:  Additional CLI arguments as a list
        """
        if not self.cli_path:
            raise RuntimeError(
                "HandBrakeCLI not found. Install HandBrake and ensure "
                "HandBrakeCLI is on your PATH."
            )

        resolved_preset = self.PRESETS.get(preset, preset)
        _log("HANDBRAKE", f"Transcoding: {os.path.basename(input_path)} → "
                          f"{os.path.basename(output_path)} [{resolved_preset}]")

        cmd = [
            self.cli_path,
            "-i", input_path,
            "-o", output_path,
            "--preset", resolved_preset,
        ]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            _log("ERROR", f"  HandBrake failed: {result.stderr[:300]}")
            raise RuntimeError(f"HandBrake exited with code {result.returncode}")

        _log("HANDBRAKE", f"  ✓ Transcoded: {os.path.basename(output_path)}")
        return output_path

    def probe(self, input_path):
        """Get media info via HandBrakeCLI --scan."""
        if not self.cli_path:
            raise RuntimeError("HandBrakeCLI not found.")

        result = subprocess.run(
            [self.cli_path, "-i", input_path, "--scan", "-t", "0"],
            capture_output=True, text=True, timeout=30
        )
        return result.stderr  # HandBrake outputs scan info to stderr


class GStreamerEngine:
    """Video streaming/processing via GStreamer (gst-launch-1.0)."""

    NAME = "GStreamer"

    def __init__(self):
        self.cli_path = shutil.which("gst-launch-1.0")
        if not self.cli_path:
            # Check common Windows paths
            common_paths = [
                r"C:\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe",
                r"C:\gstreamer\1.0\x86_64\bin\gst-launch-1.0.exe",
            ]
            for p in common_paths:
                if os.path.isfile(p):
                    self.cli_path = p
                    break

        self.inspect_path = shutil.which("gst-inspect-1.0")

    @property
    def available(self):
        return bool(self.cli_path)

    def launch_pipeline(self, pipeline_desc, timeout=None):
        """Run a GStreamer pipeline synchronously.
        
        Args:
            pipeline_desc: GStreamer pipeline string
                           e.g. "filesrc location=input.mp4 ! decodebin ! 
                                 x264enc ! mp4mux ! filesink location=out.mp4"
            timeout:       Max seconds to run (None = unlimited)
        
        Returns:
            subprocess.CompletedProcess
        """
        if not self.cli_path:
            raise RuntimeError(
                "gst-launch-1.0 not found. Install GStreamer and ensure "
                "it's on your PATH."
            )

        _log("GSTREAMER", f"Launching pipeline: {pipeline_desc[:80]}…")

        cmd = [self.cli_path, "-e"] + pipeline_desc.split()
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout or 600)

        if result.returncode != 0:
            _log("ERROR", f"  GStreamer failed: {result.stderr[:300]}")
            raise RuntimeError(f"GStreamer exited with code {result.returncode}")

        _log("GSTREAMER", "  ✓ Pipeline completed.")
        return result

    def launch_pipeline_async(self, pipeline_desc):
        """Start a GStreamer pipeline in the background (for live streaming).
        
        Returns:
            subprocess.Popen object (caller is responsible for termination)
        """
        if not self.cli_path:
            raise RuntimeError("gst-launch-1.0 not found.")

        _log("GSTREAMER", f"Starting async pipeline: {pipeline_desc[:80]}…")
        cmd = [self.cli_path, "-e"] + pipeline_desc.split()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _log("GSTREAMER", f"  ✓ Pipeline running (PID: {proc.pid})")
        return proc

    def convert(self, input_path, output_path, video_codec="x264enc",
                audio_codec="voaacenc"):
        """Simple file conversion using GStreamer.
        
        A convenience wrapper over launch_pipeline for basic transcoding.
        """
        pipeline = (
            f"filesrc location={input_path} ! decodebin name=demux "
            f"demux. ! queue ! videoconvert ! {video_codec} ! mux. "
            f"demux. ! queue ! audioconvert ! {audio_codec} ! mux. "
            f"mp4mux name=mux ! filesink location={output_path}"
        )
        return self.launch_pipeline(pipeline)

    def list_plugins(self):
        """List available GStreamer plugins."""
        if not self.inspect_path:
            return "gst-inspect-1.0 not found."

        result = subprocess.run(
            [self.inspect_path], capture_output=True, text=True, timeout=10
        )
        return result.stdout


# ══════════════════════════════════════════════════════════════
#  UNIFIED MEDIA ENGINE
# ══════════════════════════════════════════════════════════════

class MediaEngine:
    """Unified interface that auto-routes to the best available provider."""

    # Priority order for image generation
    PROVIDER_PRIORITY = ["flux", "ideogram", "firefly", "midjourney"]

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or tempfile.gettempdir()
        _ensure_dir(self.output_dir)

        # Initialize all providers
        self.providers = {
            "flux": FluxProvider(),
            "firefly": FireflyProvider(),
            "midjourney": MidjourneyProvider(),
            "ideogram": IdeogramProvider(),
        }

        # Initialize video engines
        self.handbrake = HandBrakeEngine()
        self.gstreamer = GStreamerEngine()

        # Log availability
        self._log_status()

    def _log_status(self):
        _log("MEDIA", "═══ Media Engine Status ═══")

        for name, provider in self.providers.items():
            status = "✓ READY" if provider.available else "✗ No API key"
            _log("MEDIA", f"  {provider.NAME:18s} {status}")

        hb_status = "✓ READY" if self.handbrake.available else "✗ Not installed"
        gs_status = "✓ READY" if self.gstreamer.available else "✗ Not installed"
        _log("MEDIA", f"  {'HandBrake':18s} {hb_status}")
        _log("MEDIA", f"  {'GStreamer':18s} {gs_status}")
        _log("MEDIA", "═══════════════════════════")

    def get_available_providers(self):
        """Return list of provider names that have API keys configured."""
        return [name for name, p in self.providers.items() if p.available]

    # ── Image Generation ────────────────────────────────────

    def generate_image(self, prompt, provider="auto", filename=None,
                       width=1024, height=1024, **kwargs):
        """Generate an image using the specified or best available provider.
        
        Args:
            prompt:    Text description of the image
            provider:  "flux", "firefly", "midjourney", "ideogram", or "auto"
            filename:  Output filename (auto-generated if None)
            width:     Image width in pixels
            height:    Image height in pixels
            **kwargs:  Provider-specific options
        
        Returns:
            Absolute path to the generated image file
        """
        # Resolve provider
        if provider == "auto":
            provider = self._pick_best_provider()

        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}. "
                             f"Available: {list(self.providers.keys())}")

        p = self.providers[provider]
        if not p.available:
            raise RuntimeError(
                f"{p.NAME} is not configured. Set the {p.ENV_KEY} "
                f"environment variable."
            )

        # Build output path
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{provider}_{ts}.png"
        output_path = os.path.join(self.output_dir, filename)

        return p.generate(prompt, output_path, width=width, height=height,
                          **kwargs)

    def _pick_best_provider(self):
        """Select the first available provider by priority."""
        for name in self.PROVIDER_PRIORITY:
            if self.providers[name].available:
                return name

        raise RuntimeError(
            "No image generation providers configured. "
            "Set at least one API key: FLUX_API_KEY, IDEOGRAM_API_KEY, "
            "FIREFLY_CLIENT_ID+FIREFLY_CLIENT_SECRET, or MIDJOURNEY_API_KEY"
        )

    # ── Video Transcoding (HandBrake) ───────────────────────

    def transcode_video(self, input_path, output_path, preset="default",
                        **kwargs):
        """Transcode a video using HandBrake.
        
        Args:
            input_path:   Source video file
            output_path:  Destination file
            preset:       "default", "web", "hq", "4k", "fast", "mobile"
                          or any raw HandBrake preset name
        """
        return self.handbrake.transcode(input_path, output_path, preset,
                                         **kwargs)

    # ── Streaming Pipeline (GStreamer) ───────────────────────

    def stream_pipeline(self, pipeline_desc, async_mode=False, **kwargs):
        """Run a GStreamer pipeline.
        
        Args:
            pipeline_desc:  GStreamer pipeline string
            async_mode:     If True, run in background (returns Popen)
        """
        if async_mode:
            return self.gstreamer.launch_pipeline_async(pipeline_desc)
        return self.gstreamer.launch_pipeline(pipeline_desc, **kwargs)

    def convert_video(self, input_path, output_path, engine="handbrake",
                      **kwargs):
        """High-level video conversion — auto-selects the best engine.
        
        Args:
            engine: "handbrake" (ease of use) or "gstreamer" (low-latency)
        """
        if engine == "handbrake":
            if not self.handbrake.available:
                raise RuntimeError("HandBrake not available.")
            return self.handbrake.transcode(input_path, output_path, **kwargs)
        elif engine == "gstreamer":
            if not self.gstreamer.available:
                raise RuntimeError("GStreamer not available.")
            return self.gstreamer.convert(input_path, output_path, **kwargs)
        else:
            # Auto: prefer HandBrake for simplicity, fall back to GStreamer
            if self.handbrake.available:
                return self.handbrake.transcode(input_path, output_path,
                                                 **kwargs)
            elif self.gstreamer.available:
                return self.gstreamer.convert(input_path, output_path, **kwargs)
            else:
                raise RuntimeError(
                    "No video processing engine available. "
                    "Install HandBrakeCLI or GStreamer."
                )


# ── Standalone Test ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  OVERLORD Media Engine — Diagnostics")
    print("=" * 60)

    engine = MediaEngine(output_dir="./media_output")

    available = engine.get_available_providers()
    if available:
        print(f"\nReady providers: {', '.join(available)}")
        print("Run a test: engine.generate_image('a sunset over mountains')")
    else:
        print("\nNo image providers configured. Set API keys to enable:")
        print("  FLUX_API_KEY, IDEOGRAM_API_KEY, FIREFLY_CLIENT_ID/SECRET, MIDJOURNEY_API_KEY")

    if engine.handbrake.available:
        print(f"\nHandBrake: {engine.handbrake.cli_path}")
    else:
        print("\nHandBrake: NOT FOUND — Install HandBrakeCLI")

    if engine.gstreamer.available:
        print(f"GStreamer: {engine.gstreamer.cli_path}")
    else:
        print("GStreamer: NOT FOUND — Install GStreamer")
