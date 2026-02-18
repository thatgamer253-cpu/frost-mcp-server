import os
import time
import shutil
import magic
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import Healer Protocols
from healing_protocols.python_healer import PythonHealer
from healing_protocols.video_healer import VideoHealer
from healing_protocols.data_healer import DataHealer

class UniversalHealer(FileSystemEventHandler):
    def __init__(self):
        self.python_healer = PythonHealer()
        self.video_healer = VideoHealer()
        self.data_healer = DataHealer()
        
        # Ensure folders exist
        os.makedirs("./synthesis_final", exist_ok=True)
        os.makedirs("./quarantine", exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = os.path.abspath(event.src_path)
        # Wait for file to stabilize
        time.sleep(2)
        
        if not os.path.exists(file_path):
            return

        try:
            # Check if file is still there and accessible
            try:
                with open(file_path, 'rb') as f: pass
            except: 
                print(f"!!! [Access Denied]: {os.path.basename(file_path)} is locked.")
                return

            file_type = magic.from_file(file_path, mime=True)
            print(f"\n--- [Target Detected]: {os.path.basename(file_path)} ({file_type}) ---")

            # Route to Healer
            healer = self._get_healer(file_path, file_type)
            
            if not healer:
                # Sentinel Rule: Try to read header if unknown
                if self._attempt_manual_id(file_path):
                    print("  ✓ Manual ID successful. Routing to PythonHealer...")
                    healer = self.python_healer
                else:
                    self._quarantine(file_path, "Unidentifiable header/mime")
                    return

            # UNIVERSAL PROTOCOL
            # 1. SENTINEL
            valid, reason = healer.sentinel_validate(file_path)
            if valid:
                print(f"  ✓ Sentinel: PASS")
                
                # 2. ALCHEMIST
                print(f"  ⚡ Alchemist: Processing...")
                healed_path = healer.alchemist_process(file_path)
                
                # 3. STEALTH
                print(f"  👤 Stealth: Applying cover...")
                final_path = healer.stealth_apply(healed_path)
                
                # Final Move to Synthesis Folder
                dest_name = os.path.basename(file_path)
                dest_path = os.path.join("./synthesis_final", dest_name)
                
                # Ensure we don't overwrite with original if processing failed
                if final_path != file_path:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.move(final_path, dest_path)
                    print(f"--- [Success]: {dest_name} is now LIVE. ---")
                    
                    # Cleanup original and temp
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if healed_path != file_path and os.path.exists(healed_path):
                        os.remove(healed_path)
                else:
                    print(f"!!! [Partial Failure]: Healer returned original path for {dest_name}")
            else:
                self._quarantine(file_path, reason)

        except Exception as e:
            print(f"Critical Healer Error: {e}")

    def _get_healer(self, path, mime):
        basename = os.path.basename(path).lower()
        if "python" in mime or path.endswith(".py") or basename == "requirements.txt":
            return self.python_healer
        elif "video" in mime or path.endswith(".mp4"):
            return self.video_healer
        elif "json" in mime or path.endswith(".json"):
            return self.data_healer
        elif "text" in mime:
            return self.python_healer
        return None

    def _attempt_manual_id(self, path):
        """Sentinel Rule: Read header if MIME fails."""
        try:
            basename = os.path.basename(path).lower()
            if basename == "requirements.txt": return True
            
            with open(path, 'rb') as f:
                header = f.read(1024).decode('utf-8', errors='ignore').lower()
                # Check for common patterns
                if "import " in header or "def " in header or "class " in header:
                    return True
                if header.strip().startswith("{") or header.strip().startswith("["):
                    return True
        except: pass
        return False

    def _quarantine(self, path, reason):
        print(f"--- [Failed]: {reason}. Moved to Quarantine. ---")
        dest = os.path.join("./quarantine", os.path.basename(path))
        shutil.move(path, dest)

if __name__ == "__main__":
    path = "./output"
    if not os.path.exists(path):
        os.makedirs(path)
        
    event_handler = UniversalHealer()
    observer = Observer()
    # Recursive set to True to catch agent-specific subfolders
    observer.schedule(event_handler, path, recursive=True)
    
    print(f"╔════════════════════════════════════════════╗")
    print(f"║  UNIVERSAL HEALING PIPELINE ACTIVE         ║")
    print(f"║  Watching: {os.path.abspath(path)} (Recursive) ║")
    print(f"╚════════════════════════════════════════════╝")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
