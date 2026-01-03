"""
ACGS-2 Tiered Cache Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/tiered_cache.py focusing on tier promotion/demotion logic.
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import module under test
from shared.tiered_cache import (
    CONSTITUTIONAL_HASH,
    AccessRecord,
    CacheTier,
    TieredCacheConfig,
    TieredCacheManager,
    TieredCacheStats,
    get_tiered_cache,
    reset_tiered_cache,
)

# ============================================================================
# CacheTier Enum Tests
# ============================================================================


class TestCacheTierEnum:
    """Test CacheTier enumeration."""

    def test_l1_tier_value(self):
        """Test L1 tier value."""
        assert CacheTier.L1.value == "L1"

    def test_l2_tier_value(self):
        """Test L2 tier value."""
        assert CacheTier.L2.value == "L2"

    def test_l3_tier_value(self):
        """Test L3 tier value."""
        assert CacheTier.L3.value == "L3"

    def test_none_tier_value(self):
        """Test NONE tier value."""
        assert CacheTier.NONE.value == "NONE"

    def test_all_tiers_defined(self):
        """Test all expected tiers exist."""
        tiers = [t.value for t in CacheTier]
        assert "L1" in tiers
        assert "L2" in tiers
        assert "L3" in tiers
        assert "NONE" in tiers


# ============================================================================
# TieredCacheConfig Tests
# ============================================================================


class TestTieredCacheConfig:
    """Test TieredCacheConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TieredCacheConfig()
        assert config.l1_maxsize == 1024
        assert config.l1_ttl == 300
        assert config.l2_ttl == 3600
        assert config.l3_ttl == 86400
        assert config.l3_enabled is True
        assert config.promotion_threshold == 10
        assert config.demotion_threshold_hours == 1.0
        assert config.serialize is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TieredCacheConfig(
            l1_maxsize=512,
            l1_ttl=120,
            l2_ttl=1800,
            l3_ttl=43200,
            l3_enabled=False,
            promotion_threshold=5,
            demotion_threshold_hours=0.5,
            serialize=False,
        )
        assert config.l1_maxsize == 512
        assert config.l1_ttl == 120
        assert config.l2_ttl == 1800
        assert config.l3_ttl == 43200
        assert config.l3_enabled is False
        assert config.promotion_threshold == 5
        assert config.demotion_threshold_hours == 0.5
        assert config.serialize is False

    def test_partial_custom_values(self):
        """Test partial custom configuration."""
        config = TieredCacheConfig(promotion_threshold=20)
        assert config.promotion_threshold == 20
        assert config.l1_maxsize == 1024  # Default


# ============================================================================
# TieredCacheStats Tests
# ============================================================================


