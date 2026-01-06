"""
ACGS-2 Tiered Cache Manager Tests - Logic
Focused tests for promotion, demotion, L3 operations, and thread safety.
"""

import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.shared.tiered_cache import (
    AccessRecord,
    CacheTier,
    TieredCacheConfig,
    TieredCacheManager,
    reset_tiered_cache,
)


class TestAccessRecord:
    """Test AccessRecord for access tracking."""

    def test_default_initialization(self):
        """Test AccessRecord default values."""
        record = AccessRecord(key="test_key")
        assert record.key == "test_key"
        assert record.access_times == []

    def test_record_access_adds_timestamp(self):
        """Test record_access adds current timestamp."""
        record = AccessRecord(key="test_key")
        record.record_access()
        assert len(record.access_times) == 1


class TestTierPromotionLogic:
    """Test tier promotion based on access frequency."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TieredCacheManager for testing."""
        reset_tiered_cache()
        config = TieredCacheConfig(promotion_threshold=10)
        with patch("src.core.shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_should_promote_at_threshold(self, manager):
        """Test _should_promote_to_l1 returns True at threshold."""
        key = "test_key"
        for _ in range(10):
            manager._record_access(key)
        assert manager._should_promote_to_l1(key) is True

    def test_check_and_promote_promotes_to_l1(self, manager):
        """Test _check_and_promote moves hot data to L1."""
        key = "hot_key"
        value = {"data": "important"}
        for _ in range(12):
            manager._record_access(key)
        manager._access_records[key].current_tier = CacheTier.L2
        manager._check_and_promote(key, value)
        assert manager._access_records[key].current_tier == CacheTier.L1


class TestTierDemotionLogic:
    """Test tier demotion based on access inactivity."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TieredCacheManager for testing."""
        reset_tiered_cache()
        config = TieredCacheConfig(demotion_threshold_hours=1.0, l3_enabled=True)
        with patch("src.core.shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    @pytest.mark.asyncio
    async def test_demotion_check_demotes_cold_l1_keys(self, manager):
        """Test run_demotion_check moves cold L1 data to L3."""
        key = "cold_key"
        value = "cold_data"
        manager._l1_cache.set(key, value)
        manager._access_records[key] = AccessRecord(key=key, current_tier=CacheTier.L1)
        manager._access_records[key].last_access = time.time() - 7200
        demoted = await manager.run_demotion_check()
        assert demoted == 1
        assert manager._access_records[key].current_tier == CacheTier.L3


class TestL3CacheOperations:
    """Test L3 cache tier operations."""

    @pytest.fixture
    def manager(self):
        """Create manager with L3 enabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(l3_enabled=True, l3_ttl=3600)
        with patch("src.core.shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_get_from_l3_returns_cached_value(self, manager):
        """Test _get_from_l3 returns cached value."""
        key = "l3_key"
        value = {"data": "test"}
        manager._l3_cache[key] = {"data": value, "timestamp": time.time()}
        result = manager._get_from_l3(key)
        assert result == value


class TestSynchronousGet:
    """Test synchronous get() method (L1 + L3 only)."""

    @pytest.fixture
    def manager(self):
        """Create manager for sync get tests."""
        reset_tiered_cache()
        config = TieredCacheConfig(promotion_threshold=10, l3_enabled=True)
        with patch("src.core.shared.tiered_cache.logger"):
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


class TestGracefulDegradation:
    """Test graceful degradation when Redis (L2) is unavailable."""

    @pytest.fixture
    def manager(self):
        """Create manager for degradation tests."""
        reset_tiered_cache()
        with patch("src.core.shared.tiered_cache.logger"):
            mgr = TieredCacheManager(name="test")
        yield mgr
        reset_tiered_cache()

    def test_redis_health_change_to_unhealthy(self, manager):
        """Test manager enters degraded mode on Redis UNHEALTHY."""
        from src.core.shared.redis_config import RedisHealthState

        manager._on_redis_health_change(RedisHealthState.HEALTHY, RedisHealthState.UNHEALTHY)
        assert manager._l2_degraded is True


class TestThreadSafety:
    """Test thread safety of TieredCacheManager."""

    @pytest.fixture
    def manager(self):
        """Create manager for thread safety tests."""
        reset_tiered_cache()
        with patch("src.core.shared.tiered_cache.logger"):
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


class TestSerialization:
    """Test serialization/deserialization logic."""

    @pytest.fixture
    def manager(self):
        """Create manager with serialization enabled."""
        reset_tiered_cache()
        config = TieredCacheConfig(serialize=True)
        with patch("src.core.shared.tiered_cache.logger"):
            mgr = TieredCacheManager(config=config, name="test")
        yield mgr
        reset_tiered_cache()

    def test_serialize_dict(self, manager):
        """Test serializing dictionary value."""
        value = {"key": "value", "number": 42}
        serialized = manager._serialize(value)
        assert isinstance(serialized, str)


@pytest.mark.asyncio
async def test_delete_and_exists():
    """Test delete and exists operations."""
    reset_tiered_cache()
    with patch("src.core.shared.tiered_cache.logger"):
        manager = TieredCacheManager(name="test")
    key = "l1_key"
    manager._l1_cache.set(key, "value")
    exists = await manager.exists(key)
    assert exists is True
    await manager.delete(key)
    exists = await manager.exists(key)
    assert exists is False
    reset_tiered_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
