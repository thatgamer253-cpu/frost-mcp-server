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
from .vault import Vault


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
        env_base = provider.get("env_key", "").replace("_API_KEY", "").replace("_KEY", "")
        
        self.keys = []
        seen = set()

        def add_key(k):
            k = k.strip()
            if k and k not in seen:
                self.keys.append(k)
                seen.add(k)

        # 1. Flexible Environment Scanning
        # We look for: PROVIDER_API_KEY, PROVIDER_KEY, PROVIDER_API_KEY_N, PROVIDER_KEYS, etc.
        for var_name, value in os.environ.items():
            name_up = var_name.upper()
            
            # Check if this variable belongs to our provider
            # e.g. for "openai", env_base is "OPENAI"
            is_match = False
            if env_base and env_base in name_up:
                # Must contain "KEY", "TOKEN", "SK", or "SECRET" to be a candidate
                if any(x in name_up for x in ["KEY", "TOKEN", "SK", "SECRET"]):
                    is_match = True
            
            if is_match:
                # If it's a list variant (comma-separated)
                if "KEYS" in name_up:
                    for k in value.split(","):
                        add_key(k)
                else:
                    add_key(value)

        # 2. Merge with keys from Secure Vault
        try:
            vault = Vault()
            vault_keys = vault.get_keys_for_provider(provider_id)
            for v_key in vault_keys:
                add_key(v_key)
        except Exception as e:
            log("WARN", f"  Vault load error for {provider_id}: {e}")

        self._index = 0
        self._cooldowns = {}
        self._rotations = 0
        self._key_lock = threading.Lock()

        if len(self.keys) > 0:
            label = provider.get("label", provider_id)
            msg = f"  🔑 {label} pool: {len(self.keys)} key(s) loaded"
            if len(self.keys) > 1:
                log("KEYPOOL", msg)
            else:
                # Optional: log single keys too but maybe less noisy
                pass 

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

def resolve_auto_model() -> tuple:
    """Smart auto-detection: pick the best model based on which API keys are available.
    Returns (model_name, provider_id).
    Priority: Force-Local > Gemini > OpenAI > OpenRouter > Groq > Anthropic > Ollama.
    """
    if os.environ.get("OVERLORD_FORCE_LOCAL", "").lower() in ("1", "true", "yes"):
        log("INFO", "🔒 Resolve: Force-Local Mode (Environment Triggered)")
        return "local/qwen2.5-coder:7b", "ollama"

    _priority = [
        ("gemini",    "gemini-2.0-flash",      "GEMINI_API_KEY"),
        ("openai",    "gpt-4o-mini",            "OPENAI_API_KEY"),
        ("openrouter","openrouter/google/gemini-2.0-flash-exp:free", "OPENROUTER_API_KEY"),
        ("groq",      "llama3-70b-8192",        "GROQ_API_KEY"),
        ("anthropic", "claude-sonnet-4-20250514",  "ANTHROPIC_API_KEY"),
    ]
    for provider_id, default_model, env_key in _priority:
        key = os.environ.get(env_key, "").strip()
        pool_key = env_key.replace("_KEY", "_KEYS")
        pool = os.environ.get(pool_key, "").strip()

        if (key and key.lower() not in ("none", "your-key-here", "")) or pool:
            log("INFO", f"🔮 Auto-detected provider: {PROVIDERS[provider_id]['label']}")
            return default_model, provider_id

    # Check DeepSeek specifically as it's a popular high-value option
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEYS", "")
    if ds_key:
        log("INFO", "🔮 Auto-detected provider: DeepSeek (key found)")
        return "deepseek-chat", "openrouter" # Mapping to openrouter for now if not distinct

    # Last resort: check if Ollama is running locally
    try:
        import urllib.request
        # Check for qwen2.5-coder which is our current preferred local model
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        models_data = json.loads(resp.read().decode())
        available_models = [m.get("name", "") for m in models_data.get("models", [])]
        
        pref_models = ["qwen2.5-coder:7b", "qwen2.5-coder", "llama3", "mistral"]
        for pm in pref_models:
            if pm in available_models or any(pm in m for m in available_models):
                log("INFO", f"🔮 Auto-detected provider: Ollama 🦙 (found {pm})")
                return f"local/{pm}", "ollama"
                
        log("INFO", "🔮 Auto-detected provider: Ollama 🦙 (local server running)")
        return "local/llama3", "ollama"
    except Exception:
        pass

    log("WARN", "🔮 Auto-select found no API keys! Defaulting to gemini-2.0-flash")
    return "gemini-2.0-flash", "gemini"


def detect_provider(model_name: str) -> str:
    """Auto-detect provider from model name prefix."""
    model_lower = model_name.lower()
    if model_lower == "auto":
        _, provider = resolve_auto_model()
        return provider
    for provider_id, info in PROVIDERS.items():
        for prefix in info["prefixes"]:
            if model_lower.startswith(prefix):
                return provider_id
    return "openai"