class TestTieredCacheStats:
    """Test TieredCacheStats dataclass."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = TieredCacheStats()
        assert stats.l1_hits == 0
        assert stats.l1_misses == 0
        assert stats.l2_hits == 0
        assert stats.l2_misses == 0
        assert stats.l3_hits == 0
        assert stats.l3_misses == 0
        assert stats.promotions == 0
        assert stats.demotions == 0
        assert stats.redis_failures == 0

    def test_total_hits_property(self):
        """Test total_hits aggregates all tiers."""
        stats = TieredCacheStats(l1_hits=10, l2_hits=20, l3_hits=5)
        assert stats.total_hits == 35

    def test_total_misses_property(self):
        """Test total_misses aggregates all tiers."""
        stats = TieredCacheStats(l1_misses=5, l2_misses=10, l3_misses=3)
        assert stats.total_misses == 18

    def test_hit_ratio_property(self):
        """Test hit_ratio calculation."""
        stats = TieredCacheStats(l1_hits=80, l2_hits=10, l3_hits=5, l3_misses=5)
        # 95 hits, 5 misses = 95%
        assert stats.hit_ratio == 0.95

    def test_hit_ratio_zero_accesses(self):
        """Test hit_ratio with no accesses."""
        stats = TieredCacheStats()
        assert stats.hit_ratio == 0.0

    def test_l1_hit_ratio_property(self):
        """Test L1-specific hit ratio."""
        stats = TieredCacheStats(l1_hits=90, l1_misses=10)
        assert stats.l1_hit_ratio == 0.9


# ============================================================================
# AccessRecord Tests
# ============================================================================


class TestAccessRecord:
    """Test AccessRecord for access tracking."""

    def test_default_initialization(self):
        """Test AccessRecord default values."""
        record = AccessRecord(key="test_key")
        assert record.key == "test_key"
        assert record.access_times == []
        assert record.current_tier == CacheTier.NONE
        assert record.last_access <= time.time()

    def test_record_access_adds_timestamp(self):
        """Test record_access adds current timestamp."""
        record = AccessRecord(key="test_key")
        record.access_times = []  # Clear any init times

        before = time.time()
        record.record_access()
        after = time.time()

        assert len(record.access_times) == 1
        assert before <= record.access_times[0] <= after

    def test_record_access_updates_last_access(self):
        """Test record_access updates last_access time."""
        record = AccessRecord(key="test_key")
        old_last = record.last_access

        time.sleep(0.01)  # Small delay
        record.record_access()

        assert record.last_access >= old_last

    def test_accesses_per_minute_counts_recent(self):
        """Test accesses_per_minute counts only last minute."""
        record = AccessRecord(key="test_key")
        now = time.time()

        # Add 5 recent accesses
        record.access_times = [now - 30, now - 20, now - 10, now - 5, now]

        assert record.accesses_per_minute == 5

    def test_accesses_per_minute_excludes_old(self):
        """Test accesses_per_minute excludes accesses older than 1 minute."""
        record = AccessRecord(key="test_key")
        now = time.time()

        # 3 old accesses (>60s ago), 2 recent
        record.access_times = [now - 120, now - 90, now - 65, now - 10, now]

        assert record.accesses_per_minute == 2

    def test_hours_since_access(self):
        """Test hours_since_access calculation."""
        record = AccessRecord(key="test_key")

        # Set last_access to 2 hours ago
        record.last_access = time.time() - 7200

        hours = record.hours_since_access
        assert 1.9 < hours < 2.1  # Allow small tolerance

    def test_record_access_prunes_old_entries(self):
        """Test record_access removes entries older than 1 minute."""
        record = AccessRecord(key="test_key")
        now = time.time()

        # Add old entries
        record.access_times = [now - 120, now - 90, now - 65]

        # Record new access - should prune old entries
        record.record_access()

        # Only the new access should remain (old ones pruned)
        assert len(record.access_times) == 1


# ============================================================================
# TieredCacheManager Initialization Tests
# ============================================================================


class TestTieredCacheManagerInit:
    """Test TieredCacheManager initialization."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_tiered_cache()
        yield
        reset_tiered_cache()

    def test_default_initialization(self):
        """Test manager initializes with defaults."""
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager()

        assert manager.name == "default"
        assert manager.config.l1_maxsize == 1024
        assert manager._l2_client is None
        assert manager._l2_degraded is False

    def test_custom_name(self):
        """Test manager with custom name."""
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(name="custom_cache")

        assert manager.name == "custom_cache"

    def test_custom_config(self):
        """Test manager with custom config."""
        config = TieredCacheConfig(l1_maxsize=256, promotion_threshold=5)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        assert manager.config.l1_maxsize == 256
        assert manager.config.promotion_threshold == 5

    def test_l1_ttl_adjusted_if_exceeds_l2(self):
        """Test L1 TTL is adjusted to not exceed L2 TTL."""
        config = TieredCacheConfig(l1_ttl=7200, l2_ttl=3600)  # L1 > L2
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        # L1 TTL should be adjusted to match L2 TTL
        assert manager.config.l1_ttl == 3600

    def test_constitutional_hash_correct(self):
        """Test constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# ============================================================================
# Tier Promotion Logic Tests
# ============================================================================


class TestTierPromotionLogic:
    """Test tier promotion based on access frequency."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TieredCacheManager for testing."""
        reset_tiered_cache()
        config = TieredCacheConfig(promotion_threshold=10)
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_should_promote_below_threshold(self, manager):
        """Test _should_promote_to_l1 returns False below threshold."""
        key = "test_key"
        # Record 5 accesses (below threshold of 10)
        for _ in range(5):
            manager._record_access(key)

        assert manager._should_promote_to_l1(key) is False

    def test_should_promote_at_threshold(self, manager):
        """Test _should_promote_to_l1 returns True at threshold."""
        key = "test_key"
        # Record 10 accesses (at threshold)
        for _ in range(10):
            manager._record_access(key)

        assert manager._should_promote_to_l1(key) is True

    def test_should_promote_above_threshold(self, manager):
        """Test _should_promote_to_l1 returns True above threshold."""
        key = "test_key"
        # Record 15 accesses (above threshold)
        for _ in range(15):
            manager._record_access(key)

        assert manager._should_promote_to_l1(key) is True

    def test_should_promote_unknown_key(self, manager):
        """Test _should_promote_to_l1 returns False for unknown key."""
        assert manager._should_promote_to_l1("unknown_key") is False

    def test_check_and_promote_promotes_to_l1(self, manager):
        """Test _check_and_promote moves hot data to L1."""
        key = "hot_key"
        value = {"data": "important"}

        # Record enough accesses to trigger promotion
        for _ in range(12):
            manager._record_access(key)

        # Set initial tier to L2
        manager._access_records[key].current_tier = CacheTier.L2

        # Check and promote
        manager._check_and_promote(key, value)

        # Should be promoted to L1
        assert manager._access_records[key].current_tier == CacheTier.L1
        assert manager._stats.promotions == 1

    def test_check_and_promote_no_action_if_already_l1(self, manager):
        """Test _check_and_promote doesn't re-promote if already L1."""
        key = "hot_key"
        value = {"data": "important"}

        # Record enough accesses
        for _ in range(15):
            manager._record_access(key)

        # Already in L1
        manager._access_records[key].current_tier = CacheTier.L1

        # Check and promote
        manager._check_and_promote(key, value)

        # Promotions counter should not increment
        assert manager._stats.promotions == 0

    def test_check_and_promote_tier_only(self, manager):
        """Test _check_and_promote_tier_only marks key for L1 tier."""
        key = "hot_key"

        # Record enough accesses
        for _ in range(12):
            manager._record_access(key)

        # Set initial tier
        manager._access_records[key].current_tier = CacheTier.L2

        # Check tier only (no value)
        manager._check_and_promote_tier_only(key)

        # Should be marked for L1
        assert manager._access_records[key].current_tier == CacheTier.L1
        assert manager._stats.promotions == 1

    def test_promotion_threshold_custom_value(self):
        """Test promotion with custom threshold."""
        reset_tiered_cache()
        config = TieredCacheConfig(promotion_threshold=5)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        key = "test_key"
        # Record 5 accesses (at custom threshold)
        for _ in range(5):
            manager._record_access(key)

        assert manager._should_promote_to_l1(key) is True
        reset_tiered_cache()

    def test_get_access_stats_returns_promotion_info(self, manager):
        """Test get_access_stats shows promotion decision info."""
        key = "test_key"

        # Record 12 accesses
        for _ in range(12):
            manager._record_access(key)

        stats = manager.get_access_stats(key)

        assert stats["key"] == key
        assert stats["accesses_per_minute"] == 12
        assert stats["promotion_threshold"] == 10
        assert stats["would_promote"] is True

    def test_get_access_stats_unknown_key(self, manager):
        """Test get_access_stats for unknown key."""
        stats = manager.get_access_stats("unknown_key")

        assert stats["key"] == "unknown_key"
        assert stats["accesses_per_minute"] == 0
        assert stats["current_tier"] == "NONE"
        assert stats["would_promote"] is False


