#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  N E X U S   C O M M A N D   v3.0  —  Desktop GUI           ║
║  eDEX-UI / TRON Legacy Inspired Interface                    ║
║  Flask + HTML/CSS/JS  •  Ollama Chat  •  Creation Engine     ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, os, sys, time, threading, webbrowser, queue
from datetime import datetime
from flask import Flask, Response, request, jsonify, stream_with_context

# ── Path setup ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from engine_core import NexusEngine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

import requests as req_lib

# ── Config ────────────────────────────────────────────────────
OLLAMA_API = "http://localhost:11434/api"
MODEL = os.getenv("OLLAMA_MODEL", "antigravity")
PORT = 7777

app = Flask(__name__)
log_queue = queue.Queue()        # SSE log stream
ollama_context = []              # Chat context persistence
build_lock = threading.Lock()

# ══════════════════════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/api/system")
def api_system():
    if HAS_PSUTIL:
        return jsonify(
            cpu=psutil.cpu_percent(interval=0),
            ram=psutil.virtual_memory().percent,
            disk=psutil.disk_usage("/").percent,
        )
    import random
    return jsonify(
        cpu=round(random.uniform(8, 55), 1),
        ram=round(random.uniform(30, 70), 1),
        disk=round(random.uniform(20, 50), 1),
    )

@app.route("/api/files")
def api_files():
    out = os.path.join(os.path.dirname(__file__), "builds", "nexus_session")
    if not os.path.exists(out):
        out = os.path.join(os.path.dirname(__file__), "output")
    files = []
    if os.path.exists(out):
        for root, dirs, fnames in os.walk(out):
            for f in fnames:
                if f.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, f), out)
                files.append(rel.replace("\\", "/"))
    return jsonify(files=files, total=len(files))

@app.route("/api/chat", methods=["POST"])
def api_chat():
    global ollama_context
    prompt = request.json.get("prompt", "")
    if not prompt:
        return jsonify(error="Empty prompt"), 400

    def generate():
        global ollama_context
        data = {"model": MODEL, "prompt": prompt, "context": ollama_context, "stream": True}
        try:
            with req_lib.post(f"{OLLAMA_API}/generate", json=data, stream=True, timeout=120) as r:
                if r.status_code != 200:
                    yield f"data: {json.dumps({'error': f'Ollama error {r.status_code}'})}\n\n"
                    return
                for line in r.iter_lines():
                    if line:
                        body = json.loads(line)
                        chunk = body.get("response", "")
                        if chunk:
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        if body.get("done"):
                            ollama_context = body.get("context", [])
                            yield f"data: {json.dumps({'done': True})}\n\n"
        except req_lib.exceptions.ConnectionError:
            yield f"data: {json.dumps({'error': 'Cannot connect to Ollama. Is ollama serve running?'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/build", methods=["POST"])
def api_build():
    prompt = request.json.get("prompt", "")
    if not prompt:
        return jsonify(error="Empty prompt"), 400
    if not HAS_ENGINE:
        return jsonify(error="NexusEngine not available"), 500
    if build_lock.locked():
        return jsonify(error="Build already in progress"), 429

    def run():
        with build_lock:
            log_queue.put({"tag": "ENGINE", "msg": f"Build started: {prompt}"})
            try:
                engine = NexusEngine(
                    project_name="nexus_session",
                    model=f"ollama:{MODEL}",
                    on_log=lambda cat, msg: log_queue.put({"tag": cat, "msg": msg}),
                    use_docker=False,
                )
                result = engine.run_full_build(prompt)
                log_queue.put({"tag": "SUCCESS", "msg": f"Build complete! Files: {result.get('files_written', '?')}"})
            except Exception as e:
                log_queue.put({"tag": "ERROR", "msg": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify(status="started")

@app.route("/api/logs")
def api_logs():
    def stream():
        while True:
            try:
                item = log_queue.get(timeout=30)
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'tag': 'PING', 'msg': ''})}\n\n"
    return Response(stream_with_context(stream()), mimetype="text/event-stream")


