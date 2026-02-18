#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  PIPELINE EVENTS — Thread-Safe Event Bus for Build Pipeline
  
  Bridges agent_brain.py ↔ Streamlit Dashboard.
  Events are written to build_events.jsonl for cross-process
  communication (dashboard polls this file).
  
  Zero breaking change to existing stdout-based Electron flow.
══════════════════════════════════════════════════════════════
"""

import json
import os
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime

try:
    from digital_ego import DigitalEgo
    _HAS_EGO = True
except ImportError:
    _HAS_EGO = False


# ── Pipeline Phases ──────────────────────────────────────────
PHASES = [
    "planning",
    "provisioning",
    "coding",
    "reviewing",
    "testing",
    "deploying",
    "success",
    "failed",
]

PHASE_LABELS = {
    "planning":     "🧠 Planning",
    "provisioning": "🏗️ Provisioning",
    "coding":       "⚙️ Coding",
    "reviewing":    "🔍 Reviewing",
    "testing":      "🐛 Testing",
    "deploying":    "🚀 Deploying",
    "success":      "✅ Success",
    "failed":       "❌ Failed",
}


# ── Event Types ──────────────────────────────────────────────
class EventType:
    """Constants for event types emitted during the build pipeline."""
    PHASE_CHANGE    = "phase_change"
    LOG             = "log"
    FILE_WRITE      = "file_write"
    FILE_REVIEW     = "file_review"
    ERROR           = "error"
    COST_UPDATE     = "cost_update"
    DOCKER_STATUS   = "docker_status"
    BUILD_START     = "build_start"
    BUILD_COMPLETE  = "build_complete"
    WISDOM_TRIGGER  = "wisdom_trigger"


# ── Pipeline Event ───────────────────────────────────────────
@dataclass
class PipelineEvent:
    """Single event emitted by the build pipeline."""
    event_type: str
    phase: str = ""
    status: str = ""          # "active", "done", "error", "waiting"
    tag: str = ""             # Log tag: ARCHITECT, ENGINEER, REVIEWER, etc.
    message: str = ""         # Human-readable message
    file: str = ""            # File path being written/reviewed
    code: str = ""            # Code content (for live viewer)
    language: str = ""        # Code language (python, javascript, etc.)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to compact JSON string."""
        d = asdict(self)
        # Don't write full code to the log line — can be enormous
        if len(d.get("code", "")) > 500:
            d["code_preview"] = d["code"][:500] + "..."
            d["code_length"] = len(d["code"])
        d["iso_time"] = datetime.fromtimestamp(d["timestamp"]).isoformat()
        return json.dumps(d, ensure_ascii=False)