# ============================================================================
# Tier Demotion Logic Tests
# ============================================================================


class TestTierDemotionLogic:
    """Test tier demotion based on access inactivity."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TieredCacheManager for testing."""
        reset_tiered_cache()
        config = TieredCacheConfig(
            demotion_threshold_hours=1.0,
            l3_enabled=True,
        )
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    @pytest.mark.asyncio
    async def test_demotion_check_demotes_cold_l1_keys(self, manager):
        """Test run_demotion_check moves cold L1 data to L3."""
        key = "cold_key"
        value = "cold_data"

        # Set up in L1 with old access time
        manager._l1_cache.set(key, value)
        manager._access_records[key] = AccessRecord(
            key=key,
            current_tier=CacheTier.L1,
        )
        # Set last_access to 2 hours ago (> demotion threshold)
        manager._access_records[key].last_access = time.time() - 7200

        # Run demotion check
        demoted = await manager.run_demotion_check()

        assert demoted == 1
        assert manager._access_records[key].current_tier == CacheTier.L3
        assert manager._stats.demotions == 1

    @pytest.mark.asyncio
    async def test_demotion_check_skips_recent_keys(self, manager):
        """Test run_demotion_check skips recently accessed keys."""
        key = "hot_key"
        value = "hot_data"

        # Set up in L1 with recent access
        manager._l1_cache.set(key, value)
        manager._access_records[key] = AccessRecord(
            key=key,
            current_tier=CacheTier.L1,
        )
        manager._access_records[key].last_access = time.time()

        # Run demotion check
        demoted = await manager.run_demotion_check()

        assert demoted == 0
        assert manager._access_records[key].current_tier == CacheTier.L1

    @pytest.mark.asyncio
    async def test_demotion_check_skips_l3_keys(self, manager):
        """Test run_demotion_check skips keys already in L3."""
        key = "l3_key"

        # Already in L3 with old access
        manager._access_records[key] = AccessRecord(
            key=key,
            current_tier=CacheTier.L3,
        )
        manager._access_records[key].last_access = time.time() - 7200

        # Run demotion check
        demoted = await manager.run_demotion_check()

        assert demoted == 0

    @pytest.mark.asyncio
    async def test_demotion_moves_value_to_l3(self, manager):
        """Test demotion actually moves value to L3 storage."""
        key = "cold_key"
        value = "cold_data"

        # Set up in L1
        manager._l1_cache.set(key, value)
        manager._access_records[key] = AccessRecord(
            key=key,
            current_tier=CacheTier.L1,
        )
        manager._access_records[key].last_access = time.time() - 7200

        # Run demotion
        await manager.run_demotion_check()

        # Value should be in L3
        assert key in manager._l3_cache
        assert manager._l3_cache[key]["data"] == value

    @pytest.mark.asyncio
    async def test_demotion_custom_threshold(self):
        """Test demotion with custom hour threshold."""
        reset_tiered_cache()
        config = TieredCacheConfig(demotion_threshold_hours=0.5)  # 30 minutes
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        key = "cold_key"
        value = "data"

        # Set up with 45-minute old access (> 30 min threshold)
        manager._l1_cache.set(key, value)
        manager._access_records[key] = AccessRecord(
            key=key,
            current_tier=CacheTier.L1,
        )
        manager._access_records[key].last_access = time.time() - (45 * 60)

        demoted = await manager.run_demotion_check()
        assert demoted == 1
        reset_tiered_cache()


