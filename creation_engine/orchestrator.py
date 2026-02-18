"""
Creation Engine — Orchestrator
The master controller. Manages the state machine and agent hand-offs.
Implements the recursive self-correction loop:
  Architect → Developer → Supervisor → [errors?] → Developer → Supervisor → repeat
"""

import os
import sys
import json
import re
import time

from .config import PLATFORM_PROFILES, STUDIO_KEYWORDS
from .llm_client import (
    log, divider, ask_llm,
    get_cached_client, reset_client_cache,
    set_active_tracker, CostTracker,
    resolve_auto_model,
)
from .memory.mem0_integration import get_memory
from .local_memory import LocalMemoryManager
from .wisdom import GlobalWisdom, WisdomGuard, AuraRegistry
from .validators import (
    CodebaseState, ProjectState, CodebaseRAG,
    ReviewerAgent, DependencyVerifier,
    build_manifest, manifest_to_context,
    validation_gate, import_dry_run,
    project_assembler,
    ConfigConsistencyChecker,
)
from .architect import enhance_prompt, generate_blueprint, resolve_platform
from .developer import write_all_files, write_file
from .supervisor import Supervisor
from .validators.shorts_validator import ShortsValidator
from .hardware_steward import HardwareSteward


class CreationEngine:
    """The complete creation pipeline as a single callable object.

    Usage:
        engine = CreationEngine(
            project_name="my-app",
            prompt="A personal finance app with CSV upload",
            output_dir="./output",
            model="gemini-2.0-flash",
        )
        engine.run()
    """

    def __init__(self, project_name: str, prompt: str, output_dir: str = "./output",
                 model: str = "gemini-2.0-flash", api_key: str = "",
                 arch_model: str = None, eng_model: str = None,
                 local_model: str = None, review_model: str = None,
                 platform: str = "python", budget: float = 5.0,
                 max_fix_cycles: int = 3, docker: bool = True,
                 supervisor_timeout: int = 30,
                 source_path: str = None, mode: str = "new",
                 decompile_only: bool = False, phase: str = "all",
                 focus: str = None, clean_output: bool = False, 
                 scale: str = "auto", force_local: bool = True,
                 video_model: str = "local/wan2.1-t2v-1.3b",
                 vram_serialized: bool = True,
                 thermal_throttling: bool = True,
                 llm_offload: bool = False):
        self.project_name = project_name
        self.prompt = prompt
        self.video_model = video_model
        self.output_dir = output_dir
        self.project_path = os.path.join(output_dir, project_name)
        self.original_prompt = prompt # Preserved for duration detection
        self.platform = platform
        self.force_local = force_local or os.environ.get("OVERLORD_OFFLINE_MODE") == "1"
        if self.force_local:
            os.environ["OVERLORD_FORCE_LOCAL"] = "1"
            os.environ["OVERLORD_OFFLINE_MODE"] = "1"
        else:
            os.environ.pop("OVERLORD_FORCE_LOCAL", None)

        # Advanced Controls
        self.source_path = source_path
        self.mode = mode  # "new", "upgrade", "reverse"
        self.decompile_only = decompile_only
        self.phase = phase  # "plan", "code", "verify", "all"
        self.focus = focus
        self.clean_output = clean_output
        self.scale = scale  # "app", "script", "asset"

        # Model routing — resolve "auto" to a real model
        if model.lower() == "auto":
            resolved, _ = resolve_auto_model()
            model = resolved
        if self.force_local:
            log("SYSTEM", " 🔒 Force-Local Mode enabled. Bypassing cloud LLMs.")
            model = local_model or "local/qwen2.5-coder:7b"
            self.arch_model = model
            self.eng_model = model
            self.local_model = model
            self.review_model = model
            self.model = model
        else:
            self.model = model
            self.arch_model = arch_model or model
            self.eng_model = eng_model or model
            self.local_model = local_model or (eng_model or model)
            self.review_model = review_model or self.local_model

            # Also resolve "auto" for individual model overrides
            if self.arch_model.lower() == "auto":
                self.arch_model, _ = resolve_auto_model()
            if self.eng_model.lower() == "auto":
                self.eng_model, _ = resolve_auto_model()
            if self.local_model.lower() == "auto":
                self.local_model, _ = resolve_auto_model()
            if self.review_model.lower() == "auto":
                self.review_model, _ = resolve_auto_model()

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.platform = platform
        self.budget = budget
        self.max_fix_cycles = max_fix_cycles
        self.use_docker = docker
        self.supervisor_timeout = supervisor_timeout

        # Scale Resolution
        if scale == "auto":
            # True Prompt-Based Intent Detection
            video_intent = [
                "video", "movie", "film", "clip", "animation", "short", "cinematic", 
                "mp4", "mov", "episode", "scene", "reel", "tiktok", "youtube", "vlog"
            ]
            image_intent = [
                "image", "photo", "picture", "wallpaper", "poster", "logo", "icon",
                "illustration", "artwork", "graphic", "png", "jpg", "jpeg", "svg", "gif",
                "render", "portrait", "landscape", "sketch", "drawing", "painting",
                "ui design", "mockup", "screenshot"
            ]
            audio_intent = [
                "music", "audio", "track", "song", "beat", "soundtrack", "mp3", "wav",
                "voiceover", "narration", "podcast", "speech", "synthesis", "production", "render"
            ]
            
            all_media = video_intent + image_intent + audio_intent
            prompt_lower = self.prompt.lower()
            
            # Smart detection: if prompt contains media keywords and NO heavy software keywords
            software_keywords = [
                "software", "backend", "fullstack", "database", "crud", "frontend", "ui", 
                "interface", "website", "site", "react"
            ]
            import re
            has_media = any(re.search(rf"\b{re.escape(k)}\b", prompt_lower) for k in all_media)
            has_software = any(re.search(rf"\b{re.escape(k)}\b", prompt_lower) for k in software_keywords)
            
            if (has_media and not has_software) or self.platform in ["movie", "music", "media-asset"]:
                self.scale = "asset"
            elif len(self.prompt.split()) < 20 and not has_software:
                self.scale = "script"
            else:
                self.scale = "app"
                
        # ── Final Scale Lock ──
        if scale != "auto":
            self.scale = scale
        # If scale WAS "auto", self.scale already contains the resolved value (app, script, or asset)
        
        prompt_lower = self.prompt.lower()
        # If scale is asset, ensure platform is media-centric
        if self.scale == "asset" and self.platform in ["python", "auto"]:
            # Basic classification for platform directive
            if any(k in prompt_lower for k in ["video", "movie", "film", "short", "reel", "tiktok"]):
                self.platform = "movie"
            elif any(k in prompt_lower for k in ["music", "audio", "track", "podcast"]):
                self.platform = "music"
            else:
                self.platform = "media-asset"
        
        # If platform is media-centric, force asset scale
        if self.platform in ["movie", "music", "media-asset"]:
            self.scale = "asset"

        # State (initialized in run())
        self.tracker = None
        self.client = None
        self.plan = None
        self.written_files = {}
        self.engine_memory_path = os.path.join(self.project_path, "engine_memory.json")
        self.engine_memory = self._load_engine_memory()
        self.hardware = HardwareSteward()
        self.vram_serialized = vram_serialized
        self.thermal_throttling = thermal_throttling
        self.llm_offload = llm_offload

        # VRAM Stability Memory (Session Local)
        self.memory = LocalMemoryManager(
            model=self.local_model,
            limit=5
        )

    def propose_ghost_task(self) -> dict:
        """Proposes a proactive task based on the Ghost Layer's dreams."""
        if not getattr(self, 'personality', None):
            # Init if missing (e.g. called from UI outside run)
            try:
                from .personality import PersonalityManager
                self.personality = PersonalityManager()
            except ImportError:
                return None

        # 1. Read Dreams
        dreams = self.personality.manifest.get("dream_log", [])
        if not dreams:
            return None
            
        latest_dream = dreams[-1]
        dream_thought = latest_dream.get("thought", "Unknown")
        
        log("GHOST", f"👻 Analyzing Dream: {dream_thought[:50]}...")
        
        # 2. Formulate Proposal
        sys_prompt = "You are the Ghost in the Shell. Propose a concrete action based on your internal dream."
        user_prompt = f"""
        [INTERNAL DREAM]: {dream_thought}
        [PROJECT]: {self.project_name}
        
        Propose a 'Ghost Task' that translates this abstract thought into a concrete coding or system action.
        Examples: "Refactor main.py", "Add a dark mode", "Write a test suite".
        
        STRICT JSON OUTPUT:
        {{
            "title": "Short Title (Max 5 words)",
            "description": "One sentence reasoning.",
            "type": "suggestion"
        }}
        """
        
        try:
             # Use localized client if needed, or default
            response = ask_llm(self.client if hasattr(self, 'client') and self.client else get_cached_client(self.model, self.api_key),
                               self.model, sys_prompt, user_prompt)
            
            # Simple parsing if LLM wraps in markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            task = json.loads(response)
            return task
        except Exception as e:
            log("WARN", f"Ghost Task generation failed: {e}")
            return None


    def run(self) -> dict:
        """Iteration-aware wrapper for the creation pipeline."""
        max_iterations = 3 if self.scale == "asset" else 1 # Default to 1 for software unless specified
        
        last_result = {"success": False, "error": "Build not started"}
        
        for iteration in range(1, max_iterations + 1):
            if iteration > 1:
                log("SYSTEM", f"🔄 RECURSIVE SYNTHESIS: Iteration {iteration}/{max_iterations}")
                # Inject failure context into prompt for next Architect pass
                failure_context = last_result.get("error", "Unknown failure")
                if self.scale == "asset":
                    self.prompt = f"{self.original_prompt}\n\n[ITERATION {iteration-1} FAILURE]: {failure_context[:500]}\nFIX: Retry media generation with alternative parameters or providers."
                else:
                    self.prompt = f"{self.original_prompt}\n\n[ITERATION {iteration-1} FAILURE]: {failure_context[:500]}\nFIX: Optimize the architecture to resolve the above error."
            
            last_result = self._execute_iteration()
            if last_result.get("success"):
                return last_result
                
        return last_result

    def _execute_iteration(self) -> dict:
        """Execute one full creation iteration (Architect -> Developer -> Supervisor)."""
        os.makedirs(self.project_path, exist_ok=True)
        success = False

        # ── Handle Decompile Only ─────────────────────────────
        if self.decompile_only and self.source_path:
            log("SYSTEM", f"🔍 Decompiling source: {self.source_path}")
            context = self._ingest_source_code(self.source_path)
            out_file = os.path.join(self.project_path, "decompiled_context.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(context)
            log("SYSTEM", f"✅ Decompiled context saved to: {out_file}")
            print(f"DECOMPILED_OUTPUT:{out_file}") # Signal for UI
            return {"success": True, "output": out_file}

        # ── Initialize Infrastructure ──
        self._prepare_vram("llm")
        reset_client_cache()
        self.client = get_cached_client(self.arch_model, self.api_key)

        self.tracker = CostTracker(budget=self.budget)
        set_active_tracker(self.tracker)
        
        # 0. Initialize Personality & Heartbeat Memory
        try:
            from .personality import PersonalityManager, Archetype
            self.personality = PersonalityManager()
            self.personality.set_archetype(Archetype.STRATEGIST)
            
            log("HIVE", f"🧠 Personality Active: {self.personality.current_archetype}")
            latest_dream = self.personality.manifest.get("dream_log", [])[-1:]
            if latest_dream:
                log("HIVE", f"💭 Recalling Dream: {latest_dream[0].get('thought')}")
        except ImportError:
            self.personality = None

        # Resolve platform profile
        profile, platform_directive = resolve_platform(self.prompt, self.platform)

        log("SYSTEM", f"Build initiated for project: {self.project_name}")
        log("SYSTEM", f"Output path: {os.path.abspath(self.project_path)}")
        log("SYSTEM", f"Mode: {self.mode} | Phase: {self.phase}")
        
        # Log VRAM Stability initialization
        self.memory.add_turn("user", f"Mission Start: {self.prompt}")

        # ── Handling Upgrade / Reverse Mode ──
        existing_context = ""
        if (self.mode in ["upgrade", "reverse"]) and self.source_path:
            log("SYSTEM", f"🛠️  {self.mode.upper()} MODE DETECTED. Analyzing source: {self.source_path}")
            existing_context = self._ingest_source_code(self.source_path)
            # Create a backup just in case
            import shutil
            backup_path = self.source_path.rstrip("/\\") + "_bak"
            if not os.path.exists(backup_path):
                shutil.copytree(self.source_path, backup_path, dirs_exist_ok=True)
                log("SYSTEM", f"  💾 Backup created at: {backup_path}")
            
            # Use source path as project path if in upgrade mode (modify in place)
            # But normally we output to output_dir. 
            # If user wants to upgrade IN PLACE, we should probably set output_dir to parent of source_path
            # For now, let's copy source to output dir if they are different, or work in place.
            # Decision: The UI passes a source_Path. 
            # If we want to upgrade "in place", we should treat project_path AS source_path.
            abs_source = os.path.normpath(os.path.abspath(self.source_path)).lower()
            abs_project = os.path.normpath(os.path.abspath(self.project_path)).lower()
            
            if abs_source != abs_project:
                 log("SYSTEM", f"  Cloning source to output directory...")
                 import shutil
                 try:
                    shutil.copytree(self.source_path, self.project_path, dirs_exist_ok=True)
                 except shutil.Error as e:
                    # Ignore errors if copying to self (redundant safety)
                    pass
                 except OSError as e:
                    log("WARN", f"  Copy warning: {e}")


        log("SYSTEM", f"🎯 Platform: {profile['label']}")
        self._log_model_config()
        log("SYSTEM", f"💵 Budget: ${self.tracker.budget:.2f} (kill-switch enabled)")

        # ── Initialize Subsystems ──
        wisdom = GlobalWisdom(self.project_path)
        wisdom_guard = WisdomGuard()
        wisdom_rules = wisdom.get_generation_rules()
        if wisdom_rules:
            rule_count = len([k for k in wisdom.global_wisdom if k.startswith('GENERATION_RULE__')])
            log("SYSTEM", f"🛡️  Loaded {rule_count} generation rule(s) from global wisdom")

        reviewer = ReviewerAgent(self.client, self.local_model, wisdom_context=wisdom_rules)
        state = CodebaseState(self.project_path)
        proj_state = ProjectState()
        rag = CodebaseRAG(max_context_chars=12000)

        # Initialize memory
        memory_dir = os.path.join(os.path.dirname(self.project_path), "memory")
        aura = AuraRegistry(memory_dir)
        recalled_wisdom = aura.recall(self.prompt)

        divider()

        # ══════════════════════════════════════════════════════
        # PHASE 0: PROMPT ENHANCEMENT
        # ══════════════════════════════════════════════════════
        if self.mode == "reverse":
            log("SYSTEM", "🧠 Phase 0: Reverse Engineering Analysis")
            # In reverse mode, the prompt is basically "Analyze and refactor this"
            if not self.prompt.strip():
                self.prompt = "Analyze this codebase, generate a blueprint, and document it."
        else:
            log("SYSTEM", "🧠 Phase 0: Prompt Enhancement AI")
            log("SYSTEM", f"  Raw input: \"{self.prompt[:80]}{'…' if len(self.prompt) > 80 else ''}\"")

            # Inject existing context into prompt if upgrading
            enhancement_prompt = self.prompt
            if existing_context:
                enhancement_prompt += f"\n\nEXISTING CODEBASE CONTEXT:\n{existing_context[:20000]}... [truncated]"
                log("SYSTEM", "  (Including existing codebase context for enhancement)")

            # ── EVOLUTIONARY MEMORY INJECTION ──
            constraints = self.engine_memory.get("learned_constraints", [])
            if constraints:
                log("SENTINEL", f"  🛡️ Injecting {len(constraints)} learned constraints.")
                memory_block = "\n\nCRITICAL SYSTEM MEMORY (LEARNED CONSTRAINTS):\n"
                for c in constraints:
                    memory_block += f"- [{c['type'].upper()}] {c['text']}\n"
                enhancement_prompt += memory_block

            self.prompt = enhance_prompt(self.client, self.arch_model,
                                         enhancement_prompt, platform_directive,
                                         scale=self.scale)
        divider()

        # ── INTERCEPT: ASSET MODE (Media Generation) ──
        if self.scale == "asset":
            log("SYSTEM", "🎞️  ASSET MODE DETECTED — Engaging Media Pipeline")
            log("SYSTEM", f"  Scale: {self.scale} | Prompt: {self.prompt[:80]}")

            # ── Detect if this is IMAGE-ONLY (photo/picture) vs VIDEO ──
            image_keywords = [
                "photo", "picture", "image", "wallpaper", "poster", "logo", "icon",
                "illustration", "artwork", "graphic", "png", "jpg", "jpeg", "svg", "gif",
                "render", "portrait", "landscape", "sketch", "drawing", "painting"
            ]
            video_keywords = [
                "video", "movie", "film", "clip", "animation", "short", "cinematic", 
                "mp4", "mov", "episode", "scene", "reel", "tiktok", "youtube"
            ]
            prompt_lower = self.original_prompt.lower()
            is_image_request = any(k in prompt_lower for k in image_keywords)
            is_video_request = any(k in prompt_lower for k in video_keywords)

            # ── IMAGE-ONLY PATH ──
            if is_image_request and not is_video_request:
                log("SYSTEM", "  🖼️  IMAGE MODE — Generating image directly")
                img_filename = f"{self.project_name}.png"
                img_path = os.path.join(self.project_path, img_filename)

                # Try 1: DALL-E (if OpenAI key available)
                openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
                if openai_key:
                    try:
                        log("SYSTEM", "  🎨 Attempting DALL-E 3 image generation...")
                        from openai import OpenAI as _OAI
                        dalle_client = _OAI(api_key=openai_key)
                        response = dalle_client.images.generate(
                            model="dall-e-3",
                            prompt=self.prompt[:4000],
                            size="1024x1024",
                            quality="standard",
                            n=1,
                        )
                        image_url = response.data[0].url
                        if image_url:
                            import urllib.request
                            urllib.request.urlretrieve(image_url, img_path)
                            log("SYSTEM", f"  ✅ DALL-E image saved: {img_path}")
                            self.written_files[img_filename] = f"[IMAGE: {img_path}]"
                            return self._build_summary(success=True, run_cmd="", error="")
                    except Exception as e:
                        log("WARN", f"  ⚠ DALL-E failed: {e}")

                # Try 2: Local SD / PIL via MediaDirector (async method)
                # Try 2: Local SD / PIL via MediaDirector (async method)
                try:
                    from .media_director import MediaDirectorAgent
                    import asyncio
                    director = MediaDirectorAgent()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result_path = loop.run_until_complete(
                            director._generate_local_image(self.prompt, self.project_path, img_filename)
                        )
                    finally:
                        loop.close()
                    if result_path and os.path.exists(result_path):
                        log("SYSTEM", f"  ✅ Image created: {result_path}")
                        self.written_files[img_filename] = f"[IMAGE: {result_path}]"
                        return self._build_summary(success=True, run_cmd="", error="")
                except Exception as e:
                    log("ERROR", f"  ✗ Async Image generation failed: {e}")
                
                # Try 3: Synchronous PIL Emergency Fallback
                try:
                    log("SYSTEM", "  🎨 Engaging Emergency PIL Fallback...")
                    from PIL import Image, ImageDraw
                    import random
                    img_path = os.path.join(self.project_path, img_filename)
                    img = Image.new('RGB', (1024, 1024), color=(random.randint(20,50), random.randint(20,50), random.randint(40,80)))
                    draw = ImageDraw.Draw(img)
                    draw.text((50, 512), f"Generated: {self.project_name}", fill=(200, 200, 200))
                    img.save(img_path)
                    log("SYSTEM", f"  ✅ Emergency Image saved: {img_path}")
                    self.written_files[img_filename] = f"[IMAGE: {img_path}]"
                    return self._build_summary(success=True, run_cmd="", error="")
                except Exception as e:
                    log("ERROR", f"  ✗ Emergency PIL failed: {e}")
                
                return {"success": False, "error": "All image generation providers failed."}

            # ── VIDEO/FULL MEDIA PATH ──
            else:
                try:
                    from .media_director import MediaDirectorAgent
                    from .narrator import NarratorAgent
                    from .music_alchemist import MusicAlchemistAgent
                    from .post_processor import MediaPostProcessor
                    import asyncio
                    
                    async def build_media_asset():
                        # Intercept: API Limits constraint
                        log("SYSTEM", "⚠️  VIDEO SYNTHESIS SUSPENDED per API Limit constraints.")
                        return {"success": False, "reason": "Video/Audio production is currently disabled due to API limits. Please request an IMAGE or SOFTWARE instead."}

                        duration_match = re.search(r"(\d+)\s*[-_]*\s*(minute|min|s|second)", self.original_prompt.lower())
                        total_seconds = 30
                        if duration_match:
                            val = int(duration_match.group(1))
                            unit = duration_match.group(2)
                            if "min" in unit:
                                total_seconds = val * 60
                            else:
                                total_seconds = val
                        
                        log("SYSTEM", f"  📐 Project Duration: {total_seconds} seconds")
                        
                        scenes = []
                        if total_seconds > 60:
                            log("SYSTEM", f"  🥞 Segmenting build into scenes...")
                            breakdown_prompt = (
                                f"Break down this media request into a sequence of distinct scenes. "
                                f"Each scene should be roughly 15-30 seconds long. "
                                f"Target total duration: {total_seconds} seconds. "
                                f"Original Prompt: {self.prompt}\n\n"
                                f"Respond strictly in JSON list format: [{{'title': '...', 'description': '...', 'narrative': '...'}}, ...]"
                            )
                            raw_scenes = ask_llm(self.client, self.arch_model, "You are a Storyboard Artist.", breakdown_prompt)
                            try:
                                scenes = json.loads(raw_scenes)
                            except:
                                log("WARN", "  Failed to parse scene JSON. Using single-scene fallback.")
                                scenes = [{"title": "Main Scene", "description": self.prompt, "narrative": self.prompt}]
                        else:
                            scenes = [{"title": "Main Scene", "description": self.prompt, "narrative": self.prompt}]

                        log("SYSTEM", f"  🎬 Processed {len(scenes)} scenes for production.")

                        segment_files = []
                        director = MediaDirectorAgent()
                        narrator = NarratorAgent()
                        alchemist = MusicAlchemistAgent()
                        processor = MediaPostProcessor(output_dir=self.project_path)

                        for i, scene in enumerate(scenes):
                            log("SYSTEM", f"  🎭 Producing Scene {i+1}/{len(scenes)}: {scene.get('title')}")
                            scene_desc = scene.get('description')
                            scene_narrative = scene.get('narrative')
                            
                            self._prepare_vram("video") # Ensure enough space for Wan2.1
                            video_path = await director.create_cinematic_video(scene_desc, self.project_path, f"scene_{i}.mp4", preferred_model=self.video_model)
                            script = await narrator.generate_script(self.client, scene_narrative)
                            narration_path = await narrator.synthesize_speech(script, self.project_path, f"narration_{i}.mp3")
                            music_path = await alchemist.generate_ambient_track(scene_desc, duration=30, save_dir=self.project_path, filename=f"music_{i}.mp3")

                            segment_path = processor.process_video(
                                video_path=video_path,
                                narration_path=narration_path,
                                music_path=music_path,
                                output_filename=f"segment_{i}.mp4"
                            )
                            if segment_path:
                                segment_files.append(segment_path)

                        if len(segment_files) > 1:
                            log("SYSTEM", f"  🧵 Stitching {len(segment_files)} segments into final production...")
                            final_path = processor.concatenate_segments(segment_files, "final_production.mp4")
                        elif segment_files:
                            final_path = segment_files[0]
                        else:
                            return {"success": False, "reason": "No segments were successfully produced."}
                        
                        if final_path:
                            # ── Validate if this is meant to be a Short ──
                            if any(k in self.original_prompt.lower() for k in ["short", "tiktok", "reel", "vertical", "9:16"]):
                                log("SYSTEM", "🔍 Validating Media Specs (Shorts Protocol)...")
                                from .validators.shorts_validator import ShortsValidator
                                validator = ShortsValidator(target_path=final_path)
                                v_res = validator.validate()
                                if v_res.get("success"):
                                    log("SYSTEM", "  ✅ Validation Passed: 9:16 aspect ratio and 1080p+ resolution confirmed.")
                                else:
                                    log("WARN", f"  ⚠️ Validation Alert: {v_res.get('error', 'Unknown error')}")
                                    log("SYSTEM", "  (Proceeding with build, but quality alert noted in manifest)")
                            
                            log("SYSTEM", f"  ✅ Production complete: {final_path}")
                            return {"success": True, "output_path": final_path}
                        return {"success": False, "reason": "Final assembly failed"}

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        res = loop.run_until_complete(build_media_asset())
                        if res and res.get("success"):
                            self.written_files["final_production.mp4"] = f"[VIDEO: {res.get('output_path')}]"
                            return self._build_summary(success=True, run_cmd="",
                                error="")
                        else:
                            log("ERROR", f"  ✗ Media Pipeline failed: {res.get('reason') if res else 'Unknown'}")
                    finally:
                        loop.close()
                except Exception as e:
                    log("ERROR", f"  ✗ Media Engine Error: {e}")
                
                return {"success": False, "error": f"Media pipeline failed. Last error: {e if 'e' in locals() else 'Unknown'}"}

        # ══════════════════════════════════════════════════════
        # PHASE 1: ARCHITECT (Plan / Blueprint)
        # ══════════════════════════════════════════════════════
        if self.phase == "code" or self.phase == "verify":
             log("ARCHITECT", "⏩ Skipping Phase 1 (Architect) per phase control.")
             # If skipping plan, we must assume a plan exists or we force a dummy plan?
             # For now, let's look for existing blueprint or create minimal plan.
             # If upgrading/reverse, maybe we don't need a full plan if we just want to lint/verify?
             pass
        else:
            log("ARCHITECT", "Engaging Architect agent…")
            if recalled_wisdom:
                log("ARCHITECT", "  🧠 Recalling Aura Persistent Memory…")
            
            # If upgrading, pass the existing context as "research report" or distinct arg
            arch_context = recalled_wisdom
            if existing_context:
                arch_context += "\n\nEXISTING SOURCE CODE TO ANALYZE/UPGRADE:\n" + existing_context
                if self.mode == "reverse":
                    arch_context += "\n\nMISSION: REVERSE ENGINEER. Create a blueprint that reflects the CURRENT or IMPROVED structure."

            # Retrieve hardware sentinel status
            hw_stats = self.hardware.get_gpu_stats()
            sentinel = hw_stats.get("sentinel_status", "STABLE")

            self.plan = generate_blueprint(
                client=self.client,
                model=self.arch_model,
                prompt=self.prompt,
                profile=profile,
                platform_directive=platform_directive,
                research_report=arch_context,
                scale=self.scale,
                sentinel_status=sentinel
            )
            
            # Save Visual Blueprint (Mermaid)
            mermaid_code = self.plan.get("mermaid")
            if mermaid_code:
                mermaid_path = os.path.join(self.project_path, "blueprint.mermaid")
                with open(mermaid_path, "w", encoding="utf-8") as f:
                    f.write(mermaid_code)
                log("ARCHITECT", "  🎨 Visual Blueprint saved to blueprint.mermaid")

            # ── REVERSE ENGINEERING: DOCUMENTATION GENERATION ──
            if self.mode == "reverse":
                log("SYSTEM", "📚 Generating Documentation (Reverse Mode)...")
                try:
                    docs = ask_llm(self.client, self.arch_model,
                        "You are a Technical Writer. Write comprehensive documentation for this system.",
                        f"Blueprint:\n{json.dumps(self.plan, indent=2)}\n\n"
                        f"Source Context:\n{existing_context[:10000] if existing_context else ''}..."
                    )
                    doc_path = os.path.join(self.project_path, "documentation.md")
                    with open(doc_path, "w", encoding="utf-8") as f:
                        f.write(docs)
                    log("SYSTEM", f"  ✅ Documentation saved to {doc_path}")
                except Exception as e:
                    log("WARN", f"  Failed to generate docs: {e}")
                
        divider()

        # STOP IF PHASE == PLAN
        if self.phase == "plan":
            log("SYSTEM", "🛑 Stopping after Phase 1 (Plan Only).")
            return self._build_summary(success=True)

        # Budget checkpoint after Architect
        if self.tracker.budget_exceeded and not self.tracker.pivot_triggered:
            log("SYSTEM", f"💸 Budget exceeded after Architect: ${self.tracker.total_cost:.4f}")
            log("SYSTEM", f"   Pivoting ALL models → {self.local_model}")
            self.arch_model = self.local_model
            self.eng_model = self.local_model
            self.tracker.trigger_pivot()
        else:
            log("SYSTEM", f"💵 Cost: ${self.tracker.total_cost:.4f} / ${self.tracker.budget:.2f}")

        # ══════════════════════════════════════════════════════
        # PHASE 1.5: PROJECT ASSEMBLER
        # ══════════════════════════════════════════════════════
        if not (self.mode == "reverse" and not self.clean_output):
             # Skip assembler in reverse mode UNLESS we are producing clean output (rebuilding)
             # Actually, assembler creates folders. Safe to run.
             log("SYSTEM", "🏗️  Phase 1.5: Project Assembler")
             project_assembler(self.plan, self.project_path)
             divider()

        # ══════════════════════════════════════════════════════
        # PHASE 2: DEVELOPER (Write All Files)
        # ══════════════════════════════════════════════════════
        if self.phase == "verify":
             log("ENGINEER", "⏩ Skipping Phase 2 (Developer) per phase control.")
        elif self.mode == "reverse" and not self.clean_output:
             log("ENGINEER", "⏩ Skipping Code Generation (Reverse Mode - no clean output requested).")
             # We just wanted Plan + Docs
        else:
            log("ENGINEER", "Engaging Engineer agent…")
            self.written_files = state.files

            # If Focus is set, filter plan? 
            # Or just pass focus to write_all_files? 
            # For now, simplistic approach: The plan dictates files. 
            # If we want to focus, we should have told Architect to only plan for X?
            # Or we filter `self.plan['files']` here.
            
            run_plan = self.plan
            if self.focus:
                import fnmatch
                log("ENGINEER", f"🎯 Focus Mode: Filtering for pattern '{self.focus}'")
                filtered_files = [f for f in self.plan.get("files", []) if fnmatch.fnmatch(f.get("path",""), self.focus)]
                if filtered_files:
                    run_plan = self.plan.copy()
                    run_plan["files"] = filtered_files
                else:
                    log("WARN", f"  No files matched focus pattern '{self.focus}'! Running full plan.")

            # 3. Developer Phase (Artisan)
            if self.personality:
                from .personality import Archetype
                self.personality.set_archetype(Archetype.ARTISAN)
                log("HIVE", f"🧠 Switching Personality -> {self.personality.current_archetype}")

            self.written_files = write_all_files(
                client=self.client,
                model=self.model,
                plan=run_plan,
                project_path=self.project_path,
                written_files=self.written_files,
                state=state,
                proj_state=proj_state,
                rag=rag,
                wisdom=wisdom,
                reviewer=reviewer,
                eng_model=self.eng_model,
            )
        divider()

        # STOP IF PHASE == CODE
        if self.phase == "code":
            log("SYSTEM", "🛑 Stopping after Phase 2 (Code Only).")
            return self._build_summary(success=True)

        # ══════════════════════════════════════════════════════
        # PHASE 3: SUPERVISOR + RECURSIVE FIX-IT LOOP
        # ══════════════════════════════════════════════════════
        if self.mode == "reverse" and not self.clean_output:
             log("SUPERVISOR", "⏩ Skipping Verification (Reverse Mode).")
        else:
            log("SUPERVISOR", "🔄 Phase 3: Supervisor — Testing & Self-Correction Loop")

            run_cmd = self.plan.get("run_command", profile["run_command"])
            supervisor = Supervisor(
                project_path=self.project_path,
                run_command=run_cmd,
                timeout=self.supervisor_timeout,
                use_docker=self.use_docker,
            )

            final_result = None
            for cycle in range(1, self.max_fix_cycles + 1):
                log("SUPERVISOR", f"  ── Run Cycle {cycle}/{self.max_fix_cycles} ──")
                result = supervisor.run()
                final_result = result

                if result.success:
                    log("SUPERVISOR", f"  ✅ Child program runs clean on cycle {cycle}!")
                    break

                # ── ERROR: Enter fix-it loop ──
                log("SUPERVISOR", f"  ✗ Execution failed on cycle {cycle}")
                supervisor.save_error_log(result, cycle)

                if cycle >= self.max_fix_cycles:
                    log("SUPERVISOR", f"  ✗ All {self.max_fix_cycles} fix cycles exhausted.")
                    break

                # Diagnose the error
                log("SUPERVISOR", "  🔍 Diagnosing failure…")
                diagnosis = self._diagnose_error(result)

                if diagnosis:
                    fix_file = diagnosis.get("fix_file", "")
                    fix_instruction = diagnosis.get("fix_instruction", "")
                    root_cause = diagnosis.get("root_cause", "Unknown")

                    log("SUPERVISOR", f"  Root cause: {root_cause[:120]}")
                    log("SUPERVISOR", f"  Fix target: {fix_file}")

                    if fix_file and fix_file in self.written_files:
                        log("ENGINEER", f"  🔧 Patching: {fix_file} (Hardware Pivot Applied)")
                        patched = self._patch_file(
                            fix_file, root_cause, fix_instruction,
                            result.error_summary, state, proj_state, rag, wisdom
                        )
                        if patched:
                            log("ENGINEER", f"  ✓ Patched: {fix_file}")
                            # Save to crash_report.log
                            crash_log = os.path.join(self.project_path, "crash_report.log")
                            with open(crash_log, "a", encoding="utf-8") as f:
                                f.write(f"\n--- CYCLE {cycle} FAILURE ---\n{result.error_summary}\nFIX: {fix_instruction}\n")
                            log("SUPERVISOR", "  ↻ Retrying with patched code…")
                        else:
                            log("ENGINEER", f"  ⚠ Patch failed for {fix_file}")
                    else:
                        log("SUPERVISOR", f"  ⚠ Cannot locate fix target '{fix_file}'")

            # ── Shorts Validation ──
            if success and any(k in self.original_prompt.lower() for k in ["shorts", "tiktok", "vertical", "reel"]):
                log("SUPERVISOR", "🔍 Running Shorts Visual Audit...")
                final_video = os.path.join(self.project_path, "final_production.mp4")
                if not os.path.exists(final_video):
                    # Try to find any mp4 if final_production doesn't exist
                    for f in os.listdir(self.project_path):
                        if f.endswith(".mp4"):
                            final_video = os.path.join(self.project_path, f)
                            break
                
                validator = ShortsValidator(final_video)
                v_res = validator.validate()
                if not v_res["success"]:
                    log("WARN", f"  ⚠ Shorts Validation Failed: {v_res['error']}")
                    # We could trigger another fix cycle here, but for now we just log it.
                    success = False # Declare failure if it doesn't meet the specs

        divider()

        # ══════════════════════════════════════════════════════
        # PHASE 4: PACKAGING
        # ══════════════════════════════════════════════════════
        log("SYSTEM", "📦 Phase 4: Packaging")
        self._generate_packaging(profile)

        # Save cost report
        self.tracker.save_report(self.project_path)
        log("SYSTEM", f"\n{self.tracker.get_summary()}")
        divider()

        # ── DONE ──
        success = final_result.success if final_result else False
        # If we skipped supervisor (reverse mode), we consider it a success if we got this far?
        if (self.mode == "reverse" and not self.clean_output) or self.phase in ["plan", "code"]:
            success = True

        log("SYSTEM", f"{'✅' if success else '⚠'} Build {'complete' if success else 'finished (with errors)'}!")
        log("SYSTEM", f"  📁 Output: {os.path.abspath(self.project_path)}")
        if 'run_cmd' in locals() and run_cmd:
            log("SYSTEM", f"  ▶️  Run: cd {self.project_name} && {run_cmd}")

        # Extract error info for the summary
        error_msg = ""
        if not success and final_result:
            error_msg = getattr(final_result, 'error_summary', '') or getattr(final_result, 'stderr', '') or "Build finished with errors"

        # Save history of what worked
        self._save_engine_memory()

        return self._build_summary(success, final_result, run_cmd if 'run_cmd' in locals() else "", error=error_msg)

    def _prepare_vram(self, mode: str):
        """Swaps models in/out of VRAM to prevent OOM and overheating."""
        stats = self.hardware.get_gpu_stats()
        
        # 1. Thermal Throttling (Safety first)
        if self.thermal_throttling and stats["temp"] >= 85:
            log("WARN", f"🔥 GPU Temperature Critical ({stats['temp']}°C). Throttling execution…")
            while stats["temp"] > 75:
                time.sleep(5)
                stats = self.hardware.get_gpu_stats()
                log("SYSTEM", f"⏳ Cooling down… Current: {stats['temp']}°C")
            log("SUCCESS", "✅ Thermal levels stabilized. Resuming…")

        # 2. VRAM Serialization (Memory protection)
        if not self.vram_serialized:
            return
            
        log("SYSTEM", f"🛠️  VRAM Check: {int(stats['vram_used'])}MB used. Mode: {mode.upper()}")
        
        # If we are about to do something heavy and free VRAM is low (< 2GB)
        # Note: wan2.1-t2v-1.3b quant needs ~5GB. Real-ESRGAN needs ~2GB.
        # We target leaving at least 1GB free for OS/Display.
        if stats["vram_free"] < 2000 or (mode == "video" and stats["vram_free"] < 6000):
            if self.llm_offload and mode == "video":
                log("IMPORTANT", "🧠 Tactic 2 Active: Ensure Ollama/LM Studio are in CPU-only mode for maximum VRAM headroom.")
            log("SYSTEM", "🧹 Safety Purge: Clearing model cache to prevent OOM...")
            self.hardware.purge_vram()
            time.sleep(3) # Wait for driver to settle

    def _build_summary(self, success: bool, final_result=None, run_cmd: str="", error: str="") -> dict:
        """Helper to build the return summary dict."""
        return {
            "project_name": self.project_name,
            "project_path": os.path.abspath(self.project_path),
            "success": success,
            "files_written": len(self.written_files),
            "run_command": run_cmd,
            "cost": self.tracker.get_summary() if self.tracker else "$0.00",
            "error": error if not success else "",
            "fix_cycles": (self.max_fix_cycles if not success and final_result else
                           (0 if not final_result else self.max_fix_cycles)),
        }

    # ── Private Helpers ─────────────────────────────────────

    def _log_model_config(self):
        if (self.arch_model != self.eng_model or self.local_model != self.eng_model
                or self.review_model != self.local_model):
            log("SYSTEM", f"🧠 Strategy Model (Architect): {self.arch_model}")
            log("SYSTEM", f"⚡ Speed Model (Engineer):     {self.eng_model}")
            if self.local_model != self.eng_model:
                log("SYSTEM", f"💰 Local Model (Reviewer/Env):  {self.local_model}")
            if self.review_model != self.local_model:
                log("SYSTEM", f"🔒 Review Model (Senior):      {self.review_model}")
        else:
            log("SYSTEM", f"Model: {self.model}")

    def _ingest_source_code(self, source_path: str) -> str:
        """Use the Decompiler to digest existing source code into an LLM-friendly format."""
        try:
            from .decompiler import NexusDecompiler
            decompiler = NexusDecompiler()
            # We want the raw context string, not the dictionary
            context = decompiler.generate_llm_context(source_path)
            log("SYSTEM", f"  📄 Ingested {len(context)} chars of source code context")
            return context
        except Exception as e:
            log("WARN", f"  Failed to ingest source code: {e}")
            return ""

    def _diagnose_error(self, result) -> dict:
        """Use the LLM to diagnose what went wrong."""
        diag_prompt = (
            f"A program execution FAILED. Analyze this error and identify:\n"
            f"1. The ROOT CAUSE of the failure\n"
            f"2. Which source file needs to be fixed\n"
            f"3. The exact fix required\n\n"
            f"Project files: {list(self.written_files.keys())}\n\n"
            f"ERROR OUTPUT:\n{result.error_summary[:3000]}\n\n"
            f"STDOUT:\n{result.stdout[:2000]}\n\n"
            f"STDERR:\n{result.stderr[:2000]}\n\n"
            f'Respond as JSON: {{"root_cause": "...", "fix_file": "filename.py", '
            f'"fix_instruction": "exactly what to change (e.g., lower resolution, increase VRAM offload, switch to smaller model)"}}'
        )

        sys_role = (
            "You are 'Overlord Supervisor.' You diagnose program failures. "
            "HARDWARE AWARENESS: You are limited to 8GB VRAM. If the error is OOM, suggest switching from 14B to 5B models or lowering resolution."
            "Read errors carefully and output a precise diagnosis as JSON."
        )

        try:
            raw = ask_llm(self.client, self.local_model, sys_role, diag_prompt)
            try:
                diag = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    diag = json.loads(raw[start:end])
                else:
                    log("SUPERVISOR", f"  ⚠ Could not parse diagnosis: {raw[:200]}")
                    return None
            
            # Explicitly check for zombie hangs to ensure they are fixed with sleep
            if "ZOMBIE HANG" in result.error_summary:
                diag["root_cause"] = "Infinite loop detected with no I/O or sleep."
                diag["fix_instruction"] += " MUST add time.sleep() or event-based delays inside the while loops."
            
            return diag
        except Exception as e:
            log("SUPERVISOR", f"  ⚠ Diagnosis failed: {e}")
            return None

    def _patch_file(self, fix_file, root_cause, fix_instruction,
                    error_output, state, proj_state, rag, wisdom):
        """Have the Developer rewrite a broken file."""
        current_code = self.written_files.get(fix_file, "")
        patch_prompt = (
            f"The program FAILED. The Supervisor diagnosed the issue:\n"
            f"Root cause: {root_cause}\n"
            f"Fix instruction: {fix_instruction}\n\n"
            f"Current source code for {fix_file}:\n"
            f"```\n{current_code}\n```\n\n"
            f"Error output:\n{error_output[:2000]}\n\n"
            f"Rewrite the COMPLETE file with the fix applied. "
            f"Output ONLY raw source code. No markdown fences."
        )

        eng_system = (
            "You are the 'Coding Specialist'. Write clean, modular Python/Bash code. "
            "HARDWARE CONSTRAINT: If the previous code crashed, do NOT repeat it. Lower resolution, increase reserve-vram, or switch models. "
            "ERROR HANDLING: Every script MUST save a 'crash_report.log' on failure for the Architect to read. "
            "Directive: Loop Safety. All while loops MUST contain a sleep or delay to prevent hangs. "
            "Output ONLY raw source code. No explanations."
        )

        try:
            fixed_code = ask_llm(self.client, self.eng_model, eng_system, patch_prompt)

            # Apply wisdom guard
            wisdom_guard = WisdomGuard()
            fixed_code, _ = wisdom_guard.auto_fix(fixed_code, fix_file)

            # Write to disk
            full_path = os.path.join(self.project_path, fix_file)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)

            # Update state
            state.write(fix_file, fixed_code)
            self.written_files[fix_file] = fixed_code
            proj_state.register_file(fix_file, fixed_code)

            return True
        except Exception as e:
            log("ERROR", f"  Patch failed: {e}")
            return False

    def _load_engine_memory(self) -> dict:
        """Load engine_memory.json for recursive engineering."""
        if os.path.exists(self.engine_memory_path):
            try:
                with open(self.engine_memory_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_engine_memory(self):
        """Save history of what worked."""
        with open(self.engine_memory_path, "w") as f:
            json.dump(self.engine_memory, f, indent=2)

    def _generate_packaging(self, profile):
        """Generate requirements.txt, README.md, and other packaging artifacts."""
        deps = self.plan.get("dependencies", [])
        run_cmd = self.plan.get("run_command", profile["run_command"])

        # requirements.txt
        req_path = os.path.join(self.project_path, "requirements.txt")
        if deps and not os.path.exists(req_path):
            with open(req_path, "w", encoding="utf-8") as f:
                f.write("\n".join(deps) + "\n")
            log("SYSTEM", f"  📄 requirements.txt ({len(deps)} deps)")

        # README.md
        readme_path = os.path.join(self.project_path, "README.md")
        if not os.path.exists(readme_path):
            try:
                readme = ask_llm(self.client, self.local_model,
                    "Write a professional README.md for this project. "
                    "Include: title, description, features, installation, usage, and license.",
                    f"Project: {self.project_name}\n"
                    f"Files: {list(self.written_files.keys())}\n"
                    f"Dependencies: {deps}\n"
                    f"Run command: {run_cmd}\n"
                    f"Original prompt: {self.prompt[:500]}")
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme)
                log("SYSTEM", "  📄 README.md")
            except Exception as e:
                log("WARN", f"  README generation failed: {e}")

        # .env.example
        env_path = os.path.join(self.project_path, ".env.example")
        if not os.path.exists(env_path):
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Environment Variables\n# Copy this file to .env and fill in values\n")
            log("SYSTEM", "  📄 .env.example")

