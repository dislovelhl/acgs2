"""
ACGS-2 Cache Warming Module Tests - Logic
Focused tests for warm_cache logic, rate limiting, priority loading, and key loading.
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.shared.cache_warming import (
    CacheWarmer,
    RateLimiter,
    WarmingConfig,
    WarmingStatus,
    reset_cache_warmer,
)


@pytest.fixture
def mock_cache_manager():
    """Create a mock TieredCacheManager."""
    manager = MagicMock()
    manager._l3_cache = {}
    manager._l3_lock = threading.Lock()
    manager._access_records = {}
    manager._access_lock = threading.Lock()
    manager.get = MagicMock(return_value=None)
    manager.set = AsyncMock()
    return manager


class TestCacheWarmerWarmCache:
    """Test CacheWarmer warm_cache method."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_warm_cache_with_source_keys(self, mock_cache_manager):
        """Test warming with explicit source keys."""
        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
            "key2": {"data": "value2", "timestamp": time.time()},
        }
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=["key1", "key2"])
        assert result.status == WarmingStatus.COMPLETED
        assert result.keys_warmed == 2

    @pytest.mark.asyncio
    async def test_warm_cache_l1_l2_distribution(self, mock_cache_manager):
        """Test keys are distributed to L1 and L2 correctly."""
        keys = [f"key{i}" for i in range(15)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(l1_count=5, l2_count=15)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        assert result.l1_keys == 5
        assert result.l2_keys == 10


class TestRateLimiter:
    """Test RateLimiter token bucket algorithm."""

    def test_acquire_immediate_success(self):
        """Test acquiring tokens when available."""
        limiter = RateLimiter(tokens_per_second=100.0)
        wait_time = limiter.acquire(10)
        assert wait_time == 0.0
        assert limiter.tokens == 90.0

    @pytest.mark.asyncio
    async def test_acquire_async_waits(self):
        """Test async acquire waits when needed."""
        limiter = RateLimiter(tokens_per_second=1000.0, max_tokens=10)
        limiter.tokens = 0
        start = time.monotonic()
        await limiter.acquire_async(10)
        elapsed = time.monotonic() - start
        assert 0.005 <= elapsed <= 0.05


class TestRateLimitingBehavior:
    """Test rate limiting behavior in CacheWarmer."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_warming_respects_rate_limit(self, mock_cache_manager):
        """Test warming respects configured rate limit."""
        keys = [f"key{i}" for i in range(50)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(rate_limit=1000, batch_size=10)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)
        assert result.status == WarmingStatus.COMPLETED


class TestPriorityLoading:
    """Test priority loading logic."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_top_10_to_l1(self, mock_cache_manager):
        """Test top 10 keys are loaded to L1."""
        keys = [f"key{i}" for i in range(20)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(l1_count=10, l2_count=20)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)
        assert result.l1_keys == 10
        assert result.l2_keys == 10


class TestKeyLoading:
    """Test key loading from various sources."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_load_from_l3_cache(self, mock_cache_manager):
        """Test loading keys from L3 cache."""
        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
            "key2": {"data": "value2", "timestamp": time.time()},
        }
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache()
        assert result.keys_warmed == 2


class TestRetryLogic:
    """Test retry logic for failed key loads."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, mock_cache_manager):
        """Test retrying on key load failure."""
        attempts = [0]

        def flaky_loader(key):
            attempts[0] += 1
            if attempts[0] < 3:
                raise RuntimeError("Temporary failure")
            return "value"

        config = WarmingConfig(max_retries=3, retry_delay=0.01)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=["key1"], key_loader=flaky_loader)
        assert result.keys_warmed == 1
        assert attempts[0] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