def detect_provider_from_key(api_key: str) -> str:
    """Intelligently detect provider based on API key format/prefix."""
    k = api_key.strip()
    if not k: return ""
    
    if k.startswith("sk-ant-"): return "anthropic"
    if k.startswith("gsk_"): return "groq"
    if k.startswith("AIzaSy"): return "gemini"
    if k.startswith("sk-or-v1-"): return "openrouter"
    if k.startswith("luma-"): return "luma"
    if k.startswith("sk-"):
        if "dsk" in k.lower() or "deepseek" in k.lower(): return "deepseek"
        return "openai"
    return ""


def get_client_for_model(model_name: str, fallback_key: str = "") -> OpenAI:
    """Create the right OpenAI client for any provider based on model name."""
    provider_id = detect_provider(model_name)
    provider = PROVIDERS[provider_id]

    pool = KeyPool.get_pool(provider_id)
    api_key = pool.next_key() or fallback_key

    # Try session-wide or user-level env fallback if pool is empty
    if not api_key:
        env_key = provider.get("env_key", "")
        if env_key:
            api_key = os.environ.get(env_key, "")
    
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

def _try_fallback_provider(original_provider: str, system_role: str,
                           user_content: str, tracker=None) -> str:
    """Try alternative providers when the primary one is rate-limited."""
    _fallback_order = [
        ("gemini",   "gemini-2.0-flash"),
        ("openai",   "gpt-4o-mini"),
        ("local",    "local/qwen2.5:7b"),
        ("local",    "local/llama3"),
        ("groq",     "llama3-70b-8192"),
        ("anthropic", "claude-3-5-haiku-20241022"),
    ]
    for fb_id, fb_model in _fallback_order:
        if fb_id == original_provider:
            continue
            
        # Offline Mode Block
        if os.environ.get("OVERLORD_OFFLINE_MODE") == "1" and fb_id not in ("local", "ollama"):
            continue

        fb_pool = KeyPool.get_pool(fb_id)
        if not fb_pool.keys:
            # Check env as last resort
            env_key = PROVIDERS.get(fb_id, {}).get("env_key", "")
            if not (env_key and os.environ.get(env_key, "").strip()):
                continue
        log("KEYPOOL", f"  🔀 Falling back to {PROVIDERS.get(fb_id, {}).get('label', fb_id)}...")
        try:
            if fb_model.startswith("claude"):
                return _ask_anthropic(fb_model, system_role, user_content, tracker)
            fb_client = get_client_for_model(fb_model)
            response = fb_client.chat.completions.create(
                model=fb_model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            log("KEYPOOL", f"  ✓ Fallback succeeded via {fb_id}")
            return strip_fences(raw)
        except Exception as fb_err:
            log("KEYPOOL", f"  ⚠ Fallback {fb_id} failed: {fb_err}")
            continue
    raise RuntimeError("All providers exhausted (rate-limited). Please wait and try again.")


def ask_llm(client: OpenAI, model: str, system_role: str, user_content: str,
            tracker=None) -> str:
    """Send a chat completion request and return the cleaned response.
    Auto-resolves the right client for multi-provider model mixing.
    Routes Claude models through the Anthropic SDK automatically.
    Includes exponential backoff retry and automatic provider fallback."""
    global _active_tracker

    if os.environ.get("OVERLORD_OFFLINE_MODE") == "1" or os.environ.get("OVERLORD_FORCE_LOCAL") == "1":
        # Redirect to local model
        log("SYSTEM", "🔒 OFFLINE MODE: Bypassing cloud API call")
        model, provider_id = resolve_auto_model()
        client = get_cached_client(model)
        
        if provider_id not in ("local", "ollama"):
            # Emergency override if resolve_auto_model somehow picked a cloud name
            model = "local/qwen2.5-coder:7b"
            client = get_cached_client(model)
    else:
        provider_id = detect_provider(model) if not model.lower().startswith("claude") else "anthropic"

    pool = KeyPool.get_pool(provider_id)
    # Always retry at least 5 times on rate limits, more if we have keys to rotate
    max_retries = max(len(pool.keys), 5) if pool.keys else 5

    last_error = None

    for attempt in range(max_retries):
        try:
            log("INFO", f"  ⏳ Connecting to {model} (Attempt {attempt+1}/{max_retries})...")
            
            # ── Anthropic/Claude Route ──
            if model.lower().startswith("claude"):
                return _ask_anthropic(model, system_role, user_content, tracker)

            # ── Standard OpenAI-compatible Route ──
            resolved_client = client or get_cached_client(model)
            
            # Check for missing keys causing immediate failure
            if not resolved_client.api_key or resolved_client.api_key == "none":
                 # If we are local/ollama, "none" key is fine. If not, it's a fail.
                 if "localhost" not in str(resolved_client.base_url) and "127.0.0.1" not in str(resolved_client.base_url):
                     raise ValueError(f"No API key found for requested model {model}.")

            # Strip internal routing prefixes like 'local/'
            effective_model = model
            if effective_model.startswith("local/"):
                effective_model = effective_model.replace("local/", "", 1)
                
            response = resolved_client.chat.completions.create(
                model=effective_model,
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
            last_error = e
            err_str = str(e).lower()
            
            # Fast fail for auth errors
            if "authentication" in err_str or "api key" in err_str:
                log("ERROR", f"  ❌ Auth Error: {e}")
                break # Don't retry auth errors

            # Handle Connection Errors (e.g. Ollama/Local server not running)
            is_conn_error = "connection" in err_str or "winerror 10061" in err_str
            is_rate_limit = '429' in err_str or 'rate' in err_str or 'resource_exhausted' in err_str
            
            if is_conn_error:
                log("WARN", f"  ⚠️ Connection error to {model}: {e}. Local server might be down.")
                # If we are in force-local mode, we still try fallbacks but restricted to local if offline
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

            if is_rate_limit and attempt < max_retries - 1:
                wait = min(2 ** attempt, 32)
                if len(pool.keys) > 1:
                    current_key = pool.current_key()
                    pool.mark_limited(current_key)
                    pool.rotate()
                    _client_cache.pop(provider_id, None)
                    log("KEYPOOL", f"  🔄 Rate limited on key …{current_key[-6:]} — rotating (retry in {wait}s)")
                else:
                    log("KEYPOOL", f"  ⏳ Rate limited — backing off {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            elif not is_rate_limit and not is_conn_error:
                log("ERROR", f"  ❌ LLM Request Failed: {e}")
                raise

    # All retries exhausted — try fallback providers
    log("KEYPOOL", f"  ⚠ {provider_id} exhausted after {max_retries} retries/connection failures. Trying fallback providers...")
    try:
        return _try_fallback_provider(provider_id, system_role, user_content, tracker)
    except RuntimeError:
        raise last_error  # Re-raise the original error if all fallbacks fail


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

def ask_llm_stream(client: OpenAI, model: str, system_role: str, user_content: str, tracker=None, parse_monologue: bool = False):
    """
    Streaming generator for chat completion.
    Yields string chunks as they arrive from the LLM.
    If parse_monologue=True, buffers the JSON output to extract only 'final_response'
    and logs the 'internal_monologue' to console.
    """
    global _active_tracker
    
    # 1. Resolve Model/Client
    if os.environ.get("OVERLORD_OFFLINE_MODE") == "1" or os.environ.get("OVERLORD_FORCE_LOCAL") == "1":
        model, _ = resolve_auto_model()
    
    # 2. Claude Fallback (No streaming support in this simple wrapper yet)
    if model.lower().startswith("claude") or model == "anthropic":
        # Block and yield once
        resp = ask_llm(client, model, system_role, user_content, tracker)
        if parse_monologue:
            try:
                import json
                # Handle possible markdown blocks
                clean_resp = resp.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_resp)
                if "internal_monologue" in data:
                    print(f"\n[INTERNAL MONOLOGUE]: {data['internal_monologue']}\n")
                yield data.get("final_response", resp)
            except:
                yield resp
        else:
            yield resp
        return

    # 3. Get Client
    resolved_client = client or get_cached_client(model)
    if not resolved_client:
        yield "Error: Could not resolve LLM client."
        return

    # 4. Stream
    effective_model = model.replace("local/", "", 1) if model.startswith("local/") else model
    
    try:
        stream = resolved_client.chat.completions.create(
            model=effective_model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.7,
            stream=True
        )
        
        if not parse_monologue:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            # Monologue Buffering Logic
            buffer = ""
            yield_active = False
            response_key = '"final_response":'
            
            # Simple buffer logic: wait for "final_response": "
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    
                    if yield_active:
                        # Stop at closing quote/brace of the JSON structure
                        # This is a heuristic: if we see `"` followed by `}` or `,` it might be end.
                        # But simplest is to just yield everything and let UI render markedown.
                        # The only risk is seeing `"} at the end.
                        # We'll filter `"` and `}` at the *very end* of the stream? Hard in streaming.
                        # For now, yield raw content and trust the user to ignore the closing brace.
                        yield content
                    else:
                        buffer += content
                        if response_key in buffer:
                            # Start yielding!
                            yield_active = True
                            # Extract what we can from buffer
                            idx = buffer.find(response_key)
                            start_quote = buffer.find('"', idx + len(response_key))
                            if start_quote != -1:
                                preamble = buffer[:start_quote] # Contains monologue
                                valid_part = buffer[start_quote+1:] # Contains response start
                                
                                # Log the monologue
                                try:
                                    print(f"\n[GHOST LAYER]: {preamble[-200:]}...\n") # Log tail of monologue
                                except: pass
                                
                                yield valid_part

    except Exception as e:
        log("LLM", f"Stream Error: {e}")
        yield f"[Error: {e}]"
        yield f"\n[Stream Error: {str(e)}]"
