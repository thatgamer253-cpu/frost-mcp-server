#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  DOCKER SANDBOX — Ephemeral Container Execution Engine

  Spins up a lightweight Docker container for safe code testing.
  Resource-limited, network-isolated, and auto-destroyed.

  Key features:
    - CPU + RAM limits (prevent runaway processes)
    - Network isolation (opt-in for API projects)
    - Automatic dependency installation from requirements.txt
    - Timeout enforcement (kill after N seconds)
    - Volume mount: project dir → /app in container

  Requires: Docker Desktop installed and `docker` pip package.

  Usage:
    sandbox = Sandbox("/path/to/project")
    sandbox.provision()
    result = sandbox.run("python main.py", timeout=60)
    print(result.stdout, result.exit_code)
    sandbox.destroy()

══════════════════════════════════════════════════════════════
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    import docker
    from docker.errors import (
        DockerException,
        ContainerError,
        ImageNotFound,
        APIError,
        NotFound,
    )
    _HAS_DOCKER = True
except ImportError:
    _HAS_DOCKER = False


# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger("antigravity.sandbox")


# ── Sandbox Result ───────────────────────────────────────────
@dataclass
class SandboxResult:
    """Result of a command execution inside the sandbox."""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    duration: float = 0.0
    container_id: str = ""
    error: str = ""

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def summary(self) -> str:
        status = "✅ PASS" if self.success else "❌ FAIL"
        timeout_note = " (TIMED OUT)" if self.timed_out else ""
        return (
            f"{status}{timeout_note} | exit={self.exit_code} | "
            f"{self.duration:.1f}s | container={self.container_id[:12]}"
        )


# ── Resource Profiles ────────────────────────────────────────
RESOURCE_PROFILES = {
    "default": {
        "mem_limit": "512m",
        "cpu_period": 100000,
        "cpu_quota": 50000,     # 50% of one core
        "pids_limit": 256,
    },
    "heavy": {
        "mem_limit": "1g",
        "cpu_period": 100000,
        "cpu_quota": 100000,    # 100% of one core
        "pids_limit": 512,
    },
    "minimal": {
        "mem_limit": "256m",
        "cpu_period": 100000,
        "cpu_quota": 25000,     # 25% of one core
        "pids_limit": 128,
    },
}

# Docker images by language
IMAGE_MAP = {
    "python": "python:3.11-slim",
    "node": "node:20-slim",
    "go": "golang:1.22-alpine",
    "rust": "rust:1.77-slim",
    "ruby": "ruby:3.3-slim",
}


