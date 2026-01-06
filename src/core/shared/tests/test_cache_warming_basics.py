"""
ACGS-2 Cache Warming Module Tests - Basics
Focused tests for enums, configs, and basic warmer initialization.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest
from src.core.shared.cache_warming import (
    CONSTITUTIONAL_HASH,
    CacheWarmer,
    WarmingConfig,
    WarmingProgress,
    WarmingResult,
    WarmingStatus,
    get_cache_warmer,
    reset_cache_warmer,
)


class TestWarmingStatusEnum:
    """Test WarmingStatus enumeration."""

    def test_idle_status_value(self):
        """Test IDLE status value."""
        assert WarmingStatus.IDLE.value == "idle"

    def test_warming_status_value(self):
        """Test WARMING status value."""
        assert WarmingStatus.WARMING.value == "warming"

    def test_completed_status_value(self):
        """Test COMPLETED status value."""
        assert WarmingStatus.COMPLETED.value == "completed"

    def test_failed_status_value(self):
        """Test FAILED status value."""
        assert WarmingStatus.FAILED.value == "failed"

    def test_cancelled_status_value(self):
        """Test CANCELLED status value."""
        assert WarmingStatus.CANCELLED.value == "cancelled"

    def test_all_statuses_defined(self):
        """Test all expected statuses exist."""
        statuses = [s.value for s in WarmingStatus]
        assert "idle" in statuses
        assert "warming" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses


class TestWarmingConfig:
    """Test WarmingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WarmingConfig()
        assert config.rate_limit == 100
        assert config.batch_size == 10
        assert config.l1_count == 10
        assert config.l2_count == 100
        assert config.key_timeout == 1.0
        assert config.total_timeout == 300.0
        assert config.max_retries == 3
        assert config.retry_delay == 0.5
        assert config.priority_keys == []

    def test_custom_values(self):
        """Test custom configuration values."""
        config = WarmingConfig(
            rate_limit=50,
            batch_size=20,
            l1_count=5,
            l2_count=50,
            key_timeout=2.0,
            total_timeout=600.0,
            max_retries=5,
            retry_delay=1.0,
            priority_keys=["key1", "key2"],
        )
        assert config.rate_limit == 50
        assert config.batch_size == 20
        assert config.l1_count == 5
        assert config.l2_count == 50
        assert config.key_timeout == 2.0
        assert config.total_timeout == 600.0
        assert config.max_retries == 5
        assert config.retry_delay == 1.0
        assert config.priority_keys == ["key1", "key2"]


class TestWarmingResult:
    """Test WarmingResult dataclass."""

    def test_default_values(self):
        """Test default result values."""
        result = WarmingResult(status=WarmingStatus.COMPLETED)
        assert result.status == WarmingStatus.COMPLETED
        assert result.keys_warmed == 0
        assert result.keys_failed == 0
        assert result.l1_keys == 0
        assert result.l2_keys == 0
        assert result.duration_seconds == 0.0
        assert result.error_message is None
        assert result.details == {}

    def test_success_property_completed(self):
        """Test success property for completed status."""
        result = WarmingResult(status=WarmingStatus.COMPLETED)
        assert result.success is True

    def test_success_property_failed(self):
        """Test success property for failed status."""
        result = WarmingResult(status=WarmingStatus.FAILED)
        assert result.success is False

    def test_success_rate_all_warmed(self):
        """Test success rate with all keys warmed."""
        result = WarmingResult(
            status=WarmingStatus.COMPLETED,
            keys_warmed=100,
            keys_failed=0,
        )
        assert result.success_rate == 1.0


class TestWarmingProgress:
    """Test WarmingProgress dataclass."""

    def test_default_values(self):
        """Test default progress values."""
        progress = WarmingProgress()
        assert progress.total_keys == 0
        assert progress.processed_keys == 0
        assert progress.percent_complete == 0.0

    def test_percent_complete_partial(self):
        """Test percent complete with partial progress."""
        progress = WarmingProgress(total_keys=100, processed_keys=50)
        assert progress.percent_complete == 50.0


class TestCacheWarmerInit:
    """Test CacheWarmer initialization."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    def test_default_initialization(self):
        """Test warmer initializes with defaults."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer()

        assert warmer.config.rate_limit == 100
        assert warmer.status == WarmingStatus.IDLE

    def test_custom_rate_limit(self):
        """Test warmer with custom rate limit."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=50)

        assert warmer.config.rate_limit == 50

    def test_is_warming_property(self):
        """Test is_warming property."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer()

        assert warmer.is_warming is False
        warmer._status = WarmingStatus.WARMING
        assert warmer.is_warming is True


class TestCacheWarmerStatistics:
    """Test CacheWarmer get_stats method."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    def test_get_stats_structure(self):
        """Test get_stats returns expected structure."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer()

        stats = warmer.get_stats()
        assert "constitutional_hash" in stats
        assert "status" in stats
        assert "config" in stats
        assert "progress" in stats


class TestCacheWarmerSingleton:
    """Test get_cache_warmer singleton function."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_cache_warmer()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_cache_warmer()

    def test_returns_cache_warmer_instance(self):
        """Test get_cache_warmer returns CacheWarmer."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer = get_cache_warmer()
        assert isinstance(warmer, CacheWarmer)

    def test_returns_same_instance(self):
        """Test get_cache_warmer returns same instance on multiple calls."""
        with patch("src.core.shared.cache_warming.logger"):
            warmer1 = get_cache_warmer()
            warmer2 = get_cache_warmer()
        assert warmer1 is warmer2


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
