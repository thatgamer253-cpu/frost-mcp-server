import os
import json
import time
from typing import List, Dict, Any, Optional

def search_builds(output_dir: str, query: str = "", platform: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scans the output directory for project builds and filters them by query/platform.
    """
    results = []
    if not os.path.exists(output_dir):
        return []

    for item in os.listdir(output_dir):
        proj_path = os.path.join(output_dir, item)
        if not os.path.isdir(proj_path):
            continue
        
        # Look for metadata
        metadata_file = os.path.join(proj_path, "metadata.json")
        tracker_file = os.path.join(proj_path, "tracker_report.json")
        
        entry = {
            "name": item,
            "path": proj_path,
            "timestamp": os.path.getmtime(proj_path),
            "status": "UNKNOWN",
            "cost": 0.0,
            "platform": "unknown",
            "files": 0,
            "has_binary": False
        }
        
        # Try to load tracker for cost/status
        if os.path.exists(tracker_file):
            try:
                with open(tracker_file, "r") as f:
                    data = json.load(f)
                    entry["cost"] = data.get("total_cost", 0.0)
                    entry["status"] = "COMPLETE" # If tracker exists, usually complete
            except: pass
            
        # Try to load metadata for more details
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    entry["status"] = data.get("status", entry["status"])
                    entry["platform"] = data.get("platform", entry["platform"])
                    entry["files"] = data.get("files_written", 0)
            except: pass

        # Check for binary
        dist_dir = os.path.join(proj_path, "dist")
        if os.path.exists(dist_dir):
            binaries = [f for f in os.listdir(dist_dir) if f.endswith(".exe") or f.endswith(".app") or (os.name != "nt" and "." not in f)]
            if binaries:
                entry["has_binary"] = True
                entry["binary_name"] = binaries[0]

        # Filter logic
        match = True
        if query and query.lower() not in item.lower():
            match = False
        
        entry_platform = str(entry.get("platform", "unknown"))
        if platform and platform.lower() != entry_platform.lower():
            match = False
            
        if match:
            results.append(entry)
            
    # Sort by newest first
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results
