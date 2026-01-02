"""
ACGS-2 Tiered Cache Manager
Constitutional Hash: cdd01ef066bc6cf2

Coordinates L1 (in-process), L2 (Redis), and L3 (distributed) caches with
intelligent tier promotion/demotion based on access patterns.

Tier Architecture:
- L1: In-process TTLCache for ultra-hot data (<0.1ms target latency)
- L2: Redis for shared caching across instances (1-50ms latency)
- L3: Distributed cache for cold data and fallback (10-1000ms latency)

Promotion Logic:
- Data accessed >10 times/minute automatically promotes to L1
- Data accessed <1 time/hour demotes to L3

Graceful Degradation:
- When Redis (L2) is unavailable, system falls back to L1 + L3
- No exceptions are raised; degraded mode is logged

Usage:
    from shared.tiered_cache import TieredCacheManager, get_tiered_cache

    # Direct usage (synchronous L1+L3)
    mgr = TieredCacheManager()
    mgr.get('key')  # Fast sync access to L1 and L3

    # Full async usage (L1+L2+L3)
    mgr = TieredCacheManager()
    await mgr.initialize()  # Initialize Redis connection
    await mgr.set('key', 'value')
    value = await mgr.get_async('key')  # Includes Redis L2 tier

    # Singleton pattern
    mgr = get_tiered_cache()

Access Frequency Tracking:
    Keys accessed frequently (>10 times/minute) are automatically promoted
    to L1 tier for optimal performance. Use get_tier(key) to check current tier.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar

from shared.l1_cache import L1Cache
from shared.redis_config import (
    CONSTITUTIONAL_HASH,
    RedisConfig,
    RedisHealthState,
    get_redis_config,
)

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheTier(Enum):
    """Cache tier identifiers."""

    L1 = "L1"  # In-process cache (fastest)
    L2 = "L2"  # Redis cache (shared)
    L3 = "L3"  # Distributed/persistent cache (slowest)
    NONE = "NONE"  # Not cached in any tier


@dataclass
class TieredCacheConfig:
    """Configuration for tiered cache manager."""

    # L1 configuration
    l1_maxsize: int = 1024
    l1_ttl: int = 300  # 5 minutes (must be <= L2 TTL)

    # L2 configuration
    l2_ttl: int = 3600  # 1 hour
    redis_url: Optional[str] = None

    # L3 configuration
    l3_ttl: int = 86400  # 24 hours
    l3_enabled: bool = True

    # Promotion/demotion thresholds
    promotion_threshold: int = 10  # Accesses per minute to promote to L1
    demotion_threshold_hours: float = 1.0  # Hours without access to demote to L3

    # Serialization
    serialize: bool = True  # JSON serialize for type consistency across tiers


@dataclass
class TieredCacheStats:
    """Statistics for tiered cache operations."""

    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    l3_hits: int = 0
    l3_misses: int = 0
    promotions: int = 0
    demotions: int = 0
    redis_failures: int = 0

    @property
    def total_hits(self) -> int:
        """Total hits across all tiers."""
        return self.l1_hits + self.l2_hits + self.l3_hits

    @property
    def total_misses(self) -> int:
        """Total misses across all tiers."""
        return self.l1_misses + self.l2_misses + self.l3_misses

    @property
    def hit_ratio(self) -> float:
        """Overall hit ratio."""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0

    @property
    def l1_hit_ratio(self) -> float:
        """L1 hit ratio."""
        total = self.l1_hits + self.l1_misses
        return self.l1_hits / total if total > 0 else 0.0


@dataclass
class AccessRecord:
    """Tracks access patterns for a cache key."""

    key: str
    access_times: List[float] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)
    current_tier: CacheTier = CacheTier.NONE

    def record_access(self) -> None:
        """Record a new access."""
        now = time.time()
        self.last_access = now
        # Keep only accesses from the last minute for promotion calculation
        cutoff = now - 60
        self.access_times = [t for t in self.access_times if t >= cutoff]
        self.access_times.append(now)

    @property
    def accesses_per_minute(self) -> int:
        """Count of accesses in the last minute."""
        now = time.time()
        cutoff = now - 60
        return sum(1 for t in self.access_times if t >= cutoff)

    @property
    def hours_since_access(self) -> float:
        """Hours since last access."""
        return (time.time() - self.last_access) / 3600


class TieredCacheManager:
    """
    Multi-tier cache manager coordinating L1, L2, and L3 caches.

    Provides intelligent tier management with:
    - Automatic promotion of hot data to L1
    - Demotion of cold data to L3
    - Graceful degradation when Redis is unavailable
    - Per-tier statistics and metrics

    Thread Safety:
    - L1 cache uses internal threading.Lock
    - L2 (Redis) operations are async and connection-pooled
    - Access tracking uses its own lock
    """

    def __init__(
        self,
        config: Optional[TieredCacheConfig] = None,
        name: str = "default",
    ):
        """
        Initialize tiered cache manager.

        Args:
            config: Optional TieredCacheConfig for customization
            name: Cache name for metrics and logging
        """
        self.config = config or TieredCacheConfig()
        self.name = name

        # Ensure L1 TTL <= L2 TTL (requirement from spec)
        if self.config.l1_ttl > self.config.l2_ttl:
            self.config.l1_ttl = self.config.l2_ttl
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] L1 TTL adjusted to {self.config.l1_ttl}s "
                f"to not exceed L2 TTL"
            )

        # L1 cache (in-process)
        self._l1_cache = L1Cache(
            maxsize=self.config.l1_maxsize,
            ttl=self.config.l1_ttl,
            serialize=self.config.serialize,
        )

        # L2 Redis client (initialized async)
        self._l2_client: Optional[Any] = None
        self._redis_config: RedisConfig = get_redis_config()

        # L3 cache (in-memory simulation for now, to be extended)
        # In production, this could be backed by a distributed store like Memcached
        # or a persistent store like PostgreSQL
        self._l3_cache: Dict[str, Dict[str, Any]] = {}
        self._l3_lock = threading.Lock()

        # Access tracking for promotion/demotion
        self._access_records: Dict[str, AccessRecord] = {}
        self._access_lock = threading.Lock()

        # Statistics
        self._stats = TieredCacheStats()
        self._stats_lock = threading.Lock()

        # Degraded mode tracking
        self._l2_degraded = False
        self._last_l2_failure: float = 0.0
        self._l2_recovery_interval: float = 30.0  # Try to recover every 30 seconds

        # Register for Redis health changes
        self._redis_config.register_health_callback(self._on_redis_health_change)

        logger.info(
            f"[{CONSTITUTIONAL_HASH}] TieredCacheManager '{name}' initialized: "
            f"L1(maxsize={self.config.l1_maxsize}, ttl={self.config.l1_ttl}s), "
            f"L2(ttl={self.config.l2_ttl}s), L3(enabled={self.config.l3_enabled})"
        )

    async def initialize(self) -> bool:
        """
        Initialize async components (Redis L2 connection).

        Returns:
            True if all tiers initialized successfully
        """
        l2_ready = await self._initialize_l2()

        if not l2_ready:
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] L2 (Redis) not available, "
                f"running in degraded mode (L1 + L3 only)"
            )
            self._l2_degraded = True

        return l2_ready

    async def _initialize_l2(self) -> bool:
        """Initialize L2 Redis connection."""
        if aioredis is None:
            logger.warning("redis-py[async] not installed, L2 cache disabled")
            return False

        try:
            redis_url = self.config.redis_url or RedisConfig.get_url()
            self._l2_client = aioredis.from_url(
                redis_url,
                decode_responses=True,  # Avoid bytes/str confusion
            )
            await self._l2_client.ping()
            logger.info(f"[{CONSTITUTIONAL_HASH}] L2 Redis connection established")
            return True
        except Exception as e:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 Redis initialization failed: {e}")
            self._l2_client = None
            return False

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._l2_client:
            try:
                await self._l2_client.close()
            except Exception as e:
                logger.warning(f"Error closing L2 Redis: {e}")
            self._l2_client = None

        logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager '{self.name}' closed")

    def _on_redis_health_change(
        self, old_state: RedisHealthState, new_state: RedisHealthState
    ) -> None:
        """
        Handle Redis health state changes for graceful degradation.

        Args:
            old_state: Previous Redis health state
            new_state: New Redis health state
        """
        if new_state == RedisHealthState.UNHEALTHY:
            self._l2_degraded = True
            self._last_l2_failure = time.time()
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] Redis unhealthy, switching to degraded mode (L1 + L3)"
            )
        elif new_state == RedisHealthState.HEALTHY and self._l2_degraded:
            self._l2_degraded = False
            self._last_l2_failure = 0.0
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Redis recovered, resuming normal tiered operation"
            )

    def _should_try_l2_recovery(self) -> bool:
        """
        Check if enough time has passed to attempt L2 recovery.

        Returns:
            True if recovery should be attempted
        """
        if not self._l2_degraded:
            return False
        if self._l2_client is None:
            return False
        return time.time() - self._last_l2_failure >= self._l2_recovery_interval

    async def _try_l2_recovery(self) -> bool:
        """
        Attempt to recover L2 Redis connection.

        Called periodically when in degraded mode to check if Redis is back.

        Returns:
            True if recovery succeeded
        """
        if not self._l2_degraded or self._l2_client is None:
            return not self._l2_degraded

        try:
            await self._l2_client.ping()
            self._l2_degraded = False
            self._last_l2_failure = 0.0
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] L2 Redis connection recovered, "
                f"resuming normal tiered operation"
            )
            return True
        except Exception as e:
            # Still down, update failure time for next recovery attempt
            self._last_l2_failure = time.time()
            logger.debug(f"[{CONSTITUTIONAL_HASH}] L2 recovery attempt failed: {e}")
            return False

    def get(
        self,
        key: str,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """
        Get a value from the tiered cache (synchronous version).

        Lookup order: L1 -> L3 (skips L2 Redis for sync access)
        Side effects: May promote data to L1 if access frequency threshold met.

        For full async access including L2 Redis, use get_async().

        Args:
            key: Cache key
            default: Default value if key not found in any tier

        Returns:
            Cached value or default
        """
        # Track access for promotion decisions
        self._record_access(key)

        # Try L1 first (fastest)
        value = self._get_from_l1(key)
        if value is not None:
            self._check_and_promote(key, value)
            return value

        # Try L3 (distributed/persistent) - skip L2 for sync
        value = self._get_from_l3(key)
        if value is not None:
            # Check if should promote to L1
            self._check_and_promote(key, value)
            return value

        # Check for promotion based on access frequency even for misses
        # This allows tier tracking to reflect access patterns
        self._check_and_promote_tier_only(key)

        # Miss in all tiers
        return default

    async def get_async(
        self,
        key: str,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """
        Get a value from the tiered cache (async version with L2 Redis).

        Lookup order: L1 -> L2 -> L3
        Side effects: May promote data to L1 if access frequency threshold met.

        Args:
            key: Cache key
            default: Default value if key not found in any tier

        Returns:
            Cached value or default
        """
        # Track access for promotion decisions
        self._record_access(key)

        # Try L1 first (fastest)
        value = self._get_from_l1(key)
        if value is not None:
            self._check_and_promote(key, value)
            return value

        # Try L2 (Redis)
        value = await self._get_from_l2(key)
        if value is not None:
            # Check if should promote to L1
            self._check_and_promote(key, value)
            return value

        # Try L3 (distributed/persistent)
        value = self._get_from_l3(key)
        if value is not None:
            # Check if should promote
            self._check_and_promote(key, value)
            return value

        # Check for promotion based on access frequency even for misses
        self._check_and_promote_tier_only(key)

        # Miss in all tiers
        return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tier: Optional[CacheTier] = None,
    ) -> None:
        """
        Set a value in the tiered cache.

        By default, writes to L2 (Redis) and selectively to L1 for hot data.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
            tier: Optional specific tier to write to (for cache warming)
        """
        # Record access
        self._record_access(key)

        # Serialize value if needed
        serialized = self._serialize(value)

        # Determine target tier
        if tier == CacheTier.L1:
            self._set_in_l1(key, serialized)
        elif tier == CacheTier.L2:
            await self._set_in_l2(key, serialized, ttl)
        elif tier == CacheTier.L3:
            self._set_in_l3(key, serialized, ttl)
        else:
            # Default: write to L2, and L1 if hot
            await self._set_in_l2(key, serialized, ttl)

            # Also set in L1 if this is a hot key
            if self._should_promote_to_l1(key):
                self._set_in_l1(key, serialized)
                self._update_tier(key, CacheTier.L1)

    async def delete(self, key: str) -> bool:
        """
        Delete a key from all cache tiers.

        Gracefully handles Redis unavailability - continues to delete
        from L1 and L3 even if L2 fails.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted from at least one tier
        """
        deleted = False

        # Delete from L1
        if self._l1_cache.delete(key):
            deleted = True

        # Delete from L2 (graceful degradation)
        if self._l2_client and not self._l2_degraded:
            try:
                result = await self._l2_client.delete(key)
                if result:
                    deleted = True
            except Exception as e:
                logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 delete failed for key '{key}': {e}")
                with self._stats_lock:
                    self._stats.redis_failures += 1
                self._l2_degraded = True
                self._last_l2_failure = time.time()

        # Delete from L3
        with self._l3_lock:
            if key in self._l3_cache:
                del self._l3_cache[key]
                deleted = True

        # Clear access record
        with self._access_lock:
            self._access_records.pop(key, None)

        return deleted

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in any cache tier.

        Gracefully handles Redis unavailability - continues to check
        L1 and L3 even if L2 fails.

        Args:
            key: Cache key

        Returns:
            True if key exists in any tier
        """
        # Check L1
        if self._l1_cache.exists(key):
            return True

        # Check L2 (graceful degradation)
        if self._l2_client and not self._l2_degraded:
            try:
                exists = await self._l2_client.exists(key)
                if exists:
                    return True
            except Exception as e:
                logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 exists check failed: {e}")
                with self._stats_lock:
                    self._stats.redis_failures += 1
                self._l2_degraded = True
                self._last_l2_failure = time.time()

        # Check L3
        with self._l3_lock:
            if key in self._l3_cache:
                cached = self._l3_cache[key]
                if time.time() - cached.get("timestamp", 0) < self.config.l3_ttl:
                    return True

        return False

    def get_tier(self, key: str) -> str:
        """
        Get the current tier for a key.

        Args:
            key: Cache key

        Returns:
            Tier name (L1, L2, L3, or NONE)
        """
        with self._access_lock:
            record = self._access_records.get(key)
            if record:
                return record.current_tier.value
        return CacheTier.NONE.value

    def get_access_stats(self, key: str) -> Dict[str, Any]:
        """
        Get access statistics for a key.

        Useful for debugging and monitoring tier promotion decisions.

        Args:
            key: Cache key

        Returns:
            Dictionary with access frequency and tier info
        """
        with self._access_lock:
            record = self._access_records.get(key)
            if record:
                return {
                    "key": key,
                    "accesses_per_minute": record.accesses_per_minute,
                    "hours_since_access": record.hours_since_access,
                    "current_tier": record.current_tier.value,
                    "promotion_threshold": self.config.promotion_threshold,
                    "would_promote": record.accesses_per_minute >= self.config.promotion_threshold,
                }
        return {
            "key": key,
            "accesses_per_minute": 0,
            "hours_since_access": None,
            "current_tier": CacheTier.NONE.value,
            "promotion_threshold": self.config.promotion_threshold,
            "would_promote": False,
        }

    async def clear(self) -> None:
        """Clear all caches."""
        # Clear L1
        self._l1_cache.clear()

        # Clear L2 (careful - only clear our keys, not entire Redis)
        # In production, use a key prefix pattern
        if self._l2_client and not self._l2_degraded:
            logger.warning("L2 clear not implemented - would clear all Redis keys")

        # Clear L3
        with self._l3_lock:
            self._l3_cache.clear()

        # Clear access records
        with self._access_lock:
            self._access_records.clear()

        logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager '{self.name}' cleared")

    # -------------------------------------------------------------------------
    # Internal tier operations
    # -------------------------------------------------------------------------

    def _get_from_l1(self, key: str) -> Optional[Any]:
        """Get from L1 (in-process cache)."""
        value = self._l1_cache.get(key)
        with self._stats_lock:
            if value is not None:
                self._stats.l1_hits += 1
                self._update_tier(key, CacheTier.L1)
            else:
                self._stats.l1_misses += 1
        return self._deserialize(value) if value is not None else None

    async def _get_from_l2(self, key: str) -> Optional[Any]:
        """Get from L2 (Redis cache) with graceful degradation."""
        if not self._l2_client:
            return None

        # If degraded, check if we should try recovery
        if self._l2_degraded:
            if self._should_try_l2_recovery():
                await self._try_l2_recovery()
            if self._l2_degraded:
                return None

        try:
            cached_json = await self._l2_client.get(key)
            if cached_json:
                cached = json.loads(cached_json)
                with self._stats_lock:
                    self._stats.l2_hits += 1
                self._update_tier(key, CacheTier.L2)
                return cached.get("data")
            else:
                with self._stats_lock:
                    self._stats.l2_misses += 1
        except Exception as e:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 get failed for key '{key}': {e}")
            with self._stats_lock:
                self._stats.redis_failures += 1
            # Enter degraded mode - operations continue via L1 + L3
            self._l2_degraded = True
            self._last_l2_failure = time.time()

        return None

    def _get_from_l3(self, key: str) -> Optional[Any]:
        """Get from L3 (distributed/persistent cache)."""
        if not self.config.l3_enabled:
            return None

        with self._l3_lock:
            if key in self._l3_cache:
                cached = self._l3_cache[key]
                # Check TTL
                if time.time() - cached.get("timestamp", 0) < self.config.l3_ttl:
                    with self._stats_lock:
                        self._stats.l3_hits += 1
                    self._update_tier(key, CacheTier.L3)
                    return cached.get("data")
                else:
                    # Expired, remove
                    del self._l3_cache[key]

            with self._stats_lock:
                self._stats.l3_misses += 1

        return None

    def _set_in_l1(self, key: str, value: Any) -> None:
        """Set in L1 (in-process cache)."""
        self._l1_cache.set(key, value)
        self._update_tier(key, CacheTier.L1)

    async def _set_in_l2(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set in L2 (Redis cache) with graceful degradation to L3."""
        if not self._l2_client:
            # No Redis client, fall back to L3
            self._set_in_l3(key, value, ttl)
            return

        # If degraded, check if we should try recovery
        if self._l2_degraded:
            if self._should_try_l2_recovery():
                await self._try_l2_recovery()
            if self._l2_degraded:
                # Still degraded, fall back to L3
                self._set_in_l3(key, value, ttl)
                return

        effective_ttl = ttl or self.config.l2_ttl
        cache_data = {"data": value, "timestamp": time.time()}

        try:
            await self._l2_client.setex(key, effective_ttl, json.dumps(cache_data))
            self._update_tier(key, CacheTier.L2)
        except Exception as e:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 set failed for key '{key}': {e}")
            with self._stats_lock:
                self._stats.redis_failures += 1
            # Enter degraded mode and fall back to L3
            self._l2_degraded = True
            self._last_l2_failure = time.time()
            self._set_in_l3(key, value, ttl)

    def _set_in_l3(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set in L3 (distributed/persistent cache)."""
        if not self.config.l3_enabled:
            return

        cache_data = {
            "data": value,
            "timestamp": time.time(),
            "ttl": ttl or self.config.l3_ttl,
        }

        with self._l3_lock:
            self._l3_cache[key] = cache_data
        self._update_tier(key, CacheTier.L3)

    # -------------------------------------------------------------------------
    # Promotion/demotion logic
    # -------------------------------------------------------------------------

    def _record_access(self, key: str) -> None:
        """Record an access for promotion tracking."""
        with self._access_lock:
            if key not in self._access_records:
                self._access_records[key] = AccessRecord(key=key)
            self._access_records[key].record_access()

    def _should_promote_to_l1(self, key: str) -> bool:
        """Check if a key should be promoted to L1."""
        with self._access_lock:
            record = self._access_records.get(key)
            if record:
                return record.accesses_per_minute >= self.config.promotion_threshold
        return False

    def _check_and_promote(self, key: str, value: Any) -> None:
        """Check if key should be promoted to L1 and do so if needed."""
        with self._access_lock:
            record = self._access_records.get(key)
            if not record:
                return

            # Promote to L1 if threshold met and not already there
            if (
                record.accesses_per_minute >= self.config.promotion_threshold
                and record.current_tier != CacheTier.L1
            ):
                self._set_in_l1(key, self._serialize(value))
                record.current_tier = CacheTier.L1
                with self._stats_lock:
                    self._stats.promotions += 1
                logger.debug(
                    f"[{CONSTITUTIONAL_HASH}] Promoted key '{key}' to L1 "
                    f"(accesses/min: {record.accesses_per_minute})"
                )

    def _check_and_promote_tier_only(self, key: str) -> None:
        """
        Check if key should be promoted to L1 tier based on access frequency.

        Unlike _check_and_promote, this only updates tier tracking without
        storing a value. Used for tracking hot keys that don't yet have data.
        """
        with self._access_lock:
            record = self._access_records.get(key)
            if not record:
                return

            # Mark as L1 tier if threshold met (for future sets and tier queries)
            if (
                record.accesses_per_minute >= self.config.promotion_threshold
                and record.current_tier != CacheTier.L1
            ):
                record.current_tier = CacheTier.L1
                with self._stats_lock:
                    self._stats.promotions += 1
                logger.debug(
                    f"[{CONSTITUTIONAL_HASH}] Key '{key}' marked for L1 tier "
                    f"(accesses/min: {record.accesses_per_minute})"
                )

    def _update_tier(self, key: str, tier: CacheTier) -> None:
        """Update the tier record for a key."""
        with self._access_lock:
            if key in self._access_records:
                self._access_records[key].current_tier = tier
            else:
                self._access_records[key] = AccessRecord(key=key, current_tier=tier)

    async def run_demotion_check(self) -> int:
        """
        Run demotion check to move cold data to L3.

        Returns:
            Number of keys demoted
        """
        demoted = 0
        keys_to_demote = []

        with self._access_lock:
            for key, record in self._access_records.items():
                if (
                    record.hours_since_access >= self.config.demotion_threshold_hours
                    and record.current_tier in (CacheTier.L1, CacheTier.L2)
                ):
                    keys_to_demote.append((key, record))

        for key, record in keys_to_demote:
            # Get value from current tier
            value = None
            if record.current_tier == CacheTier.L1:
                value = self._l1_cache.get(key)
                if value is not None:
                    self._l1_cache.delete(key)
            elif record.current_tier == CacheTier.L2 and self._l2_client:
                try:
                    cached = await self._l2_client.get(key)
                    if cached:
                        value = json.loads(cached).get("data")
                        await self._l2_client.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to demote key '{key}' from L2: {e}")

            # Move to L3
            if value is not None:
                self._set_in_l3(key, value)
                with self._access_lock:
                    if key in self._access_records:
                        self._access_records[key].current_tier = CacheTier.L3
                with self._stats_lock:
                    self._stats.demotions += 1
                demoted += 1

        if demoted > 0:
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Demoted {demoted} keys to L3 "
                f"(threshold: {self.config.demotion_threshold_hours}h)"
            )

        return demoted

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _serialize(self, value: Any) -> Any:
        """Serialize value if configured."""
        if self.config.serialize and not isinstance(value, str):
            try:
                return json.dumps(value)
            except (TypeError, ValueError):
                return value
        return value

    def _deserialize(self, value: Any) -> Any:
        """Deserialize value if configured."""
        if self.config.serialize and isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                return value
        return value

    # -------------------------------------------------------------------------
    # Statistics and monitoring
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with per-tier and aggregate stats
        """
        with self._stats_lock:
            return {
                "name": self.name,
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "tiers": {
                    "l1": {
                        "hits": self._stats.l1_hits,
                        "misses": self._stats.l1_misses,
                        "hit_ratio": self._stats.l1_hit_ratio,
                        "size": self._l1_cache.size,
                        "maxsize": self.config.l1_maxsize,
                    },
                    "l2": {
                        "hits": self._stats.l2_hits,
                        "misses": self._stats.l2_misses,
                        "available": self._l2_client is not None,
                        "degraded": self._l2_degraded,
                        "failures": self._stats.redis_failures,
                    },
                    "l3": {
                        "hits": self._stats.l3_hits,
                        "misses": self._stats.l3_misses,
                        "enabled": self.config.l3_enabled,
                        "size": len(self._l3_cache),
                    },
                },
                "aggregate": {
                    "total_hits": self._stats.total_hits,
                    "total_misses": self._stats.total_misses,
                    "hit_ratio": self._stats.hit_ratio,
                    "promotions": self._stats.promotions,
                    "demotions": self._stats.demotions,
                },
                "config": {
                    "l1_ttl": self.config.l1_ttl,
                    "l2_ttl": self.config.l2_ttl,
                    "l3_ttl": self.config.l3_ttl,
                    "promotion_threshold": self.config.promotion_threshold,
                    "demotion_threshold_hours": self.config.demotion_threshold_hours,
                },
            }

    @property
    def stats(self) -> TieredCacheStats:
        """Get raw statistics object."""
        return self._stats

    @property
    def is_l2_available(self) -> bool:
        """Check if L2 (Redis) is available."""
        return self._l2_client is not None and not self._l2_degraded

    @property
    def is_degraded(self) -> bool:
        """Check if cache is running in degraded mode (L2 unavailable)."""
        return self._l2_degraded

    async def check_l2_health(self) -> bool:
        """
        Explicitly check L2 (Redis) health and attempt recovery if degraded.

        This method can be called periodically or on-demand to check if
        Redis has recovered and restore normal operation.

        Returns:
            True if L2 is healthy and available
        """
        if self._l2_client is None:
            return False

        if self._l2_degraded:
            return await self._try_l2_recovery()

        # Not degraded, verify connection is still good
        try:
            await self._l2_client.ping()
            return True
        except Exception as e:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] L2 health check failed: {e}")
            with self._stats_lock:
                self._stats.redis_failures += 1
            self._l2_degraded = True
            self._last_l2_failure = time.time()
            return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TieredCacheManager(name='{self.name}', "
            f"l1_size={self._l1_cache.size}/{self.config.l1_maxsize}, "
            f"l2_available={self.is_l2_available}, "
            f"hit_ratio={self._stats.hit_ratio:.2%})"
        )


# -----------------------------------------------------------------------------
# Singleton pattern for shared usage
# -----------------------------------------------------------------------------

_default_manager: Optional[TieredCacheManager] = None
_singleton_lock = threading.Lock()


def get_tiered_cache(
    config: Optional[TieredCacheConfig] = None,
    name: str = "default",
) -> TieredCacheManager:
    """
    Get or create the singleton TieredCacheManager instance.

    Thread-safe singleton pattern for shared cache access across the application.

    Args:
        config: Optional TieredCacheConfig (used only on first call)
        name: Cache name (used only on first call)

    Returns:
        TieredCacheManager singleton instance
    """
    global _default_manager

    if _default_manager is None:
        with _singleton_lock:
            if _default_manager is None:
                _default_manager = TieredCacheManager(config=config, name=name)
                logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager singleton created")

    return _default_manager


def reset_tiered_cache() -> None:
    """
    Reset the singleton TieredCacheManager instance.

    Useful for testing or when configuration needs to change.
    """
    global _default_manager

    with _singleton_lock:
        if _default_manager is not None:
            # Close is async, so we run it in an event loop if possible
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_default_manager.close())
                else:
                    loop.run_until_complete(_default_manager.close())
            except RuntimeError:
                # No event loop, just clear the reference
                pass
            _default_manager = None
            logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager singleton reset")


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Enums
    "CacheTier",
    # Classes
    "TieredCacheManager",
    "TieredCacheConfig",
    "TieredCacheStats",
    "AccessRecord",
    # Functions
    "get_tiered_cache",
    "reset_tiered_cache",
]
