#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  BUILD SIGNER — Cryptographic Provenance for Overlord Builds
  
  Creates HMAC-SHA256 signatures for every build output,
  providing tamper-evident proof of build integrity.
  
  Uses symmetric HMAC (zero system deps, no GPG needed).
  Signing key auto-generated on first run, stored locally.
═══════════════════════════════════════════════════════════════
"""

import os
import json
import hmac
import hashlib
import secrets
import datetime
from typing import Dict, Any, Optional


# ── Logging ──────────────────────────────────────────────────
try:
    from creation_engine.llm_client import log
except ImportError:
    def log(tag: str, msg: str):
        print(f"[{tag}] {msg}")


# ═══════════════════════════════════════════════════════════════
#  SIGNING KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════════

_DEFAULT_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "memory", ".signing_key"
)


def _load_or_create_key(key_path: str = _DEFAULT_KEY_PATH) -> bytes:
    """
    Load the local signing key, or generate one on first run.
    
    Key is a 256-bit random secret stored in plaintext.
    This is NOT meant to replace PKI — it's a local integrity seal.
    """
    os.makedirs(os.path.dirname(key_path), exist_ok=True)

    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read().strip()
        if len(key) >= 32:
            return key

    # Generate a fresh 256-bit key
    key = secrets.token_bytes(32)
    with open(key_path, "wb") as f:
        f.write(key)
    log("SIGNER", "  🔑 New signing key generated")
    return key


# ═══════════════════════════════════════════════════════════════
#  FILE HASHING
# ═══════════════════════════════════════════════════════════════

# Extensions worth signing (skip binaries, caches, etc.)
_SIGNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".md", ".txt", ".sh", ".bat", ".ps1",
    ".sql", ".graphql", ".proto",
}


def _hash_file(filepath: str) -> str:
    """SHA-256 hash of a single file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_project(project_dir: str) -> Dict[str, str]:
    """
    Walk a project directory and compute SHA-256 for each source file.
    
    Returns:
        Dict mapping relative paths to their SHA-256 hex digests.
    """
    file_hashes = {}

    for root, dirs, files in os.walk(project_dir):
        # Skip hidden dirs, caches, venvs
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"__pycache__", "node_modules", "venv", ".venv", "dist", "build"}
        ]

        for filename in sorted(files):
            # Skip the signature file itself (it doesn't exist at sign time)
            if filename == "BUILD_SIGNATURE.json":
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in _SIGNABLE_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, project_dir).replace("\\", "/")

            try:
                file_hashes[rel_path] = _hash_file(full_path)
            except (OSError, PermissionError):
                continue

    return file_hashes


# ═══════════════════════════════════════════════════════════════
#  BUILD SIGNING
# ═══════════════════════════════════════════════════════════════

def sign_build(
    project_dir: str,
    signer_id: str = "Donovan",
    key_path: str = _DEFAULT_KEY_PATH,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Sign an entire build output with HMAC-SHA256.
    
    Args:
        project_dir: Root directory of the built project.
        signer_id: Human identifier for the signer.
        key_path: Path to the signing key file.
        extra_metadata: Optional dict merged into the signature.
    
    Returns:
        The complete signature report dict (also written to disk).
    """
    key = _load_or_create_key(key_path)

    # 1. Hash all source files
    file_hashes = hash_project(project_dir)
    if not file_hashes:
        log("SIGNER", "  ⚠ No signable files found in project")
        return {"status": "SKIPPED", "reason": "no_signable_files"}

    # 2. Compute aggregate hash (deterministic: sorted paths)
    aggregate = hashlib.sha256()
    for path in sorted(file_hashes.keys()):
        aggregate.update(f"{path}:{file_hashes[path]}".encode("utf-8"))
    aggregate_hash = aggregate.hexdigest()

    # 3. HMAC-SHA256 signature over the aggregate
    signature = hmac.new(key, aggregate_hash.encode("utf-8"), hashlib.sha256).hexdigest()

    # 4. Build the signature report
    report = {
        "schema_version": "1.0",
        "signer": signer_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "algorithm": "HMAC-SHA256",
        "files_signed": len(file_hashes),
        "aggregate_hash": aggregate_hash,
        "signature": signature,
        "file_hashes": file_hashes,
    }

    if extra_metadata:
        report["metadata"] = extra_metadata

    # 5. Write to disk
    sig_path = os.path.join(project_dir, "BUILD_SIGNATURE.json")
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log("SIGNER", f"  ✅ Build signed: {len(file_hashes)} file(s), HMAC={signature[:16]}...")
    return report


def verify_build(
    project_dir: str,
    key_path: str = _DEFAULT_KEY_PATH,
) -> Dict[str, Any]:
    """
    Verify a signed build by recomputing hashes and checking the HMAC.
    
    Returns:
        {"valid": True/False, "details": ...}
    """
    sig_path = os.path.join(project_dir, "BUILD_SIGNATURE.json")
    if not os.path.exists(sig_path):
        return {"valid": False, "reason": "no_signature_file"}

    with open(sig_path, "r", encoding="utf-8") as f:
        stored = json.load(f)

    key = _load_or_create_key(key_path)

    # Recompute file hashes
    current_hashes = hash_project(project_dir)

    # Recompute aggregate
    aggregate = hashlib.sha256()
    for path in sorted(current_hashes.keys()):
        aggregate.update(f"{path}:{current_hashes[path]}".encode("utf-8"))
    current_aggregate = aggregate.hexdigest()

    # Recompute HMAC
    current_sig = hmac.new(key, current_aggregate.encode("utf-8"), hashlib.sha256).hexdigest()

    # Compare
    stored_sig = stored.get("signature", "")
    is_valid = hmac.compare_digest(current_sig, stored_sig)

    # Find tampered files
    tampered = []
    stored_hashes = stored.get("file_hashes", {})
    for path, current_hash in current_hashes.items():
        if stored_hashes.get(path) != current_hash:
            tampered.append(path)

    return {
        "valid": is_valid,
        "files_checked": len(current_hashes),
        "tampered_files": tampered,
        "aggregate_match": current_aggregate == stored.get("aggregate_hash"),
    }


# ═══════════════════════════════════════════════════════════════
#  CLI VERIFICATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Sign:   python code_signer.py sign <project_dir>")
        print("  Verify: python code_signer.py verify <project_dir>")
        sys.exit(1)

    action = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "."

    if action == "sign":
        result = sign_build(target)
        print(json.dumps(result, indent=2))
    elif action == "verify":
        result = verify_build(target)
        status = "✅ VALID" if result["valid"] else "❌ TAMPERED"
        print(f"\nBuild Integrity: {status}")
        if result.get("tampered_files"):
            print("Tampered files:")
            for f in result["tampered_files"]:
                print(f"  - {f}")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
