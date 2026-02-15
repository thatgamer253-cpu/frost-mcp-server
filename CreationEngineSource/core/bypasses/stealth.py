import time
import random
import requests
from typing import Dict, Optional

class StealthEngine:
    """
    Protects the workforce from IP bans and rate limits.
    Wraps requests with randomized headers and jitter.
    """
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]

    def apply_stealth(self):
        """Randomized jitter to bypass behavioral detection."""
        # Sleep between 1.5 and 4.0 seconds
        duration = random.uniform(1.5, 4.0)
        time.sleep(duration)

    def get_headers(self) -> Dict[str, str]:
        """Returns a dict with a randomized User-Agent."""
        return {"User-Agent": random.choice(self.user_agents)}

    def get(self, url: str, **kwargs) -> requests.Response:
        """Stealth wrapper for requests.get"""
        self.apply_stealth()
        headers = list(kwargs.get("headers", {}).items()) + list(self.get_headers().items())
        kwargs["headers"] = dict(headers)
        return requests.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Stealth wrapper for requests.post"""
        self.apply_stealth()
        headers = list(kwargs.get("headers", {}).items()) + list(self.get_headers().items())
        kwargs["headers"] = dict(headers)
        return requests.post(url, **kwargs)
