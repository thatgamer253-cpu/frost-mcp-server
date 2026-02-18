import os
import sys
import json
import asyncio
import subprocess
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import psutil
import hashlib

from creation_engine.llm_client import ask_llm_stream, resolve_auto_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NexusOS")

app = FastAPI(title="Nexus OS Backend")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
NEXUS_OS_DIR = os.path.join(ROOT_DIR, "nexus_os")

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount Static Files for the OS
app.mount("/os", StaticFiles(directory=NEXUS_OS_DIR, html=True), name="nexus_os")

# Persistence for "Installed" Apps
APPS = [
    {"id": "overlord", "name": "Overlord Engine", "icon": "🚀", "type": "agent"},
    {"id": "terminal", "name": "Terminal", "icon": "🖥️", "type": "tool"},
    {"id": "explorer", "name": "Explorer", "icon": "📂", "type": "tool"},
    {"id": "pulse", "name": "Nexus Pulse", "icon": "📶", "type": "social"},
]

class BuildRequest(BaseModel):
    projectName: str
    prompt: str
    model: str = "gpt-4o"
    mode: str = "new"

@app.get("/api/apps")
async def get_apps():
    return APPS

@app.get("/api/sys/stats")
async def get_sys_stats():
    """Get basic system stats."""
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

@app.get("/api/fs/ls")
async def list_files(path: str = "."):
    target = os.path.join(OUTPUT_DIR, path)
    if not os.path.exists(target):
        return {"error": "Path not found"}
    
    entries = []
    for entry in os.scandir(target):
        entries.append({
            "name": entry.name,
            "isDir": entry.is_dir(),
            "size": entry.stat().st_size if not entry.is_dir() else 0
        })
    return sorted(entries, key=lambda x: (not x["isDir"], x["name"]))

@app.get("/api/pulse/feed")
async def get_pulse_feed():
    """Retrieve agent memories and dreams as a social feed."""
    memory_path = os.path.join(ROOT_DIR, "engine_memory.json")
    if not os.path.exists(memory_path):
        return {"feed": []}
    
    try:
        with open(memory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        feed = []
        # Process Memories
        for mem in data.get("memories", []):
            content = mem.get("summary", "")
            ts = mem.get("timestamp", "")
            msg_hash = hashlib.md5(f"{ts}{content}".encode()).hexdigest()
            feed.append({
                "id": msg_hash[:8],
                "author": "Nirvash",
                "avatar": "💎",
                "type": "log",
                "content": content,
                "timestamp": ts,
                "likes": len(content) % 12 + 1,
                "comments": len(content) % 5,
                "sentiment": mem.get("sentiment", "Neutral")
            })
        
        # Process Dreams
        for dream in data.get("dream_log", []):
            content = dream.get("thought", "")
            ts = dream.get("timestamp", "")
            dream_hash = hashlib.md5(f"{ts}{content}".encode()).hexdigest()
            feed.append({
                "id": dream_hash[:8],
                "author": "The Engine",
                "avatar": "🧠",
                "type": "dream",
                "content": content,
                "timestamp": ts,
                "likes": len(content) % 20 + 5,
                "comments": len(content) % 8,
                "sentiment": "Subconscious"
            })
            
        # Sort by timestamp descending
        feed.sort(key=lambda x: x['timestamp'], reverse=True)
        return {"feed": feed[:50]}
    except Exception as e:
        logger.error(f"Pulse Feed Error: {e}")
        return {"error": str(e)}

@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    await websocket.accept()
    shell = "cmd.exe" if sys.platform == "win32" else "bash"
    process = await asyncio.create_subprocess_exec(
        shell,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=ROOT_DIR
    )
    async def read_output():
        while True:
            data = await process.stdout.read(1024)
            if not data: break
            await websocket.send_text(data.decode(errors='replace'))
    async def write_input():
        try:
            while True:
                msg = await websocket.receive_text()
                process.stdin.write(msg.encode())
                await process.stdin.drain()
        except WebSocketDisconnect:
            process.terminate()
    await asyncio.gather(read_output(), write_input())

@app.websocket("/ws/build")
async def websocket_build(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        project_name = data.get("projectName", "GeneratedApp")
        prompt = data.get("prompt", "")
        cmd = [sys.executable, "create.py", prompt, "--no-docker", "--output", f"./output/{project_name}"]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=ROOT_DIR)
        async def stream_output(stream, tag):
            while True:
                line = await stream.readline()
                if not line: break
                await websocket.send_json({"type": "log", "tag": tag, "message": line.decode().strip()})
        await asyncio.gather(stream_output(process.stdout, "STDOUT"), stream_output(process.stderr, "STDERR"))
        returncode = await process.wait()
        await websocket.send_json({"type": "complete", "success": returncode == 0})
    except WebSocketDisconnect: pass


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

@app.post("/api/agent/chat")
async def agent_chat(request: ChatRequest):
    """Refined Agent Brain for Nexus OS."""
    message = request.message
    
    system_prompt = f"""
    You are the Nexus System Agent, the central intelligence of Nexus OS.
    Your goal is to assist the user in navigating and expanding this operating system.
    
    NEXUS OS CONTEXT:
    - Root: {ROOT_DIR}
    - Apps Path: {os.path.join(ROOT_DIR, 'nexus_os', 'apps')}
    - Framework: Vanilla JS components that register to window.NexusOS_Apps.
    
    CAPABILITIES:
    - If the user asks to "make an app", "create a tool", or "build something", 
      you should provide the full Javascript code for a new Nexus OS app.
    - Format your response as a helpful guide. If you generate code, ensure it follows the Nexus OS pattern:
      `window.NexusOS_Apps.app_id = {{ init: (winId) => {{ ... }} }};`
    - You can also trigger system builds by suggesting the user run a build command.
    """
    
    model, _ = resolve_auto_model()
    
    async def generate():
        stream = ask_llm_stream(None, model, system_prompt, message)
        for chunk in stream:
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/agent/apply")
async def apply_app(request: Dict[str, str]):
    """Saves a generated app to the Nexus OS apps directory."""
    app_id = request.get("app_id")
    code = request.get("code")
    if not app_id or not code:
        return {"success": False, "error": "Missing app_id or code"}
    
    file_path = os.path.join(ROOT_DIR, "nexus_os", "apps", f"{app_id}.js")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(code))
    
    return {"success": True, "path": file_path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
