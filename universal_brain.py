#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  UNIVERSAL AGENT BRAIN — Phase 1: Expansion Nodes
═══════════════════════════════════════════════════════════════

Multi-agent orchestrator with typed shared state (AgentState).

Nodes:
  1. Spatial Architect   — glTF/3D world generation
  2. Business Concierge  — Slack/webhook build telemetry
  3. IoT Controller      — MQTT hardware synchronization
  4. Engineer Agent      — Code synthesis (bridge to NexusEngine)
  5. Media Director      — Video/image synthesis (Luma, Kie.ai)

State flows through every node via the AgentState TypedDict.

Usage:
    brain = UniversalAgentBrain("Project_Alpha")
    asyncio.run(brain.execute_universal_build("Build a 3D Studio"))
"""

import asyncio
import json
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# ── State & Memory ──────────────────────────────────────────
from agent_state import (
    AgentState,
    create_initial_state,
    push_event,
    save_state_snapshot,
    hydrate_state_with_memory,
    remember,
)

# ── Adversarial Auditor ───────────────────────────────────
try:
    from adversarial_auditor import AdversarialAuditor, pulse_sync_sequence
    _HAS_AUDITOR = True
except ImportError:
    _HAS_AUDITOR = False

# ── MQTT (graceful degrade) ─────────────────────────────────
try:
    import paho.mqtt.client as mqtt
    _HAS_MQTT = True
except ImportError:
    mqtt = None
    _HAS_MQTT = False

# ── Engine Integrations (graceful degrade) ───────────────────
try:
    from creation_engine.media_director import MediaDirectorAgent
    _HAS_DIRECTOR = True
except ImportError:
    _HAS_DIRECTOR = False

try:
    from creation_engine.llm_client import log
except ImportError:
    def log(tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}] {msg}")


# ═══════════════════════════════════════════════════════════════
#  UNIVERSAL AGENT BRAIN
# ═══════════════════════════════════════════════════════════════

class UniversalAgentBrain:
    """Orchestrates parallel synthesis across Code, Media, 3D,
    Business Ops, and IoT hardware nodes."""

    def __init__(self, project_name: str, user_id: str = "Donovan"):
        self.project_name = project_name
        self.user_id = user_id
        self.start_time = time.time()
        self.build_log: List[Dict[str, Any]] = []

        # ── Config from env ──────────────────────────────────
        self.slack_webhook = os.getenv("SLACK_WEBHOOK")
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.output_dir = os.path.join("output", project_name)
        os.makedirs(self.output_dir, exist_ok=True)

        # ── Sub-agents (lazy) ────────────────────────────────
        self._director = None

        log("BRAIN", f"═══ Universal Agent Brain ═══")
        log("BRAIN", f"  Project:  {project_name}")
        log("BRAIN", f"  User:     {user_id}")
        log("BRAIN", f"  Slack:    {'READY' if self.slack_webhook else 'NOT SET'}")
        log("BRAIN", f"  MQTT:     {self.mqtt_broker}:{self.mqtt_port} ({'AVAILABLE' if _HAS_MQTT else 'NO LIBRARY'})")
        log("BRAIN", f"  Director: {'AVAILABLE' if _HAS_DIRECTOR else 'NOT LOADED'}")
        log("BRAIN", f"═════════════════════════════")

    @property
    def director(self) -> Optional[Any]:
        """Lazy-load the MediaDirectorAgent."""
        if self._director is None and _HAS_DIRECTOR:
            self._director = MediaDirectorAgent()
        return self._director

    def _log_event(self, node: str, status: str, data: Any = None):
        """Internal build telemetry log."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "node": node,
            "status": status,
            "data": data,
            "elapsed_s": round(time.time() - self.start_time, 2),
        }
        self.build_log.append(event)
        return event

    # ─────────────────────────────────────────────────────────
    #  NODE 1: SPATIAL ARCHITECT — 3D World Builder
    # ─────────────────────────────────────────────────────────

    async def spatial_architect_node(self, prompt: str) -> Dict[str, Any]:
        """Generate glTF-compatible 3D environment assets.

        Generates a world manifest describing the 3D scene, camera
        positions, lighting, and asset references. When a 3D API
        (Meshy/Luma Genie) is available, it triggers actual generation.

        Args:
            prompt: Scene description for 3D generation.

        Returns:
            dict with manifest path, asset list, and status.
        """
        log("SPATIAL", f"🏗️  Drafting 3D environment: {prompt[:60]}...")

        # Build the world manifest (scene graph)
        assets_dir = os.path.join(self.output_dir, "spatial")
        os.makedirs(assets_dir, exist_ok=True)

        world_manifest = {
            "version": "1.0",
            "format": "glTF-2.0",
            "scene": {
                "name": f"{self.project_name}_world",
                "prompt": prompt,
                "generated_at": datetime.now().isoformat(),
            },
            "environment": {
                "skybox": "procedural_gradient",
                "ambient_light": {"color": [0.15, 0.12, 0.2], "intensity": 0.3},
                "directional_light": {
                    "direction": [-0.5, -1.0, -0.3],
                    "color": [1.0, 0.95, 0.9],
                    "intensity": 1.2,
                    "cast_shadows": True,
                },
            },
            "camera": {
                "type": "perspective",
                "fov": 60,
                "position": [0, 2.5, 5],
                "target": [0, 1, 0],
            },
            "assets": [
                {
                    "id": "ground_plane",
                    "type": "primitive",
                    "geometry": "plane",
                    "scale": [20, 1, 20],
                    "material": {"type": "pbr", "roughness": 0.8, "metallic": 0.1},
                },
                {
                    "id": "studio_environment",
                    "type": "generated",
                    "prompt": prompt,
                    "format": "glb",
                    "path": "spatial/studio_env.glb",
                    "status": "pending_generation",
                },
            ],
            "post_processing": {
                "bloom": True,
                "ambient_occlusion": True,
                "tone_mapping": "ACES",
            },
        }

        manifest_path = os.path.join(assets_dir, "world_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(world_manifest, f, indent=2)

        log("SPATIAL", f"  ✓ World manifest written: {manifest_path}")
        log("SPATIAL", f"  ✓ Scene: {world_manifest['scene']['name']}")
        log("SPATIAL", f"  ✓ Assets: {len(world_manifest['assets'])} defined")

        self._log_event("spatial_architect", "completed", {
            "manifest": manifest_path,
            "asset_count": len(world_manifest["assets"]),
        })

        return {
            "manifest": manifest_path,
            "assets_dir": assets_dir,
            "status": "Ready",
            "scene_name": world_manifest["scene"]["name"],
        }

    # ─────────────────────────────────────────────────────────
    #  NODE 2: BUSINESS CONCIERGE — Digital COO
    # ─────────────────────────────────────────────────────────

    async def business_concierge_node(self, update: str,
                                       channel: str = "#builds",
                                       severity: str = "info") -> Dict[str, Any]:
        """Dispatch build telemetry to Slack and local log.

        Args:
            update: Human-readable status message.
            channel: Slack channel (used in message context).
            severity: "info", "warning", "error", or "success".

        Returns:
            dict with dispatch status.
        """
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅",
            "start": "🚀",
        }
        emoji = emoji_map.get(severity, "📋")

        log("BUSINESS", f"{emoji} {update}")

        result = {"dispatched": False, "logged": True, "message": update}

        # ── Slack webhook dispatch ───────────────────────────
        if self.slack_webhook:
            payload = {
                "text": f"{emoji} *[{self.project_name}]* {update}",
                "username": "Overlord Build Bot",
                "icon_emoji": ":robot_face:",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"{emoji} *{update}*\n"
                                f"_Project:_ `{self.project_name}` | "
                                f"_User:_ {self.user_id} | "
                                f"_Time:_ {datetime.now().strftime('%H:%M:%S')}"
                            ),
                        },
                    }
                ],
            }

            try:
                r = requests.post(self.slack_webhook, json=payload, timeout=10)
                if r.status_code == 200:
                    log("BUSINESS", "  ✓ Slack notification sent")
                    result["dispatched"] = True
                else:
                    log("BUSINESS", f"  ⚠ Slack returned {r.status_code}")
            except requests.exceptions.RequestException as e:
                log("BUSINESS", f"  ⚠ Slack dispatch failed: {e}")
        else:
            log("BUSINESS", "  · Slack not configured (set SLACK_WEBHOOK)")

        self._log_event("business_concierge", severity, update)
        return result

    # ─────────────────────────────────────────────────────────
    #  NODE 3: IOT CONTROLLER — Hardware Link
    # ─────────────────────────────────────────────────────────

    async def iot_controller_node(self, action: str,
                                    topic: str = "studio/state",
                                    payload_data: Optional[dict] = None) -> Dict[str, Any]:
        """Publish MQTT messages to control studio hardware.

        Supports actions like "rendering_start", "build_complete",
        "ambient_warm", "ambient_cool", "alert".

        Args:
            action: Action name to publish.
            topic: MQTT topic (default: "studio/state").
            payload_data: Optional extra data to include.

        Returns:
            dict with publish status.
        """
        log("IOT", f"⚡ Hardware action: {action}")

        message = json.dumps({
            "action": action,
            "project": self.project_name,
            "timestamp": datetime.now().isoformat(),
            "user": self.user_id,
            **(payload_data or {}),
        })

        result = {"published": False, "action": action, "topic": topic}

        if not _HAS_MQTT:
            log("IOT", "  · paho-mqtt not installed — skipping hardware sync")
            self._log_event("iot_controller", "skipped", action)
            return result

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.connect(self.mqtt_broker, self.mqtt_port, keepalive=10)
            info = client.publish(topic, message, qos=1)
            info.wait_for_publish(timeout=5)
            client.disconnect()

            log("IOT", f"  ✓ Published to {topic}: {action}")
            result["published"] = True
            self._log_event("iot_controller", "published", {
                "topic": topic, "action": action,
            })
        except Exception as e:
            log("IOT", f"  ⚠ MQTT publish failed: {e}")
            log("IOT", f"    Broker: {self.mqtt_broker}:{self.mqtt_port}")
            self._log_event("iot_controller", "failed", str(e))

        return result

    # ─────────────────────────────────────────────────────────
    #  EXISTING NODE BRIDGES (state-aware)
    # ─────────────────────────────────────────────────────────

    async def engineer_agent(self, state: AgentState) -> AgentState:
        """Bridge to NexusEngine for code generation."""
        prompt = state["prompt"]
        log("ENGINEER", f"Code synthesis requested: {prompt[:60]}...")
        push_event(state, "engineer", "deferred", prompt)
        return state

    async def media_director_agent(self, state: AgentState) -> AgentState:
        """Bridge to MediaDirectorAgent for video/image synthesis."""
        prompt = state["prompt"]
        log("MEDIA", f"Media synthesis requested: {prompt[:60]}...")

        if self.director:
            result = self.director.generate_via_kie(
                prompt, model="veo-3.1", aspect_ratio="16:9"
            )
            if result.get("success"):
                state["assets"].append(str(result.get("task_id", "")))
                push_event(state, "media_director", "submitted", result)
                return state

            gen_id = await self.director.generate_cinematic_asset(prompt)
            if gen_id:
                state["assets"].append(gen_id)
                push_event(state, "media_director", "submitted", {"gen_id": gen_id})
                return state

        push_event(state, "media_director", "unavailable", None)
        return state

    async def spatial_architect_node_stateful(self, state: AgentState) -> AgentState:
        """Generate glTF manifest and write it into the shared state."""
        prompt = state["prompt"]
        result = await self.spatial_architect_node(prompt)
        state["spatial_manifest"] = result
        state["assets"].append(result.get("manifest", ""))
        push_event(state, "spatial_architect", "completed", result)
        return state

    # ─────────────────────────────────────────────────────────
    #  UNIVERSAL BUILD LOOP (state-driven)
    # ─────────────────────────────────────────────────────────

    async def execute_universal_build(self, prompt: str) -> AgentState:
        """Execute a full parallel build across all nodes.

        The AgentState flows through every node as shared memory:

          1. Create initial state
          2. Hydrate with Mem0 memories from past builds
          3. IoT: Signal "rendering_start"
          4. Parallel: Engineer + Media + Spatial
          5. Business: Report completion
          6. IoT: Signal "build_complete"
          7. Save state snapshot + remember build

        Args:
            prompt: Build directive / scene description.

        Returns:
            The final AgentState containing all node outputs.
        """
        log("BRAIN", f"")
        log("BRAIN", f"=== UNIVERSAL BUILD: {self.project_name} ===")
        log("BRAIN", f"  Prompt: {prompt[:70]}...")
        log("BRAIN", f"")

        self.start_time = time.time()

        # Phase 1: Initialize shared state
        state = create_initial_state(self.project_name, prompt, self.user_id)
        state["status"] = "building"
        log("BRAIN", f"  State initialized ({len(state)} fields)")

        # Phase 2: Hydrate with memories from past builds
        state = hydrate_state_with_memory(state)
        if state["memory_context"]:
            log("BRAIN", f"  Recalled {len(state['memory_context'])} memories")

        # Phase 3: IoT — signal rendering start
        await self.iot_controller_node("rendering_start", payload_data={
            "prompt": prompt[:100],
            "phase": "init",
        })
        push_event(state, "iot", "rendering_start")

        # Phase 4: Business — announce build start
        await self.business_concierge_node(
            f"Build Started: {self.project_name}",
            severity="start"
        )
        push_event(state, "business", "build_started")

        # Phase 5: Parallel synthesis — all nodes read/write state
        # We pass a shared state reference; each node mutates it
        tasks = [
            self.engineer_agent(state),
            self.media_director_agent(state),
            self.spatial_architect_node_stateful(state),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                node_names = ["engineer", "media_director", "spatial_architect"]
                push_event(state, node_names[i], "error", str(r))
                log("BRAIN", f"  Node {node_names[i]} failed: {r}")

        # Phase 5b: Adversarial Audit — red-team all generated code
        if _HAS_AUDITOR and state.get("code"):
            auditor = AdversarialAuditor(project_root=self.output_dir)
            aggregate_report = {"files": [], "verdict": "VIBE_VERIFIED"}
            for fname, src in state["code"].items():
                report = auditor.audit_code(src, filename=fname)
                aggregate_report["files"].append(report)
                if report["verdict"] == "CRITICAL_VULN":
                    aggregate_report["verdict"] = "CRITICAL_VULN"
            state["audit_report"] = aggregate_report
            manifest = auditor.generate_safety_manifest(aggregate_report)
            state["audit_report"]["safety_manifest"] = manifest
            push_event(state, "auditor", aggregate_report["verdict"],
                       {"files_scanned": len(state["code"])})
        elif _HAS_AUDITOR:
            log("AUDITOR", "  No generated code to audit (engineer deferred)")
            push_event(state, "auditor", "skipped", "no code to audit")
        else:
            push_event(state, "auditor", "unavailable", "module not loaded")

        # Phase 6: Finalize
        elapsed = round(time.time() - self.start_time, 2)
        state["status"] = "done"
        push_event(state, "brain", "completed", {"elapsed_seconds": elapsed})

        await self.business_concierge_node(
            f"Build Complete: {self.project_name} ({elapsed}s)",
            severity="success"
        )

        await self.iot_controller_node("build_complete", payload_data={
            "elapsed_seconds": elapsed,
            "phase": "done",
        })

        # Phase 7: Persist — save snapshot and remember for future builds
        snapshot_path = save_state_snapshot(state, self.output_dir)
        remember(
            f"Built {self.project_name}: {prompt[:100]}. "
            f"Generated {len(state['assets'])} assets in {elapsed}s.",
            user_id=self.user_id,
        )

        log("BRAIN", f"")
        log("BRAIN", f"  ======================================")
        log("BRAIN", f"  Universal Handoff Complete")
        log("BRAIN", f"  State:   {snapshot_path}")
        log("BRAIN", f"  Assets:  {len(state['assets'])}")
        log("BRAIN", f"  Events:  {len(state['build_events'])}")
        log("BRAIN", f"  Elapsed: {elapsed}s")
        log("BRAIN", f"  ======================================")
        log("BRAIN", f"")

        return state


# ═══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    project = sys.argv[1] if len(sys.argv) > 1 else "Project_Alpha"
    prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Build a 3D Studio Engine"

    brain = UniversalAgentBrain(project)
    final_state = asyncio.run(brain.execute_universal_build(prompt))

    print(f"\nDone. Status: {final_state['status']} | Assets: {len(final_state['assets'])} | Events: {len(final_state['build_events'])}")

