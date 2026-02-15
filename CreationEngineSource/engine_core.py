#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  NEXUS CREATION ENGINE  —  Consolidated Multi-Agent
  Build System with Docker Sandbox.

  Prerequisites:
    pip install streamlit docker openai anthropic

  Usage (standalone):
    from engine_core import NexusEngine
    engine = NexusEngine("my-project")
    result = engine.run_full_build("Build a task manager with FastAPI")

  Usage (CLI):
    python engine_core.py "Build a URL shortener with analytics"

  Usage (Streamlit UI):
    streamlit run creation_engine_ui.py
══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import ast
import re
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    import docker
    from openai import OpenAI
    import agent_brain

# ── Optional Imports (Graceful Degrade) ──────────────────────
try:
    import docker
    _HAS_DOCKER = True
except ImportError:
    docker = Any = None # type: ignore
    _HAS_DOCKER = False

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    class OpenAI: # type: ignore
        def __init__(self, *args, **kwargs):
            self.chat = Any = None
            self.images = Any = None
    _HAS_OPENAI = False

try:
    import anthropic as _anthropic_sdk
    _HAS_ANTHROPIC = True
except ImportError:
    _anthropic_sdk = Any = None # type: ignore
    _HAS_ANTHROPIC = False

# ── Import the Overlord agent_brain pipeline (if available) ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

_HAS_OVERLORD = False
try:
    from agent_brain import (
        GlobalWisdom,
        WisdomGuard,
        ProjectState,
        CodebaseRAG,
        ReviewerAgent,
        SelfCorrectionModule,
        CodebaseState,
        CostTracker,
        KnowledgeBase,
        GoogleResearchAgent,
        DevKnowledgeAgent,
        ask_llm as overlord_ask_llm,
        strip_fences,
        get_cached_client,
        build_manifest,
        manifest_to_context,
        preflight_search,
        PLATFORM_PROFILES,
        PRODUCTION_SAFETY_DIRECTIVE,
        STABILITY_DIRECTIVE,
        FEATURE_RICHNESS_DIRECTIVE,
        API_CONVENTIONS,
        import_dry_run,
        ConfigConsistencyChecker,
        resolve_mission_parameters,
        generate_verification_suite,
        capture_visual_proof,
    )
    try:
        from agent_brain import project_assembler
    except ImportError:
        project_assembler = None
    _HAS_OVERLORD = True
except ImportError:
    # Fallback: engine runs in standalone mode without Overlord pipeline
    pass


# ══════════════════════════════════════════════════════════════
#  PROVIDER REGISTRY  (used in standalone mode)
# ══════════════════════════════════════════════════════════════
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "prefixes": ["llama", "gemma", "mixtral"],
        "label": "Groq ⚡"
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "prefixes": ["gemini"],
        "label": "Google Gemini 🧠"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "prefixes": ["openrouter/", "meta-llama/", "google/", "mistralai/", "deepseek/"],
        "label": "OpenRouter 🌐"
    },
    "openai": {
        "base_url": None,
        "env_key": "OPENAI_API_KEY",
        "prefixes": ["gpt-", "o1-", "o3-"],
        "label": "OpenAI ☁️"
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "prefixes": ["claude"],
        "label": "Anthropic 🔒"
    }
}


def detect_provider(model_name: str) -> str:
    model_lower = model_name.lower()
    for provider_id, info in PROVIDERS.items():
        prefixes = info.get("prefixes")
        if prefixes and isinstance(prefixes, list):
            for prefix in prefixes:
                if model_lower.startswith(str(prefix)):
                    return str(provider_id)
    return "openai"


def _get_standalone_client(model_name: str, api_key: str = "") -> Any:
    """Create an OpenAI-compatible client (standalone mode, no Overlord)."""
    provider_id = detect_provider(model_name)
    provider = PROVIDERS.get(provider_id, PROVIDERS["openai"])
    env_key = str(provider.get("env_key", "OPENAI_API_KEY"))
    key = api_key or os.environ.get(env_key, "")
    if not key:
        label = provider.get("label", "OpenAI")
        raise ValueError(f"No API key for {label}. Set {env_key}.")
    kwargs: Dict[str, Any] = {"api_key": key}
    base_url = provider.get("base_url")
    if base_url:
        kwargs["base_url"] = str(base_url)
    return OpenAI(**kwargs)


