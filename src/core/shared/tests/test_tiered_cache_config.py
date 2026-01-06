"""
ACGS-2 Tiered Cache Manager Tests - Config & Management
Focused tests for enums, configs, stats, and singleton behavior.
"""

from unittest.mock import patch

import pytest
from src.core.shared.tiered_cache import (
    CONSTITUTIONAL_HASH,
    CacheTier,
    TieredCacheConfig,
    TieredCacheManager,
    TieredCacheStats,
    get_tiered_cache,
    reset_tiered_cache,
)


class TestCacheTierEnum:
    """Test CacheTier enumeration."""

    def test_l1_tier_value(self):
        """Test L1 tier value."""
        assert CacheTier.L1.value == "L1"

    def test_all_tiers_defined(self):
        """Test all expected tiers exist."""
        tiers = [t.value for t in CacheTier]
        assert "L1" in tiers
        assert "L2" in tiers
        assert "L3" in tiers
        assert "NONE" in tiers


class TestTieredCacheConfig:
    """Test TieredCacheConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TieredCacheConfig()
        assert config.l1_maxsize == 1024
        assert config.l1_ttl == 300
        assert config.promotion_threshold == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TieredCacheConfig(l1_maxsize=512, promotion_threshold=5)
        assert config.l1_maxsize == 512
        assert config.promotion_threshold == 5


class TestTieredCacheStats:
    """Test TieredCacheStats dataclass."""

    def test_total_hits_property(self):
        """Test total_hits aggregates all tiers."""
        stats = TieredCacheStats(l1_hits=10, l2_hits=20, l3_hits=5)
        assert stats.total_hits == 35

    def test_hit_ratio_property(self):
        """Test hit_ratio calculation."""
        stats = TieredCacheStats(l1_hits=80, l2_hits=10, l3_hits=5, l3_misses=5)
        assert stats.hit_ratio == 0.95


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
        with patch("src.core.shared.tiered_cache.logger"):
            manager = TieredCacheManager()
        assert manager.name == "default"

    def test_constitutional_hash_correct(self):
        """Test constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


class TestTTLConsistency:
    """Test TTL consistency across cache tiers."""

    def test_l1_ttl_never_exceeds_l2(self):
        """Test L1 TTL is adjusted to not exceed L2 TTL."""
        reset_tiered_cache()
        config = TieredCacheConfig(l1_ttl=7200, l2_ttl=3600)
        with patch("src.core.shared.tiered_cache.logger"):
            manager = TieredCacheManager(config=config)
        assert manager.config.l1_ttl <= manager.config.l2_ttl
        reset_tiered_cache()


class TestSingletonPattern:
    """Test get_tiered_cache singleton function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_tiered_cache()
        yield
        reset_tiered_cache()

    def test_returns_same_instance(self):
        """Test get_tiered_cache returns same instance on multiple calls."""
        with patch("src.core.shared.tiered_cache.logger"):
            cache1 = get_tiered_cache()
            cache2 = get_tiered_cache()
        assert cache1 is cache2


class TestStatistics:
    """Test cache statistics tracking."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_tiered_cache()
        yield
        reset_tiered_cache()

    def test_get_stats_structure(self):
        """Test get_stats returns expected structure."""
        with patch("src.core.shared.tiered_cache.logger"):
            manager = TieredCacheManager()
        stats = manager.get_stats()
        assert "name" in stats
        assert "tiers" in stats


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