# ── Event Bus ────────────────────────────────────────────────
class EventBus:
    """Thread-safe event bus that writes events to a JSONL file
    and notifies in-process subscribers.
    
    Usage in agent_brain.py:
        bus = EventBus("/path/to/project")
        bus.emit(PipelineEvent(event_type=EventType.LOG, tag="ARCH", message="Planning..."))
    
    Usage in dashboard:
        events = EventBus.read_events("/path/to/project/build_events.jsonl")
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.events_file = os.path.join(project_path, "build_events.jsonl")
        self._subscribers: List[Callable[[PipelineEvent], None]] = []
        self._lock = threading.Lock()
        self._history: List[PipelineEvent] = []
        self._current_phase = "planning"
        self._build_start_time = time.time()
        self.ego = DigitalEgo(project_path) if _HAS_EGO else None
        
        # Initialize the events file (truncate if exists from a previous build)
        os.makedirs(project_path, exist_ok=True)
        with open(self.events_file, "w", encoding="utf-8") as f:
            # Write header event
            header = PipelineEvent(
                event_type=EventType.BUILD_START,
                phase="planning",
                status="active",
                message="Build pipeline initialized",
                metadata={
                    "project_path": project_path,
                    "start_time": self._build_start_time,
                }
            )
            f.write(header.to_json() + "\n")
            self._history.append(header)

    def emit(self, event: PipelineEvent):
        """Emit an event: write to file + notify subscribers."""
        with self._lock:
            # Set timestamp if not already set
            if not event.timestamp:
                event.timestamp = time.time()
            
            self._history.append(event)
            
            # Track phase changes
            if event.event_type == EventType.PHASE_CHANGE and event.phase:
                self._current_phase = event.phase
            
            # Write to JSONL file (append mode)
            try:
                with open(self.events_file, "a", encoding="utf-8") as f:
                    f.write(event.to_json() + "\n")
            except Exception:
                pass  # Best-effort — don't crash the build
            
            # Update Digital Ego if active
            if self.ego:
                if event.event_type == EventType.ERROR:
                    self.ego.record_event(event.tag or "General", False)
                elif event.event_type == EventType.BUILD_COMPLETE:
                    success = event.metadata.get("success", False)
                    self.ego.record_event("Build", success)
            
            # Notify in-process subscribers
            for callback in self._subscribers:
                try:
                    callback(event)
                except Exception:
                    pass

    def subscribe(self, callback: Callable[[PipelineEvent], None]):
        """Register a callback for real-time event notifications."""
        with self._lock:
            self._subscribers.append(callback)

    def get_history(self) -> List[PipelineEvent]:
        """Return all events emitted so far."""
        with self._lock:
            return list(self._history)

    @property
    def current_phase(self) -> str:
        return self._current_phase

    @property
    def elapsed(self) -> float:
        return time.time() - self._build_start_time

    # ── Helper Emitters ──────────────────────────────────────
    def log(self, tag: str, message: str, phase: str = ""):
        """Convenience: emit a LOG event."""
        self.emit(PipelineEvent(
            event_type=EventType.LOG,
            tag=tag,
            message=message,
            phase=phase or self._current_phase,
        ))

    def phase(self, phase_name: str, status: str = "active"):
        """Convenience: emit a PHASE_CHANGE event."""
        self.emit(PipelineEvent(
            event_type=EventType.PHASE_CHANGE,
            phase=phase_name,
            status=status,
            message=f"Phase: {PHASE_LABELS.get(phase_name, phase_name)}",
        ))

    def file_write(self, filepath: str, code: str, language: str = ""):
        """Convenience: emit a FILE_WRITE event with code content."""
        if not language:
            language = _detect_language(filepath)
        self.emit(PipelineEvent(
            event_type=EventType.FILE_WRITE,
            file=filepath,
            code=code,
            language=language,
            phase=self._current_phase,
            message=f"Writing: {filepath}",
        ))

    def cost_update(self, total_cost: float, budget: float, model: str = ""):
        """Convenience: emit a COST_UPDATE event."""
        self.emit(PipelineEvent(
            event_type=EventType.COST_UPDATE,
            phase=self._current_phase,
            message=f"Cost: ${total_cost:.4f} / ${budget:.2f}",
            metadata={"total_cost": total_cost, "budget": budget, "model": model},
        ))

    def docker_status(self, status: str, container_id: str = "", message: str = ""):
        """Convenience: emit a DOCKER_STATUS event."""
        self.emit(PipelineEvent(
            event_type=EventType.DOCKER_STATUS,
            status=status,
            message=message or f"Docker: {status}",
            metadata={"container_id": container_id},
        ))

    def build_complete(self, success: bool, summary: str = ""):
        """Convenience: emit BUILD_COMPLETE event."""
        self.emit(PipelineEvent(
            event_type=EventType.BUILD_COMPLETE,
            phase="success" if success else "failed",
            status="done" if success else "error",
            message=summary or ("Build succeeded" if success else "Build failed"),
            metadata={"elapsed": self.elapsed, "success": success},
        ))

    # ── Static Reader (for Dashboard) ────────────────────────
    @staticmethod
    def read_events(events_file: str, after_line: int = 0) -> List[dict]:
        """Read events from a JSONL file, optionally starting after a given line.
        Used by the dashboard to poll for new events."""
        events = []
        if not os.path.exists(events_file):
            return events
        try:
            with open(events_file, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i < after_line:
                        continue
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass
        return events


# ── Chronicle (Historical Anchoring) ──────────────────────────
class Chronicle:
    """Persistent project history that summarizes builds from Seed to Final."""
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.chronicle_file = os.path.join(project_path, "project_chronicle.json")
        self.history = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.chronicle_file):
            try:
                with open(self.chronicle_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def anchor_build(self, success: bool, summary: str, elapsed: float):
        """Record a build milestone in the chronicle."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "milestone": "build_cycle",
            "success": success,
            "summary": summary,
            "elapsed": round(elapsed, 2),
            "evolution_step": len(self.history) + 1
        }
        self.history.append(entry)
        self._save()

    def add_note(self, note: str, milestone: str = "manual_intervention"):
        """Add a manual note or intervention record."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "milestone": milestone,
            "note": note,
            "evolution_step": len(self.history) + 1
        }
        self.history.append(entry)
        self._save()

    def _save(self):
        try:
            with open(self.chronicle_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4)
        except Exception:
            pass

    def get_summary(self) -> str:
        """Get a concise summary of the project evolution."""
        if not self.history:
            return "Project is at the Seed stage (no history yet)."
        
        last = self.history[-1]
        return f"Project evolved through {len(self.history)} steps. Last milestone: {last.get('milestone')} ({last.get('timestamp')})"


# ── Future Projector ─────────────────────────────────────────
class FutureProjector:
    """Predicts future state like storage exhaustion or strategy pivots."""
    def __init__(self, project_path: str):
        self.project_path = project_path

    def predict_storage_exhaustion(self, days=7) -> Optional[str]:
        """Simple heuristic: if storage is growing, predict exhaustion."""
        # Mock logic for demo
        import shutil
        total, used, free = shutil.disk_usage(self.project_path)
        percent_free = (free / total) * 100
        
        if percent_free < 10:
            return f"CRITICAL: Storage is at {100-percent_free:.1f}%. Predicted exhaustion in less than 2 days."
        elif percent_free < 25:
            return f"WARNING: Storage is dropping. Predicted exhaustion in approx {days} days if generation continues."
        return None

    def analyze_market_pivot(self, current_strategy: str) -> Optional[str]:
        """Suggests strategy pivots based on market trends (mocked)."""
        if "Bitcoin" in current_strategy:
            return "Note: Bitcoin volatility is dropping. Consider pivoting to 'Solana Ecosystem' tomorrow for higher engagement."
        return None


# ── Language Detection ───────────────────────────────────────
def _detect_language(filepath: str) -> str:
    """Detect code language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sql": "sql",
        ".sh": "bash",
        ".ps1": "powershell",
        ".bat": "batch",
        ".dockerfile": "dockerfile",
        ".toml": "toml",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
    }
    _, ext = os.path.splitext(filepath.lower())
    # Special case: Dockerfile has no extension
    if os.path.basename(filepath).lower() in ("dockerfile", "docker-compose.yml"):
        return "dockerfile" if "dockerfile" in filepath.lower() else "yaml"
    return ext_map.get(ext, "text")


