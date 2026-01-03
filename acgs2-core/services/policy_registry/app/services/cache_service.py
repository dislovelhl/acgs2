"""
Cache service for policy data with Redis and local caching
"""

import json
import logging
import time
from functools import lru_cache
from typing import Any, Dict, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class CacheService:
    """Multi-level caching service with Redis and local LRU cache"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        local_cache_size: int = 100,
        redis_ttl: int = 3600,  # 1 hour
        local_ttl: int = 300,  # 5 minutes
    ):
        self.redis_url = redis_url
        self.redis_ttl = redis_ttl
        self.local_ttl = local_ttl
        self.redis_client = None
        self._local_cache: Dict[str, Dict[str, Any]] = {}

        # Configure LRU cache for frequently accessed items
        self._get_cached_policy = lru_cache(maxsize=local_cache_size)(self._get_cached_policy_impl)

    async def initialize(self):
        """Initialize Redis connection"""
        if redis:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}")
                self.redis_client = None
        else:
            logger.warning("Redis not available, using local cache only")

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def set_policy(self, policy_id: str, version: str, data: Dict[str, Any]):
        """Cache policy data"""
        cache_key = f"policy:{policy_id}:{version}"
        cache_data = {"data": data, "timestamp": time.time()}

        # Set in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(cache_key, self.redis_ttl, json.dumps(cache_data))
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

        # Set in local cache
        self._local_cache[cache_key] = cache_data

        # Clear LRU cache
        self._get_cached_policy.cache_clear()

    async def get_policy(self, policy_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Get cached policy data"""
        cache_key = f"policy:{policy_id}:{version}"

        # Try local cache first
        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if time.time() - cached["timestamp"] < self.local_ttl:
                return cached["data"]
            else:
                # Expired, remove from local cache
                del self._local_cache[cache_key]

        # Try Redis
        if self.redis_client:
            try:
                cached_json = await self.redis_client.get(cache_key)
                if cached_json:
                    cached = json.loads(cached_json)
                    # Update local cache
                    self._local_cache[cache_key] = cached
                    return cached["data"]
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        return None

    def _get_cached_policy_impl(self, policy_id: str, version: str) -> Optional[Dict[str, Any]]:
        """LRU cached implementation for frequently accessed policies"""
        # This will be wrapped by lru_cache decorator
        cache_key = f"policy:{policy_id}:{version}"

        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if time.time() - cached["timestamp"] < self.local_ttl:
                return cached["data"]

        return None

    async def invalidate_policy(self, policy_id: str, version: Optional[str] = None):
        """Invalidate policy cache"""
        if version:
            cache_key = f"policy:{policy_id}:{version}"
            keys_to_remove = [cache_key]
        else:
            # Invalidate all versions of the policy
            keys_to_remove = [
                key for key in self._local_cache.keys() if key.startswith(f"policy:{policy_id}:")
            ]

        # Remove from local cache
        for key in keys_to_remove:
            self._local_cache.pop(key, None)

        # Remove from Redis
        if self.redis_client:
            try:
                await self.redis_client.delete(*keys_to_remove)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        # Clear LRU cache
        self._get_cached_policy.cache_clear()

    async def set_public_key(self, key_id: str, public_key: str):
        """Cache public key"""
        cache_key = f"pubkey:{key_id}"
        cache_data = {"public_key": public_key, "timestamp": time.time()}

        # Redis cache (longer TTL for keys)
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.redis_ttl * 24,
                    json.dumps(cache_data),  # 24 hours
                )
            except Exception as e:
                logger.warning(f"Redis set public key failed: {e}")

        # Local cache
        self._local_cache[cache_key] = cache_data

    async def get_public_key(self, key_id: str) -> Optional[str]:
        """Get cached public key"""
        cache_key = f"pubkey:{key_id}"

        # Try local cache
        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if time.time() - cached["timestamp"] < self.local_ttl:
                return cached["public_key"]
            else:
                del self._local_cache[cache_key]

        # Try Redis
        if self.redis_client:
            try:
                cached_json = await self.redis_client.get(cache_key)
                if cached_json:
                    cached = json.loads(cached_json)
                    self._local_cache[cache_key] = cached
                    return cached["public_key"]
            except Exception as e:
                logger.warning(f"Redis get public key failed: {e}")

        return None

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "local_cache_size": len(self._local_cache),
            "redis_available": self.redis_client is not None,
        }

        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update(
                    {
                        "redis_connected_clients": info.get("connected_clients", 0),
                        "redis_used_memory": info.get("used_memory_human", "unknown"),
                    }
                )
            except Exception as e:
                logger.warning(f"Redis info failed: {e}")

        return stats