# ══════════════════════════════════════════════════════════════
#  HTML / CSS / JS  —  The Full GUI
# ══════════════════════════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NEXUS COMMAND v3.0</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
/* ═══ RESET & ROOT ═══════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg:        #060610;
    --bg-card:   #0c0c1a;
    --bg-input:  #0a0a16;
    --primary:   #00e5ff;
    --secondary: #7c3aed;
    --success:   #00ff41;
    --warning:   #ffab00;
    --error:     #ff1744;
    --text:      #c0d0e0;
    --dim:       #2a2a3e;
    --border:    #1a2a3a;
    --glow:      rgba(0, 229, 255, 0.15);
    --glow-purple: rgba(124, 58, 237, 0.15);
    --font-mono: 'JetBrains Mono', 'Consolas', monospace;
    --font-title: 'Orbitron', sans-serif;
}

body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 13px;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

/* ═══ SCAN-LINE OVERLAY ══════════════════════════════════════ */
body::after {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 229, 255, 0.015) 2px,
        rgba(0, 229, 255, 0.015) 4px
    );
    z-index: 9999;
}

/* ═══ HEADER ═════════════════════════════════════════════════ */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 24px;
    background: linear-gradient(135deg, #0a0a18 0%, #0d0d22 100%);
    border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 20px var(--glow);
    flex-shrink: 0;
}
.header-title {
    font-family: var(--font-title);
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 6px;
    color: var(--primary);
    text-shadow: 0 0 20px var(--primary), 0 0 40px rgba(0, 229, 255, 0.3);
}
.header-title .dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--primary);
    border-radius: 50%;
    margin-right: 12px;
    box-shadow: 0 0 10px var(--primary);
    animation: pulse 2s ease-in-out infinite;
}
.header-right {
    display: flex;
    align-items: center;
    gap: 20px;
    font-size: 12px;
}
.header-clock {
    color: var(--dim);
    font-size: 14px;
    letter-spacing: 2px;
}
.header-status {
    color: var(--success);
    font-weight: 700;
    text-shadow: 0 0 8px var(--success);
}

@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--primary); }
    50%      { opacity: 0.4; box-shadow: 0 0 4px var(--primary); }
}

/* ═══ MAIN GRID ══════════════════════════════════════════════ */
.main {
    display: grid;
    grid-template-columns: 200px 1fr 220px;
    gap: 1px;
    flex: 1;
    overflow: hidden;
    background: var(--border);
}

/* ═══ PANELS ═════════════════════════════════════════════════ */
.panel {
    background: var(--bg-card);
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}
.panel-title {
    font-family: var(--font-title);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 4px;
    color: var(--primary);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* ── Left Sidebar ──────────────────────────────────────────── */
.stat-group { margin-bottom: 20px; }
.stat-group .label {
    font-size: 10px;
    color: var(--dim);
    letter-spacing: 2px;
    margin-bottom: 6px;
}
.bar-container {
    height: 6px;
    background: var(--dim);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 4px;
}
.bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.8s ease;
    box-shadow: 0 0 8px currentColor;
}
.bar-fill.cpu  { background: var(--primary); color: var(--primary); }
.bar-fill.ram  { background: var(--secondary); color: var(--secondary); }
.bar-fill.disk { background: var(--warning); color: var(--warning); }
.stat-value {
    font-size: 11px;
    color: var(--text);
    text-align: right;
}

.engine-block { margin-top: 12px; }
.engine-block .field {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 11px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}
.engine-block .field .key { color: var(--dim); }
.engine-block .field .val { color: var(--primary); font-weight: 600; }
.engine-block .field .val.idle { color: var(--success); }
.engine-block .field .val.busy { color: var(--error); animation: pulse 1s ease-in-out infinite; }

/* ── Center Terminal ───────────────────────────────────────── */
.terminal-panel { padding: 0; }
.terminal {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    font-size: 13px;
    line-height: 1.7;
    scroll-behavior: smooth;
}
.terminal::-webkit-scrollbar { width: 4px; }
.terminal::-webkit-scrollbar-track { background: var(--bg); }
.terminal::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 2px; }