# ============================================================================
# L3 Cache Operations Tests
# ============================================================================


class TestL3CacheOperations:
    """Test L3 cache tier operations."""

    @pytest.fixture
    def manager(self):
        """Create manager with L3 enabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(l3_enabled=True, l3_ttl=3600)
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_get_from_l3_returns_cached_value(self, manager):
        """Test _get_from_l3 returns cached value."""
        key = "l3_key"
        value = {"data": "test"}

        # Directly set in L3
        manager._l3_cache[key] = {
            "data": value,
            "timestamp": time.time(),
        }

        result = manager._get_from_l3(key)
        assert result == value

    def test_get_from_l3_tracks_stats(self, manager):
        """Test _get_from_l3 updates statistics."""
        key = "l3_key"
        manager._l3_cache[key] = {
            "data": "test",
            "timestamp": time.time(),
        }

        manager._get_from_l3(key)
        assert manager._stats.l3_hits == 1

    def test_get_from_l3_miss(self, manager):
        """Test _get_from_l3 returns None on miss."""
        result = manager._get_from_l3("nonexistent")
        assert result is None
        assert manager._stats.l3_misses == 1

    def test_get_from_l3_expired_entry(self, manager):
        """Test _get_from_l3 returns None for expired entry."""
        key = "expired_key"
        # Set with old timestamp (beyond TTL)
        manager._l3_cache[key] = {
            "data": "old_data",
            "timestamp": time.time() - 7200,  # 2 hours ago
        }

        result = manager._get_from_l3(key)
        assert result is None
        # Entry should be removed
        assert key not in manager._l3_cache

    def test_set_in_l3_stores_value(self, manager):
        """Test _set_in_l3 stores value correctly."""
        key = "new_key"
        value = {"data": "new"}

        manager._set_in_l3(key, value)

        assert key in manager._l3_cache
        assert manager._l3_cache[key]["data"] == value

    def test_set_in_l3_disabled(self):
        """Test _set_in_l3 does nothing when L3 disabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(l3_enabled=False)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        manager._set_in_l3("key", "value")
        assert len(manager._l3_cache) == 0
        reset_tiered_cache()