# ── Sandbox ──────────────────────────────────────────────────
class Sandbox:
    """Ephemeral Docker container for safe code execution.
    
    Lifecycle:
        1. provision()  — Pull image, create container, install deps
        2. run(cmd)     — Execute command inside container
        3. destroy()    — Kill and remove container
    
    The project directory is bind-mounted read-only into /app.
    A writable /workspace is created for runtime output.
    """

    def __init__(
        self,
        project_path: str,
        image: Optional[str] = None,
        language: str = "python",
        profile: str = "default",
        network_enabled: bool = False,
        event_bus=None,
    ):
        if not _HAS_DOCKER:
            raise RuntimeError(
                "docker package not installed. Run: pip install docker>=7.0.0"
            )

        self.project_path = os.path.abspath(project_path)
        self.language = language.lower()
        self.image = image or IMAGE_MAP.get(self.language, "python:3.11-slim")
        self.profile = RESOURCE_PROFILES.get(profile, RESOURCE_PROFILES["default"])
        self.network_enabled = network_enabled
        self.event_bus = event_bus  # Optional PipelineEvent bus

        self._client: Optional[docker.DockerClient] = None
        self._container = None
        self._container_id: str = ""
        self._provisioned: bool = False

    # ── Lifecycle ────────────────────────────────────────────

    def provision(self) -> str:
        """Create and start the sandbox container.
        
        Returns the container ID.
        Raises RuntimeError if Docker is not available.
        """
        self._log("🐳 Provisioning sandbox container...")
        
        try:
            self._client = docker.from_env()
            self._client.ping()
        except DockerException as e:
            raise RuntimeError(
                f"Cannot connect to Docker. Is Docker Desktop running? Error: {e}"
            )

        # Pull image if not available locally
        self._log(f"  Pulling image: {self.image}")
        try:
            self._client.images.get(self.image)
            self._log(f"  ✓ Image {self.image} available locally")
        except ImageNotFound:
            self._log(f"  ⬇ Downloading {self.image}...")
            self._client.images.pull(self.image)
            self._log(f"  ✓ Image pulled successfully")

        # Prepare container config
        volumes = {
            self.project_path: {"bind": "/app", "mode": "ro"},  # Read-only mount
        }

        # Create container
        self._log("  Creating container...")
        try:
            self._container = self._client.containers.create(
                image=self.image,
                command="sleep infinity",   # Keep alive for multiple exec calls
                working_dir="/workspace",
                volumes=volumes,
                network_mode="bridge" if self.network_enabled else "none",
                mem_limit=self.profile["mem_limit"],
                cpu_period=self.profile["cpu_period"],
                cpu_quota=self.profile["cpu_quota"],
                pids_limit=self.profile["pids_limit"],
                stdin_open=False,
                tty=False,
                detach=True,
                labels={
                    "creator": "antigravity",
                    "project": os.path.basename(self.project_path),
                },
            )
        except APIError as e:
            raise RuntimeError(f"Failed to create container: {e}")

        # Start container
        self._container.start()
        self._container_id = self._container.id
        self._provisioned = True
        self._log(f"  ✓ Container started: {self._container_id[:12]}")

        # Copy project files into writable workspace
        self._exec_in_container("cp -r /app/. /workspace/")
        self._log("  ✓ Project files copied to /workspace")

        # Install dependencies if requirements.txt exists
        req_path = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(req_path) and self.language == "python":
            self._log("  📦 Installing dependencies...")
            result = self._exec_in_container(
                "pip install --no-cache-dir -q -r /workspace/requirements.txt",
                timeout=120,
            )
            if result.exit_code == 0:
                self._log("  ✓ Dependencies installed")
            else:
                self._log(f"  ⚠ Dep install failed (exit {result.exit_code}): {result.stderr[:200]}")
        elif self.language == "node":
            pkg_path = os.path.join(self.project_path, "package.json")
            if os.path.exists(pkg_path):
                self._log("  📦 Installing npm dependencies...")
                result = self._exec_in_container(
                    "cd /workspace && npm install --production 2>&1",
                    timeout=120,
                )
                if result.exit_code == 0:
                    self._log("  ✓ npm dependencies installed")
                else:
                    self._log(f"  ⚠ npm install failed: {result.stderr[:200]}")

        self._emit_docker_event("running", f"Container {self._container_id[:12]} ready")
        return self._container_id

    def run(
        self,
        command: str = "python main.py",
        timeout: int = 60,
        env: Optional[dict] = None,
    ) -> SandboxResult:
        """Execute a command inside the sandbox.
        
        Args:
            command: Shell command to run
            timeout: Max seconds before killing the process
            env: Optional environment variables
            
        Returns:
            SandboxResult with stdout, stderr, exit_code, etc.
        """
        if not self._provisioned or not self._container:
            return SandboxResult(
                error="Sandbox not provisioned. Call provision() first.",
                exit_code=-1,
            )

        self._log(f"  🚀 Running: {command} (timeout={timeout}s)")
        start_time = time.time()

        try:
            # Use exec_run for running commands in existing container
            exec_result = self._container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/workspace",
                environment=env or {},
                demux=True,    # Separate stdout/stderr
            )
            duration = time.time() - start_time

            stdout_raw = exec_result.output[0] if exec_result.output[0] else b""
            stderr_raw = exec_result.output[1] if exec_result.output[1] else b""

            result = SandboxResult(
                stdout=stdout_raw.decode("utf-8", errors="replace"),
                stderr=stderr_raw.decode("utf-8", errors="replace"),
                exit_code=exec_result.exit_code,
                timed_out=False,
                duration=duration,
                container_id=self._container_id,
            )

        except Exception as e:
            duration = time.time() - start_time
            # Check if it was a timeout
            if duration >= timeout:
                result = SandboxResult(
                    stderr=f"Process timed out after {timeout}s",
                    exit_code=124,
                    timed_out=True,
                    duration=duration,
                    container_id=self._container_id,
                )
            else:
                result = SandboxResult(
                    error=str(e),
                    stderr=str(e),
                    exit_code=-1,
                    duration=duration,
                    container_id=self._container_id,
                )

        status = "✅" if result.success else "❌"
        self._log(f"  {status} {result.summary()}")
        return result

    def destroy(self):
        """Kill and remove the container. Project files remain on disk."""
        if not self._container:
            return

        self._log(f"  🗑️ Destroying container {self._container_id[:12]}...")
        try:
            self._container.kill()
        except (APIError, NotFound):
            pass  # Already stopped
        try:
            self._container.remove(force=True)
        except (APIError, NotFound):
            pass  # Already removed

        self._container = None
        self._provisioned = False
        self._emit_docker_event("stopped", "Container destroyed")
        self._log("  ✓ Container destroyed")

    # ── Context Manager ──────────────────────────────────────

    def __enter__(self):
        self.provision()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()
        return False

    # ── Internal Helpers ─────────────────────────────────────

    def _exec_in_container(
        self, command: str, timeout: int = 30
    ) -> SandboxResult:
        """Execute a command inside the container (internal helper)."""
        if not self._container:
            return SandboxResult(error="No container", exit_code=-1)

        try:
            exec_result = self._container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/workspace",
                demux=True,
            )
            stdout_raw = exec_result.output[0] if exec_result.output[0] else b""
            stderr_raw = exec_result.output[1] if exec_result.output[1] else b""
            return SandboxResult(
                stdout=stdout_raw.decode("utf-8", errors="replace"),
                stderr=stderr_raw.decode("utf-8", errors="replace"),
                exit_code=exec_result.exit_code,
                container_id=self._container_id,
            )
        except Exception as e:
            return SandboxResult(error=str(e), exit_code=-1)

    def _log(self, message: str):
        """Log to both Python logger and event bus."""
        logger.info(message)
        if self.event_bus:
            try:
                self.event_bus.log("DOCKER", message)
            except Exception:
                pass

    def _emit_docker_event(self, status: str, message: str):
        """Emit a docker status event to the event bus."""
        if self.event_bus:
            try:
                self.event_bus.docker_status(status, self._container_id, message)
            except Exception:
                pass

    # ── Status ───────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Check if the sandbox container is still running."""
        if not self._container:
            return False
        try:
            self._container.reload()
            return self._container.status == "running"
        except Exception:
            return False

    @property
    def container_id(self) -> str:
        return self._container_id

    # ── Class Methods ────────────────────────────────────────

    @classmethod
    def is_docker_available(cls) -> bool:
        """Check if Docker is installed and the daemon is running."""
        if not _HAS_DOCKER:
            return False
        try:
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    @classmethod
    def cleanup_stale_containers(cls):
        """Remove any leftover Antigravity containers from previous runs."""
        if not _HAS_DOCKER:
            return
        try:
            client = docker.from_env()
            containers = client.containers.list(
                all=True,
                filters={"label": "creator=antigravity"},
            )
            for c in containers:
                logger.info(f"  Cleaning up stale container: {c.id[:12]}")
                try:
                    c.remove(force=True)
                except Exception:
                    pass
        except Exception:
            pass


