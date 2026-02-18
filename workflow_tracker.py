#!/usr/bin/env python3
import os
import time
import json
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WorkflowTracker")

class WorkflowHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

class WorkflowTracker:
    def __init__(self, watch_path, chronicle_callback=None):
        self.watch_path = watch_path
        self.chronicle_callback = chronicle_callback
        self.last_intervention = {} # {path: timestamp}
        self.observer = Observer()

    def start(self):
        handler = WorkflowHandler(self._handle_change)
        self.observer.schedule(handler, self.watch_path, recursive=True)
        self.observer.start()
        logger.info(f"Workflow Tracker active: Watching {self.watch_path}")

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def _handle_change(self, path):
        # Ignore logs, hidden files, and common noise directories
        ignore_patterns = [
            ".log", ".git", ".gemini", "__pycache__", 
            "node_modules", "venv", ".next", "build", "dist",
            ".jsonl", ".bak"
        ]
        if any(x in path for x in ignore_patterns):
            return


        now = time.time()
        # Debounce: user might save multiple times
        if path in self.last_intervention and now - self.last_intervention[path] < 10:
            return

        self.last_intervention[path] = now
        logger.info(f"⚡ User Intervention Detected: {os.path.basename(path)}")
        
        if self.chronicle_callback:
            self.chronicle_callback(f"User manually modified {os.path.basename(path)}", "user_refinement")

if __name__ == "__main__":
    # Test block
    def mock_callback(note, type):
        print(f"Chronicle Entry: {note} [{type}]")
    
    tracker = WorkflowTracker(os.getcwd(), mock_callback)
    tracker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tracker.stop()
