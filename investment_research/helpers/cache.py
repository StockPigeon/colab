"""Session-scoped cache for API responses."""

from typing import Any, Optional
from datetime import datetime, timedelta
import hashlib
import json


class SessionCache:
    """
    In-memory cache for API responses within a single analysis session.

    Features:
    - Automatic cache key generation from URL + params
    - Configurable TTL per cache entry
    - Easy clear() for new ticker analysis
    - Thread-safe for sequential CrewAI execution
    """

    def __init__(self):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = timedelta(hours=1)
        self._hits = 0
        self._misses = 0

    def _make_key(self, url: str, params: dict) -> str:
        """
        Generate cache key from URL and params.
        Excludes 'apikey' from params for security and consistency.
        """
        clean_params = {k: v for k, v in sorted(params.items()) if k != "apikey"}
        key_data = f"{url}|{json.dumps(clean_params, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, url: str, params: dict) -> Optional[dict]:
        """
        Get cached response if exists and not expired.

        Returns:
            Cached response dict or None if not found/expired.
        """
        key = self._make_key(url, params)

        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._default_ttl:
                self._hits += 1
                return data
            else:
                # Expired, remove it
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, url: str, params: dict, data: dict) -> None:
        """
        Store response in cache.

        Args:
            url: The API endpoint URL
            params: Query parameters
            data: Response data to cache
        """
        key = self._make_key(url, params)
        self._cache[key] = (data, datetime.now())

    def clear(self) -> None:
        """Clear all cached data. Call between different ticker analyses."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate_pct": round(hit_rate, 1),
            "cached_entries": len(self._cache),
        }


# Global session cache instance
_session_cache: Optional[SessionCache] = None


def get_cache() -> SessionCache:
    """Get or create the global session cache."""
    global _session_cache
    if _session_cache is None:
        _session_cache = SessionCache()
    return _session_cache


def clear_cache() -> None:
    """Clear the global session cache."""
    global _session_cache
    if _session_cache is not None:
        _session_cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return get_cache().stats