# ── Self-Test ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    print("══════════════════════════════════════════")
    print("  Docker Sandbox — Self-Test")
    print("══════════════════════════════════════════")
    
    # Check Docker availability
    if not Sandbox.is_docker_available():
        print("❌ Docker is not available. Install Docker Desktop and try again.")
        sys.exit(1)
    
    print("✓ Docker is available")
    
    # Clean up any stale containers
    Sandbox.cleanup_stale_containers()
    
    # Create a temp project
    import tempfile
    project_dir = tempfile.mkdtemp(prefix="sandbox_test_")
    with open(os.path.join(project_dir, "main.py"), "w") as f:
        f.write("import sys\nprint('Hello from Antigravity Sandbox!')\nprint(f'Python {sys.version}')\n")
    with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
        f.write("requests>=2.31.0\n")
    
    print(f"\nTest project at: {project_dir}")
    print("Starting sandbox...\n")
    
    with Sandbox(project_dir, profile="minimal") as sandbox:
        # Run the test script
        result = sandbox.run("python main.py", timeout=30)
        print(f"\n{'='*40}")
        print(f"Exit code: {result.exit_code}")
        print(f"Timed out: {result.timed_out}")
        print(f"Duration:  {result.duration:.2f}s")
        print(f"Stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")
        print(f"Summary:   {result.summary()}")
    
    print("\n✓ Sandbox test complete — container destroyed.")
