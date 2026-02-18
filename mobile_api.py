import os
import sys
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime
import subprocess
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import io
try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

# Ensure we can import agent_ipc from the project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import agent_ipc as hub
except ImportError:
    print("Error: agent_ipc not found. Please run this script from the project root.")
    sys.exit(1)

app = FastAPI(title="Sovereign Council Mobile API")

# Enable CORS for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost", 
        "capacitor://localhost", 
        "http://localhost:3000", 
        "http://192.168.0.207:3000",
        "http://localhost:8081", 
        "http://192.168.0.207:8081"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": str(datetime.datetime.now())}

# Project Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount artifacts and output as static to serve files
app.mount("/static/output", StaticFiles(directory=OUTPUT_DIR), name="output")

class PostMessageRequest(BaseModel):
    content: str
    sender: str = "human"
    target: str = "council"
    channel: str = "GENERAL"

@app.get("/api/agents")
async def get_agents():
    """Return the list of project agents."""
    agents_list = []
    for agent_id, info in hub.AGENTS.items():
        agents_list.append({
            "id": agent_id,
            "name": info["name"],
            "icon": info["icon"],
            "color": info["color"]
        })
    return {"agents": agents_list}

@app.get("/api/status")
async def get_status():
    """Return system heartbeats."""
    # psutil.cpu_percent(interval=None) can return 0.0 on the first call.
    # We'll use a very short interval to get a real reading.
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    
    return {
        "hardware": {
            "cpu": cpu,
            "ram": ram
        },
        "agents_online": True
    }

@app.get("/api/messages")
async def get_messages(limit: int = 50):
    """Fetch recent messages from the IPC bus."""
    messages = hub.read_recent(n=limit)
    return {"messages": messages}

@app.get("/api/revenue")
async def get_revenue():
    """Fetch total real-world revenue and recent events."""
    revenue_log = os.path.join(ROOT_DIR, "revenue_events.log")
    events = []
    total = 0.0
    if os.path.exists(revenue_log):
        with open(revenue_log, "r") as f:
            for line in f:
                if "|" in line:
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        try:
                            amount = float(parts[1].replace("$", "").strip())
                            total += amount
                            events.append({
                                "ts": parts[0].strip(),
                                "amount": amount,
                                "service": parts[2].strip()
                            })
                        except: pass
    
    # Also grab real Stripe balance
    stripe_available = 0.0
    try:
        from creation_engine.stripe_service import StripeService
        stripe = StripeService()
        balance = stripe.get_balance()
        stripe_available = balance.get("available", 0.0)
    except: pass

    return {
        "total_logged": total,
        "stripe_available": stripe_available,
        "recent_events": events[-10:]
    }

@app.get("/api/missions")
async def get_missions():
    """Fetch global outreach missions found by Ambassador."""
    # We poll the 'BOUNTY' messages from the IPC bus
    bounties = hub.get_latest(msg_type="BOUNTY", n=10)
    
    missions = []
    for b in bounties:
        missions.append({
            "ts": b.get("ts"),
            "agent": b.get("from"),
            "content": b.get("content", "")
        })
        
    return {"missions": missions}

@app.get("/api/explorer/ls")
async def list_files(path: str = ""):
    """List files in the output directory."""
    target = os.path.normpath(os.path.join(OUTPUT_DIR, path))
    if not target.startswith(OUTPUT_DIR):
        return {"error": "Access denied"}
    
    if not os.path.exists(target):
        return {"error": "Path not found"}
    
    entries = []
    try:
        for entry in os.scandir(target):
            entries.append({
                "name": entry.name,
                "isDir": entry.is_dir(),
                "path": os.path.relpath(entry.path, OUTPUT_DIR),
                "size": entry.stat().st_size if not entry.is_dir() else 0
            })
    except Exception as e:
        return {"error": str(e)}
        
    return sorted(entries, key=lambda x: (not x["isDir"], x["name"]))

@app.get("/api/explorer/read")
async def read_file(path: str):
    """Read file content."""
    target = os.path.normpath(os.path.join(OUTPUT_DIR, path))
    if not target.startswith(OUTPUT_DIR):
        return {"error": "Access denied"}
    
    if not os.path.exists(target) or os.path.isdir(target):
        return {"error": "File not found"}
    
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/terminal/run")
async def run_cmd(req: Dict[str, str]):
    """Execute a terminal command."""
    cmd = req.get("command")
    if not cmd:
        return {"error": "No command"}
    
    try:
        # Run in a shell, capturing output
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd=ROOT_DIR
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/system/screenshot")
async def get_screenshot():
    """Take a live screenshot of the host machine."""
    if not ImageGrab:
        return {"error": "Pillow not installed"}
    
    try:
        img = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/system/audit")
async def get_audit():
    """Fetch the system audit log."""
    audit_log = os.path.join(ROOT_DIR, "system_audit.log")
    if not os.path.exists(audit_log):
        return {"events": []}
    
    events = []
    try:
        with open(audit_log, "r", encoding="utf-8") as f:
            for line in f.readlines()[-100:]:
                events.append(line.strip())
    except: pass
    return {"events": events}

@app.get("/api/system/arch")
async def get_arch():
    """Return the system architecture map."""
    return {
        "nexus_core": "Sovereign Engine v2.5",
        "nodes": [
            {"id": "sentinel", "role": "Perimeter Security", "status": "Shields Up"},
            {"id": "ambassador", "role": "Commercial Outreach", "status": "Scouting"},
            {"id": "alchemist", "role": "Content Synthesis", "status": "Idle"},
            {"id": "healer", "role": "Autonomous Repair", "status": "Monitoring"},
            {"id": "steward", "role": "Hardware I/O", "status": "Ready"}
        ],
        "links": [
            {"source": "sentinel", "target": "nexus_core"},
            {"source": "ambassador", "target": "nexus_core"},
            {"source": "healer", "target": "sentinel"},
            {"source": "steward", "target": "nexus_core"}
        ]
    }

@app.post("/api/system/decompile")
async def decompile(req: Dict[str, str]):
    """Analyze code as a 'decompiler'."""
    path = req.get("path")
    if not path: return {"error": "No path"}
    
    # Mock advanced analysis
    return {
        "symbols": ["core_loop", "init_seq", "auth_gate"],
        "vulnerabilities": ["Unprotected IPC", "Loose CORS"],
        "entropy": 0.84,
        "recommendation": "Seal the logic gate in sector 7."
    }

@app.post("/api/send")
async def send_message(req: PostMessageRequest):
    """Post a new message to the IPC bus."""
    hub.post(
        sender=req.sender,
        msg_type=hub.MessageType.HUMAN if req.sender == "human" else hub.MessageType.PROPOSE,
        content=req.content,
        target=req.target,
        channel=req.channel
    )
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    # Run on all interfaces so the phone can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000)
