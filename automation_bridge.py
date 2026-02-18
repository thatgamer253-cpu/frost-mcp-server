import os
import json
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# SETTINGS
WATCH_PATH = Path("./nexus-os-react/public/exports")
REGISTRY_PATH = Path("./nexus-os-react/public/app_registry.json")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutomationBridge")

class EngineBridge(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('app_manifest.json'):
            logger.info(f"🔄 Detected manifest update: {event.src_path}")
            self._handle_manifest(Path(event.src_path))
            
    def on_created(self, event):
        if event.src_path.endswith('app_manifest.json'):
            logger.info(f"✨ Detected new manifest: {event.src_path}")
            self._handle_manifest(Path(event.src_path))
            
    def _handle_manifest(self, path):
        # Wait for file to be released by the writer
        manifest = None
        for i in range(10):
            try:
                time.sleep(0.5)
                # Try UTF-8 first
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                except UnicodeDecodeError:
                    # Fallback to UTF-16 (common in PowerShell)
                    with open(path, 'r', encoding='utf-16') as f:
                        content = f.read().strip()
                
                if not content: continue
                manifest = json.loads(content)
                break
            except (json.JSONDecodeError, PermissionError, IOError):
                continue
                
        if not manifest:
            logger.error(f"❌ Failed to reach manifest at {path}")
            return

        app_id = manifest.get('app_id', 'unknown')
        resources = manifest.get('resources', {})
        entry_point = manifest.get('entry_point', {})

        self._update_registry(app_id, {
            "id": app_id,
            "name": manifest.get('name', 'Untitled App'),
            "type": manifest.get('type', 'native_engine_build'),
            "color": manifest.get('color', 'bg-cyan-600'),
            "icon": resources.get('icon', '💠'),
            "path": entry_point.get('binary', ''),
            "entry_point": entry_point,
            "resources": resources
        })

    def _update_registry(self, app_id, app_data):
        for _ in range(5):
            try:
                registry = {}
                if REGISTRY_PATH.exists():
                    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                
                registry[app_id] = app_data
                
                # Atomic write
                temp_path = REGISTRY_PATH.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(registry, f, indent=4)
                
                os.replace(temp_path, REGISTRY_PATH)
                logger.info(f"✔️ Registered: {app_data['name']} ({app_id})")
                return
            except Exception as e:
                time.sleep(0.5)
                continue
        logger.error(f"❌ Critical Registry Failure for {app_id}")

if __name__ == "__main__":
    if not WATCH_PATH.exists():
        WATCH_PATH.mkdir(parents=True, exist_ok=True)
        
    observer = Observer()
    handler = EngineBridge()
    observer.schedule(handler, str(WATCH_PATH), recursive=True)
    observer.start()
    logger.info(f"🚀 Bridge Active. Monitoring {WATCH_PATH}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
