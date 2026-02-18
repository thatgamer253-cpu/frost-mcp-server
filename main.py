import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, Header, HTTPException, Body
from pydantic import BaseModel
from core.media import MultimodalEngine
from tool_generator import ToolGenerator
from security_hardened_mcp import require_auth, sanitize_prompt, VALID_API_KEY

# Configure Hardened Logging
LOG_FILE = os.getenv("MCP_LOG_FILE", "/tmp/mcp-server.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("FrostMCP")

app = FastAPI(title="Frost Hardened MCP Server", version="2026.0.1")

# State Initialization
media_engine = MultimodalEngine()
tool_forge = ToolGenerator(os.path.join(os.getcwd(), "frost_tools"))

class ImageRequest(BaseModel):
    context: str
    save_dir: str

class VideoRequest(BaseModel):
    image_path: str
    save_dir: str

class ToolRequest(BaseModel):
    description: str
    name: str

@app.get("/")
async def root():
    return {"status": "Frost MCP Online", "security": "Zero-Trust Active"}

@app.get("/.well-known/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-02-15"}

@app.post("/tools/generate_image")
@require_auth
async def generate_image(request: ImageRequest, auth_token: Optional[str] = Header(None)):
    """Exposes MultimodalEngine.generate_visual_dna with sanitization and auth."""
    logger.info(f"Image generation requested. Token hash: {hash(auth_token)}")
    
    # Sanitization is handled within the engine, but we log here for visibility
    result = media_engine.generate_visual_dna(request.context, request.save_dir)
    
    if not result:
        raise HTTPException(status_code=500, detail="Image generation failed.")
    
    return {"status": "success", "image_path": result}

@app.post("/tools/generate_video")
@require_auth
async def generate_video(request: VideoRequest, auth_token: Optional[str] = Header(None)):
    """Exposes MultimodalEngine.generate_ux_motion with sanitization and auth."""
    logger.info(f"Video motion requested. Image: {request.image_path}")
    
    result = media_engine.generate_ux_motion(request.image_path, request.save_dir)
    
    if not result:
        raise HTTPException(status_code=500, detail="Video generation failed.")
    
    return {"status": "success", "video_path": result}

@app.post("/tools/forge_tool")
@require_auth
async def forge_tool(request: ToolRequest, auth_token: Optional[str] = Header(None)):
    """Exposes ToolGenerator.generate_util with sanitization and auth."""
    logger.info(f"Tool forge initiated: {request.name}")
    
    # Sanitization happens in tool_forge.generate_util
    result = tool_forge.generate_util(request.description, request.name)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail="Tool forgery failed.")
    
    return result

if __name__ == "__main__":
    import uvicorn
    # Standalone mode (mostly for local testing/dev)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
