
import os
import json
import uvicorn
import subprocess
import sys
import psutil
import base64
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import agent_ipc

try:
    import pyautogui
    from PIL import Image
    HAS_SCREENSHOT = True
except ImportError:
    HAS_SCREENSHOT = False

app = FastAPI(title="Overlord Sovereign Mobile Relay", version="2.0.0")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Hardware Steward ──
_steward = None

def get_steward():
    global _steward
    if _steward is None:
        try:
            from creation_engine.hardware_steward import HardwareSteward
            _steward = HardwareSteward()
        except:
            return None
    return _steward

# ── Models ───────────────────────────────────────────────────

class MessageRequest(BaseModel):
    content: str
    target: str = "council"
    msg_type: str = "HUMAN_OVERRIDE"
    sender: str = "human"

class TerminalRequest(BaseModel):
    command: str

class DecompileRequest(BaseModel):
    path: str

# ── Endpoints ────────────────────────────────────────────────

@app.get("/api/status")
async def get_system_status():
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        steward = get_steward()
        gpu_stats = steward.get_gpu_stats() if steward else {"error": "NVIDIA monitoring unavailable"}
        return {
            "status": "ONLINE",
            "timestamp": datetime.now().isoformat(),
            "hardware": {"cpu": cpu, "ram": ram, "gpu": gpu_stats},
            "agents_count": len(agent_ipc.AGENTS)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages")
async def get_messages(limit: int = 50, after: Optional[str] = None):
    try:
        messages = agent_ipc.read_recent(n=limit, after=after)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send")
async def send_message(req: MessageRequest):
    try:
        agent_ipc.post(
            sender=req.sender,
            msg_type=req.msg_type,
            content=req.content,
            target=req.target,
            channel="GENERAL"
        )
        return {"success": True, "ts": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents")
async def get_agents():
    return {"agents": [{"id": k, **v} for k, v in agent_ipc.AGENTS.items()]}

@app.get("/api/revenue")
async def get_revenue():
    log_path = os.path.join(os.getcwd(), "revenue_events.log")
    events = []
    total = 0
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    events.append(ev)
                    total += ev.get("amount", 0)
                except: continue
    return {
        "total_logged": total,
        "stripe_available": total * 0.95, # Mock deduction
        "recent_events": events[-10:][::-1]
    }

@app.get("/api/explorer/ls")
async def list_files(path: str = ""):
    root = os.getcwd()
    target_path = os.path.join(root, path) if path else root
    if not os.path.exists(target_path):
        return {"error": "Path not found"}
    
    items = []
    try:
        for entry in os.scandir(target_path):
            if entry.name.startswith(".") or entry.name == "node_modules": continue
            items.append({
                "name": entry.name,
                "path": os.path.relpath(entry.path, root),
                "isDir": entry.is_dir()
            })
        return items
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/explorer/read")
async def read_file(path: str):
    root = os.getcwd()
    target_path = os.path.join(root, path)
    if not os.path.exists(target_path) or os.path.isdir(target_path):
        return {"error": "Invalid file"}
    
    try:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000) # Limit to 10kb for mobile
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/terminal/run")
async def run_terminal(req: TerminalRequest):
    try:
        # Restricted command list or just run it (careful!)
        # For now, let's allow basic commands
        process = subprocess.Popen(
            req.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        stdout, stderr = process.communicate(timeout=10)
        return {"stdout": stdout, "stderr": stderr}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/system/audit")
async def get_audit():
    # Use agent_ipc to get security flags
    events = agent_ipc.get_latest(channel="SECURITY", n=20)
    return {"events": [f"{m['ts']} [{m['from']}]: {m['content']}" for m in events]}

@app.get("/api/system/arch")
async def get_arch():
    # Mock architectural map
    return {
        "nodes": [
            {"id": "architect", "role": "Design & Planning", "status": "Stable"},
            {"id": "sentinel", "role": "Security & Audit", "status": "Active"},
            {"id": "alchemist", "role": "Optimization", "status": "Hibernating"},
            {"id": "phantom", "role": "Hardware Vision", "status": "Active"}
        ]
    }

@app.get("/api/system/screenshot")
async def get_screenshot():
    if not HAS_SCREENSHOT:
        raise HTTPException(status_code=501, detail="Screenshot extension not installed")
    
    try:
        img = pyautogui.screenshot()
        img = img.convert("RGB")
        img.thumbnail((1280, 720)) # Resize for mobile
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/missions")
async def get_missions():
    # Mock mission list
    return {
        "missions": [
            {"id": "M-101", "name": "Global Outreach", "status": "Active", "reward": 500},
            {"id": "M-102", "name": "Security Hardening", "status": "Pending", "reward": 1200},
            {"id": "M-103", "name": "UI Evolution", "status": "Completed", "reward": 800}
        ]
    }

@app.post("/api/system/decompile")
async def decompile_file(req: DecompileRequest):
    # Mock decompiler output
    return {
        "symbols": ["init_core", "seal_vram", "bridge_ipc", "auth_link"],
        "vulnerabilities": ["CORS broad wildcard", "Unencrypted IPC socket"],
        "recommendation": "Seal the relay with JWT and restrict CORS to identified mobile IPs."
    }

if __name__ == "__main__":
    print("🚀 Overlord Mobile Relay starting on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