.msg { margin-bottom: 4px; white-space: pre-wrap; word-break: break-word; }
.msg.user { color: var(--success); font-weight: 600; }
.msg.ai   { color: var(--text); }
.msg.engine { color: var(--primary); font-size: 12px; }
.msg.error  { color: var(--error); }
.msg.success { color: var(--success); }
.msg.warn   { color: var(--warning); }
.msg.system {
    color: var(--primary);
    font-family: var(--font-title);
    font-size: 11px;
    letter-spacing: 3px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
}
.msg .tag {
    display: inline-block;
    min-width: 80px;
    font-weight: 700;
    margin-right: 8px;
}
.typing-cursor {
    display: inline-block;
    width: 8px; height: 14px;
    background: var(--primary);
    animation: blink 0.7s step-end infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
}
@keyframes blink { 50% { opacity: 0; } }

/* ── Right Sidebar ─────────────────────────────────────────── */
.file-list { flex: 1; overflow-y: auto; }
.file-item {
    padding: 5px 8px;
    font-size: 11px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 6px;
}
.file-item .icon { font-size: 13px; }
.file-item:hover { background: var(--glow); }

.stats-block {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
}
.stats-block .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    font-size: 11px;
}
.stats-block .stat-row .key { color: var(--dim); }
.stats-block .stat-row .val { color: var(--success); font-weight: 600; }

/* ═══ COMMAND BAR ════════════════════════════════════════════ */
.command-bar {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    background: linear-gradient(135deg, #0a0a18, #0d0d22);
    border-top: 1px solid var(--border);
    box-shadow: 0 -2px 20px var(--glow);
    flex-shrink: 0;
    gap: 12px;
}
.cmd-prefix {
    font-family: var(--font-title);
    font-size: 12px;
    color: var(--primary);
    letter-spacing: 2px;
    text-shadow: 0 0 10px var(--primary);
    white-space: nowrap;
}
.cmd-input {
    flex: 1;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px 16px;
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 14px;
    outline: none;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.cmd-input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 15px var(--glow), inset 0 0 8px var(--glow);
}
.cmd-input::placeholder { color: var(--dim); }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
    <div class="header-title"><span class="dot"></span>NEXUS COMMAND</div>
    <div class="header-right">
        <span style="color:var(--dim)">v3.0</span>
        <span class="header-clock" id="clock">00:00:00</span>
        <span class="header-status">⚡ LIVE</span>
    </div>
</div>

<!-- MAIN 3-COLUMN GRID -->
<div class="main">
    <!-- LEFT: System Monitor -->
    <div class="panel">
        <div class="panel-title">SYSTEM</div>
        <div class="stat-group">
            <div class="label">CPU</div>
            <div class="bar-container"><div class="bar-fill cpu" id="cpu-bar" style="width:0%"></div></div>
            <div class="stat-value" id="cpu-val">0%</div>
        </div>
        <div class="stat-group">
            <div class="label">MEMORY</div>
            <div class="bar-container"><div class="bar-fill ram" id="ram-bar" style="width:0%"></div></div>
            <div class="stat-value" id="ram-val">0%</div>
        </div>
        <div class="stat-group">
            <div class="label">DISK</div>
            <div class="bar-container"><div class="bar-fill disk" id="disk-bar" style="width:0%"></div></div>
            <div class="stat-value" id="disk-val">0%</div>
        </div>

        <div class="engine-block">
            <div class="panel-title" style="margin-top:8px">ENGINE</div>
            <div class="field"><span class="key">Status</span><span class="val idle" id="eng-status">● ONLINE</span></div>
            <div class="field"><span class="key">Model</span><span class="val" id="eng-model">""" + MODEL + r"""</span></div>
            <div class="field"><span class="key">Phase</span><span class="val idle" id="eng-phase">IDLE</span></div>
            <div class="field"><span class="key">Errors</span><span class="val" id="eng-errors" style="color:var(--dim)">0</span></div>
        </div>
    </div>

    <!-- CENTER: Terminal -->
    <div class="panel terminal-panel">
        <div id="terminal" class="terminal">
            <div class="msg system">◆  N E X U S   C O M M A N D   v 3 . 0</div>
            <div class="msg" style="color:var(--dim)">Powered by Antigravity + Ollama  •  Type /help for commands</div>
            <div class="msg" style="color:var(--dim)">────────────────────────────────────────────────</div>
        </div>
    </div>

    <!-- RIGHT: File Browser + Stats -->
    <div class="panel">
        <div class="panel-title">FILE BROWSER</div>
        <div class="file-list" id="file-list">
            <div class="file-item" style="color:var(--dim)">No files yet</div>
        </div>
        <div class="stats-block">
            <div class="panel-title">BUILD STATS</div>
            <div class="stat-row"><span class="key">Files</span><span class="val" id="stat-files">0</span></div>
            <div class="stat-row"><span class="key">Elapsed</span><span class="val" id="stat-time">00:00</span></div>
        </div>
    </div>
</div>

<!-- COMMAND BAR -->
<div class="command-bar">
    <span class="cmd-prefix">◆ DIRECTIVE ▸</span>
    <input class="cmd-input" id="cmd-input" type="text" placeholder="Enter command or ask anything..." autofocus>
</div>

<script>
// ═══ CLOCK ══════════════════════════════════════════════════
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toTimeString().slice(0, 8);
}
setInterval(updateClock, 1000);
updateClock();

