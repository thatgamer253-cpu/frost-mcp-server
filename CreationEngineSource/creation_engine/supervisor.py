"""
Creation Engine — Supervisor Agent
Runs the generated child program in an isolated sandbox (Docker preferred,
local subprocess fallback). Captures errors for the fix-it loop.
"""

import os
import sys
import subprocess
import shutil

from .llm_client import log


class SupervisorResult:
    """Result of a single sandbox execution attempt."""

    def __init__(self, success: bool, stdout: str = "", stderr: str = "",
                 return_code: int = -1, error_summary: str = ""):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.error_summary = error_summary

    def __repr__(self):
        status = "✓ PASS" if self.success else "✗ FAIL"
        return f"<SupervisorResult {status} rc={self.return_code}>"


class Supervisor:
    """Runs child programs in a sandbox and captures results.
    Prefers Docker for isolation; falls back to local subprocess."""

    def __init__(self, project_path: str, run_command: str = "python main.py",
                 timeout: int = 30, use_docker: bool = True):
        self.project_path = os.path.abspath(project_path)
        self.run_command = run_command
        self.timeout = timeout
        self.use_docker = use_docker and self._check_docker()

    def _check_docker(self) -> bool:
        try:
            r = subprocess.run(["docker", "--version"], capture_output=True,
                               text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def run(self) -> SupervisorResult:
        """Execute the child program and capture results."""
        if self.use_docker:
            return self._run_docker()
        return self._run_local()

    def _run_docker(self) -> SupervisorResult:
        """Run in a disposable Docker container."""
        log("SUPERVISOR", "  🐳 Running in Docker sandbox…")

        # Determine docker base image from requirements
        docker_base = "python:3.12-slim"

        proj_unix = self.project_path.replace("\\", "/")

        # Build a one-shot container command
        cmd_parts = self.run_command.split()
        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",  # No network access for safety
            "--memory=512m",   # Memory limit
            "--cpus=1",        # CPU limit
            "-v", f"{proj_unix}:/app",
            "-w", "/app",
            docker_base,
        ]

        # If requirements.txt exists, install deps first
        req_path = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(req_path):
            setup_cmd = "pip install --no-cache-dir -r /app/requirements.txt 2>&1 && "
        else:
            setup_cmd = ""

        # Full command: install deps + run app
        full_cmd = f"{setup_cmd}{self.run_command}"
        docker_cmd += ["bash", "-c", full_cmd]

        try:
            result = subprocess.run(
                docker_cmd, capture_output=True, text=True,
                timeout=self.timeout + 60,  # Extra time for dep install
            )
            success = result.returncode == 0
            error_summary = ""
            if not success:
                error_summary = self._extract_error(result.stderr + result.stdout)

            log("SUPERVISOR", f"  {'✓' if success else '✗'} Docker exit code: {result.returncode}")
            return SupervisorResult(
                success=success,
                stdout=result.stdout[-2000:],
                stderr=result.stderr[-2000:],
                return_code=result.returncode,
                error_summary=error_summary,
            )
        except subprocess.TimeoutExpired as e:
            log("SUPERVISOR", f"  ⏱ Docker execution timed out ({self.timeout + 60}s)")
            raw_stdout = e.stdout if e.stdout is not None else b""
            raw_stderr = e.stderr if e.stderr is not None else b""
            
            stdout = raw_stdout.decode(errors="ignore") if isinstance(raw_stdout, bytes) else str(raw_stdout or "")
            stderr = raw_stderr.decode(errors="ignore") if isinstance(raw_stderr, bytes) else str(raw_stderr or "")
            
            if not stdout.strip() and not stderr.strip():
                return SupervisorResult(
                    success=False, 
                    error_summary=f"ZOMBIE HANG DETECTED: App survived {self.timeout + 60}s but produced NO output. Likely an infinite loop without I/O or sleep."
                )
            
            return SupervisorResult(
                success=False, error_summary=f"Execution timed out after {self.timeout + 60}s"
            )
        except Exception as e:
            log("SUPERVISOR", f"  ✗ Docker execution error: {e}")
            return SupervisorResult(success=False, error_summary=str(e))

    def _run_local(self) -> SupervisorResult:
        """Run locally as a subprocess."""
        log("SUPERVISOR", "  💻 Running locally (no Docker)…")

        cmd_parts = self.run_command.split()

        # Install dependencies first if requirements.txt exists
        req_path = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(req_path):
            log("SUPERVISOR", "  📦 Installing dependencies…")
            try:
                dep_result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_path, "-q"],
                    capture_output=True, text=True, timeout=120,
                    cwd=self.project_path,
                )
                if dep_result.returncode != 0:
                    log("SUPERVISOR", f"  ⚠ Dep install issues: {dep_result.stderr[:200]}")
            except Exception as e:
                log("SUPERVISOR", f"  ⚠ Dep install failed: {e}")

        try:
            # Replace 'python' with actual executable for reliability
            if cmd_parts and cmd_parts[0] in ("python", "python3"):
                cmd_parts[0] = sys.executable

            result = subprocess.run(
                cmd_parts, capture_output=True, text=True,
                timeout=self.timeout, cwd=self.project_path,
            )
            success = result.returncode == 0
            error_summary = ""
            if not success:
                error_summary = self._extract_error(result.stderr + result.stdout)

            log("SUPERVISOR", f"  {'✓' if success else '✗'} Exit code: {result.returncode}")
            return SupervisorResult(
                success=success,
                stdout=result.stdout[-2000:],
                stderr=result.stderr[-2000:],
                return_code=result.returncode,
                error_summary=error_summary,
            )
        except subprocess.TimeoutExpired as e:
            log("SUPERVISOR", f"  ⏱ Execution timed out ({self.timeout}s)")
            raw_stdout = e.stdout if e.stdout is not None else b""
            raw_stderr = e.stderr if e.stderr is not None else b""
            
            stdout = raw_stdout.decode(errors="ignore") if isinstance(raw_stdout, bytes) else str(raw_stdout or "")
            stderr = raw_stderr.decode(errors="ignore") if isinstance(raw_stderr, bytes) else str(raw_stderr or "")
            
            if not stdout.strip() and not stderr.strip():
                 return SupervisorResult(
                    success=False, 
                    error_summary=f"ZOMBIE HANG DETECTED: App survived {self.timeout}s but produced NO output. Likely an infinite loop without I/O or sleep."
                )
                
            return SupervisorResult(
                success=False, error_summary=f"Execution timed out after {self.timeout}s"
            )
        except FileNotFoundError:
            log("SUPERVISOR", f"  ✗ Command not found: {cmd_parts[0]}")
            return SupervisorResult(
                success=False, error_summary=f"Command not found: {cmd_parts[0]}"
            )
        except Exception as e:
            log("SUPERVISOR", f"  ✗ Execution error: {e}")
            return SupervisorResult(success=False, error_summary=str(e))

    def _extract_error(self, output: str) -> str:
        """Extract the most meaningful error from output."""
        if not output:
            return "No error output captured."

        lines = output.strip().split("\n")

        # Look for Python tracebacks
        error_lines = []
        in_traceback = False
        for line in lines:
            if "Traceback" in line:
                in_traceback = True
                error_lines = [line]
            elif in_traceback:
                error_lines.append(line)

        if error_lines:
            return "\n".join(error_lines[-10:])

        # Look for common error patterns
        error_patterns = ["Error:", "ERROR", "FATAL", "ModuleNotFoundError",
                          "ImportError", "SyntaxError", "Exception"]
        for line in reversed(lines):
            for pattern in error_patterns:
                if pattern in line:
                    return line.strip()

        # Fallback: last few lines
        return "\n".join(lines[-5:])

    def save_error_log(self, result: SupervisorResult, cycle: int):
        """Save detailed error log to disk."""
        log_path = os.path.join(self.project_path, f"error_cycle_{cycle}.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== RUN CYCLE {cycle} ===\n")
            f.write(f"Command: {self.run_command}\n")
            f.write(f"Return code: {result.return_code}\n")
            f.write(f"Success: {result.success}\n\n")
            f.write(f"STDOUT:\n{result.stdout}\n\n")
            f.write(f"STDERR:\n{result.stderr}\n\n")
            f.write(f"ERROR SUMMARY:\n{result.error_summary}\n")
        log("SUPERVISOR", f"  📄 Error log saved: error_cycle_{cycle}.log")
