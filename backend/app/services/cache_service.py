"""Cache service for weather data with TTL."""

from cachetools import TTLCache
from typing import Any


class CacheService:
    """In-memory cache service with TTL (Time To Live)."""

    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        """
        Initialize cache service.

        Args:
            maxsize: Maximum number of cached items (LRU eviction)
            ttl: Time to live in seconds (default 1 hour)
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value

    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache


# Singleton instance - will be configured from settings
weather_cache: CacheService | None = None


def get_weather_cache(ttl: int = 3600) -> CacheService:
    """
    Get or create weather cache instance.

    Args:
        ttl: Cache TTL in seconds

    Returns:
        CacheService instance
    """
    global weather_cache
    if weather_cache is None:
        weather_cache = CacheService(maxsize=1000, ttl=ttl)
    return weather_cache