# ── Demo / Self-Test ─────────────────────────────────────────
if __name__ == "__main__":
    import tempfile
    demo_dir = tempfile.mkdtemp(prefix="antigravity_demo_")
    print(f"Demo events at: {demo_dir}/build_events.jsonl")
    
    bus = EventBus(demo_dir)
    bus.phase("planning")
    bus.log("ARCHITECT", "Designing system architecture...")
    bus.phase("coding")
    bus.file_write("main.py", "print('Hello, Antigravity!')", "python")
    bus.log("ENGINEER", "Writing main.py...")
    bus.cost_update(0.0042, 5.0, "gpt-4o")
    bus.phase("testing")
    bus.docker_status("running", "abc123", "Container provisioned")
    bus.log("DEBUGGER", "All tests passed ✓")
    bus.phase("success")
    bus.build_complete(True, "Built 5 files in 42s")
    
    # Read back
    events = EventBus.read_events(os.path.join(demo_dir, "build_events.jsonl"))
    print(f"\n{len(events)} events written:")
    for e in events:
        tag = e.get('tag', '') or e.get('event_type', '')
        msg = e.get('message', '')
        try:
            print(f"  [{tag}] {msg}")
        except UnicodeEncodeError:
            print(f"  [{tag}] {msg.encode('ascii', 'replace').decode('ascii')}")
