"""
Creation Engine — Kie.ai Multi-Model Video Provider (V2 API)
Provides access to Kling 2.1/3.0, Sora2, Wan, Hailuo, and more
through Kie.ai's unified, credit-based API.

Updated to use the official v2 endpoints:
  - POST /api/v1/jobs/createTask  (create generation tasks)
  - GET  /api/v1/jobs/recordInfo?taskId={taskId}  (poll status)

Usage:
    from creation_engine.kie_provider import KieAiProvider
    
    kie = KieAiProvider()
    task = kie.text_to_video("A cinematic sunrise", model="kling/v2-1-master-text-to-video")
    result = kie.poll_task(task["task_id"])
"""

import os
import time
import requests
from typing import Optional, Dict, Any

try:
    from .llm_client import log
except ImportError:
    def log(tag, msg): print(f"[{tag}] {msg}")


# ═══════════════════════════════════════════════════════════
#  KIE.AI MULTI-MODEL PROVIDER (V2 API)
# ═══════════════════════════════════════════════════════════

class KieAiProvider:
    """Unified video generation via Kie.ai's aggregator API.
    
    Supported Text-to-Video Models:
      - kling/v2-1-master-text-to-video : Kling 2.1 Master (text-to-video, best quality)
      - kling/v2-1-standard             : Kling 2.1 Standard (image-to-video)
      - kling/v2-1-pro                   : Kling 2.1 Pro (image-to-video)
      - kling/v3-0-standard              : Kling 3.0 Standard
      - wan/2-2-a14b-text-to-video-turbo : Wan 2.2 Turbo
      - sora2/sora-2-pro-text-to-video   : Sora 2 Pro
    """

    BASE_URL = "https://api.kie.ai"
    CREATE_TASK_ENDPOINT = "/api/v1/jobs/createTask"
    QUERY_TASK_ENDPOINT = "/api/v1/jobs/recordInfo"

    # Model display names
    MODELS = {
        "kling/v2-1-master-text-to-video": "Kling 2.1 Master (Text-to-Video)",
        "kling/v2-1-standard": "Kling 2.1 Standard (Image-to-Video)",
        "kling/v2-1-pro": "Kling 2.1 Pro (Image-to-Video)",
        "kling/v3-0-standard": "Kling 3.0 Standard",
        "wan/2-2-a14b-text-to-video-turbo": "Wan 2.2 A14B Turbo",
        "wan/2-2-5b-text-to-video": "Wan 2.2 5B",
        "sora2/sora-2-pro-text-to-video": "Sora 2 Pro",
    }

    # Default text-to-video model (no image required)
    DEFAULT_T2V_MODEL = "kling/v2-1-master-text-to-video"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIE_API_KEY")
        self.available = bool(self.api_key)
        self._callback_url = "https://example.com/kie-callback"  # Placeholder
        
        status = "READY" if self.available else "NO API KEY"
        log("KIE", f"Kie.ai Multi-Model Provider: {status}")
        if self.available:
            log("KIE", f"  Default T2V model: {self.DEFAULT_T2V_MODEL}")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Text-to-Video ───────────────────────────────────────

    def text_to_video(self, prompt: str, model: str = None,
                       aspect_ratio: str = "16:9",
                       duration: int = 5,
                       callback_url: Optional[str] = None) -> Dict[str, Any]:
        """Generate video from text prompt.
        
        Args:
            prompt: Scene description.
            model: Model name (see MODELS dict). Defaults to Master T2V.
            aspect_ratio: "16:9", "9:16", or "1:1".
            duration: Video duration in seconds (5 or 10).
            callback_url: Optional webhook URL for completion notification.
            
        Returns:
            dict with task_id, status, and provider info.
        """
        if not self.available:
            return {"success": False, "reason": "Kie.ai API key not set"}

        # Use default text-to-video model if none specified or if old-style model given
        if not model or not model.startswith("kling/"):
            model = self.DEFAULT_T2V_MODEL

        model_name = self.MODELS.get(model, model)
        log("KIE", f"  Generating video via {model_name}...")

        # Build V2 API payload
        payload = {
            "model": model,
            "callBackUrl": callback_url or self._callback_url,
            "input": {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
                "negative_prompt": "blur, distort, low quality",
                "cfg_scale": 0.5,
            }
        }

        url = f"{self.BASE_URL}{self.CREATE_TASK_ENDPOINT}"

        try:
            r = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            data = r.json()

            code = data.get("code", 0)
            
            if code == 200:
                task_id = (data.get("data", {}) or {}).get("taskId")
                if task_id:
                    log("KIE", f"  Task submitted: {task_id}")
                    return {
                        "success": True,
                        "task_id": task_id,
                        "model": model,
                        "provider": "kie.ai",
                        "raw": data,
                    }
                else:
                    log("KIE", f"  ✗ No taskId in success response: {data}")
                    return {"success": False, "reason": "No taskId in response", "raw": data}
            elif code == 402:
                log("KIE", f"  ✗ Insufficient credits: {data.get('msg')}")
                return {"success": False, "reason": "Insufficient credits", "raw": data}
            else:
                log("KIE", f"  ✗ API Error [{code}]: {data.get('msg', 'Unknown')}")
                return {"success": False, "status_code": code, "error": data}
        except Exception as e:
            log("KIE", f"  Request Error: {e}")
            return {"success": False, "reason": str(e)}

    # ── Image-to-Video ──────────────────────────────────────

    def image_to_video(self, image_url: str, prompt: str = "",
                        model: str = "kling/v2-1-pro",
                        duration: int = 5) -> Dict[str, Any]:
        """Generate video from an image.
        
        Args:
            image_url: Public URL of the source image.
            prompt: Optional motion/scene description.
            model: Model name (must be I2V capable).
            duration: Video duration in seconds.
            
        Returns:
            dict with task_id and status.
        """
        if not self.available:
            return {"success": False, "reason": "Kie.ai API key not set"}

        log("KIE", f"  Image-to-Video via {self.MODELS.get(model, model)}...")

        payload = {
            "model": model,
            "callBackUrl": self._callback_url,
            "input": {
                "prompt": prompt,
                "image_url": image_url,
                "duration": str(duration),
                "negative_prompt": "blur, distort, low quality",
                "cfg_scale": 0.5,
                "tail_image_url": "",
            }
        }

        url = f"{self.BASE_URL}{self.CREATE_TASK_ENDPOINT}"

        try:
            r = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            data = r.json()
            code = data.get("code", 0)

            if code == 200:
                task_id = (data.get("data", {}) or {}).get("taskId")
                log("KIE", f"  I2V Task submitted: {task_id}")
                return {"success": True, "task_id": task_id, "model": model, "provider": "kie.ai"}
            else:
                log("KIE", f"  I2V API Error [{code}]: {data.get('msg', 'Unknown')}")
                return {"success": False, "status_code": code, "error": data}
        except Exception as e:
            log("KIE", f"  I2V Request Error: {e}")
            return {"success": False, "reason": str(e)}

    # ── Poll Task ───────────────────────────────────────────

    def poll_task(self, task_id: str, save_dir: str = None,
                   filename: str = "kie_output.mp4",
                   timeout_minutes: int = 5) -> Dict[str, Any]:
        """Poll for task completion and optionally download the result.
        
        Args:
            task_id: The taskId from createTask response.
            save_dir: Directory to save the video (None to skip download).
            filename: Output filename.
            timeout_minutes: Max wait time.
            
        Returns:
            dict with status and optional video_path.
        """
        if not self.available:
            return {"success": False, "reason": "Kie.ai API key not set"}

        log("KIE", f"  Polling task {task_id}...")
        
        # V2 API status endpoint
        status_url = f"{self.BASE_URL}{self.QUERY_TASK_ENDPOINT}"
        
        max_polls = timeout_minutes * 6  # Every 10s

        for i in range(max_polls):
            time.sleep(10)
            
            try:
                r = requests.get(
                    status_url,
                    params={"taskId": task_id},
                    headers=self._headers(),
                    timeout=15
                )
                data = r.json()
                code = data.get("code", 0)
                
                if code != 200:
                    if i % 6 == 0:
                        log("KIE", f"  ... waiting (code={code})...")
                    continue
                    
                task_data = data.get("data", {}) or {}
                status = (task_data.get("status") or "").lower()

                if status in ["completed", "succeeded", "success", "done"]:
                    # Extract video URL from response
                    video_url = (
                        task_data.get("resultUrl") or
                        task_data.get("video_url") or
                        task_data.get("output_url") or
                        task_data.get("result", {}).get("video_url") if isinstance(task_data.get("result"), dict) else None
                    )
                    
                    # Also check output array
                    if not video_url and isinstance(task_data.get("output"), list) and task_data["output"]:
                        video_url = task_data["output"][0]
                    
                    log("KIE", f"  Task completed!")
                    
                    if save_dir and video_url:
                        path = self._download(video_url, save_dir, filename)
                        return {"success": True, "video_path": path, "raw": data}
                    return {"success": True, "video_url": video_url, "raw": data}

                elif status in ["failed", "error"]:
                    reason = task_data.get("error") or task_data.get("failure_reason") or "Unknown"
                    log("KIE", f"  Task failed: {reason}")
                    return {"success": False, "reason": reason, "raw": data}

                else:
                    if i % 6 == 0:
                        log("KIE", f"  ... rendering ({status})...")
                    
            except requests.exceptions.RequestException:
                continue

        log("KIE", "  Task timed out.")
        return {"success": False, "reason": "Timeout"}

    # ── Helper ──────────────────────────────────────────────

    @staticmethod
    def _download(url: str, save_dir: str, filename: str) -> str:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, filename)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        log("KIE", f"  Saved: {path}")
        return path


# ── Standalone Test ─────────────────────────────────────────

if __name__ == "__main__":
    kie = KieAiProvider()
    if kie.available:
        result = kie.text_to_video(
            "A futuristic AI engine rendering holographic code",
        )
        print(result)
    else:
        print("KIE_API_KEY not set.")