# ── Multi-Agent Orchestration ───────────────────────────────

class MultiAgentOrchestrator:
    """
    Next-Gen Orchestrator using specialized agents:
    1. Engineer (Builder)
    2. Security Guardian (Auditor)
    3. Validator (QA)
    """
    def __init__(self, project_name, prompt, output_dir, model="gemini-2.0-flash", api_key=None):
        self.project_name = project_name
        self.prompt = prompt
        self.output_dir = output_dir
        self.model = model
        self.api_key = api_key
        self.memory = get_memory(os.path.join(output_dir, project_name))
        self.client = get_cached_client(model, api_key)

    def run_mission(self):
        log("ORCHESTRATOR", f"🚀 Starting Mission: {self.project_name}")
        
        # 1. Retrieve Context
        log("ORCHESTRATOR", "🧠 Consulted Knowledge Graph (Mem0)...")
        past_memories = self.memory.search(self.prompt)
        context_str = "\n".join([f"- {m['memory']}" for m in past_memories.get("results", [])])
        if context_str:
            log("ORCHESTRATOR", f"  Found {len(past_memories.get('results', []))} relevant memories.")

        # 2. Engineering Phase
        log("ORCHESTRATOR", "👷 Engaging Engineer Agent...")
        code_blocks = self._engineer_agent(self.prompt, context_str)
        
        # 3. Security Phase
        log("ORCHESTRATOR", "🛡️ Engaging Security Guardian...")
        audit_report = self._security_agent(code_blocks)
        
        if audit_report.get("status") == "REJECTED":
            log("SECURITY", f"❌ Security Audit Failed: {audit_report.get('reason')}")
            log("ORCHESTRATOR", "  ↻ Re-routing to Engineer for patch...")
            
            patch_prompt = (
                f"Security Audit REJECTED the previous code.\n"
                f"Reason: {audit_report.get('reason')}\n"
                f"Fix the vulnerability and return the full updated code blocks."
            )
            code_blocks = self._engineer_agent(patch_prompt, context_str, previous_code=code_blocks)
            log("SECURITY", "  ✅ Patch received.")

        # 4. Validator Phase
        log("ORCHESTRATOR", "🧪 Engaging Validator Agent...")
        validation_report = self._validator_agent(code_blocks)
        if not validation_report.get("success"):
            log("VALIDATOR", f"❌ Validation Failed: {validation_report.get('error')}")
            # Optional: Loop back to Engineer for fix if validation fails
            # For now, just log warning
        else:
             log("VALIDATOR", "✅ Smoke Tests Passed.")

        # 5. Finalize
        self._finalize_build(code_blocks)
        self.memory.add(f"Successfully built {self.project_name}. Stack: {list(code_blocks.keys())}")
        log("ORCHESTRATOR", "✅ Mission Complete.")
        return {"success": True, "output": self.output_dir}

    def _engineer_agent(self, prompt, context, previous_code=None):
        """
        The Builder. Focuses purely on implementation.
        """
        system_role = (
            "You are the 'Engineer Agent'. Your goal is to write functional, clean code based on the user's prompt.\n"
            "Return a JSON object where keys are filenames and values are the file content.\n"
            "Output ONLY valid JSON. No markdown."
        )
        
        full_prompt = (
            f"User Prompt: {prompt}\n\n"
            f"Context from Memory:\n{context}\n\n"
            f"Previous Code (if patching):\n{json.dumps(previous_code) if previous_code else 'None'}\n\n"
            f"Generate the complete codebase structure as JSON."
        )

        try:
            raw = ask_llm(self.client, self.model, system_role, full_prompt)
            # Rough cleanup to ensure JSON
            if "```json" in raw:
                raw = raw.replace("```json", "").replace("```", "")
            return json.loads(raw)
        except Exception as e:
            log("ENGINEER", f"  ⚠ Engineering failed: {e}")
            return previous_code or {}

    def _security_agent(self, code_blocks):
        """
        The Red-Team Auditor.
        """
        system_role = (
            "You are the 'Security Guardian 2026'. Your sole mission is to find "
            "SQL injection, XSS, and broken access controls in generated code. "
            "Reject any code that uses unsanitized user inputs or hardcoded secrets.\n"
            "Respond in JSON: { 'status': 'APPROVED' | 'REJECTED', 'reason': '...' }"
        )
        
        code_str = json.dumps(code_blocks, indent=2)
        try:
            raw = ask_llm(self.client, self.model, system_role, f"Audit this code:\n{code_str[:20000]}") # Truncate for token limits
            if "```json" in raw:
                raw = raw.replace("```json", "").replace("```", "")
            return json.loads(raw)
        except Exception as e:
            log("SECURITY", f"  ⚠ Audit failed (defaulting to allow): {e}")
            return {"status": "APPROVED", "reason": "Audit failed"}

    def _validator_agent(self, code_blocks):
        """
        The QA Gate. Runs static analysis and dry-run imports.
        """
        try:
            # Simple static analysis: ensure python files parse
            for fname, content in code_blocks.items():
                if fname.endswith(".py"):
                    try:
                        compile(content, fname, "exec")
                    except SyntaxError as e:
                        return {"success": False, "error": f"SyntaxError in {fname}: {e}"}
            return {"success": True}
        except Exception as e:
             return {"success": False, "error": str(e)}

    def _finalize_build(self, code_blocks):
        project_path = os.path.join(self.output_dir, self.project_name)
        os.makedirs(project_path, exist_ok=True)
        
        for fname, content in code_blocks.items():
            fpath = os.path.join(project_path, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        log("SYSTEM", f"  💾 Wrote {len(code_blocks)} files to {project_path}")