# ============================================================================
# Synchronous Get Tests
# ============================================================================


class TestSynchronousGet:
    """Test synchronous get() method (L1 + L3 only)."""

    @pytest.fixture
    def manager(self):
        """Create manager for sync get tests."""
        reset_tiered_cache()
        config = TieredCacheConfig(promotion_threshold=10, l3_enabled=True)
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_get_from_l1_hit(self, manager):
        """Test sync get returns L1 cached value."""
        key = "l1_key"
        value = "l1_value"

        manager._l1_cache.set(key, value)

        result = manager.get(key)
        assert result == value
        assert manager._stats.l1_hits == 1

    def test_get_from_l3_hit(self, manager):
        """Test sync get returns L3 value on L1 miss."""
        key = "l3_key"
        value = "l3_value"

        manager._l3_cache[key] = {
            "data": value,
            "timestamp": time.time(),
        }

        result = manager.get(key)
        assert result == value
        assert manager._stats.l1_misses == 1
        assert manager._stats.l3_hits == 1

    def test_get_default_on_miss(self, manager):
        """Test sync get returns default on total miss."""
        result = manager.get("nonexistent", default="fallback")
        assert result == "fallback"

    def test_get_records_access(self, manager):
        """Test sync get records access for promotion tracking."""
        key = "tracked_key"
        manager._l1_cache.set(key, "value")

        manager.get(key)

        assert key in manager._access_records
        assert manager._access_records[key].accesses_per_minute >= 1

    def test_get_triggers_promotion_check(self, manager):
        """Test sync get checks for promotion after access."""
        key = "hot_key"
        value = "hot_value"

        # Pre-populate L3 with value
        manager._l3_cache[key] = {
            "data": value,
            "timestamp": time.time(),
        }

        # Access many times to trigger promotion
        for _ in range(12):
            manager.get(key)

        # Key should be promoted to L1
        assert manager._access_records[key].current_tier == CacheTier.L1


# ============================================================================
# Graceful Degradation Tests
# ============================================================================


