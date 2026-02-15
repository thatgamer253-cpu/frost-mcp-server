import os
import time
import requests
import base64
import json
from typing import Optional

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
        
        body = {
            "text_prompts": [{"text": f"Professional software UI, {context}, high fidelity, 4k", "weight": 1}],
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
        """Generates a high-fidelity video using Luma (Primary) or Runway (Secondary)."""
        if not image_path or not os.path.exists(image_path):
            print("[MEDIA] Source image missing for video generation.")
            return None

        print(f"[MEDIA] Initiating Video Generation via {self.active_video_engine}...")

        if self.luma_key:
            return self._generate_luma(image_path, save_dir)
        elif self.runway_key:
            return self._generate_runway(image_path, save_dir)
        else:
            print("[MEDIA] No Video API Keys found (Luma/Runway). Skipping.")
            return None

    def _generate_luma(self, image_path: str, save_dir: str) -> Optional[str]:
        """Luma Dream Machine Implementation."""
        url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        headers = {
            "Authorization": f"Bearer {self.luma_key}",
            "Content-Type": "application/json"
        }
        
        # Upload image to Luma creates a complication: Luma API often expects a URL.
        # For local files, we'd need to upload first. 
        # HOWEVER, Luma also supports start_frame_url.
        # Since we don't have a public URL for local files, we might be limited to Text-to-Video
        # OR we need a temporary upload service. 
        # FOR NOW: We will use Luma's TEXT-TO-VIDEO with the prompt context, 
        # as verified in the probe script, to ensure success without an image host.
        
        # TODO: Implement image upload/hosting for full Image-to-Video.
        print("[MEDIA] Luma strategy: High-Fidelity Text-to-Video (Local Image Upload not supported without host)")
        
        payload = {
            "prompt": "Professional software interface animation, cinematic camera movement, high resolution, 4k",
            "aspect_ratio": "16:9",
            "model": "ray-2"
        }

        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code in [200, 201]:
                gen_id = resp.json().get("id")
                print(f"[MEDIA] Luma Task Queued: {gen_id}")
                return self._poll_luma(gen_id, save_dir)
            else:
                print(f"[MEDIA] Luma Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[MEDIA] Luma Exception: {e}")
        return None

    def _poll_luma(self, gen_id: str, save_dir: str) -> Optional[str]:
        """Polls Luma API for completion."""
        url = f"https://api.lumalabs.ai/dream-machine/v1/generations/{gen_id}"
        headers = {"Authorization": f"Bearer {self.luma_key}"}
        
        print("[MEDIA] Rendering Video (approx. 2-5 mins)...")
        for _ in range(30): # 30 * 10s = 5 mins
            time.sleep(10)
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    state = data.get("state")
                    if state == "completed":
                        video_url = data["assets"]["video"]
                        return self._download_video(video_url, save_dir, "luma_motion.mp4")
                    elif state == "failed":
                        print(f"[MEDIA] Luma Generation Failed: {data.get('failure_reason')}")
                        return None
            except Exception:
                pass
        print("[MEDIA] Luma Timeout.")
        return None

    def _generate_runway(self, image_path: str, save_dir: str) -> Optional[str]:
        """Runway Gen-3 Implementation with PixelBridge."""
        print("[MEDIA] Runway: Engaging PixelBridge for temporary asset hosting...")
        
        # 1. Upload to Bridge
        bridge_url = self._upload_to_bridge(image_path)
        if not bridge_url:
            print("[MEDIA] Runway Skipped: Bridge upload failed.")
            return None

        # 2. Call Runway
        url = "https://api.dev.runwayml.com/v1/image_to_video"
        headers = {
            "Authorization": f"Bearer {self.runway_key}",
            "X-Runway-Version": "2024-09-13",
            "Content-Type": "application/json"
        }
        
        payload = {
            "promptText": "Professional software interface animation, cinematic camera movement, high resolution, 4k",
            "promptImage": bridge_url,
            "model": "gen3a_turbo",
        }

        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 200 or resp.status_code == 201:
                data = resp.json()
                task_id = data.get("id")
                print(f"[MEDIA] Runway Task Queued: {task_id}")
                return self._poll_runway(task_id, save_dir)
            else:
                print(f"[MEDIA] Runway Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[MEDIA] Runway Exception: {e}")
        return None

    def _upload_to_bridge(self, image_path: str) -> Optional[str]:
        """Uploads image to tmpfiles.org for a temporary public URL."""
        url = "https://tmpfiles.org/api/v1/upload"
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                resp = requests.post(url, files=files)
            
            if resp.status_code == 200:
                data = resp.json()
                raw_url = data["data"]["url"]
                # Convert to direct link and force HTTPS for Runway
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

    def _poll_runway(self, task_id: str, save_dir: str) -> Optional[str]:
        """Polls Runway for completion."""
        url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.runway_key}", "X-Runway-Version": "2024-09-13"}
        
        print("[MEDIA] Rendering Runway Video...")
        for _ in range(30): 
            time.sleep(10)
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    if status == "SUCCEEDED":
                        video_url = data.get("output", [])[0]
                        return self._download_video(video_url, save_dir, "runway_motion.mp4")
                    elif status == "FAILED":
                        print(f"[MEDIA] Runway Failed: {data.get('failure')}")
                        return None
            except Exception:
                pass
        return None

    def _download_video(self, url: str, save_dir: str, filename: str) -> str:
        """Helper to download result."""
        path = os.path.join(save_dir, filename)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        print(f"[MEDIA] Video Saved: {path}")
        return path
