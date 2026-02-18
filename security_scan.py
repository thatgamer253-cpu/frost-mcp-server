
import os
import sys
import subprocess
import json
from datetime import datetime

# Windows-specific: suppress console windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=CREATE_NO_WINDOW)
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return str(e), 1

def log(msg, color="white"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {msg}")
    except UnicodeEncodeError:
        # Fallback for Windows consoles that don't support emojis
        msg = msg.encode('ascii', 'ignore').decode('ascii')
        print(f"[{timestamp}] {msg}")

def audit_engine(target_dir="."):
    log("🛡️  Initiating Creation Engine Security Self-Audit...", "cyan")
    
    # 1. BANDIT (SAST) - Scanning Codebase
    log("Running BANDIT (Static Application Security Testing)...")
    # Exclude venv, tests, and build artifacts
    cmd = f"{sys.executable} -m bandit -r {target_dir} -x venv,tests,build,dist,.git -f json"
    output, code = run_command(cmd)
    
    try:
        report = json.loads(output)
        results = report.get('results', [])
        high_sev = [r for r in results if r['issue_severity'] == 'HIGH']
        
        if high_sev:
            log(f"❌ BANDIT: Found {len(high_sev)} HIGH severity issues!", "red")
            for issue in high_sev:
                log(f"  - {issue['filename']}:{issue['line_number']} >> {issue['issue_text']}")
        else:
            log("✅ BANDIT: No High Severity issues found in engine code.", "green")
            
    except json.JSONDecodeError:
        log("⚠️ BANDIT: Could not parse report. Raw output:", "yellow")
        print(output[:500])

    # 2. SAFETY (SCA) - Scanning Dependencies
    log("Running SAFETY (Software Composition Analysis)...")
    cmd = f"{sys.executable} -m safety check --json"
    output, code = run_command(cmd)
    
    try:
        # Safety might return non-JSON if no issues or error, handle carefully
        if output.strip().startswith('{') or output.strip().startswith('['):
            vulns = json.loads(output)
            # Safety 2.x returns a dictionary with 'vulnerabilities' key
            if isinstance(vulns, dict):
                 issues = vulns.get('vulnerabilities', [])
            else:
                 issues = vulns # Safety 1.x style
            
            if issues:
                log(f"❌ SAFETY: Found {len(issues)} vulnerable packages!", "red")
                for v in issues:
                    pkg = v.get('package_name', 'unknown')
                    ver = v.get('vulnerable_spec', 'unknown')
                    log(f"  - {pkg} ({ver})")
            else:
                log("✅ SAFETY: No known vulnerabilities in dependencies.", "green")
        else:
             # If it's just text input like "No vulnerabilities found"
             if "No known security vulnerabilities" in output:
                  log("✅ SAFETY: No known vulnerabilities in dependencies.", "green")
             else:
                  log(f"ℹ️ SAFETY Output: {output.strip()[:200]}")

    except Exception as e:
        log(f"⚠️ SAFETY: Scan failed or unparseable: {e}", "yellow")

    log("🏁 Security Audit Complete.")

if __name__ == "__main__":
    audit_engine()
