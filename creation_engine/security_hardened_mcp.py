"""
Creation Engine — Zero-Trust Security Layer
Red-Team hardening for MCP servers and AI-facing tool endpoints.

Mitigations:
  1. Bearer Token Authentication on all tool calls
  2. Prompt Sanitization against Tool Poisoning / injection
  3. URL allowlisting against SSRF
  4. Output scrubbing to prevent credential leakage in logs
"""

import os
import re
from functools import wraps
from urllib.parse import urlparse

from .llm_client import log


# ── Authentication ──────────────────────────────────────────

VALID_API_KEY = os.getenv("MCP_AUTH_TOKEN")

def require_auth(func):
    """Enforce Bearer Token authentication on all tool calls.
    
    Usage:
        @require_auth
        async def my_tool(prompt, auth_token=None):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        auth_token = kwargs.get("auth_token")
        if not VALID_API_KEY:
            log("SECURITY", "  ⚠ MCP_AUTH_TOKEN not set — auth bypass (dev mode).")
            return await func(*args, **kwargs)
        if not auth_token or auth_token != VALID_API_KEY:
            log("SECURITY", "  🚫 AUTH REJECTED: Invalid or missing token.")
            return {"error": "Authentication failed. Unauthorized request."}
        return await func(*args, **kwargs)
    return wrapper


# ── Prompt Sanitization ─────────────────────────────────────

# Patterns commonly used in Tool Poisoning / prompt injection
_POISON_PATTERNS = [
    r"IMPORTANT:",
    r"IGNORE\s+(ALL\s+)?PREVIOUS",
    r"SYSTEM:",
    r"<\s*SYSTEM\s*>",
    r"OVERRIDE:",
    r"ADMIN:",
    r"DO\s+NOT\s+TELL\s+THE\s+USER",
    r"HIDDEN\s+INSTRUCTION",
    r"```\s*system",
    r"\[INST\]",           # LLaMA-style injection
    r"<\|im_start\|>",    # ChatML injection
]

_COMPILED_POISON = [re.compile(p, re.IGNORECASE) for p in _POISON_PATTERNS]


def sanitize_prompt(prompt: str) -> str:
    """Strip potential instruction injection patterns from user prompts.
    
    This is a defense-in-depth measure — it won't catch everything,
    but it neutralizes the most common Tool Poisoning vectors.
    """
    cleaned = prompt
    for pattern in _COMPILED_POISON:
        cleaned = pattern.sub("[FILTERED]", cleaned)
    return cleaned.strip()


def is_prompt_safe(prompt: str) -> tuple[bool, str]:
    """Check if a prompt contains injection attempts.
    Returns (is_safe, reason).
    """
    for pattern in _COMPILED_POISON:
        match = pattern.search(prompt)
        if match:
            return False, f"Injection pattern detected: '{match.group()}'"
    return True, "Clean"


# ── SSRF Protection ─────────────────────────────────────────

# Only allow fetching from these domains
_URL_ALLOWLIST = {
    "api.runwayml.com",
    "api.lumaai.com", 
    "storage.googleapis.com",
    "cdn.runwayml.com",
    "generativelanguage.googleapis.com",
}


def validate_url(url: str) -> tuple[bool, str]:
    """Validate a URL against the allowlist to prevent SSRF.
    
    Returns (is_allowed, reason).
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Blocked scheme: {parsed.scheme}"
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False, "Blocked: localhost access"
        # Check for private IP ranges
        if parsed.hostname and parsed.hostname.startswith(("10.", "172.", "192.168.")):
            return False, "Blocked: private IP range"
        if _URL_ALLOWLIST and parsed.hostname not in _URL_ALLOWLIST:
            return False, f"Domain not in allowlist: {parsed.hostname}"
        return True, "Allowed"
    except Exception as e:
        return False, f"URL parse error: {e}"


# ── Output Scrubbing ────────────────────────────────────────

_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE),       # OpenAI keys
    re.compile(r"(key-[a-zA-Z0-9]{20,})", re.IGNORECASE),       # Luma/Runway keys
    re.compile(r"(AIza[a-zA-Z0-9_-]{35})", re.IGNORECASE),      # Google API keys
    re.compile(r"(ghp_[a-zA-Z0-9]{36})", re.IGNORECASE),        # GitHub PATs
    re.compile(r"(Bearer\s+[a-zA-Z0-9._-]{20,})", re.IGNORECASE),
]


def scrub_output(text: str) -> str:
    """Remove potential secrets from log output before display."""
    scrubbed = text
    for pattern in _SECRET_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed
