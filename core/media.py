import os
import time
import requests
import base64
import json
from typing import Optional
from security_hardened_mcp import sanitize_prompt

class MultimodalEngine:
    """
    Autonomous Visual DNA & Motion Engine.
    Integrates Stability AI (Images), Luma (Primary Video), and Runway (Secondary Video).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.stability_key = api_key or os.getenv("STABILITY_API_KEY")
        self.luma_key = os.getenv("LUMA_API_KEY")
        self.runway_key = os.getenv("RUNWAY_API_KEY")
        
        self.stability_host = "https://api.stability.ai"
        
        # Log active engines
        self.active_video_engine = "None"
        if self.luma_key: self.active_video_engine = "Luma Dream Machine"
        elif self.runway_key: self.active_video_engine = "Runway Gen-3"

    def ensure_asset_dirs(self, root_path: str) -> str:
        """Creates the standardized asset tree."""
        gen_dir = os.path.join(root_path, "assets", "gen")
        os.makedirs(gen_dir, exist_ok=True)
        return gen_dir

    def generate_visual_dna(self, context: str, save_dir: str) -> Optional[str]:
        """Uses SDXL to generate a master brand asset."""
        if not self.stability_key:
            print("[MEDIA] Stability Key missing. Skipping Visual DNA.")
            return None

        os.makedirs(save_dir, exist_ok=True)
        print("[MEDIA] Generating Master Visual DNA (SDXL)...")
        
        # Stability V1 SDXL Endpoint
        engine_id = "stable-diffusion-xl-1024-v1-0"
        endpoint = f"{self.stability_host}/v1/generation/{engine_id}/text-to-image"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.stability_key}"
        }
        
        sanitized_context = sanitize_prompt(context)
        
        body = {
            "text_prompts": [{"text": f"Professional software UI, {sanitized_context}, high fidelity, 4k", "weight": 1}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        }

        try:
            resp = requests.post(endpoint, headers=headers, json=body)
            if resp.status_code == 200:
                data = resp.json()
                path = os.path.join(save_dir, "master_brand.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data["artifacts"][0]["base64"]))
                print(f"[MEDIA] Visual DNA saved: {path}")
                return path
            else:
                print(f"[MEDIA] SDXL Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[MEDIA] SDXL Exception: {e}")
        return None

    def generate_ux_motion(self, image_path: str, save_dir: str) -> Optional[str]:
        """Generates a high-fidelity video using Luma (Primary) or Runway (Secondary).
        
        Uses the official lumaai/runwayml SDKs via MediaDirectorAgent.
        """
        if not image_path or not os.path.exists(image_path):
            print("[MEDIA] Source image missing for video generation.")
            return None

        print(f"[MEDIA] Initiating Video Generation via {self.active_video_engine}...")

        try:
            from creation_engine.media_director import MediaDirectorAgent
            director = MediaDirectorAgent()
        except ImportError:
            print("[MEDIA] MediaDirectorAgent not available. Falling back disabled.")
            return None

        os.makedirs(save_dir, exist_ok=True)

        if self.luma_key:
            # Luma Ray-2: Cinematic Text-to-Video via official SDK
            import asyncio
            prompt = "Professional software interface animation, cinematic camera movement, high resolution, 4k"
            return asyncio.run(
                director.create_cinematic_video(prompt, save_dir, "luma_motion.mp4")
            )
        elif self.runway_key:
            # Runway Gen-4 Turbo: Image-to-Video via official SDK
            bridge_url = self._upload_to_bridge(image_path)
            if not bridge_url:
                print("[MEDIA] Runway Skipped: Bridge upload failed.")
                return None
            prompt = "Professional software interface animation, cinematic camera movement, high resolution, 4k"
            return director.create_video_from_image(
                bridge_url, prompt, save_dir, "runway_motion.mp4"
            )
        else:
            print("[MEDIA] No Video API Keys found (Luma/Runway). Skipping.")
            return None

    def _upload_to_bridge(self, image_path: str) -> Optional[str]:
        """Uploads image to tmpfiles.org for a temporary public URL (needed for Runway)."""
        url = "https://tmpfiles.org/api/v1/upload"
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                resp = requests.post(url, files=files)
            
            if resp.status_code == 200:
                data = resp.json()
                raw_url = data["data"]["url"]
                direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                if direct_url.startswith("http://"):
                    direct_url = direct_url.replace("http://", "https://")
                print(f"[MEDIA] Bridge Established: {direct_url}")
                return direct_url
            else:
                print(f"[MEDIA] Bridge Failed: {resp.status_code}")
        except Exception as e:
            print(f"[MEDIA] Bridge Exception: {e}")
        return None
