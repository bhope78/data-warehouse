"""Shared utilities for API ingestion — retry logic, rate limiting, logging."""

import logging
import time
from functools import wraps

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def fetch_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    """Fetch JSON from a URL with automatic retry on failure."""
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def rate_limit(calls_per_second: float = 1.0):
    """Decorator to rate-limit API calls."""
    min_interval = 1.0 / calls_per_second

    def decorator(func):
        last_called = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_called[0] = time.time()
            return func(*args, **kwargs)

        return wrapper

    return decorator