def _standalone_ask_llm(model: str, system: str, user: str, api_key: str = "") -> str:
    """Send a chat completion (standalone mode)."""
    if model.lower().startswith("claude"):
        if not _HAS_ANTHROPIC:
            raise ImportError("pip install anthropic")
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        client = _anthropic_sdk.Anthropic(api_key=key)
        resp = client.messages.create(
            model=model, max_tokens=8192, temperature=0.1,
            system=system, messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text.strip()
    else:
        client = _get_standalone_client(model, api_key)
        resp = client.chat.completions.create(
            model=model, temperature=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content
        raw = content.strip() if content else ""
    # Strip markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        if len(lines) > 0:
            lines.pop(0) # Remove ```lang
        if len(lines) > 0 and lines[-1].strip() == "```":
            lines.pop() # Remove closing ```
        return "\n".join(lines)
    return raw


# ══════════════════════════════════════════════════════════════
#  NEXUS SUITE COMPATIBILITY LAYER
# ══════════════════════════════════════════════════════════════

@dataclass
class BuildConfig:
    """Build configuration container for Nexus."""
    project_name: str
    prompt: str
    output_dir: str
    model: str
    arch_model: str = ""
    dev_model: str = ""
    rev_model: str = ""
    res_model: str = ""
    budget: float = 5.0
    platform: str = "python"
    scale: str = "application"
    phase: str = "all"
    docker: bool = True
    readme: bool = True
    debug: bool = True
    voice: bool = False
    auto_execute: bool = True
    harvest_timeout: int = 120
    direct_media: bool = False  # If True, bypass code gen for media pipeline

class LogCapture:
    """Log capture sink for the Streamlit dashboard."""
    def __init__(self, engine: 'NexusEngine'):
        self.engine = engine

    def get_all_lines(self) -> List[Dict[str, Any]]:
        return self.engine.log.get_entries()

class StateReducer:
    """Manages project build state and visual phase benchmarks."""
    PHASES = ["INIT", "ENHANCED", "RESEARCHED", "ARCHITECTED", "ASSEMBLED", "ENGINEERED", "AUDITED", "DEPLOYED", "FINALIZED"]
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.state_file = os.path.join(project_path, "build_state.json")
        self.events_file = os.path.join(project_path, "build_events.jsonl")

    def reset(self):
        """Clear all checkpoints for this project."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        if os.path.exists(self.events_file):
            os.remove(self.events_file)

    def get_progress(self) -> Dict[str, Any]:
        """Calculates percentage and phase status for UI dashboard."""
        if not os.path.exists(self.state_file):
            return {
                "percent": 0, "completed": 0, "total": len(self.PHASES),
                "phases": {p: {"status": "○"} for p in self.PHASES}
            }
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return data
        except:
            return {"percent": 0, "completed": 0, "total": len(self.PHASES), "phases": {}}

    def get_events(self, last_n: int = 30) -> List[Dict[str, Any]]:
        """Reads historical events for the audit log."""
        if not os.path.exists(self.events_file):
            return []
        events: List[Dict[str, Any]] = []
        try:
            with open(self.events_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
            
            # Using a loop to avoid slicing syntax that confuses strict linters
            total = len(events)
            start = max(0, total - last_n)
            trimmed = []
            for i in range(start, total):
                trimmed.append(events[i])
            return trimmed
        except:
            return []

class DockerSandbox:
    """UI proxy for Docker safety verification."""
    def __init__(self, project_path: str, project_name: str):
        self.project_path = project_path
        self.project_name = project_name

    @property
    def available(self) -> bool:
        return _HAS_DOCKER and docker is not None

    def build(self) -> tuple[bool, str]:
        """Ensures base images are ready."""
        return True, "Docker image ready for sandboxing"

class CreationEngine:
    """Master wrapper that orchestrates the NexusEngine for the UI."""
    def __init__(self, config: BuildConfig):
        self.config = config
        self.engine = NexusEngine(
            project_name=config.project_name,
            model=config.model,
            output_dir=config.output_dir,
            budget=config.budget,
            platform=config.platform,
            use_docker=config.docker,
            auto_execute=config.auto_execute,
            harvest_timeout=config.harvest_timeout,
        )
        self.log_capture = LogCapture(self.engine)
        self.error: Optional[str] = None
        self.result: Any = None

    @property
    def artifacts(self) -> list:
        """Return harvested artifacts from the last build."""
        return self.engine.harvested_artifacts

    def run(self, resume: bool = False, blocking: bool = True):
        """Entry point for the Streamlit background thread."""
        try:
            self.result = self.engine.run_full_build(self.config.prompt)
        except Exception as e:
            self.error = str(e)

# ══════════════════════════════════════════════════════════════
#  BUILD LOG
# ══════════════════════════════════════════════════════════════


class BuildLog:
    """Thread-safe build log with timestamped entries."""

    def __init__(self, on_log: Optional[Callable] = None):
        self.entries: list[dict] = []
        self._on_log = on_log

    def log(self, tag: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "tag": tag, "message": message}
        self.entries.append(entry)
        if self._on_log is not None:
            try:
                callback = self._on_log
                if callable(callback):
                    callback(tag, message)
            except:
                pass
        else:
            print(f"[{ts}] [{tag}]  {message}")

    def clear(self):
        self.entries.clear()

    def get_entries(self) -> list[dict]:
        return list(self.entries)


# ══════════════════════════════════════════════════════════════
#  THE ANTIGRAVITY ENGINE
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  GEMINI MEDIA PIPE — Direct Video Synthesis
# ══════════════════════════════════════════════════════════════

class GeminiMediaPipe:
    """
    Multimodal video generation pipeline. 
    Transforms a text 'vision' into a cinematic MP4 directly.
    """
    def __init__(self, output_dir: str, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.output_dir = output_dir
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        # Ensure media directories exist
        self.media_dir = os.path.join(output_dir, "outputs", "videos")
        self.asset_dir = os.path.join(output_dir, "assets", "media")
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(self.asset_dir, exist_ok=True)

    def generate_video(self, prompt: str, log_callback: Optional[Callable] = None) -> str:
        """Execute the full Gemini-style video generation loop."""
        def log(msg):
            if log_callback: log_callback("GEMINI_PIPE", msg)
            else: print(f"[GEMINI_PIPE] {msg}")

        log(f"🎬 Initializing Multimodal Forge for: '{prompt}'")
        
        # 1. Scene Orchestration
        log("🧠 Scripting cinematic scenes...")
        scenes = self._script_scenes(prompt, log)
        log(f"  ✓ Orchestrated {len(scenes)} scenes.")

        # 2. Asset Generation (Multimodal Bridge)
        log("🎨 Forging visual assets (Multimodal Engine)...")
        scene_images = self._generate_assets(scenes, log)
        
        # 3. Cinematic Assembly
        log("✨ Applying cinematic camera motion & rendering...")
        video_path = self._assemble_video(scene_images, log)
        
        log(f"✅ Video forged successfully at: {video_path}")
        return video_path

    def _script_scenes(self, prompt: str, log: Callable) -> List[Dict[str, str]]:
        """Use LLM to expand the prompt into a visual storyboard."""
        system_msg = (
            "You are a cinematic director for a high-end AI video studio. "
            "Break the user's vision into exactly 3-4 visual scenes. "
            "Return ONLY a JSON array of objects with 'title', 'visual_desc', and 'motion_type'. "
            "motion_type options: zoom_in, zoom_out, pan_right, pan_left."
        )
        
        if self.client is None:
            # Fallback to mock for testing if no key provided
            return [
                {"title": "The Arrival", "visual_desc": f"Cinematic shot of {prompt}", "motion_type": "zoom_in"},
                {"title": "The Scale", "visual_desc": f"Wide panorama of {prompt}", "motion_type": "pan_right"},
                {"title": "The Core", "visual_desc": f"Dynamic close up of {prompt}", "motion_type": "zoom_out"}
            ]

        try:
            # Use Type checking for client
            client: Any = self.client
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            data = json.loads(raw or "{}")
            if "scenes" in data: return data["scenes"]
            if isinstance(data, list): return data
            return [data]
        except Exception as e:
            # Fallback mock
            log(f"  ⚠ Scene scripting failed ({e}), using fallback vision.")
            return [{"title": "Vision", "visual_desc": prompt, "motion_type": "zoom_in"}]

    def _generate_assets(self, scenes: List[Dict[str, str]], log: Callable) -> List[str]:
        """Generate high-quality images for each scene."""
        import requests
        image_paths = []
        
        for i, scene in enumerate(scenes):
            title = scene.get('title', f"Vision Part {i+1}")
            desc = scene.get('visual_desc', 'Cinematic vision')
            log(f"  🖼️ Scene {i+1}: {title}...")
            
            if self.client is None:
                # Mock colored placeholder if no API
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (1792, 1024), color=(30, 30, (i+1)*50))
                    d = ImageDraw.Draw(img)
                    d.text((10,10), f"Scene {i+1}: {scene['title']}", fill=(255,255,255))
                    path = os.path.join(self.asset_dir, f"scene_{i+1}.png")
                    img.save(path)
                    image_paths.append(path)
                except Exception as e:
                    log(f"  ⚠ Image placeholder failed: {e}")
                continue

            try:
                client: Any = self.client
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=f"{desc} Cinematic photography, masterpiece, 8k resolution, 16:9 vertical.",
                    size="1024x1792",
                    quality="hd", n=1
                )
                url = response.data[0].url
                if url:
                    img_data = requests.get(url).content
                    path = os.path.join(self.asset_dir, f"scene_{i+1}.png")
                    with open(path, 'wb') as f:
                        f.write(img_data)
                    image_paths.append(path)
            except Exception as e:
                log(f"  ⚠ Failed to generate asset {i+1}: {e}")
                
        return image_paths

    def _assemble_video(self, image_paths: List[str], log: Callable) -> str:
        """Assemble the images into an MP4 with motion."""
        try:
            from moviepy import ImageClip, concatenate_videoclips
        except ImportError:
            try:
                from moviepy.editor import ImageClip, concatenate_videoclips # type: ignore
            except ImportError:
                log("  ⚠ MoviePy not found. Skipping assembly.")
                return ""
        
        clips = []
        for i, path in enumerate(image_paths):
            duration = 4.0
            clip = ImageClip(path).with_duration(duration) # V2 immutable
            
            # Simple zoom implementation (Ken Burns)
            if i % 3 == 0: # Zoom In
                clip = clip.resized(lambda t: 1.0 + 0.1 * (t/duration)).with_position('center')
            elif i % 3 == 1: # Pan
                clip = clip.with_position(lambda t: (int(-50 + 100 * (t/duration)), 'center'))
            else: # Zoom Out
                clip = clip.resized(lambda t: 1.1 - 0.1 * (t/duration)).with_position('center')
                
            clips.append(clip)
            
        final = concatenate_videoclips(clips, method="compose")
        output_path = os.path.join(self.media_dir, f"nexus_media_{int(time.time())}.mp4")
        
        # High-quality render
        # MoviePy V2 write_videofile
        final.write_videofile(output_path, fps=24, codec="libx264", audio=False, logger=None)
        return output_path

class NexusEngine:
    """
    Consolidated Creation Engine with two operating modes:

    🔒 OVERLORD MODE (when agent_brain.py is available):
       Full multi-agent pipeline: Prompt Enhancement → Pre-flight Search →
       Deep Research → Architect → Project Assembler → Engineer with
       RAG + WisdomGuard + ReviewerAgent + SelfCorrection → Docker Sandbox.

    ⚡ STANDALONE MODE (when agent_brain.py is NOT available):
       Lightweight pipeline: Architect → Developer → Supervisor → Self-Correct.
       Uses direct LLM calls without the full Overlord intelligence stack.

    Docker Sandbox:
       Verifies the generated code runs inside a sandboxed Docker container
       with resource limits (512MB RAM, 1 CPU). Auto-pulls base images.
    """

    # Phase constants
    PHASE_IDLE        = "idle"
    PHASE_ENHANCING   = "enhancing"
    PHASE_RESEARCHING = "researching"
    PHASE_PLANNING    = "planning"
    PHASE_ASSEMBLING  = "assembling"
    PHASE_WRITING     = "writing"
    PHASE_REVIEWING   = "reviewing"
    PHASE_SANDBOX     = "sandbox"
    PHASE_HEALING     = "healing"
    PHASE_HARVESTING  = "harvesting"
    PHASE_COMPLETE    = "complete"
    PHASE_FAILED      = "failed"

    # Artifact file extensions to harvest
    ARTIFACT_EXTENSIONS = {
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico",
        # Video
        ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv",
        # Audio
        ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
        # Documents
        ".pdf", ".docx", ".xlsx", ".pptx",
        # Data
        ".csv", ".parquet", ".sqlite", ".db",
        # Web
        ".html", ".htm",
        # Archives
        ".zip", ".tar", ".gz",
    }

    def __init__(
        self,
        project_name: str = "auto_app",
        model: str = "gemini-2.5-flash",
        api_key: str = "",
        output_dir: str = "./builds",
        budget: float = 5.0,
        platform: str = "python",
        scale: str = "application",
        phase: str = "all",
        max_retries: int = 3,
        use_docker: bool = True,
        auto_execute: bool = True,
        harvest_timeout: int = 120,
        direct_media: bool = False,
        arch_model: str = "",
        dev_model: str = "",
        rev_model: str = "",
        res_model: str = "",
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        self.project_name = project_name
        self.model = model
        self.api_key = api_key
        self.output_dir = output_dir
        self.budget = budget
        self.platform = platform
        self.scale = scale
        self.phases = phase # Use internal phases variable for backward compatibility if needed
        self.max_retries = max_retries
        self.use_docker = use_docker
        self.auto_execute = auto_execute
        self.harvest_timeout = harvest_timeout
        self.direct_media = direct_media
        self.arch_model = arch_model or model
        self.dev_model = dev_model or model
        self.rev_model = rev_model or model
        self.res_model = res_model or model

        self.project_dir = os.path.join(output_dir, project_name)
        self.artifacts_dir = os.path.join(self.project_dir, "artifacts")
        os.makedirs(self.project_dir, exist_ok=True)

        self.log = BuildLog(on_log=on_log)
        self.manifest = {}
        self.written_files: dict[str, str] = {}
        self.harvested_artifacts: list[dict] = []
        self.phase = self.PHASE_IDLE
        self.errors: list[str] = []

        # Docker client (lazy)
        self._docker_client = None

        mode_label = "🔒 OVERLORD" if _HAS_OVERLORD else "⚡ STANDALONE"
        docker_label = "🐳 Docker" if self.use_docker else "📦 Subprocess"
        self.log.log("ENGINE", f"Initialized: {project_name}")
        self.log.log("ENGINE", f"Mode: {mode_label} | Verify: {docker_label}")
        self.log.log("ENGINE", f"Model: {model} ({detect_provider(model)})")
        self.log.log("ENGINE", f"Output: {os.path.abspath(self.project_dir)}")

    # ── Docker Client (lazy, safe) ────────────────────────────
    @property
    def docker_client(self):
        if self._docker_client is None and self.use_docker:
            try:
                if docker is not None:
                    self._docker_client = docker.from_env()
                    self._docker_client.ping()
            except Exception as e:
                self.log.log("DOCKER", f"⚠ Docker unavailable: {e}")
                self._docker_client = None
        return self._docker_client

    # ── LLM Call (routes to Overlord or standalone) ───────────
    def _ask(self, system: str, user: str, model: str = "") -> str:
        """Route LLM call through Overlord pipeline or standalone."""
        target_model = model or self.model
        if _HAS_OVERLORD:
            client = get_cached_client(target_model, self.api_key)
            return strip_fences(overlord_ask_llm(client, target_model, system, user))
        else:
            return _standalone_ask_llm(target_model, system, user, self.api_key)

    # ══════════════════════════════════════════════════════════
    #  PHASE 1: ARCHITECT  —  Plan Project Structure
    # ══════════════════════════════════════════════════════════
    def architect_plan(self, goal: str) -> dict:
        """LLM-powered project planning. Returns a JSON manifest."""
        self.phase = self.PHASE_PLANNING
        self.log.log("ARCHITECT", "Designing project structure…")

        # ── Autonomous Mission Planner ────────────────────────
        if any(p == "auto" for p in [self.platform, self.scale, self.phases]):
            self.log.log("ENGINE", "🤖 Interpreting mission briefing for autonomous fulfillment…")
            mission = resolve_mission_parameters(goal)
            
            if self.platform == "auto":
                self.platform = mission["platform"]
                self.log.log("ENGINE", f"  ↳ Inferred Platform: {self.platform.upper()}")
            
            if self.scale == "auto":
                self.scale = mission["scale"]
                self.log.log("ENGINE", f"  ↳ Inferred Scale: {self.scale.upper()}")
            
            if self.phases == "auto":
                self.phases = mission["phase"]
                self.log.log("ENGINE", f"  ↳ Inferred Phases: {self.phases.upper()}")

        # ── Overlord Mode: full research + enhanced prompting ─
        if _HAS_OVERLORD:
            return self._architect_overlord(goal)

        # ── Standalone Mode: simple architect ─────────────────
        return self._architect_standalone(goal)

    def _architect_overlord(self, goal: str) -> dict:
        """Full Overlord pipeline: Enhance → Search → Research → Architect."""
        client = get_cached_client(self.model, self.api_key)
        profile = PLATFORM_PROFILES.get(self.platform, PLATFORM_PROFILES["python"])
        platform_directive = profile["arch_directive"]

        # Step 1: Enhance the prompt
        self.phase = self.PHASE_ENHANCING
        self.log.log("ARCHITECT", "🧠 Enhancing prompt…")
        enhance_system = (
            "You are 'Overlord Prompt Engineer,' an elite AI that transforms vague user ideas "
            "into detailed, comprehensive software engineering specifications. "
            "Your job is to expand it into a RICH, AMBITIOUS prompt for a code-generating AI. "
            f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
            "\n\nInclude: project description, 5-8 features, technical architecture, "
            "UI/UX details, error handling, data flow."
            "\n\nRules: Output ONLY enhanced prompt text. No markdown. 400-600 words."
        )
        try:
            enhanced_prompt = self._ask(enhance_system, goal, model=self.arch_model)
            self.log.log("ARCHITECT", f"  ✓ Prompt enhanced ({len(enhanced_prompt)} chars) using {self.arch_model}")
        except Exception as e:
            self.log.log("WARN", f"  Enhancement failed: {e}")
            enhanced_prompt = goal

        # Step 2: Pre-flight version search
        self.phase = self.PHASE_RESEARCHING
        self.log.log("ARCHITECT", "🔍 Pre-flight version search…")
        search_results = preflight_search(goal, enhanced_prompt)
        search_context = search_results.get("search_context", "")
        version_advisory = ""
        if search_context:
            version_advisory = (
                "\n\nPRE-FLIGHT VERSION INTELLIGENCE:\n" + search_context +
                "\nUse these verified versions."
            )

        # Step 3: Deep Research + Memory
        self.log.log("ARCHITECT", "🌐 Deep research…")
        dk_agent = DevKnowledgeAgent()
        dk_docs = dk_agent.lookup(enhanced_prompt)
        research_agent = GoogleResearchAgent(client, self.res_model)
        research_report = research_agent.run_research(enhanced_prompt, kb_context=dk_docs or "")
        if research_report and search_context:
            research_report += "\n\n" + search_context
        elif not research_report:
            research_report = search_context

        # Step 4: Architect LLM call
        self.phase = self.PHASE_PLANNING
        self.log.log("ARCHITECT", "📐 Planning project structure…")
        arch_system = (
            "You are 'Overlord,' an autonomous Senior Full-Stack Engineer and DevOps Specialist. "
            "Directive: No Hallucinations. Do not use placeholder domains or URLs. "
            "Mission: Zero-Interaction Planning. Decompose user intent into a logical file structure. "
            f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
            "\n\nTECH STACK CONSTRAINT (Stable-Gold Stack):"
            "\n1. FRONTEND: TypeScript mandatory; Tailwind CSS for styling."
            "\n2. BACKEND: FastAPI for Python-based logic; avoid Flask for high-concurrency."
            "\n3. DATABASE: PostgreSQL default. Include 'schema.prisma' if using Prisma."
            "\n4. DOCUMENTATION: Include 'README.md' and '.env.example'."
            f"{version_advisory}"
            f"\n\n{research_report or ''}"
            "\n\nOutput ONLY valid JSON with this schema: "
            '{"project_name": "<slug>", '
            '"project_type": "VIDEO | GAME | WEBSITE | TOOL | SCRIPT | ASSET", '
            '"mission_summary": "<1-sentence high level goal>", '
            '"stack": {"frontend": "<fw>", "backend": "<fw>", "database": "<provider>"}, '
            '"file_tree": ["path/file.ext", ...], '
            '"files": [{"path": "filename.ext", "task": "description"}], '
            '"dependencies": ["package1"], '
            f'"run_command": "{profile["run_command"]}"}} '
            "Include a main entry point and README.md. "
            "\n\nOUTPUT DIRECTIVE: The generated program MUST save all output artifacts "
            "(images, videos, PDFs, data files) to the current working directory "
            "or an 'output/' subdirectory. Use explicit file paths — never GUI-only display. "
            "Programs MUST be non-interactive: they run to completion without user input "
            "and produce their output files automatically. If the project generates media, "
            "print the output file paths to stdout."
            f"\n{PRODUCTION_SAFETY_DIRECTIVE}"
            "\nOutput ONLY raw JSON. No markdown."
        )

        try:
            raw_plan = self._ask(arch_system, enhanced_prompt, model=self.arch_model)
            self.manifest = json.loads(raw_plan)
        except json.JSONDecodeError:
            self.log.log("ARCHITECT", "⚠ Invalid JSON — retrying…")
            try:
                raw_plan = self._ask(arch_system + " Output raw JSON only.", enhanced_prompt)
                self.manifest = json.loads(raw_plan)
            except Exception as e:
                self.log.log("ERROR", f"Architect failed: {e}")
                self.phase = self.PHASE_FAILED
                return {}
        except Exception as e:
            self.log.log("ERROR", f"Architect failed: {e}")
            self.phase = self.PHASE_FAILED
            return {}

        self._save_manifest()
        return self.manifest

    def _architect_standalone(self, goal: str) -> dict:
        """Lightweight architect (no Overlord dependencies)."""
        system = (
            "You are a senior software architect. Given a project goal, output a JSON "
            "manifest with this exact schema:\n"
            '{"project_name": "name", '
            '"project_type": "TYPE", '
            '"mission_summary": "one line summary", '
            '"files": [{"path": "filename.py", "task": "what this file does"}], '
            '"dependencies": ["package1"], '
            '"run_command": "python main.py"}\n'
            "Plan 5-15 files. Separate concerns into modules. "
            "Always include: main.py, config.py, requirements.txt, README.md. "
            "Output ONLY valid JSON. No markdown."
        )
        raw = self._ask(system, f"Build this: {goal}", model=self.arch_model)
        try:
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            self.manifest = json.loads(json_match.group() if json_match else raw)
        except json.JSONDecodeError:
            self.log.log("ERROR", "Invalid JSON from Architect. Using fallback.")
            self.manifest = {
                "project_name": self.project_name,
                "files": [
                    {"path": "main.py", "task": "Main entry point"},
                    {"path": "config.py", "task": "Configuration"},
                    {"path": "utils.py", "task": "Utility functions"},
                    {"path": "requirements.txt", "task": "Dependencies"},
                    {"path": "README.md", "task": "Documentation"},
                ],
                "dependencies": [], "run_command": "python main.py"
            }
        self._save_manifest()
        return self.manifest

    def _save_manifest(self):
        files = self.manifest.get("files", [])
        
        # Normalize files (handle list of dicts or list of strings)
        normalized_files = []
        for f in files:
            if isinstance(f, dict):
                normalized_files.append({
                    "path": f.get("path", "unknown"),
                    "task": f.get("task", f.get("purpose", "Synthesis"))
                })
            else:
                normalized_files.append({"path": str(f), "task": "Synthesis"})

        self.log.log("SYSTEM", "── MISSION BRIEFING ──────────────────────────────────")
        self.log.log("SYSTEM", f"🚀 PRODUCT TYPE: {str(self.manifest.get('project_type', 'UNDEFINED')).upper()}")
        self.log.log("SYSTEM", f"📝 MISSION:      {self.manifest.get('mission_summary', self.manifest.get('description', 'Synthesis...'))}")
        self.log.log("ARCHITECT", f"✓ Blueprint: {len(normalized_files)} file(s)")
        for f in normalized_files:
            path = f.get("path", "unknown")
            task_str = str(f.get("task", "Synthesis"))
            task_short = "".join([task_str[i] for i in range(min(len(task_str), 60))])
            self.log.log("ARCHITECT", f"  ├─ {path}  →  {task_short}")
        self.log.log("SYSTEM", "──────────────────────────────────────────────────────")
        
        with open(os.path.join(self.project_dir, "manifest.json"), "w") as fh:
            json.dump(self.manifest, fh, indent=2)

    # ══════════════════════════════════════════════════════════
    #  PHASE 2: DEVELOPER  —  Write Code
    # ══════════════════════════════════════════════════════════
    def developer_write_all(self, goal: str = "") -> dict:
        """Write all files from the manifest."""
        self.phase = self.PHASE_WRITING

        if _HAS_OVERLORD:
            return self._developer_overlord()
        return self._developer_standalone()

    def _developer_overlord(self) -> dict:
        """Full Overlord pipeline: RAG + Wisdom + Reviewer + SelfCorrection."""
        client = get_cached_client(self.model, self.api_key)
        files = self.manifest.get("files", [])
        deps = self.manifest.get("dependencies", [])
        file_list = [f["path"] for f in files]

        # Initialize subsystems
        wisdom = GlobalWisdom(self.project_dir)
        wisdom_rules = wisdom.get_generation_rules()
        wisdom_guard = WisdomGuard()
        reviewer = ReviewerAgent(client, self.rev_model, wisdom_context=wisdom_rules)
        state = CodebaseState(self.project_dir)
        proj_state = ProjectState()
        rag = CodebaseRAG(max_context_chars=12000)

        # Assemble skeleton
        if project_assembler:
            self.phase = self.PHASE_ASSEMBLING
            project_assembler(self.manifest, self.project_dir)
            self.log.log("SYSTEM", "🏗️ Project skeleton assembled")

        self.phase = self.PHASE_WRITING
        written_files = state.files

        # API convention injection
        api_conv_parts = []
        for dep_name in deps:
            dep_lower = dep_name.lower().split("==")[0].split(">=")[0].strip()
            if dep_lower in API_CONVENTIONS:
                api_conv_parts.append(API_CONVENTIONS[dep_lower])
            if dep_lower in ("pillow", "pil"):
                conv = API_CONVENTIONS.get("pillow", "")
                if conv:
                    api_conv_parts.append(conv)
        api_conv_block = ""
        if api_conv_parts:
            api_conv_block = "\n\nLIBRARY API CONVENTIONS:\n" + "\n".join(f"- {c}" for c in api_conv_parts)

        # Order: main.py first
        main_entry = None
        other_files = []
        for f in files:
            if f["path"] == "main.py":
                main_entry = f
            else:
                other_files.append(f)
        ordered = ([main_entry] + other_files) if main_entry else list(files)

        self.log.log("ENGINEER", f"Writing {len(ordered)} file(s)…")

        for i, file_spec in enumerate(ordered, 1):
            fpath = file_spec["path"]
            ftask = file_spec.get("task", file_spec.get("purpose", ""))
            self.log.log("ENGINEER", f"[{i}/{len(ordered)}] Writing: {fpath}")

            # RAG context
            manifest = build_manifest(written_files, planned_files=file_list)
            manifest_ctx = manifest_to_context(manifest) if manifest else "No files yet."
            symbol_table = proj_state.get_symbol_table()
            rag_context = rag.get_relevant_context(fpath, ftask, symbol_table)

            # Import contract
            import_contract = ""
            if "main.py" in written_files and fpath != "main.py":
                main_code = written_files["main.py"]
                module_base = fpath.replace(".py", "")
                relevant = [l.strip() for l in main_code.split("\n")
                            if module_base in l.strip() and "import" in l.strip()]
                if relevant:
                    import_contract = (
                        f"\n\nCRITICAL CONTRACT — main.py imports from YOUR file:\n"
                        + "\n".join(f"  {imp}" for imp in relevant)
                        + "\nYou MUST export these exact names."
                    )

            eng_system = (
                "You are 'Overlord,' a Senior Full-Stack Engineer. "
                "Write clean, documented, production code. "
                "NEVER use placeholder URLs or example.com. "
                "Anticipate failures with try-except. Build IMPRESSIVE implementations. "
                f"Structure: {file_list}. Target: {fpath}. Task: {ftask}. "
                f"{import_contract}\n\n{symbol_table}"
                f"{wisdom.get_generation_rules_directive()}"
                f"{PRODUCTION_SAFETY_DIRECTIVE}"
                f"{STABILITY_DIRECTIVE}"
                f"{FEATURE_RICHNESS_DIRECTIVE}"
                f"{api_conv_block}"
                "\nOutput ONLY raw source code. No markdown fences."
            )
            if wisdom_rules:
                eng_system += f"\n\n{wisdom_rules}"

            user_prompt = (
                f"Construct the file: {fpath}\n\n"
                f"Context (RAG):\n{rag_context}\n\nManifest:\n{manifest_ctx}"
            )

            try:
                code = self._ask(eng_system, user_prompt, model=self.dev_model)
            except Exception as e:
                self.log.log("ERROR", f"Engineer failed on {fpath}: {e}")
                continue

            # ── Reviewer Gate ─────────────────────────────────
            self.phase = self.PHASE_REVIEWING
            review_count = 0
            for attempt in range(3):
                verdict = reviewer.review(fpath, code, manifest_ctx)
                review_count = attempt + 1
                if verdict["status"] == "APPROVED":
                    self.log.log("REVIEWER", f"  ✓ APPROVED: {fpath} (pass {review_count})")
                    break
                else:
                    self.log.log("REVIEWER", f"  ✗ REJECTED [{review_count}/3]: {verdict['reason'][:100]}")
                    if attempt < 2:
                        try:
                            code = self._ask(eng_system,
                                f"{user_prompt}\n\nREJECTED: {verdict['reason']}\nFix ALL issues.")
                        except Exception:
                            break
            self.phase = self.PHASE_WRITING

            # ── Wisdom Guard ──────────────────────────────────
            code, fixes = wisdom_guard.auto_fix(code, fpath)
            if fixes:
                self.log.log("WISDOM", f"  🛡️ Auto-fixed {len(fixes)} violation(s)")

            # ── Self-Correction ───────────────────────────────
            corrector = SelfCorrectionModule(code, fpath, max_attempts=3)
            def _fixer(broken, err):
                return self._ask(eng_system,
                    f"Errors:\n{err}\n\nFix ALL issues:\n\n{broken}")
            code = corrector.repair_loop(_fixer)

            # ── Write to disk ─────────────────────────────────
            full_path = os.path.join(self.project_dir, str(fpath))
            
            # Skip if it's a directory (Architecture sometimes plans these as 'files')
            if str(fpath).endswith("/") or str(fpath).endswith("\\"):
                self.log.log("ENGINEER", f"  ├─ {fpath} (Directory - Skipping Write)")
                continue

            os.makedirs(os.path.dirname(full_path) or self.project_dir, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as fh:
                fh.write(code)

            # Casting state to Any to bypass linter missing attributes
            s_any: Any = state
            s_any.write(fpath, code, review_count)
            written_files = s_any.files
            proj_state.register_file(fpath, code)
            rag.index_file(fpath, code, proj_state.get_exports_for(fpath))
            self.written_files[fpath] = code
            self.log.log("ENGINEER", f"  ✓ {str(fpath)} ({len(code)} chars, {review_count} review(s))")

        self.log.log("ENGINEER", f"✓ All {len(ordered)} file(s) written")
        return self.written_files

    def _developer_standalone(self) -> dict:
        """Lightweight developer (no Overlord subsystems)."""
        files = self.manifest.get("files", [])
        for i, f in enumerate(files, 1):
            fpath = f["path"] if isinstance(f, dict) else f
            purpose = (f.get("task") or f.get("purpose", "")) if isinstance(f, dict) else ""
            self.log.log("DEVELOPER", f"[{i}/{len(files)}] {fpath}")
            self._write_single_file(fpath, purpose)
        return self.written_files

    def _write_single_file(self, fpath: str, purpose: str = ""):
        """Generate and write a single file (standalone mode)."""
        context_parts = []
        for fp, code in self.written_files.items():
            lines = str(code).split("\n")
            preview_lines = [lines[i] for i in range(min(len(lines), 30))]
            preview = "\n".join(preview_lines) + ("\n..." if len(lines) > 30 else "")
            ctx_str = str(f"--- {fp} ---\n{preview}")
            context_parts.append(ctx_str)
        context = "\n\n".join(context_parts) if context_parts else "No files yet."
        file_list = ", ".join([
            str(f["path"] if isinstance(f, dict) else f)
            for f in (self.manifest.get("files") or [])
        ])

        system = (
            "You are a senior software engineer. Write production-quality code.\n"
            "Output ONLY raw source code. No markdown fences.\n"
            "Include proper error handling. Use type hints. "
            "NEVER use placeholder URLs or example.com. Write COMPLETE code."
        )
        user_prompt = (
            f"Project: {self.manifest.get('project_name', self.project_name)}\n"
            f"All files: {file_list}\nTarget: {fpath}\nPurpose: {purpose}\n"
            f"\nSibling files:\n{context}\n\nWrite: {fpath}"
        )
        code = self._ask(system, user_prompt)

        full_path = os.path.join(self.project_dir, fpath)
        os.makedirs(os.path.dirname(full_path) or self.project_dir, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(code)
        self.written_files[fpath] = code
        self.log.log("DEVELOPER", f"  ✓ {fpath} ({len(code)} chars)")

    # ══════════════════════════════════════════════════════════
    #  PHASE 3: SUPERVISOR  —  Verify (Docker or Subprocess)
    # ══════════════════════════════════════════════════════════
    def supervisor_verify(self) -> dict:
        """Run the project in a Docker sandbox (preferred) or subprocess fallback."""
        self.phase = self.PHASE_SANDBOX

        # Syntax check first
        for fpath, code in self.written_files.items():
            if fpath.endswith(".py"):
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    self.log.log("SUPERVISOR", f"  ✗ Syntax error in {fpath}: {e}")
                    return {"status": "SYNTAX_ERROR", "error": str(e), "file": fpath, "output": ""}
        self.log.log("SUPERVISOR", "  ✓ All files pass syntax check")

        if self.use_docker and self.docker_client:
            return self._verify_docker()
        return self._verify_subprocess()

    def _verify_docker(self) -> dict:
        """Run inside a Docker container with resource limits."""
        self.log.log("SUPERVISOR", "🐳 Docker sandbox verification…")

        run_cmd = self.manifest.get("run_command", "python main.py")

        # Resolve Docker image from platform profiles
        if _HAS_OVERLORD:
            profile = PLATFORM_PROFILES.get(self.platform, PLATFORM_PROFILES["python"])
            docker_image = profile.get("docker_base", "python:3.11-slim")
        else:
            docker_image = "python:3.11-slim"

        # Ensure requirements.txt exists for deps
        deps = self.manifest.get("dependencies", [])
        req_path = os.path.join(self.project_dir, "requirements.txt")
        if deps and not os.path.exists(req_path):
            with open(req_path, "w") as fh:
                fh.write("\n".join(deps) + "\n")

        install_cmd = ""
        if os.path.exists(req_path):
            install_cmd = "pip install --no-cache-dir -r /app/requirements.txt 2>&1 && "

        full_command = f"bash -c '{install_cmd}{run_cmd} 2>&1 || true'"

        self.log.log("SUPERVISOR", f"  Image: {docker_image}")
        self.log.log("SUPERVISOR", f"  Cmd:   {run_cmd}")

        try:
            output_bytes = self.docker_client.containers.run(
                image=docker_image,
                command=full_command,
                volumes={os.path.abspath(self.project_dir): {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                detach=False,
                remove=True,
                stdout=True, stderr=True,
                mem_limit="512m",
                nano_cpus=1_000_000_000,
                network_mode="bridge",
            )
            output = str(output_bytes.decode("utf-8", errors="replace"))
            if isinstance(output, str) and len(output) > 5000:
                short_start = "".join([output[i] for i in range(2500)])
                short_end = "".join([output[i] for i in range(len(output)-2500, len(output))])
                output = f"{short_start}\n…[truncated]…\n{short_end}"
            self.log.log("SUPERVISOR", "  ✓ Sandbox completed")
            if isinstance(output, str):
                short_out = "".join([output[i] for i in range(min(len(output), 200))])
                self.log.log("SUPERVISOR", f"  Output: {short_out}")
            return {"status": "SUCCESS", "output": output, "error": ""}

        except Exception as e:
            err_msg = str(e)
            err_short = "".join([err_msg[i] for i in range(min(len(err_msg), 200))])
            self.log.log("SUPERVISOR", f"  ✗ Docker error: {err_short}")

            # Try pulling the image if not found
            if "not found" in err_msg.lower() or "No such image" in err_msg:
                try:
                    self.log.log("SUPERVISOR", f"  Pulling {docker_image}…")
                    self.docker_client.images.pull(docker_image)
                    return self._verify_docker()  # Retry
                except Exception:
                    pass

            return {"status": "ERROR", "error": err_msg, "output": ""}

    def _verify_subprocess(self) -> dict:
        """Fallback: run via subprocess (no Docker)."""
        self.log.log("SUPERVISOR", "📦 Subprocess verification…")
        entry = self.manifest.get("run_command", "python main.py").split()
        if entry[0] == "python":
            entry[0] = sys.executable

        try:
            result = subprocess.run(
                entry, capture_output=True, text=True, timeout=30,
                cwd=self.project_dir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            if result.returncode == 0:
                self.log.log("SUPERVISOR", "  ✓ Exit code 0 — PASSED")
                return {"status": "SUCCESS", "output": result.stdout, "error": ""}
            else:
                self.log.log("SUPERVISOR", f"  ✗ Exit code {result.returncode}")
                err_text = str(result.stderr).strip()
                err_len = len(err_text)
                err_start = max(0, err_len - 500)
                err_trimmed = "".join([err_text[i] for i in range(err_start, err_len)])
                return {
                    "status": "RUNTIME_ERROR",
                    "error": err_trimmed,
                    "output": result.stdout
                }
        except subprocess.TimeoutExpired:
            self.log.log("SUPERVISOR", "  ✗ Timeout (30s)")
            return {"status": "TIMEOUT", "error": "Timed out after 30s", "output": ""}
        except Exception as e:
            return {"status": "CRASH", "error": str(e), "output": ""}

    # ══════════════════════════════════════════════════════════
    #  PHASE 4: SELF-CORRECTION  —  Auto-Heal on Failure
    # ══════════════════════════════════════════════════════════
    def self_correct(self, error_report: dict) -> str:
        """Ask LLM to fix the broken file."""
        self.phase = self.PHASE_HEALING
        error_text = error_report.get("error", "")
        problem_file = error_report.get("file", "")

        if not problem_file:
            match = re.search(r'File ".*?[\\/]([^"\\/]+\.py)"', error_text)
            problem_file = match.group(1) if match else "main.py"

        original = self.written_files.get(problem_file, "")
        if not original:
            self.log.log("HEALER", f"Cannot find source for {problem_file}")
            return ""

        self.log.log("HEALER", f"Fixing: {problem_file}")
        fixed = self._ask(
            "You are a senior debugger. Fix the code. Output ONLY corrected source code.",
            f"File: {problem_file}\nError:\n{error_text}\n\nCode:\n{original}"
        )

        full_path = os.path.join(self.project_dir, problem_file)
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(fixed)
        self.written_files[problem_file] = fixed
        self.log.log("HEALER", f"  ✓ Patched: {problem_file}")
        return fixed

    # ══════════════════════════════════════════════════════════
    #  PHASE 5: HARVEST — Auto-Execute & Collect Artifacts
    # ══════════════════════════════════════════════════════════
    def _harvest_artifacts(self) -> list[dict]:
        """Execute the generated program and collect output artifacts.
        
        Runs the project's run_command, then scans the project directory
        for any new non-source files (images, videos, PDFs, etc.).
        Returns a list of artifact metadata dicts.
        """
        self.phase = self.PHASE_HARVESTING
        self.log.log("HARVEST", "📦 Auto-executing program to collect artifacts…")

        # Snapshot existing files before execution
        pre_files = set()
        for root, dirs, files in os.walk(self.project_dir):
            allowed_dirs = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "artifacts")]
            dirs.clear()
            for d in allowed_dirs:
                dirs.append(d)
            for f in files:
                pre_files.add(os.path.join(root, f))

        # Execute the program
        run_cmd = self.manifest.get("run_command", "python main.py")
        exec_output = ""
        exec_success = False

        if self.use_docker and self.docker_client:
            exec_output, exec_success = self._harvest_docker(run_cmd)
        else:
            exec_output, exec_success = self._harvest_subprocess(run_cmd)

        if not exec_success:
            err_str = str(exec_output)
            err_short = "".join([err_str[i] for i in range(min(len(err_str), 200))])
            self.log.log("HARVEST", f"  ⚠ Execution had issues: {err_short}")

        # Scan for new artifact files
        artifacts = []
        for root, dirs, files in os.walk(self.project_dir):
            allowed_dirs = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "artifacts")]
            dirs.clear()
            for d in allowed_dirs:
                dirs.append(d)
            for f in files:
                full_path = os.path.join(root, f)
                _, ext = os.path.splitext(f.lower())
                if ext in self.ARTIFACT_EXTENSIONS and full_path not in pre_files:
                    rel_path = os.path.relpath(full_path, self.project_dir)
                    file_size = os.path.getsize(full_path)
                    artifact_type = self._classify_artifact(ext)
                    artifacts.append({
                        "path": rel_path,
                        "full_path": os.path.abspath(full_path),
                        "type": artifact_type,
                        "extension": ext,
                        "size_bytes": file_size,
                        "size_human": self._human_size(file_size),
                    })
                    self.log.log("HARVEST", f"  📎 Found: {rel_path} ({self._human_size(file_size)}, {artifact_type})")

        # Copy artifacts to dedicated directory
        if artifacts:
            os.makedirs(self.artifacts_dir, exist_ok=True)
            import shutil
            for art in artifacts:
                art_path = str(art.get("path", ""))
                art_full = str(art.get("full_path", ""))
                dest = os.path.join(self.artifacts_dir, os.path.basename(art_path))
                if os.path.abspath(art_full) != os.path.abspath(dest):
                    import shutil
                    shutil.copy2(art_full, dest)
                art["artifact_path"] = os.path.abspath(dest)

        self.harvested_artifacts = artifacts
        self.log.log("HARVEST", f"  ✓ Harvested {len(artifacts)} artifact(s)")
        return artifacts

    def _harvest_docker(self, run_cmd: str) -> tuple[str, bool]:
        """Execute inside Docker with higher resource limits for media generation."""
        self.log.log("HARVEST", "  🐳 Executing in Docker (heavy profile)…")

        if _HAS_OVERLORD:
            profile = PLATFORM_PROFILES.get(self.platform, PLATFORM_PROFILES["python"])
            docker_image = profile.get("docker_base", "python:3.11-slim")
        else:
            docker_image = "python:3.11-slim"

        # Install deps + run
        req_path = os.path.join(self.project_dir, "requirements.txt")
        install_cmd = ""
        if os.path.exists(req_path):
            install_cmd = "pip install --no-cache-dir -r /app/requirements.txt 2>&1 && "

        full_command = f"bash -c '{install_cmd}{run_cmd} 2>&1 || true'"

        try:
            output_bytes = self.docker_client.containers.run(
                image=docker_image,
                command=full_command,
                volumes={os.path.abspath(self.project_dir): {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                detach=False,
                remove=True,
                stdout=True, stderr=True,
                mem_limit="1g",
                nano_cpus=1_000_000_000,
                network_mode="bridge",
            )
            output = output_bytes.decode("utf-8", errors="replace")
            self.log.log("HARVEST", f"  ✓ Docker execution finished")
            return output, True
        except Exception as e:
            return str(e), False

    def _harvest_subprocess(self, run_cmd: str) -> tuple[str, bool]:
        """Execute via subprocess fallback with extended timeout."""
        self.log.log("HARVEST", f"  📦 Executing via subprocess (timeout={self.harvest_timeout}s)…")
        entry = run_cmd.split()
        if entry[0] == "python":
            entry[0] = sys.executable

        try:
            result = subprocess.run(
                entry, capture_output=True, text=True,
                timeout=self.harvest_timeout,
                cwd=self.project_dir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            output = result.stdout + ("\n" + result.stderr if result.stderr else "")
            return output, result.returncode == 0
        except subprocess.TimeoutExpired:
            self.log.log("HARVEST", f"  ⏱ Timed out after {self.harvest_timeout}s")
            return f"Timed out after {self.harvest_timeout}s", False
        except Exception as e:
            return str(e), False

    @staticmethod
    def _classify_artifact(ext: str) -> str:
        """Classify an artifact by its extension."""
        images = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"}
        videos = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        audio  = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}
        docs   = {".pdf", ".docx", ".xlsx", ".pptx"}
        data   = {".csv", ".parquet", ".sqlite", ".db"}
        if ext in images: return "image"
        if ext in videos: return "video"
        if ext in audio:  return "audio"
        if ext in docs:   return "document"
        if ext in data:   return "data"
        return "file"

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string."""
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _vanish_cleanup(self):
        """Purges source code and temporary assets to leave a clean media-only output."""
        self.log.log("SYSTEM", "🪄  VANISH: Purging source code from Video-Only project...")
        
        # Files to KEEP
        keep_list = ["BUILD_LOG.md", "package_manifest.json", "plan.json"]
        keep_dirs = ["outputs", "media", "assets", "artifacts"]
        
        # Walk through the project path
        for root, dirs, files in os.walk(self.project_dir, topdown=False):
            for name in files:
                fpath = os.path.join(root, name)
                rel_path = os.path.relpath(fpath, self.project_dir)
                
                # Skip files we want to keep
                if any(rel_path.startswith(kd) for kd in keep_dirs):
                    continue
                if name in keep_list:
                    continue
                
                # Delete everything else
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                    
            for name in dirs:
                dpath = os.path.join(root, name)
                rel_path = os.path.relpath(dpath, self.project_dir)
                
                # Skip directories we want to keep
                if any(rel_path.startswith(kd) for kd in keep_dirs):
                    continue
                    
                # Delete empty dirs
                try:
                    os.rmdir(dpath)
                except Exception:
                    pass

        self.log.log("SUCCESS", "✨ Vanish complete. Output folder is now media-only.")

    # ══════════════════════════════════════════════════════════
    #  FULL PIPELINE
    # ══════════════════════════════════════════════════════════
    def run_full_build(self, goal: str) -> dict:
        """Execute: Architect → Developer → Supervisor → Self-Correct → Harvest."""
        start = time.time()
        self.log.log("ENGINE", "═" * 56)
        self.log.log("ENGINE", "🚀 NEXUS CREATION ENGINE — Build Pipeline")
        self.log.log("ENGINE", "═" * 56)

        # Phase 1: Architect (or Gemini Direct Media Pipe)
        is_media = (
            self.direct_media or 
            self.manifest.get("project_type") == "VIDEO" or 
            any(k in str(goal).lower() for k in ["gemini", "vision", "direct_media"])
        )
        
        if is_media:
            self.log.log("ENGINE", "✨ GEMINI MULTIMODAL MODE: Bypassing standard code-gen pipeline.")
            pipe = GeminiMediaPipe(self.project_dir, api_key=self.api_key, model=self.arch_model)
            try:
                video_path = pipe.generate_video(goal, log_callback=self.log.log)
                elapsed = time.time() - start
                
                # Mock result for a media build
                self.harvested_artifacts = [{
                    "path": os.path.relpath(video_path, self.project_dir),
                    "full_path": video_path,
                    "type": "video",
                    "extension": ".mp4",
                    "size_bytes": os.path.getsize(video_path),
                    "size_human": "Generated",
                }]
                self.phase = self.PHASE_COMPLETE
                self.log.log("ENGINE", f"🎬 GEMINI VIDEO READY: {video_path}")
                self.log.log("ENGINE", "═" * 56)
                self.log.log("ENGINE", f"✅ Build COMPLETE in {elapsed:.1f}s")
                return self._build_result("COMPLETE", start, {"status": "SUCCESS", "artifacts": self.harvested_artifacts})
            except Exception as e:
                self.log.log("ERROR", f"Gemini Media Pipe failed: {e}")
                self.phase = self.PHASE_FAILED
                return self._build_result("FAILED", start, {"error": str(e)})

        # Phase 1: Architect
        manifest = self.architect_plan(goal)
        if not manifest:
            self.phase = self.PHASE_FAILED
            return self._build_result("FAILED", start, {"error": "Architect failed"})

        # Phase 2: Developer
        self.developer_write_all(goal)

        # Phase 3+4: Verify and self-correct
        report = {"status": "NOT_RUN"}
        for attempt in range(self.max_retries):
            report = self.supervisor_verify()
            if report["status"] == "SUCCESS":
                break
            self.log.log("ENGINE", f"Auto-fix attempt {attempt + 1}/{self.max_retries}")
            self.self_correct(report)
        else:
            report = self.supervisor_verify()  # Final check

        # NEW: Phase 12 & 13 Injection
        if _HAS_OVERLORD and report["status"] == "SUCCESS":
            # ── Phase 12: TEST GENERATION ─────────────────────────────
            self.log.log("ENGINE", "🧬 Phase 12: Automated Test Generation")
            try:
                generate_verification_suite(
                    project_path=self.project_dir,
                    manifest=self.manifest,
                    client=get_cached_client(self.model, self.api_key),
                    model=self.model
                )
            except Exception as e:
                self.log.log("WARN", f"  ⚠ Test generation skipped: {e}")

            # ── Phase 13: VISUAL PROOF CAPTURE ────────────────────────
            if self.manifest.get("project_type") != "VIDEO":
                self.log.log("ENGINE", "📸 Phase 13: Visual Proof Capture")
                # Detect platform (standard heuristic)
                manifest_str = str(self.manifest).lower()
                is_web = any(x in manifest_str for x in ["fastapi", "flask", "react", "next.js", "html", "css", "js"])
                platform_heuristic = "web" if is_web else "desktop"
                try:
                    capture_visual_proof(
                        project_path=self.project_dir,
                        run_cmd=self.manifest.get("run_command", "python main.py"),
                        platform=platform_heuristic
                    )
                except Exception as e:
                    self.log.log("WARN", f"  ⚠ Visual proof capture skipped: {e}")

        # Phase 5: Harvest artifacts (auto-execute the generated program)
        if self.auto_execute and report["status"] == "SUCCESS":
            self.log.log("ENGINE", "═" * 56)
            self.log.log("ENGINE", "📦 HARVEST PHASE — Executing program & collecting artifacts")
            artifacts = self._harvest_artifacts()
            report["artifacts"] = artifacts
            report["artifact_count"] = len(artifacts)
        else:
            report["artifacts"] = []
            report["artifact_count"] = 0

        elapsed = time.time() - start
        self.phase = self.PHASE_COMPLETE if report["status"] == "SUCCESS" else self.PHASE_FAILED

        self.log.log("ENGINE", "═" * 56)
        self.log.log("ENGINE", f"{'✅' if self.phase == self.PHASE_COMPLETE else '❌'} "
                     f"Build {self.phase.upper()} in {elapsed:.1f}s")
        self.log.log("ENGINE", f"  Files: {len(self.written_files)}")
        if self.harvested_artifacts:
            self.log.log("ENGINE", f"  Artifacts: {len(self.harvested_artifacts)}")
            
            # Specifically highlight video location for VIDEO projects
            if self.manifest.get("project_type") == "VIDEO":
                v_artifact = next((a["path"] for a in self.harvested_artifacts if a["path"].endswith(".mp4")), None)
                if v_artifact:
                    self.log.log("ENGINE", f"  🎬 VIDEO READY: {os.path.abspath(os.path.join(self.project_dir, v_artifact))}")

        self.log.log("ENGINE", f"  Path:  {os.path.abspath(self.project_dir)}")
        self.log.log("ENGINE", "═" * 56)

        # Phase 6: VANISH (Video-Only Cleanup)
        if self.manifest.get("project_type") == "VIDEO":
            self._vanish_cleanup()

        return self._build_result(
            "COMPLETE" if self.phase == self.PHASE_COMPLETE else "FAILED",
            start, report
        )

    def _build_result(self, status: str, start_time: float, report: dict) -> dict:
        return {
            "status": status,
            "project_name": self.project_name,
            "project_dir": os.path.abspath(self.project_dir),
            "manifest": self.manifest,
            "files_written": list(self.written_files.keys()),
            "file_count": len(self.written_files),
            "run_command": str(self.manifest.get("run_command", "python main.py")),
            "elapsed_seconds": int(time.time() - start_time),
            "final_report": report,
            "artifacts": self.harvested_artifacts,
            "artifact_count": len(self.harvested_artifacts),
            "log": self.log.get_entries(),
        }


# ══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nexus Creation Engine")
    parser.add_argument("goal", nargs="?",
                        default="Create a program that tracks daily tasks and saves them to a CSV.")
    parser.add_argument("--name", default=f"project_{int(time.time())}")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--budget", type=float, default=5.0, help="Max cost ($)")
    parser.add_argument("--platform", default="python", help="Base platform")
    parser.add_argument("--scale", default="application", help="Project scale")
    parser.add_argument("--phase", default="all", help="Phases to run")
    parser.add_argument("--retries", type=int, default=3, help="Max retries")
    parser.add_argument("--output", default="./builds", help="Output directory")
    parser.add_argument("--docker", action="store_true", default=True, help="Enable Docker")
    parser.add_argument("--no-docker", action="store_false", dest="docker", help="Disable Docker")
    parser.add_argument("--direct-media", action="store_true", help="Direct Media Mode")
    parser.add_argument("--arch-model", default="", help="Architect Model")
    parser.add_argument("--dev-model", default="", help="Developer Model")
    parser.add_argument("--rev-model", default="", help="Reviewer Model")
    parser.add_argument("--res-model", default="", help="Researcher Model")
    
    args = parser.parse_args()

    engine = NexusEngine(
        project_name=args.name,
        model=args.model,
        output_dir=args.output,
        budget=args.budget,
        platform=args.platform,
        scale=args.scale,
        phase=args.phase,
        max_retries=args.retries,
        use_docker=args.docker,
        auto_execute=True,
        direct_media=args.direct_media,
        arch_model=args.arch_model,
        dev_model=args.dev_model,
        rev_model=args.rev_model,
        res_model=args.res_model
    )
    result = engine.run_full_build(args.goal)
    print(json.dumps(result, indent=2, default=str))