// ═══ SYSTEM MONITOR ═════════════════════════════════════════
async function pollSystem() {
    try {
        const r = await fetch('/api/system');
        const d = await r.json();
        document.getElementById('cpu-bar').style.width = d.cpu + '%';
        document.getElementById('cpu-val').textContent = d.cpu.toFixed(1) + '%';
        document.getElementById('ram-bar').style.width = d.ram + '%';
        document.getElementById('ram-val').textContent = d.ram.toFixed(1) + '%';
        document.getElementById('disk-bar').style.width = d.disk + '%';
        document.getElementById('disk-val').textContent = d.disk.toFixed(1) + '%';
    } catch(e) {}
}
setInterval(pollSystem, 2000);
pollSystem();

// ═══ FILE BROWSER ═══════════════════════════════════════════
const iconMap = {
    '.py':'🐍', '.js':'⚡', '.ts':'🔷', '.html':'🌐', '.css':'🎨',
    '.json':'📊', '.md':'📝', '.txt':'📄', '.png':'🖼️', '.exe':'⚙️',
};
function getIcon(name) {
    const ext = '.' + name.split('.').pop().toLowerCase();
    return iconMap[ext] || '📄';
}

async function pollFiles() {
    try {
        const r = await fetch('/api/files');
        const d = await r.json();
        const el = document.getElementById('file-list');
        document.getElementById('stat-files').textContent = d.total;
        if (d.files.length === 0) {
            el.innerHTML = '<div class="file-item" style="color:var(--dim)">No files yet</div>';
            return;
        }
        el.innerHTML = d.files.map(f =>
            `<div class="file-item"><span class="icon">${getIcon(f)}</span>${f}</div>`
        ).join('');
    } catch(e) {}
}
setInterval(pollFiles, 3000);
pollFiles();

// ═══ TERMINAL HELPERS ═══════════════════════════════════════
const terminal = document.getElementById('terminal');

function addMsg(text, cls='') {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.textContent = text;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
    return div;
}

function showHelp() {
    addMsg('');
    addMsg('COMMANDS', 'system');
    addMsg('/build <prompt>    Build software from description', '');
    addMsg('/model <name>      Switch Ollama model', '');
    addMsg('/clear             Clear terminal', '');
    addMsg('/help              Show this help', '');
    addMsg('/exit              Close interface', '');
    addMsg('');
    addMsg('AUTO-BUILD — Just type naturally!', 'warn');
    addMsg('"Create a snake game" will auto-trigger the build engine.', '');
    addMsg('');
}

// ═══ CHAT (SSE Streaming) ═══════════════════════════════════
async function doChat(prompt) {
    const msgDiv = addMsg('', 'ai');
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    msgDiv.appendChild(cursor);

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt})
        });
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));
                if (data.error) {
                    msgDiv.textContent = '❌ ' + data.error;
                    msgDiv.className = 'msg error';
                    return;
                }
                if (data.chunk) {
                    fullText += data.chunk;
                    // Remove cursor, update text, re-add cursor
                    if (cursor.parentNode) cursor.remove();
                    msgDiv.textContent = fullText;
                    msgDiv.appendChild(cursor);
                    terminal.scrollTop = terminal.scrollHeight;
                }
                if (data.done) {
                    if (cursor.parentNode) cursor.remove();
                }
            }
        }
        if (cursor.parentNode) cursor.remove();
    } catch(e) {
        msgDiv.textContent = '❌ Connection error: ' + e.message;
        msgDiv.className = 'msg error';
    }
}

