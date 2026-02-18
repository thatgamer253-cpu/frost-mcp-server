"""
Creation Engine — Studio AI Bridge
Integrates Runway Gen-4 and Luma Ray-2 for automated video/image
asset generation within the Studio Engine.

Providers:
  - Runway Gen-4 Turbo: Image-to-Video, Upscaling (up to 4K)
  - Luma Ray-2: Text-to-Video with cinematic 16:9 aspect ratio

Usage:
    from creation_engine.studio_ai_bridge import generate_asset, upscale_asset

    asset_id = await generate_asset("A sunset over mountains", provider="luma")
    upscaled = await upscale_asset(image_path, provider="runway")
"""

import os
import asyncio
import time
from .llm_client import log


# ── Runway Gen-4 Integration ────────────────────────────────

def _get_runway_client():
    """Lazy-load RunwayML client."""
    try:
        from runwayml import RunwayML
        api_key = os.getenv("RUNWAY_API_KEY")
        if not api_key:
            log("STUDIO_AI", "  ⚠ RUNWAY_API_KEY not set.")
            return None
        return RunwayML(api_key=api_key)
    except ImportError:
        log("STUDIO_AI", "  ⚠ runwayml package not installed. Run: pip install runwayml")
        return None


def runway_image_to_video(image_uri: str, prompt: str, duration: int = 10) -> dict:
    """Generate video from image using Runway Gen-4 Turbo.
    
    Args:
        image_uri: URL or local path to source image.
        prompt: Motion/scene description.
        duration: Video length in seconds (5 or 10).
    
    Returns:
        dict with task_id and status.
    """
    client = _get_runway_client()
    if not client:
        return {"success": False, "reason": "Runway client unavailable"}

    try:
        log("STUDIO_AI", f"  🎬 Runway Gen-4: Generating video from image ({duration}s)...")
        task = client.image_to_video.create(
            model="gen-4-turbo",
            prompt_image=image_uri,
            prompt_text=prompt,
            duration=duration,
        )
        log("STUDIO_AI", f"  ✓ Task submitted: {task.id}")
        return {"success": True, "task_id": task.id, "provider": "runway"}
    except Exception as e:
        log("STUDIO_AI", f"  ✗ Runway error: {e}")
        return {"success": False, "reason": str(e)}


def runway_upscale(image_uri: str) -> dict:
    """Upscale image to 4K using Runway's upscale model.
    
    Args:
        image_uri: URL or local path to source image.
    
    Returns:
        dict with task_id and status.
    """
    client = _get_runway_client()
    if not client:
        return {"success": False, "reason": "Runway client unavailable"}

    try:
        log("STUDIO_AI", "  🔍 Runway Upscale: Enhancing to 4K...")
        task = client.image_to_video.create(
            model="upscale-v1",
            prompt_image=image_uri,
        )
        log("STUDIO_AI", f"  ✓ Upscale task submitted: {task.id}")
        return {"success": True, "task_id": task.id, "provider": "runway"}
    except Exception as e:
        log("STUDIO_AI", f"  ✗ Runway upscale error: {e}")
        return {"success": False, "reason": str(e)}


# ── Luma Ray-2 Integration ──────────────────────────────────

async def _get_luma_client():
    """Lazy-load AsyncLumaAI client."""
    try:
        from lumaai import AsyncLumaAI
        api_key = os.getenv("LUMAAI_API_KEY") or os.getenv("LUMA_API_KEY")
        if not api_key:
            log("STUDIO_AI", "  ⚠ LUMA_API_KEY not set.")
            return None
        return AsyncLumaAI(auth_token=api_key)
    except ImportError:
        log("STUDIO_AI", "  ⚠ lumaai package not installed. Run: pip install lumaai")
        return None


async def luma_text_to_video(prompt: str, aspect_ratio: str = "16:9",
                              loop: bool = False) -> dict:
    """Generate cinematic video from text using Luma Ray-2.
    
    Args:
        prompt: Scene description for video generation.
        aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1).
        loop: Whether to create a seamless loop.
    
    Returns:
        dict with generation_id and status.
    """
    client = await _get_luma_client()
    if not client:
        return {"success": False, "reason": "Luma client unavailable"}

    try:
        log("STUDIO_AI", f"  🎥 Luma Ray-2: Generating cinematic video ({aspect_ratio})...")
        generation = await client.generations.create(
            model="ray-2",
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            loop=loop,
        )
        log("STUDIO_AI", f"  ✓ Generation submitted: {generation.id}")
        return {"success": True, "generation_id": generation.id, "provider": "luma"}
    except Exception as e:
        log("STUDIO_AI", f"  ✗ Luma error: {e}")
        return {"success": False, "reason": str(e)}


# ── Unified Interface ───────────────────────────────────────

async def generate_asset(prompt: str, provider: str = "luma",
                          image_uri: str = None, **kwargs) -> dict:
    """Unified asset generation interface.
    
    Routes to the appropriate provider based on the task:
      - luma: Text-to-Video (cinematic, 16:9)
      - runway: Image-to-Video (if image_uri provided) or Text-to-Video
    
    All prompts are sanitized against Tool Poisoning before API dispatch.
    All image URIs are validated against the SSRF allowlist.
    
    Args:
        prompt: Description of the desired output.
        provider: "luma" or "runway".
        image_uri: Optional source image for image-to-video.
    
    Returns:
        dict with task/generation ID and status.
    """
    # Security: sanitize prompt before any API call
    from .security_hardened_mcp import sanitize_prompt, validate_url
    prompt = sanitize_prompt(prompt)

    # Security: validate image URI against SSRF allowlist
    if image_uri and image_uri.startswith(("http://", "https://")):
        allowed, reason = validate_url(image_uri)
        if not allowed:
            log("STUDIO_AI", f"  🚫 SSRF BLOCKED: {reason}")
            return {"success": False, "reason": f"URL blocked: {reason}"}

    if provider == "runway" and image_uri:
        return runway_image_to_video(image_uri, prompt, **kwargs)
    elif provider == "luma":
        return await luma_text_to_video(prompt, **kwargs)
    elif provider == "runway":
        return runway_image_to_video("", prompt, **kwargs)
async def upscale_media(asset_path: str, provider: str = "runway") -> dict:
    """Standardized media upscaling to 4K.
    
    Uses MediaDirectorAgent (official SDK) when available,
    falls back to direct runway_upscale call.
    
    Args:
        asset_path: Local path or URL of the asset to upscale.
        provider: "runway" (default).
    
    Returns:
        dict with success status and task/result info.
    """
    log("STUDIO_AI", f"🚀 Initiating 4K Resolution Reconstruction for: {os.path.basename(asset_path)}")
    
    if provider == "runway":
        # Try the official SDK via MediaDirectorAgent first
        try:
            from .media_director import MediaDirectorAgent
            director = MediaDirectorAgent()
            task_id = director.upscale_to_4k(asset_path)
            if task_id:
                return {"success": True, "task_id": task_id, "provider": "runway"}
        except ImportError:
            pass
        
        # Fallback to direct Runway call
        return runway_upscale(asset_path)
    else:
        return {"success": False, "reason": f"Upscale provider not supported: {provider}"}


# ── Standalone Test ──────────────────────────────────────────

if __name__ == "__main__":
    # Test logic
    pass
