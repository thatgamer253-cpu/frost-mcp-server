import os, shutil, datetime, subprocess, json, re, sys, stat, requests

# Windows-specific: suppress console windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# === EXTENDED CONFIGURATION ===
OLLAMA_MODEL = "llama3"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
LOG_FILE = os.path.join(PROJECT_ROOT, "overlord.log")
# Protected files to ensure system stability
PROTECTED_FILES = ["interface_v2.py", "NexusCommand.bat", "config.json", "dashboard.py"]

os.makedirs(BACKUP_DIR, exist_ok=True)

# Master Prompt for Social Architecture (Sovereign v2026)
SOCIAL_BLUEPRINT = """
You are the SOVEREIGN SOCIAL ARCHITECT v2026.
When tasked to 'clone' or 'build social', synthesize a high-fidelity digital ecosystem:
1. INFRASTRUCTURE: PostgreSQL relational core with Redis caching for real-time throughput.
2. AUTH: Secure JWT/Bearer Zero-Trust authentication logic.
3. ALGORITHM: Advanced feed scoring (Velocity, Sentiment, Engagement) in feed.py.
4. UI/UX: Next.js 15 (App Router), Tailwind CSS 4, and Framer Motion for premium aesthetics.
5. NEXUS NATIVE: Every social app MUST include an internal 'Pulse' feed for agent chatter.

Formatting: Output code with '### FILENAME: path/to/file.ext' precedes each block.
Architecture Depth: Target 10+ modular files. Use premium typography and glassmorphism.
"""

def create_backup(filename):
    src_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(src_path):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst_path = os.path.join(BACKUP_DIR, f"{os.path.basename(filename)}.{ts}.bak")
        shutil.copy2(src_path, dst_path)

def process_response(text):
    # Detect directory-aware filenames
    pattern = r"### FILENAME: ([\w\./]+)\s+```[\w]*\n([\s\S]*?)```"
    matches = re.findall(pattern, text)
    
    for filename, code in matches:
        if any(p in filename for p in PROTECTED_FILES): continue
        
        full_path = os.path.join(PROJECT_ROOT, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        create_backup(filename)
        with open(full_path, "w") as f:
            f.write(code.strip())
        print(f"🛠️ [ARCHITECT] Deployed: {filename}")
        
        # Self-Healing: Auto-run tests on backend files
        if filename.endswith(".py"): execute_and_heal(filename)

def execute_and_heal(filename):
    file_path = os.path.join(PROJECT_ROOT, filename)
    try:
        result = subprocess.run([sys.executable, file_path], capture_output=True, text=True, timeout=10, creationflags=CREATE_NO_WINDOW)
        if result.returncode != 0:
            print(f"🚨 [HEALER] Crash in {filename}. Patching...")
            repair_prompt = f"Fix this {filename}. Error: {result.stderr}\nCode: {open(file_path).read()}"
            process_response(call_ollama(repair_prompt))
    except Exception as e: print(f"❌ Error: {e}")

def call_ollama(prompt):
    try:
        r = requests.post('http://localhost:11434/api/generate', 
                          json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        return r.json().get('response', "")
    except: return "Connection Lost."

def main():
    print("\n--- 🛸 OVERLORD SOCIAL ENGINE: ACTIVE ---")
    while True:
        cmd = input("\nNexus > ")
        if cmd.lower() in ['exit', 'shutdown']: break
        process_response(call_ollama(f"{SOCIAL_BLUEPRINT}\nUser Request: {cmd}"))

if __name__ == "__main__":
    main()