class TestGracefulDegradation:
    """Test graceful degradation when Redis (L2) is unavailable."""

    @pytest.fixture
    def manager(self):
        """Create manager for degradation tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    def test_redis_health_change_to_unhealthy(self, manager):
        """Test manager enters degraded mode on Redis UNHEALTHY."""
        from shared.redis_config import RedisHealthState

        assert manager._l2_degraded is False

        manager._on_redis_health_change(RedisHealthState.HEALTHY, RedisHealthState.UNHEALTHY)

        assert manager._l2_degraded is True
        assert manager._last_l2_failure > 0

    def test_redis_health_change_to_healthy(self, manager):
        """Test manager exits degraded mode on Redis HEALTHY."""
        from shared.redis_config import RedisHealthState

        # Start in degraded mode
        manager._l2_degraded = True
        manager._last_l2_failure = time.time()

        manager._on_redis_health_change(RedisHealthState.UNHEALTHY, RedisHealthState.HEALTHY)

        assert manager._l2_degraded is False
        assert manager._last_l2_failure == 0.0

    def test_is_degraded_property(self, manager):
        """Test is_degraded property reflects degraded state."""
        assert manager.is_degraded is False

        manager._l2_degraded = True
        assert manager.is_degraded is True

    def test_is_l2_available_property(self, manager):
        """Test is_l2_available reflects L2 availability."""
        # No client, not available
        assert manager.is_l2_available is False

        # Set mock client but degraded
        manager._l2_client = MagicMock()
        manager._l2_degraded = True
        assert manager.is_l2_available is False

        # Client available and not degraded
        manager._l2_degraded = False
        assert manager.is_l2_available is True

    def test_should_try_l2_recovery(self, manager):
        """Test _should_try_l2_recovery timing logic."""
        manager._l2_client = MagicMock()
        manager._l2_degraded = True
        manager._l2_recovery_interval = 30.0

        # Just failed - don't retry
        manager._last_l2_failure = time.time()
        assert manager._should_try_l2_recovery() is False

        # Failed long ago - retry
        manager._last_l2_failure = time.time() - 60
        assert manager._should_try_l2_recovery() is True

    @pytest.mark.asyncio
    async def test_try_l2_recovery_success(self, manager):
        """Test _try_l2_recovery on successful ping."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        manager._l2_client = mock_client
        manager._l2_degraded = True
        manager._last_l2_failure = time.time() - 60

        result = await manager._try_l2_recovery()

        assert result is True
        assert manager._l2_degraded is False

    @pytest.mark.asyncio
    async def test_try_l2_recovery_failure(self, manager):
        """Test _try_l2_recovery on failed ping."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=ConnectionError("Connection refused"))

        manager._l2_client = mock_client
        manager._l2_degraded = True
        manager._last_l2_failure = time.time() - 60

        with patch("shared.tiered_cache.logger"):
            result = await manager._try_l2_recovery()

        assert result is False
        assert manager._l2_degraded is True


# ============================================================================
# TTL Consistency Tests
# ============================================================================


class TestTTLConsistency:
    """Test TTL consistency across cache tiers."""

    def test_l1_ttl_never_exceeds_l2(self):
        """Test L1 TTL is adjusted to not exceed L2 TTL."""
        reset_tiered_cache()
        config = TieredCacheConfig(l1_ttl=7200, l2_ttl=3600)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        assert manager.config.l1_ttl <= manager.config.l2_ttl
        reset_tiered_cache()

    def test_l1_ttl_equal_to_l2_allowed(self):
        """Test L1 TTL equal to L2 TTL is valid."""
        reset_tiered_cache()
        config = TieredCacheConfig(l1_ttl=3600, l2_ttl=3600)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        assert manager.config.l1_ttl == 3600
        assert manager.config.l2_ttl == 3600
        reset_tiered_cache()

    def test_l1_ttl_less_than_l2_preserved(self):
        """Test L1 TTL less than L2 TTL is preserved."""
        reset_tiered_cache()
        config = TieredCacheConfig(l1_ttl=300, l2_ttl=3600)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        assert manager.config.l1_ttl == 300
        assert manager.config.l2_ttl == 3600
        reset_tiered_cache()


# ============================================================================
# Thread Safety Tests
# ============================================================================


class TestThreadSafety:
    """Test thread safety of TieredCacheManager."""

    @pytest.fixture
    def manager(self):
        """Create manager for thread safety tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    def test_concurrent_access_recording(self, manager):
        """Test concurrent access recording is thread-safe."""
        errors = []
        key = "concurrent_key"

        def record_access():
            try:
                for _ in range(100):
                    manager._record_access(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_access) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert key in manager._access_records

    def test_concurrent_l1_get(self, manager):
        """Test concurrent L1 cache gets are thread-safe."""
        key = "l1_key"
        manager._l1_cache.set(key, "value")

        results = []
        errors = []

        def get_value():
            try:
                for _ in range(50):
                    result = manager.get(key)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_value) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 500
        assert all(r == "value" for r in results)

    def test_concurrent_stats_updates(self, manager):
        """Test concurrent statistics updates are thread-safe."""
        errors = []

        def update_stats():
            try:
                for _ in range(100):
                    with manager._stats_lock:
                        manager._stats.l1_hits += 1
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_stats) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert manager._stats.l1_hits == 1000


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestSingletonPattern:
    """Test get_tiered_cache singleton function."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_tiered_cache()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_tiered_cache()

    def test_returns_tiered_cache_manager_instance(self):
        """Test get_tiered_cache returns TieredCacheManager."""
        with patch("shared.tiered_cache.logger"):
            cache = get_tiered_cache()

        assert isinstance(cache, TieredCacheManager)

    def test_returns_same_instance(self):
        """Test get_tiered_cache returns same instance on multiple calls."""
        with patch("shared.tiered_cache.logger"):
            cache1 = get_tiered_cache()
            cache2 = get_tiered_cache()

        assert cache1 is cache2

    def test_reset_creates_new_instance(self):
        """Test reset_tiered_cache allows new instance creation."""
        with patch("shared.tiered_cache.logger"):
            cache1 = get_tiered_cache()
            reset_tiered_cache()
            cache2 = get_tiered_cache()

        assert cache1 is not cache2


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test cache statistics tracking."""

    @pytest.fixture
    def manager(self):
        """Create manager for stats tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    def test_get_stats_structure(self, manager):
        """Test get_stats returns expected structure."""
        stats = manager.get_stats()

        assert "name" in stats
        assert "constitutional_hash" in stats
        assert "tiers" in stats
        assert "aggregate" in stats
        assert "config" in stats

        # Check tier sections
        assert "l1" in stats["tiers"]
        assert "l2" in stats["tiers"]
        assert "l3" in stats["tiers"]

        # Check aggregate sections
        assert "total_hits" in stats["aggregate"]
        assert "total_misses" in stats["aggregate"]
        assert "hit_ratio" in stats["aggregate"]
        assert "promotions" in stats["aggregate"]
        assert "demotions" in stats["aggregate"]

    def test_get_stats_l1_section(self, manager):
        """Test get_stats L1 section contains expected fields."""
        stats = manager.get_stats()
        l1 = stats["tiers"]["l1"]

        assert "hits" in l1
        assert "misses" in l1
        assert "hit_ratio" in l1
        assert "size" in l1
        assert "maxsize" in l1

    def test_get_stats_l2_section(self, manager):
        """Test get_stats L2 section contains expected fields."""
        stats = manager.get_stats()
        l2 = stats["tiers"]["l2"]

        assert "hits" in l2
        assert "misses" in l2
        assert "available" in l2
        assert "degraded" in l2
        assert "failures" in l2

    def test_stats_property(self, manager):
        """Test stats property returns TieredCacheStats."""
        stats = manager.stats
        assert isinstance(stats, TieredCacheStats)

    def test_repr(self, manager):
        """Test __repr__ format."""
        repr_str = repr(manager)

        assert "TieredCacheManager" in repr_str
        assert "name='test'" in repr_str
        assert "l1_size=" in repr_str
        assert "l2_available=" in repr_str
        assert "hit_ratio=" in repr_str


# ============================================================================
# Tier Tracking Tests
# ============================================================================


class TestTierTracking:
    """Test tier tracking and get_tier functionality."""

    @pytest.fixture
    def manager(self):
        """Create manager for tier tracking tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    def test_get_tier_unknown_key(self, manager):
        """Test get_tier returns NONE for unknown key."""
        tier = manager.get_tier("unknown")
        assert tier == "NONE"

    def test_get_tier_after_l1_set(self, manager):
        """Test get_tier returns L1 after L1 set."""
        key = "l1_key"
        manager._set_in_l1(key, "value")

        tier = manager.get_tier(key)
        assert tier == "L1"

    def test_get_tier_after_l3_set(self, manager):
        """Test get_tier returns L3 after L3 set."""
        key = "l3_key"
        manager._set_in_l3(key, "value")

        tier = manager.get_tier(key)
        assert tier == "L3"

    def test_update_tier_creates_record(self, manager):
        """Test _update_tier creates record if missing."""
        key = "new_key"

        manager._update_tier(key, CacheTier.L2)

        assert key in manager._access_records
        assert manager._access_records[key].current_tier == CacheTier.L2

    def test_update_tier_updates_existing(self, manager):
        """Test _update_tier updates existing record."""
        key = "existing_key"
        manager._access_records[key] = AccessRecord(key=key, current_tier=CacheTier.L3)

        manager._update_tier(key, CacheTier.L1)

        assert manager._access_records[key].current_tier == CacheTier.L1


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    """Test serialization/deserialization logic."""

    @pytest.fixture
    def manager(self):
        """Create manager with serialization enabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(serialize=True)
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_serialize_dict(self, manager):
        """Test serializing dictionary value."""
        value = {"key": "value", "number": 42}
        serialized = manager._serialize(value)

        assert isinstance(serialized, str)
        assert "key" in serialized

    def test_serialize_string_unchanged(self, manager):
        """Test strings are not double-serialized."""
        value = "already a string"
        serialized = manager._serialize(value)

        assert serialized == value

    def test_deserialize_json_string(self, manager):
        """Test deserializing JSON string."""
        serialized = '{"key": "value"}'
        deserialized = manager._deserialize(serialized)

        assert isinstance(deserialized, dict)
        assert deserialized["key"] == "value"

    def test_deserialize_invalid_json(self, manager):
        """Test deserializing invalid JSON returns original."""
        value = "not valid json {"
        deserialized = manager._deserialize(value)

        assert deserialized == value

    def test_serialization_disabled(self):
        """Test with serialization disabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(serialize=False)
        with patch("shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)

        value = {"key": "value"}
        serialized = manager._serialize(value)

        # Should return original object
        assert serialized is value
        reset_tiered_cache()


# ============================================================================
# Delete and Exists Tests
# ============================================================================


class TestDeleteAndExists:
    """Test delete and exists operations."""

    @pytest.fixture
    def manager(self):
        """Create manager for delete/exists tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    @pytest.mark.asyncio
    async def test_delete_from_l1(self, manager):
        """Test delete removes from L1."""
        key = "l1_key"
        manager._l1_cache.set(key, "value")

        deleted = await manager.delete(key)

        assert deleted is True
        assert not manager._l1_cache.exists(key)

    @pytest.mark.asyncio
    async def test_delete_from_l3(self, manager):
        """Test delete removes from L3."""
        key = "l3_key"
        manager._l3_cache[key] = {"data": "value", "timestamp": time.time()}

        deleted = await manager.delete(key)

        assert deleted is True
        assert key not in manager._l3_cache

    @pytest.mark.asyncio
    async def test_delete_clears_access_record(self, manager):
        """Test delete clears access tracking."""
        key = "tracked_key"
        manager._access_records[key] = AccessRecord(key=key)
        manager._l1_cache.set(key, "value")

        await manager.delete(key)

        assert key not in manager._access_records

    @pytest.mark.asyncio
    async def test_exists_l1_hit(self, manager):
        """Test exists returns True for L1 key."""
        key = "l1_key"
        manager._l1_cache.set(key, "value")

        exists = await manager.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_l3_hit(self, manager):
        """Test exists returns True for L3 key."""
        key = "l3_key"
        manager._l3_cache[key] = {"data": "value", "timestamp": time.time()}

        exists = await manager.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_miss(self, manager):
        """Test exists returns False for nonexistent key."""
        exists = await manager.exists("nonexistent")
        assert exists is False


# ============================================================================
# Clear Tests
# ============================================================================


class TestClear:
    """Test clear operation."""

    @pytest.fixture
    def manager(self):
        """Create manager for clear tests."""
        reset_tiered_cache()
        with patch("shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    @pytest.mark.asyncio
    async def test_clear_l1(self, manager):
        """Test clear removes L1 entries."""
        manager._l1_cache.set("key1", "value1")
        manager._l1_cache.set("key2", "value2")

        await manager.clear()

        assert manager._l1_cache.size == 0

    @pytest.mark.asyncio
    async def test_clear_l3(self, manager):
        """Test clear removes L3 entries."""
        manager._l3_cache["key1"] = {"data": "value"}
        manager._l3_cache["key2"] = {"data": "value"}

        await manager.clear()

        assert len(manager._l3_cache) == 0

    @pytest.mark.asyncio
    async def test_clear_access_records(self, manager):
        """Test clear removes access records."""
        manager._access_records["key1"] = AccessRecord(key="key1")
        manager._access_records["key2"] = AccessRecord(key="key2")

        await manager.clear()

        assert len(manager._access_records) == 0


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_in_module(self):
        """Verify constitutional hash is exported."""
        from shared import tiered_cache

        assert hasattr(tiered_cache, "CONSTITUTIONAL_HASH")
        assert tiered_cache.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
