"""HTTP client utilities for API requests."""

import requests

from .cache import get_cache

# Shared session for connection pooling
session = requests.Session()
session.headers.update({"User-Agent": "codespaces-crewai-fmp/1.0"})


def get_json(url: str, params: dict, timeout: int = 30, use_cache: bool = True) -> dict:
    """
    Fetch JSON with caching and good error visibility.

    Args:
        url: The API endpoint URL
        params: Query parameters to include
        timeout: Request timeout in seconds
        use_cache: Whether to use caching (default True)

    Returns:
        Dictionary with 'ok' status and either 'data' or error info
    """
    cache = get_cache()

    # Check cache first
    if use_cache:
        cached = cache.get(url, params)
        if cached is not None:
            return {**cached, "cache_hit": True}

    # Make actual request
    try:
        r = session.get(url, params=params, timeout=timeout)
        text = r.text
        try:
            payload = r.json()
        except Exception:
            payload = {"_non_json_response": text[:1200]}

        if r.status_code != 200:
            # Don't cache errors
            return {"ok": False, "status_code": r.status_code, "url": r.url, "error_payload": payload}

        result = {"ok": True, "data": payload, "url": r.url}

        # Cache successful responses
        if use_cache:
            cache.set(url, params, result)

        return result
    except Exception as e:
        return {"ok": False, "exception": str(e), "url": url}
