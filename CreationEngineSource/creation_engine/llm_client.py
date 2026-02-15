"""
Creation Engine — LLM Client Infrastructure
KeyPool, provider detection, client caching, ask_llm(), CostTracker.
Supports OpenAI, Anthropic, Groq, Gemini, and OpenRouter providers.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from openai import OpenAI

try:
    import anthropic as _anthropic_sdk
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

from .config import PROVIDERS, PRICING, DEFAULT_PRICING


# ── Logging ─────────────────────────────────────────────────

_log_listeners = []

def add_log_listener(callback):
    """Register a callback(tag, message) for logs."""
    _log_listeners.append(callback)

def log(tag: str, message: str):
    """Print a timestamped, tagged log line (streamed to Electron via stdout)."""
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] [{tag}]  {message}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] [{tag}]  {message.encode('ascii', 'replace').decode('ascii')}", flush=True)
    
    # Notify listeners
    for listener in _log_listeners:
        try:
            listener(tag, message)
        except Exception:
            pass


def divider():
    log("SYSTEM", "-" * 52)


def strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return raw


# ── Multi-Key Pool ──────────────────────────────────────────

class KeyPool:
    """Round-robin API key pool with rate-limit backoff."""
    _pools = {}
    _lock = threading.Lock()

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        provider = PROVIDERS.get(provider_id, {})
        env_key = provider.get("env_key", "")

        pool_env = env_key.replace("_KEY", "_KEYS") if env_key else ""
        raw_pool = os.environ.get(pool_env, "")
        raw_single = os.environ.get(env_key, "") if env_key else ""

        if raw_pool:
            self.keys = [k.strip() for k in raw_pool.split(",") if k.strip()]
        elif raw_single:
            self.keys = [raw_single.strip()]
        else:
            self.keys = []

        self._index = 0
        self._cooldowns = {}
        self._rotations = 0
        self._key_lock = threading.Lock()

        if len(self.keys) > 1:
            label = provider.get("label", provider_id)
            log("KEYPOOL", f"  🔑 {label} pool: {len(self.keys)} keys loaded")

    @classmethod
    def get_pool(cls, provider_id: str) -> 'KeyPool':
        if provider_id not in cls._pools:
            with cls._lock:
                if provider_id not in cls._pools:
                    cls._pools[provider_id] = KeyPool(provider_id)
        return cls._pools[provider_id]

    @classmethod
    def reset_all(cls):
        with cls._lock:
            cls._pools.clear()

    def next_key(self) -> str:
        if not self.keys:
            return ""
        with self._key_lock:
            now = time.time()
            for _ in range(len(self.keys)):
                key = self.keys[self._index % len(self.keys)]
                cooldown_until = self._cooldowns.get(key, 0)
                if now >= cooldown_until:
                    self._index = (self._index + 1) % len(self.keys)
                    return key
                self._index = (self._index + 1) % len(self.keys)
            return self.keys[self._index % len(self.keys)]

    def current_key(self) -> str:
        if not self.keys:
            return ""
        idx = (self._index - 1) % len(self.keys)
        return self.keys[idx]

    def rotate(self):
        with self._key_lock:
            self._index = (self._index + 1) % max(len(self.keys), 1)
            self._rotations += 1

    def mark_limited(self, key: str, cooldown_secs: float = 60.0):
        with self._key_lock:
            self._cooldowns[key] = time.time() + cooldown_secs

    @property
    def pool_size(self) -> int:
        return len(self.keys)

    @property
    def total_rotations(self) -> int:
        return self._rotations


# ── Provider Detection & Client Factory ─────────────────────

def detect_provider(model_name: str) -> str:
    """Auto-detect provider from model name prefix."""
    model_lower = model_name.lower()
    for provider_id, info in PROVIDERS.items():
        for prefix in info["prefixes"]:
            if model_lower.startswith(prefix):
                return provider_id
    return "openai"


def get_client_for_model(model_name: str, fallback_key: str = "") -> OpenAI:
    """Create the right OpenAI client for any provider based on model name."""
    provider_id = detect_provider(model_name)
    provider = PROVIDERS[provider_id]

    pool = KeyPool.get_pool(provider_id)
    api_key = pool.next_key() or fallback_key

    if not api_key and provider_id == "openai":
        api_key = fallback_key or os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        log("WARN", f"  No API key for {provider['label']}. Set {provider['env_key']} env var.")

    kwargs = {"api_key": api_key or "none"}
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]

    return OpenAI(**kwargs)


# ── Client Cache ────────────────────────────────────────────
_client_cache = {}


def get_cached_client(model_name: str, fallback_key: str = "") -> OpenAI:
    """Get or create a cached client for the model's provider."""
    provider_id = detect_provider(model_name)
    pool = KeyPool.get_pool(provider_id)
    cache_key = f"{provider_id}:{pool._index}" if pool.keys else provider_id
    if cache_key not in _client_cache:
        stale = [k for k in _client_cache if k.startswith(provider_id)]
        for k in stale:
            del _client_cache[k]
        _client_cache[cache_key] = get_client_for_model(model_name, fallback_key)
        if pool.pool_size > 1:
            log("KEYPOOL", f"  🔌 Connected {PROVIDERS[provider_id]['label']} (key {pool._index + 1}/{pool.pool_size})")
        else:
            log("SYSTEM", f"  🔌 Connected: {PROVIDERS[provider_id]['label']}")
    return _client_cache[cache_key]