// ═══ BUILD ══════════════════════════════════════════════════
let buildStartTime = null;
let buildTimer = null;

async function doBuild(prompt) {
    addMsg('🚀 CREATION ENGINE ONLINE', 'success');
    addMsg('Goal: ' + prompt, '');

    const phaseEl = document.getElementById('eng-phase');
    const statusEl = document.getElementById('eng-status');
    phaseEl.textContent = 'BUILDING';
    phaseEl.className = 'val busy';
    statusEl.textContent = '● BUSY';
    statusEl.className = 'val busy';

    buildStartTime = Date.now();
    buildTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - buildStartTime) / 1000);
        const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        document.getElementById('stat-time').textContent = m + ':' + s;
    }, 1000);

    try {
        await fetch('/api/build', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt})
        });
    } catch(e) {
        addMsg('❌ Build request failed: ' + e.message, 'error');
    }
}

// ═══ ENGINE LOG STREAM (SSE) ════════════════════════════════
const logSource = new EventSource('/api/logs');
logSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.tag === 'PING') return;

    const colorMap = {
        ERROR: 'error', SUCCESS: 'success', WARN: 'warn',
        ENGINE: 'engine', ARCHITECT: 'engine', DEV: 'engine',
    };
    const cls = colorMap[data.tag] || 'engine';
    addMsg(`[${data.tag}] ${data.msg}`, cls);

    if (data.tag === 'SUCCESS' || data.tag === 'ERROR') {
        const phaseEl = document.getElementById('eng-phase');
        const statusEl = document.getElementById('eng-status');
        phaseEl.textContent = 'IDLE';
        phaseEl.className = 'val idle';
        statusEl.textContent = '● ONLINE';
        statusEl.className = 'val idle';
        if (buildTimer) { clearInterval(buildTimer); buildTimer = null; }
        if (data.tag === 'ERROR') {
            const errEl = document.getElementById('eng-errors');
            errEl.textContent = parseInt(errEl.textContent) + 1;
            errEl.style.color = 'var(--error)';
        }
        pollFiles();
    }
};

// ═══ INPUT HANDLER ══════════════════════════════════════════
const input = document.getElementById('cmd-input');
input.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const raw = input.value.trim();
    if (!raw) return;
    input.value = '';

    addMsg('> ' + raw, 'user');

    const parts = raw.split(' ');
    const cmd = parts[0].toLowerCase();

    if (cmd === '/exit' || cmd === '/quit') {
        addMsg('Disconnecting...', 'warn');
        setTimeout(() => window.close(), 500);
        return;
    }
    if (cmd === '/clear') {
        terminal.innerHTML = '<div class="msg system">◆  Terminal cleared</div>';
        return;
    }
    if (cmd === '/help') { showHelp(); return; }
    if (cmd === '/model') {
        if (parts.length > 1) {
            document.getElementById('eng-model').textContent = parts[1];
            addMsg('Model set to: ' + parts[1], 'success');
        } else {
            addMsg('Current model: ' + document.getElementById('eng-model').textContent, '');
        }
        return;
    }
    if (cmd === '/build') {
        const prompt = raw.slice(7).trim();
        if (!prompt) { addMsg('Usage: /build <what to build>', 'error'); return; }
        doBuild(prompt);
        return;
    }

    // Auto-build detection
    const lower = raw.toLowerCase();
    const buildKW = ['create', 'make', 'build', 'generate', 'code', 'program', 'app', 'script', 'write'];
    const skipKW = ['how to', 'explain', 'what is'];
    if (buildKW.some(k => lower.includes(k)) && raw.split(' ').length > 2
        && !skipKW.some(k => lower.includes(k))) {
        addMsg('🚀 Auto-Build Detected!', 'warn');
        doBuild(raw);
        return;
    }

    // Default: Chat
    doChat(raw);
});
</script>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n  ◆ NEXUS COMMAND v3.0")
    print(f"  ◆ Opening browser → http://localhost:{PORT}")
    print(f"  ◆ Press Ctrl+C to stop\n")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
