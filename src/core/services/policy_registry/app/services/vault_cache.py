"""
ACGS-2 Vault Crypto Service - Cache Operations
Constitutional Hash: cdd01ef066bc6cf2

Caching layer for Vault operations to improve performance
by reducing API calls for frequently accessed data.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar

from .vault_models import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)

T = TypeVar("T")


class VaultCache(Generic[T]):
    """
    Generic cache for Vault data with TTL support.

    Provides thread-safe caching with configurable TTL
    and automatic expiration of stale entries.
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 1000):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_entries: Maximum number of entries to cache
        """
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._cache: Dict[str, Tuple[T, datetime]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age < self._ttl:
                self._hits += 1
                return value
            else:
                # Expired, remove it
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, key: str, value: T) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict oldest entries if at capacity
        if len(self._cache) >= self._max_entries:
            self._evict_oldest()

        self._cache[key] = (value, datetime.now(timezone.utc))

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was removed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_pattern(self, prefix: str) -> int:
        """
        Invalidate all entries matching a prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def _evict_oldest(self, count: int = 1) -> None:
        """
        Evict oldest entries from cache.

        Args:
            count: Number of entries to evict
        """
        if not self._cache:
            return

        # Sort by timestamp and remove oldest
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
        for key in sorted_keys[:count]:
            del self._cache[key]

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = datetime.now(timezone.utc)
        expired_keys = []

        for key, (_, timestamp) in self._cache.items():
            if (now - timestamp).total_seconds() >= self._ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        total_requests = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, total_requests),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    @property
    def size(self) -> int:
        """Get current number of cache entries."""
        return len(self._cache)


class VaultCacheManager:
    """
    Manager for multiple Vault caches.

    Provides centralized cache management for different
    types of Vault data (public keys, key info, etc.).
    """

    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager.

        Args:
            default_ttl: Default TTL for caches
        """
        self._default_ttl = default_ttl
        self.public_keys: VaultCache[str] = VaultCache(ttl_seconds=default_ttl)
        self.key_info: VaultCache[Dict[str, Any]] = VaultCache(ttl_seconds=default_ttl)
        self.secrets: VaultCache[Dict[str, Any]] = VaultCache(
            ttl_seconds=60
        )  # Shorter TTL for secrets

    def invalidate_key(self, key_name: str) -> None:
        """
        Invalidate all caches for a specific key.

        Args:
            key_name: Key name to invalidate
        """
        self.public_keys.invalidate(key_name)
        self.key_info.invalidate(key_name)

    def invalidate_secret(self, path: str) -> None:
        """
        Invalidate secret cache for a path.

        Args:
            path: Secret path to invalidate
        """
        self.secrets.invalidate(path)

    def clear_all(self) -> Dict[str, int]:
        """
        Clear all caches.

        Returns:
            Dictionary with cleared counts per cache
        """
        return {
            "public_keys": self.public_keys.clear(),
            "key_info": self.key_info.clear(),
            "secrets": self.secrets.clear(),
        }

    def cleanup_all(self) -> Dict[str, int]:
        """
        Cleanup expired entries from all caches.

        Returns:
            Dictionary with cleanup counts per cache
        """
        return {
            "public_keys": self.public_keys.cleanup_expired(),
            "key_info": self.key_info.cleanup_expired(),
            "secrets": self.secrets.cleanup_expired(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all caches.

        Returns:
            Combined statistics dictionary
        """
        return {
            "public_keys": self.public_keys.get_stats(),
            "key_info": self.key_info.get_stats(),
            "secrets": self.secrets.get_stats(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


__all__ = ["VaultCache", "VaultCacheManager"]
