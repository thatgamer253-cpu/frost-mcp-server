#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  UNIVERSAL EXPANSION PACKAGE — core/expansions.py

  Three specialist agents that plug into the Overlord AgentState DAG:

    1. SpatialArchitectAgent — 3D asset generation (Meshy.ai / Luma Genie)
    2. BusinessConciergeAgent — Logistical ops (Slack / Trello / Airtable)
    3. IoTControllerAgent — Hardware orchestration via MQTT

  Each agent:
    - Has an async `run(state: AgentState) -> AgentState` for DAG integration
    - Gracefully degrades if SDK / service is unavailable
    - Logs with [TAG] format matching existing Creator convention
══════════════════════════════════════════════════════════════
"""

import asyncio
import json
import os
import time
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Import logging from parent ──────────────────────────────
try:
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from agent_brain import log
except ImportError:
    def log(tag, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{tag}] {msg}")


# ══════════════════════════════════════════════════════════════
#  AGENT 1: SPATIAL ARCHITECT
#  3D Asset & World Generation via Meshy.ai REST API
# ══════════════════════════════════════════════════════════════

class SpatialArchitectAgent:
    """
    Specialized in 3D asset generation for immersive projects.

    Providers (priority order):
      1. Meshy.ai — text-to-3D (glTF/FBX/OBJ/USDZ) via REST API
      2. Luma Genie — fallback 3D from existing Luma SDK

    Integrates into AgentState via:
      state["assets"]  — appends generated .glb/.obj paths
      state["blueprint"]["visuals"] — reads 3D prompts from architect

    API Docs: https://docs.meshy.ai
    """

    MESHY_BASE = "https://api.meshy.ai/openapi/v2"

    def __init__(self):
        self.api_key = os.getenv("MESHY_API_KEY", "")
        self.available = bool(self.api_key)

        if self.available:
            log("SPATIAL", "✓ Meshy.ai 3D Engine: ONLINE")
        else:
            log("SPATIAL", "⚠ MESHY_API_KEY not set — 3D generation unavailable")

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Text-to-3D ──────────────────────────────────────────

    def text_to_3d(self, prompt: str, art_style: str = "realistic",
                   topology: str = "quad",
                   target_poly_count: int = 30000) -> Optional[str]:
        """
        Submit a text-to-3D generation task to Meshy.ai.

        Args:
            prompt: Scene/object description.
            art_style: "realistic", "sculpture", "pbr", etc.
            topology: "quad" or "triangle".
            target_poly_count: Target polygon count.

        Returns:
            Task ID string, or None on failure.
        """
        if not self.available:
            log("SPATIAL", "  ✗ Cannot generate: Meshy.ai unavailable")
            return None

        try:
            log("SPATIAL", f"  📐 Submitting 3D generation: '{prompt[:60]}...'")
            resp = requests.post(
                f"{self.MESHY_BASE}/text-to-3d",
                headers=self.headers,
                json={
                    "mode": "refine",
                    "prompt": prompt,
                    "art_style": art_style,
                    "topology": topology,
                    "target_polycount": target_poly_count,
                },
                timeout=30,
            )

            if resp.status_code in (200, 201, 202):
                data = resp.json()
                task_id = data.get("result", data.get("id", ""))
                log("SPATIAL", f"  ✓ Task submitted: {task_id}")
                return task_id
            else:
                log("SPATIAL", f"  ✗ Meshy API error {resp.status_code}: {resp.text[:200]}")
                return None

        except Exception as e:
            log("SPATIAL", f"  ✗ Request failed: {e}")
            return None

    def poll_task(self, task_id: str, save_dir: str,
                  filename: str = "model.glb",
                  timeout_minutes: int = 10) -> Optional[str]:
        """
        Poll a Meshy task until completion and download the result.

        Returns:
            Path to downloaded 3D model, or None on timeout/failure.
        """
        if not self.available or not task_id:
            return None

        os.makedirs(save_dir, exist_ok=True)
        max_polls = timeout_minutes * 6  # Every 10s
        log("SPATIAL", f"  ⏳ Polling task {task_id}...")

        for i in range(max_polls):
            time.sleep(10)
            try:
                resp = requests.get(
                    f"{self.MESHY_BASE}/text-to-3d/{task_id}",
                    headers=self.headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                status = data.get("status", "")

                if status == "SUCCEEDED":
                    model_urls = data.get("model_urls", {})
                    # Prefer glb > fbx > obj
                    download_url = (
                        model_urls.get("glb")
                        or model_urls.get("fbx")
                        or model_urls.get("obj")
                    )
                    if download_url:
                        return self._download(download_url, save_dir, filename)
                    log("SPATIAL", "  ✗ Task succeeded but no model URLs found")
                    return None

                elif status in ("FAILED", "EXPIRED"):
                    log("SPATIAL", f"  ✗ Task {status}: {data.get('task_error', {}).get('message', 'Unknown')}")
                    return None

                else:
                    if i % 6 == 0:
                        progress = data.get("progress", 0)
                        log("SPATIAL", f"  ... rendering ({status}, {progress}%)...")

            except Exception as e:
                log("SPATIAL", f"  ⚠ Poll error: {e}")

        log("SPATIAL", "  ✗ 3D generation timed out")
        return None

    # ── Image-to-3D ─────────────────────────────────────────

    def image_to_3d(self, image_url: str,
                    topology: str = "quad") -> Optional[str]:
        """
        Convert a 2D image to a 3D model via Meshy.ai.

        Args:
            image_url: Public URL of the source image.
            topology: "quad" or "triangle".

        Returns:
            Task ID string, or None on failure.
        """
        if not self.available:
            return None

        try:
            log("SPATIAL", f"  📐 Image-to-3D: {image_url[:60]}...")
            resp = requests.post(
                f"{self.MESHY_BASE}/image-to-3d",
                headers=self.headers,
                json={
                    "image_url": image_url,
                    "topology": topology,
                    "enable_pbr": True,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                task_id = data.get("result", data.get("id", ""))
                log("SPATIAL", f"  ✓ Image-to-3D task: {task_id}")
                return task_id
            return None
        except Exception as e:
            log("SPATIAL", f"  ✗ Image-to-3D failed: {e}")
            return None

    # ── Full Pipeline ───────────────────────────────────────

    async def generate(self, prompt: str, save_dir: str,
                       filename: str = "model.glb") -> Optional[str]:
        """End-to-end: submit + poll + download."""
        task_id = await asyncio.to_thread(self.text_to_3d, prompt)
        if not task_id:
            return None
        return await asyncio.to_thread(self.poll_task, task_id, save_dir, filename)

    # ── DAG Integration ─────────────────────────────────────

    async def run(self, state: dict) -> dict:
        """
        AgentState DAG node.
        Reads 3D prompts from blueprint["visuals"] where filename ends in
        .glb/.obj/.fbx, generates assets, and appends to state["assets"].
        """
        blueprint = state.get("blueprint", {})
        visuals = blueprint.get("visuals", [])
        project_name = blueprint.get("project_name", "project")
        assets_dir = os.path.join("output", project_name, "assets", "models")

        # Filter for 3D-specific visuals
        spatial_tasks = [
            v for v in visuals
            if any(v.get("filename", "").endswith(ext) for ext in (".glb", ".obj", ".fbx", ".usdz"))
        ]

        if not spatial_tasks:
            log("SPATIAL", "📐 No 3D assets in blueprint — skipping")
            return state

        log("SPATIAL", f"📐 Generating {len(spatial_tasks)} 3D asset(s)...")
        os.makedirs(assets_dir, exist_ok=True)
        assets = list(state.get("assets", []))

        for task in spatial_tasks:
            prompt = task.get("prompt", "")
            filename = task.get("filename", "model.glb")

            if self.available:
                result = await self.generate(prompt, assets_dir, filename)
                if result:
                    assets.append(f"./assets/models/{filename}")
                    log("SPATIAL", f"  ✓ {filename}")
                    continue

            # Deferred manifest fallback
            manifest = {
                "status": "deferred", "type": "3d",
                "prompt": prompt, "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "instructions": "Set MESHY_API_KEY to generate"
            }
            manifest_path = os.path.join(assets_dir, f"{filename}.manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            assets.append(f"./assets/models/{filename}.manifest.json")
            log("SPATIAL", f"  ℹ Deferred: {filename}")

        state["assets"] = assets
        return state

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _download(url: str, save_dir: str, filename: str) -> str:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, filename)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        log("SPATIAL", f"  📥 Downloaded: {path}")
        return path


# ══════════════════════════════════════════════════════════════
#  AGENT 2: BUSINESS CONCIERGE
#  Logistical Ops — Slack / Trello / Airtable Dispatch
# ══════════════════════════════════════════════════════════════

class BusinessConciergeAgent:
    """
    Specialized in automated project status reporting and task management.

    Channels:
      1. Slack — Webhook-based status updates
      2. Trello — Card creation for build artifacts
      3. Airtable — Record logging for build history

    Integrates into AgentState via:
      - Reads state["blueprint"], state["audit_report"], state["final_package_path"]
      - Posts build summaries to configured channels
      - Appends dispatch receipts to state["audit_report"]["dispatches"]
    """

    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.trello_key = os.getenv("TRELLO_API_KEY", "")
        self.trello_token = os.getenv("TRELLO_TOKEN", "")
        self.trello_list_id = os.getenv("TRELLO_LIST_ID", "")
        self.airtable_token = os.getenv("AIRTABLE_PAT", "")
        self.airtable_base = os.getenv("AIRTABLE_BASE_ID", "")
        self.airtable_table = os.getenv("AIRTABLE_TABLE_NAME", "Builds")

        channels = []
        if self.slack_webhook:
            channels.append("Slack")
        if self.trello_key and self.trello_token:
            channels.append("Trello")
        if self.airtable_token and self.airtable_base:
            channels.append("Airtable")

        if channels:
            log("CONCIERGE", f"✓ Business Concierge: {', '.join(channels)} ONLINE")
        else:
            log("CONCIERGE", "⚠ No dispatch channels configured (set SLACK_WEBHOOK_URL, TRELLO_API_KEY, or AIRTABLE_PAT)")

    # ── Slack Dispatch ──────────────────────────────────────

    def post_slack(self, message: str, blocks: Optional[List[dict]] = None) -> bool:
        """Send a rich message to Slack via Incoming Webhook."""
        if not self.slack_webhook:
            return False

        try:
            payload: Dict[str, Any] = {"text": message}
            if blocks:
                payload["blocks"] = blocks

            resp = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10,
            )
            success = resp.status_code == 200
            if success:
                log("CONCIERGE", "  ✓ Slack dispatch sent")
            else:
                log("CONCIERGE", f"  ✗ Slack error {resp.status_code}: {resp.text[:100]}")
            return success

        except Exception as e:
            log("CONCIERGE", f"  ✗ Slack dispatch failed: {e}")
            return False

    def _build_slack_blocks(self, project_name: str, status: str,
                            score: Any, file_count: int,
                            cost: float) -> List[dict]:
        """Build Slack Block Kit payload for a build report."""
        emoji = "✅" if status == "APPROVED" else "⚠️"
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🏗️ Overlord Build: {project_name}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Security:*\n{emoji} {status}"},
                    {"type": "mrkdwn", "text": f"*Score:*\n{score}/100"},
                    {"type": "mrkdwn", "text": f"*Files:*\n{file_count}"},
                    {"type": "mrkdwn", "text": f"*Cost:*\n${cost:.4f}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Built by Overlord Factory V2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
                ]
            }
        ]

    # ── Trello Dispatch ─────────────────────────────────────

    def create_trello_card(self, name: str, description: str,
                           labels: Optional[List[str]] = None) -> Optional[str]:
        """Create a Trello card for the build artifact."""
        if not (self.trello_key and self.trello_token and self.trello_list_id):
            return None

        try:
            resp = requests.post(
                "https://api.trello.com/1/cards",
                params={
                    "key": self.trello_key,
                    "token": self.trello_token,
                    "idList": self.trello_list_id,
                    "name": name,
                    "desc": description,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                card_id = resp.json().get("id", "")
                log("CONCIERGE", f"  ✓ Trello card created: {card_id}")
                return card_id
            else:
                log("CONCIERGE", f"  ✗ Trello error {resp.status_code}")
                return None

        except Exception as e:
            log("CONCIERGE", f"  ✗ Trello dispatch failed: {e}")
            return None

    # ── Airtable Dispatch ───────────────────────────────────

    def log_to_airtable(self, record: dict) -> Optional[str]:
        """Log a build record to Airtable."""
        if not (self.airtable_token and self.airtable_base):
            return None

        try:
            resp = requests.post(
                f"https://api.airtable.com/v0/{self.airtable_base}/{self.airtable_table}",
                headers={
                    "Authorization": f"Bearer {self.airtable_token}",
                    "Content-Type": "application/json",
                },
                json={"records": [{"fields": record}]},
                timeout=10,
            )
            if resp.status_code == 200:
                rec_id = resp.json().get("records", [{}])[0].get("id", "")
                log("CONCIERGE", f"  ✓ Airtable record: {rec_id}")
                return rec_id
            else:
                log("CONCIERGE", f"  ✗ Airtable error {resp.status_code}")
                return None

        except Exception as e:
            log("CONCIERGE", f"  ✗ Airtable dispatch failed: {e}")
            return None

    # ── DAG Integration ─────────────────────────────────────

    async def run(self, state: dict) -> dict:
        """
        AgentState DAG node.
        Dispatches build status to all configured channels.
        Should be called AFTER the Bundler node.
        """
        blueprint = state.get("blueprint", {})
        audit = state.get("audit_report", {})
        code = state.get("code", {})
        project_name = blueprint.get("project_name", "project")
        status = audit.get("status", "UNKNOWN")
        score = audit.get("overall_score", "?")
        pkg_path = state.get("final_package_path", "")
        file_count = len(code)

        log("CONCIERGE", f"🏢 Dispatching build status for '{project_name}'...")

        dispatches: List[Dict[str, Any]] = []

        # Slack
        if self.slack_webhook:
            blocks = self._build_slack_blocks(project_name, status, score, file_count, 0.0)
            message = f"🏗️ *{project_name}* — Security: {status} ({score}/100) — {file_count} files"
            success = await asyncio.to_thread(self.post_slack, message, blocks)
            dispatches.append({"channel": "slack", "success": success, "ts": datetime.now().isoformat()})

        # Trello
        if self.trello_key:
            desc = (
                f"**Status:** {status}\n"
                f"**Score:** {score}/100\n"
                f"**Files:** {file_count}\n"
                f"**Path:** {pkg_path}\n"
            )
            card_id = await asyncio.to_thread(
                self.create_trello_card,
                f"🏗️ {project_name} [{status}]", desc
            )
            dispatches.append({"channel": "trello", "card_id": card_id, "ts": datetime.now().isoformat()})

        # Airtable
        if self.airtable_token:
            record = {
                "Project": project_name,
                "Status": status,
                "Score": int(score) if isinstance(score, (int, float)) else 0,
                "Files": file_count,
                "Timestamp": datetime.now().isoformat(),
            }
            rec_id = await asyncio.to_thread(self.log_to_airtable, record)
            dispatches.append({"channel": "airtable", "record_id": rec_id, "ts": datetime.now().isoformat()})

        if not dispatches:
            log("CONCIERGE", "  ℹ No channels configured — skipping dispatch")

        # Store dispatch receipts in audit report
        if "audit_report" not in state:
            state["audit_report"] = {}
        state["audit_report"]["dispatches"] = dispatches

        return state


# ══════════════════════════════════════════════════════════════
#  AGENT 3: IOT CONTROLLER
#  Hardware Orchestration via MQTT
# ══════════════════════════════════════════════════════════════

class IoTControllerAgent:
    """
    Specialized in physical-world command dispatch via MQTT.

    Capabilities:
      - Publish commands to devices (lights, displays, servos)
      - Subscribe to sensor feeds for build-environment awareness
      - Trigger physical build indicators (LED strips, notification lights)

    Integrates into AgentState via:
      - Reads state["audit_report"]["status"] to determine signal
      - Publishes build status to MQTT topics
      - Optionally triggers hardware on APPROVED/REJECTED

    Requires: pip install paho-mqtt
    """

    def __init__(self, broker: str = "", port: int = 1883,
                 topic_prefix: str = "overlord"):
        self.broker = broker or os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", str(port)))
        self.topic_prefix = topic_prefix
        self.username = os.getenv("MQTT_USERNAME", "")
        self.password = os.getenv("MQTT_PASSWORD", "")
        self.available = False
        self._client = None

        # Lazy-load paho-mqtt
        try:
            import paho.mqtt.client as mqtt
            self._mqtt = mqtt
            # paho-mqtt v2 requires CallbackAPIVersion; v1 doesn't have it
            if hasattr(mqtt, 'CallbackAPIVersion'):
                self._client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
                )
            else:
                self._client = mqtt.Client()
            if self.username:
                self._client.username_pw_set(self.username, self.password)
            self.available = True
            log("IOT", f"✓ MQTT Controller: {self.broker}:{self.port} READY")
        except ImportError:
            log("IOT", "⚠ paho-mqtt not installed — IoT control unavailable (pip install paho-mqtt)")
        except Exception as e:
            log("IOT", f"⚠ MQTT init error: {e}")

    # ── Core MQTT Operations ────────────────────────────────

    def publish(self, topic: str, payload: str, qos: int = 1) -> bool:
        """Publish a message to an MQTT topic."""
        if not self.available or not self._client:
            log("IOT", f"  ✗ Cannot publish: MQTT unavailable")
            return False

        full_topic = f"{self.topic_prefix}/{topic}"

        try:
            self._client.connect(self.broker, self.port, keepalive=10)
            result = self._client.publish(full_topic, payload, qos=qos)
            result.wait_for_publish(timeout=5)
            self._client.disconnect()

            log("IOT", f"  ✓ Published: {full_topic} → {payload[:50]}")
            return True

        except Exception as e:
            log("IOT", f"  ✗ Publish failed ({full_topic}): {e}")
            try:
                self._client.disconnect()
            except Exception:
                pass
            return False

    def command_device(self, topic: str, payload: str) -> bool:
        """Convenience: send a command to a specific device topic."""
        return self.publish(f"devices/{topic}", payload)

    # ── Build Status Signals ────────────────────────────────

    def signal_build_status(self, project_name: str, status: str,
                            score: Any = "?") -> bool:
        """
        Broadcast build status to MQTT for physical indicators.

        Example subscriptions:
          overlord/builds/status  → {"project":"X", "status":"APPROVED", "score":95}
          overlord/studio/lights  → "GREEN" / "RED"
        """
        # Structured status message
        status_payload = json.dumps({
            "project": project_name,
            "status": status,
            "score": score,
            "timestamp": datetime.now().isoformat(),
        })
        self.publish("builds/status", status_payload)

        # Physical light signal
        color = "GREEN" if status == "APPROVED" else "RED"
        self.publish("studio/lights", color)

        # Notification display
        self.publish("studio/display", f"🏗️ {project_name}: {status}")

        return True

    # ── DAG Integration ─────────────────────────────────────

    async def run(self, state: dict) -> dict:
        """
        AgentState DAG node.
        Publishes build completion signal to MQTT for physical indicators.
        Should be called AFTER the Guardian node.
        """
        blueprint = state.get("blueprint", {})
        audit = state.get("audit_report", {})
        project_name = blueprint.get("project_name", "project")
        status = audit.get("status", "UNKNOWN")
        score = audit.get("overall_score", "?")

        if not self.available:
            log("IOT", "🔌 Skipping IoT signals — MQTT unavailable")
            return state

        log("IOT", f"🔌 Broadcasting build signal for '{project_name}'...")
        await asyncio.to_thread(
            self.signal_build_status, project_name, status, score
        )

        return state


# ══════════════════════════════════════════════════════════════
#  EXPANSION REGISTRY — For dynamic DAG node discovery
# ══════════════════════════════════════════════════════════════

EXPANSION_REGISTRY = {
    "spatial_architect": {
        "class": SpatialArchitectAgent,
        "phase": "post-media",       # Runs after Media Director
        "env_keys": ["MESHY_API_KEY"],
        "description": "3D asset generation via Meshy.ai",
    },
    "business_concierge": {
        "class": BusinessConciergeAgent,
        "phase": "post-bundler",     # Runs after packaging
        "env_keys": ["SLACK_WEBHOOK_URL", "TRELLO_API_KEY", "AIRTABLE_PAT"],
        "description": "Slack / Trello / Airtable status dispatch",
    },
    "iot_controller": {
        "class": IoTControllerAgent,
        "phase": "post-guardian",    # Runs after security audit
        "env_keys": ["MQTT_BROKER"],
        "description": "MQTT hardware orchestration",
    },
}


def get_active_expansions() -> Dict[str, Any]:
    """
    Discover which expansion agents have valid credentials configured.
    Returns: {name: instantiated_agent} for all available expansions.
    """
    active = {}
    for name, spec in EXPANSION_REGISTRY.items():
        # Check if at least one env key is set
        has_creds = any(os.getenv(k) for k in spec["env_keys"])
        if has_creds:
            try:
                agent = spec["class"]()
                active[name] = agent
                log("EXPANSION", f"  ✓ {name}: {spec['description']}")
            except Exception as e:
                log("EXPANSION", f"  ✗ {name}: Init failed — {e}")
    return active


# ══════════════════════════════════════════════════════════════
#  SMOKE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═══ Universal Expansion Package — Status Check ═══\n")

    spatial = SpatialArchitectAgent()
    concierge = BusinessConciergeAgent()
    iot = IoTControllerAgent()

    print(f"\n  Spatial Architect:    {'ONLINE' if spatial.available else 'OFFLINE'}")
    print(f"  Business Concierge:  {'ONLINE' if concierge.slack_webhook else 'OFFLINE'}")
    print(f"  IoT Controller:      {'ONLINE' if iot.available else 'OFFLINE'}")

    print("\n═══ Active Expansions ═══")
    active = get_active_expansions()
    if active:
        for name, agent in active.items():
            print(f"  ✓ {name}")
    else:
        print("  (none — set env vars to activate)")

    print("\n✓ Expansion package loaded successfully.")