def reset_client_cache():
    """Clear client cache (used between builds)."""
    global _client_cache
    _client_cache = {}


# ── Module-Level Active Tracker ─────────────────────────────
_active_tracker = None


def set_active_tracker(tracker):
    """Set the module-level cost tracker for automatic cost recording."""
    global _active_tracker
    _active_tracker = tracker


# ── Core LLM Call ───────────────────────────────────────────

def ask_llm(client: OpenAI, model: str, system_role: str, user_content: str,
            tracker=None) -> str:
    """Send a chat completion request and return the cleaned response.
    Auto-resolves the right client for multi-provider model mixing.
    Routes Claude models through the Anthropic SDK automatically."""
    global _active_tracker

    provider_id = detect_provider(model) if not model.lower().startswith("claude") else "anthropic"
    pool = KeyPool.get_pool(provider_id)
    max_retries = min(len(pool.keys), 3) if pool.keys else 1

    for attempt in range(max_retries):
        try:
            # ── Anthropic/Claude Route ──
            if model.lower().startswith("claude"):
                return _ask_anthropic(model, system_role, user_content, tracker)

            # ── Standard OpenAI-compatible Route ──
            resolved_client = get_cached_client(model) if _client_cache else client
            response = resolved_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()

            # Track token usage and cost
            active = tracker or _active_tracker
            if active and hasattr(response, 'usage') and response.usage:
                active.record_call(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                )

            return strip_fences(raw)

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = '429' in err_str or 'rate' in err_str or 'resource_exhausted' in err_str
            if is_rate_limit and attempt < max_retries - 1 and len(pool.keys) > 1:
                current_key = pool.current_key()
                pool.mark_limited(current_key)
                pool.rotate()
                _client_cache.pop(provider_id, None)
                wait = 2 ** attempt
                log("KEYPOOL", f"  🔄 Rate limited on key …{current_key[-6:]} — rotating (retry in {wait}s)")
                time.sleep(wait)
                continue
            raise


def _ask_anthropic(model: str, system_role: str, user_content: str,
                   tracker=None) -> str:
    """Route a request through the Anthropic SDK for Claude models."""
    global _active_tracker
    if not _HAS_ANTHROPIC:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    pool = KeyPool.get_pool("anthropic")
    api_key = pool.next_key()
    if not api_key:
        raise ValueError("No Anthropic API keys available. Set ANTHROPIC_API_KEY env var.")

    client = _anthropic_sdk.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_role,
        messages=[{"role": "user", "content": user_content}],
        temperature=0.1,
    )
    raw = response.content[0].text.strip()

    active = tracker or _active_tracker
    if active and hasattr(response, 'usage') and response.usage:
        active.record_call(
            model=model,
            prompt_tokens=response.usage.input_tokens or 0,
            completion_tokens=response.usage.output_tokens or 0,
        )

    return strip_fences(raw)


# ── Cost Tracker & Budget Kill-Switch ───────────────────────

class CostTracker:
    """Tracks estimated spending across all LLM calls.
    Signals the orchestrator to pivot to cheaper models when budget exceeded."""

    def __init__(self, budget: float = 5.0):
        self.budget = budget
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.per_model = {}
        self._budget_exceeded = False
        self._pivot_triggered = False

    def record_call(self, model: str, prompt_tokens: int, completion_tokens: int):
        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (prompt_tokens / 1000 * pricing["input"]) + \
               (completion_tokens / 1000 * pricing["output"])

        self.total_cost += cost
        self.total_input_tokens += prompt_tokens
        self.total_output_tokens += completion_tokens
        self.call_count += 1

        if model not in self.per_model:
            self.per_model[model] = {"cost": 0.0, "calls": 0, "tokens": 0}
        self.per_model[model]["cost"] += cost
        self.per_model[model]["calls"] += 1
        self.per_model[model]["tokens"] += prompt_tokens + completion_tokens

        if self.total_cost >= self.budget and not self._budget_exceeded:
            self._budget_exceeded = True
            log("SYSTEM", f"⚠️ BUDGET ALERT: ${self.total_cost:.4f} / ${self.budget:.2f} exceeded!")

    @property
    def budget_exceeded(self) -> bool:
        return self._budget_exceeded

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget - self.total_cost)

    @property
    def pivot_triggered(self) -> bool:
        return self._pivot_triggered

    def trigger_pivot(self):
        self._pivot_triggered = True

    def get_summary(self) -> str:
        lines = [f"Total: ${self.total_cost:.4f} / ${self.budget:.2f} budget"]
        lines.append(f"Calls: {self.call_count} | Tokens: {self.total_input_tokens:,} in + {self.total_output_tokens:,} out")
        for m, data in sorted(self.per_model.items(), key=lambda x: -x[1]["cost"]):
            lines.append(f"  {m}: ${data['cost']:.4f} ({data['calls']} calls, {data['tokens']:,} tokens)")
        return "\n".join(lines)

    def save_report(self, project_path: str):
        report = {
            "budget": self.budget,
            "total_cost": round(self.total_cost, 6),
            "remaining": round(self.remaining, 6),
            "budget_exceeded": self._budget_exceeded,
            "pivot_triggered": self._pivot_triggered,
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "per_model": self.per_model,
        }
        report_path = os.path.join(project_path, "cost_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        log("SYSTEM", "  📊 Cost report saved: cost_report.json")
