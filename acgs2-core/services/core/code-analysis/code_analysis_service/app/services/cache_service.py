import logging
from typing import Any

logger = logging.getLogger(__name__)


"""
ACGS Code Analysis Engine - Cache Service
Redis integration with constitutional compliance and performance optimization.
"""

# Constitutional Hash: cdd01ef066bc6cf2
import hashlib
import json
import time
from datetime import datetime, timezone

import redis.asyncio as redis
from app.utils.constitutional import (
    CONSTITUTIONAL_HASH,
    ensure_constitutional_compliance,
)
from app.utils.logging import get_logger, performance_logger

logger = get_logger("services.cache")


class CacheService:
    """Cache service for ACGS Code Analysis Engine with constitutional compliance.

    Provides Redis-based caching with constitutional hash validation."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6389",
        key_prefix: str = "acgs:code_analysis:",
        default_ttl: int = 3600,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize cache service.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
            default_ttl: Default TTL in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Redis client
        self.redis_client: redis.Redis | None = None
        self.is_connected = False

        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_errors = 0

        logger.info(
            "Cache service initialized",
            extra={
                "redis_url": redis_url,
                "key_prefix": key_prefix,
                "default_ttl": default_ttl,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    async def connect(self) -> bool:
        """Connect to Redis server.

        Returns:
            bool: True if connection successful
        """
        if self.is_connected:
            return True

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

            # Test connection
            await self.redis_client.ping()
            self.is_connected = True

            logger.info(
                "Cache service connected to Redis",
                extra={
                    "redis_url": self.redis_url,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to connect to Redis: {e}",
                extra={
                    "redis_url": self.redis_url,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            self.is_connected = False

            logger.info(
                "Cache service disconnected from Redis",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
            )

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        full_key = self._build_key(key)

        try:
            start_time = time.time()

            # Get value from Redis
            cached_data = await self.redis_client.get(full_key)

            if cached_data is not None:
                # Parse cached data
                data = json.loads(cached_data)

                # Validate constitutional compliance
                if not self._validate_cached_data(data):
                    logger.warning(
                        f"Cached data failed constitutional validation: {key}",
                        extra={"constitutional_hash": CONSTITUTIONAL_HASH},
                    )
                    await self.delete(key)  # Remove invalid data
                    self.cache_misses += 1
                    return default

                # Extract actual value
                value = data.get("value")

                # Log cache hit
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_cache_operation(
                    operation="get", cache_hit=True, key=key, duration_ms=duration_ms
                )

                self.cache_hits += 1
                return value
            # Log cache miss
            duration_ms = (time.time() - start_time) * 1000
            performance_logger.log_cache_operation(
                operation="get", cache_hit=False, key=key, duration_ms=duration_ms
            )

            self.cache_misses += 1
            return default

        except Exception as e:
            logger.error(
                f"Cache get error: {e}",
                extra={"key": key, "constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            self.cache_errors += 1
            return default

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            bool: True if successful
        """
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        full_key = self._build_key(key)
        ttl = ttl or self.default_ttl

        try:
            start_time = time.time()

            # Prepare data with constitutional compliance
            cached_data = {
                "value": value,
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "ttl": ttl,
                "service": "acgs-code-analysis-engine",
            }

            # Serialize data
            serialized_data = json.dumps(cached_data, default=str)

            # Set in Redis
            await self.redis_client.setex(full_key, ttl, serialized_data)

            # Log cache set
            duration_ms = (time.time() - start_time) * 1000
            performance_logger.log_cache_operation(
                operation="set",
                cache_hit=True,  # Set is always a "hit"
                key=key,
                duration_ms=duration_ms,
                ttl=ttl,
            )

            return True

        except Exception as e:
            logger.error(
                f"Cache set error: {e}",
                extra={
                    "key": key,
                    "ttl": ttl,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )

            self.cache_errors += 1
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key to delete

        Returns:
            bool: True if successful
        """
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        full_key = self._build_key(key)

        try:
            start_time = time.time()

            # Delete from Redis
            result = await self.redis_client.delete(full_key)

            # Log cache delete
            duration_ms = (time.time() - start_time) * 1000
            performance_logger.log_cache_operation(
                operation="delete",
                cache_hit=result > 0,
                key=key,
                duration_ms=duration_ms,
            )

            return result > 0

        except Exception as e:
            logger.error(
                f"Cache delete error: {e}",
                extra={"key": key, "constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            self.cache_errors += 1
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            bool: True if key exists
        """
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        full_key = self._build_key(key)

        try:
            result = await self.redis_client.exists(full_key)
            return result > 0

        except Exception as e:
            logger.error(
                f"Cache exists error: {e}",
                extra={"key": key, "constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            self.cache_errors += 1
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            int: Number of keys deleted
        """
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        full_pattern = self._build_key(pattern)

        try:
            # Find matching keys
            keys = await self.redis_client.keys(full_pattern)

            if keys:
                # Delete all matching keys
                result = await self.redis_client.delete(*keys)

                logger.info(
                    f"Cleared {result} cache keys matching pattern: {pattern}",
                    extra={
                        "pattern": pattern,
                        "keys_deleted": result,
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )

                return result
            return 0

        except Exception as e:
            logger.error(
                f"Cache clear pattern error: {e}",
                extra={"pattern": pattern, "constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            self.cache_errors += 1
            return 0

    async def get_cache_info(self) -> dict[str, Any]:
        """Get cache information and statistics."""
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        try:
            # Get Redis info
            redis_info = await self.redis_client.info()

            # Calculate hit rate
            total_operations = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_operations) if total_operations > 0 else 0.0

            cache_info = {
                "is_connected": self.is_connected,
                "redis_url": self.redis_url,
                "key_prefix": self.key_prefix,
                "default_ttl": self.default_ttl,
                "statistics": {
                    "cache_hits": self.cache_hits,
                    "cache_misses": self.cache_misses,
                    "cache_errors": self.cache_errors,
                    "hit_rate": round(hit_rate, 4),
                    "total_operations": total_operations,
                },
                "redis_info": {
                    "used_memory": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "total_commands_processed": redis_info.get("total_commands_processed"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses"),
                },
            }

            return ensure_constitutional_compliance(cache_info)

        except Exception as e:
            logger.error(
                f"Cache info error: {e}",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            return ensure_constitutional_compliance(
                {
                    "is_connected": self.is_connected,
                    "error": str(e),
                    "statistics": {
                        "cache_hits": self.cache_hits,
                        "cache_misses": self.cache_misses,
                        "cache_errors": self.cache_errors,
                    },
                }
            )

    def _build_key(self, key: str) -> str:
        """Build full cache key with prefix."""
        return f"{self.key_prefix}, {key}"

    def _validate_cached_data(self, data: dict[str, Any]) -> bool:
        """Validate constitutional compliance of cached data."""
        # Check for constitutional hash
        cached_hash = data.get("constitutional_hash")
        if not cached_hash or cached_hash != CONSTITUTIONAL_HASH:
            return False

        # Check for required fields
        required_fields = ["value", "cached_at", "service"]
        for field in required_fields:
            if field not in data:
                return False

        # Check service name
        return data.get("service") == "acgs-code-analysis-engine"

    def generate_cache_key(self, *components: str) -> str:
        """Generate cache key from components.

        Args:
            components: Key components

        Returns:
            str: Generated cache key
        """
        # Create deterministic key from components
        key_string = ":".join(str(c) for c in components)

        # Add constitutional hash for uniqueness
        key_with_hash = f"{key_string}:{CONSTITUTIONAL_HASH}"

        # Generate hash for long keys
        if len(key_with_hash) > 200:
            try:
                key_hash = hashlib.sha256(key_with_hash.encode()).hexdigest()[:16]
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise
            return f"hash:{key_hash}"

        return key_string

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        """Async context manager exit."""
        await self.disconnect()
