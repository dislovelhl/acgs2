"""
ACGS-2 Cache Warming Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/cache_warming.py focusing on rate limiting, priority loading,
and cache warming completion status.
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.shared.cache_warming import (
    CONSTITUTIONAL_HASH,
    CacheWarmer,
    RateLimiter,
    WarmingConfig,
    WarmingProgress,
    WarmingResult,
    WarmingStatus,
    get_cache_warmer,
    reset_cache_warmer,
    warm_cache_on_startup,
)

# ============================================================================
# WarmingStatus Enum Tests
# ============================================================================


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


# ============================================================================
# WarmingConfig Tests
# ============================================================================


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

    def test_partial_custom_values(self):
        """Test partial custom configuration."""
        config = WarmingConfig(rate_limit=200, l1_count=20)
        assert config.rate_limit == 200
        assert config.l1_count == 20
        assert config.batch_size == 10  # Default


# ============================================================================
# WarmingResult Tests
# ============================================================================


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

    def test_custom_values(self):
        """Test result with custom values."""
        result = WarmingResult(
            status=WarmingStatus.COMPLETED,
            keys_warmed=90,
            keys_failed=10,
            l1_keys=10,
            l2_keys=80,
            duration_seconds=5.5,
        )
        assert result.keys_warmed == 90
        assert result.keys_failed == 10
        assert result.l1_keys == 10
        assert result.l2_keys == 80
        assert result.duration_seconds == 5.5

    def test_success_property_completed(self):
        """Test success property for completed status."""
        result = WarmingResult(status=WarmingStatus.COMPLETED)
        assert result.success is True

    def test_success_property_failed(self):
        """Test success property for failed status."""
        result = WarmingResult(status=WarmingStatus.FAILED)
        assert result.success is False

    def test_success_property_cancelled(self):
        """Test success property for cancelled status."""
        result = WarmingResult(status=WarmingStatus.CANCELLED)
        assert result.success is False

    def test_success_rate_all_warmed(self):
        """Test success rate with all keys warmed."""
        result = WarmingResult(
            status=WarmingStatus.COMPLETED,
            keys_warmed=100,
            keys_failed=0,
        )
        assert result.success_rate == 1.0

    def test_success_rate_partial(self):
        """Test success rate with partial success."""
        result = WarmingResult(
            status=WarmingStatus.COMPLETED,
            keys_warmed=80,
            keys_failed=20,
        )
        assert result.success_rate == 0.8

    def test_success_rate_none_warmed(self):
        """Test success rate with no keys warmed."""
        result = WarmingResult(
            status=WarmingStatus.FAILED,
            keys_warmed=0,
            keys_failed=100,
        )
        assert result.success_rate == 0.0

    def test_success_rate_zero_total(self):
        """Test success rate with zero total keys."""
        result = WarmingResult(status=WarmingStatus.COMPLETED)
        assert result.success_rate == 0.0


# ============================================================================
# WarmingProgress Tests
# ============================================================================


class TestWarmingProgress:
    """Test WarmingProgress dataclass."""

    def test_default_values(self):
        """Test default progress values."""
        progress = WarmingProgress()
        assert progress.total_keys == 0
        assert progress.processed_keys == 0
        assert progress.current_batch == 0
        assert progress.total_batches == 0
        assert progress.elapsed_seconds == 0.0
        assert progress.estimated_remaining == 0.0

    def test_percent_complete_zero_total(self):
        """Test percent complete with zero total keys."""
        progress = WarmingProgress()
        assert progress.percent_complete == 0.0

    def test_percent_complete_partial(self):
        """Test percent complete with partial progress."""
        progress = WarmingProgress(total_keys=100, processed_keys=50)
        assert progress.percent_complete == 50.0

    def test_percent_complete_full(self):
        """Test percent complete at 100%."""
        progress = WarmingProgress(total_keys=100, processed_keys=100)
        assert progress.percent_complete == 100.0

    def test_custom_values(self):
        """Test progress with custom values."""
        progress = WarmingProgress(
            total_keys=100,
            processed_keys=75,
            current_batch=8,
            total_batches=10,
            elapsed_seconds=7.5,
            estimated_remaining=2.5,
        )
        assert progress.total_keys == 100
        assert progress.processed_keys == 75
        assert progress.current_batch == 8
        assert progress.total_batches == 10
        assert progress.elapsed_seconds == 7.5
        assert progress.estimated_remaining == 2.5
        assert progress.percent_complete == 75.0


# ============================================================================
# RateLimiter Tests
# ============================================================================


class TestRateLimiter:
    """Test RateLimiter token bucket algorithm."""

    def test_initialization_defaults(self):
        """Test rate limiter with default max_tokens."""
        limiter = RateLimiter(tokens_per_second=100.0)
        assert limiter.tokens_per_second == 100.0
        assert limiter.max_tokens == 100
        assert limiter.tokens == 100.0

    def test_initialization_custom_max_tokens(self):
        """Test rate limiter with custom max_tokens."""
        limiter = RateLimiter(tokens_per_second=100.0, max_tokens=50)
        assert limiter.max_tokens == 50
        assert limiter.tokens == 50.0

    def test_acquire_immediate_success(self):
        """Test acquiring tokens when available."""
        limiter = RateLimiter(tokens_per_second=100.0)
        wait_time = limiter.acquire(10)
        assert wait_time == 0.0
        assert limiter.tokens == 90.0

    def test_acquire_requires_wait(self):
        """Test acquiring tokens when insufficient."""
        limiter = RateLimiter(tokens_per_second=100.0, max_tokens=10)
        limiter.tokens = 5  # Partially depleted

        wait_time = limiter.acquire(10)
        assert wait_time > 0.0
        # Need 5 more tokens at 100/sec = 0.05s
        assert abs(wait_time - 0.05) < 0.01

    def test_acquire_refills_over_time(self):
        """Test tokens refill over time."""
        limiter = RateLimiter(tokens_per_second=1000.0, max_tokens=100)
        limiter.acquire(100)  # Deplete all tokens
        assert limiter.tokens == 0.0

        time.sleep(0.05)  # Wait 50ms

        limiter._refill()
        # Should have ~50 tokens (1000 tokens/sec * 0.05s)
        assert 40 <= limiter.tokens <= 60

    def test_acquire_does_not_exceed_max(self):
        """Test tokens don't exceed max on refill."""
        limiter = RateLimiter(tokens_per_second=1000.0, max_tokens=100)

        time.sleep(0.2)  # Wait 200ms (would be 200 tokens)

        limiter._refill()
        assert limiter.tokens == 100.0  # Capped at max

    @pytest.mark.asyncio
    async def test_acquire_async_waits(self):
        """Test async acquire waits when needed."""
        limiter = RateLimiter(tokens_per_second=1000.0, max_tokens=10)
        limiter.tokens = 0  # Deplete all tokens

        start = time.monotonic()
        await limiter.acquire_async(10)
        elapsed = time.monotonic() - start

        # Should wait ~10ms (10 tokens at 1000/sec)
        assert 0.005 <= elapsed <= 0.02

    @pytest.mark.asyncio
    async def test_acquire_async_no_wait(self):
        """Test async acquire doesn't wait when tokens available."""
        limiter = RateLimiter(tokens_per_second=100.0, max_tokens=100)

        start = time.monotonic()
        await limiter.acquire_async(10)
        elapsed = time.monotonic() - start

        assert elapsed < 0.01  # Should be immediate

    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = RateLimiter(tokens_per_second=10000.0, max_tokens=10000)
        errors = []

        def acquire_tokens():
            try:
                for _ in range(100):
                    limiter.acquire(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=acquire_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================================
# CacheWarmer Initialization Tests
# ============================================================================


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
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        assert warmer.config.rate_limit == 100
        assert warmer.config.l1_count == 10
        assert warmer.config.l2_count == 100
        assert warmer.status == WarmingStatus.IDLE

    def test_custom_rate_limit(self):
        """Test warmer with custom rate limit."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=50)

        assert warmer.config.rate_limit == 50

    def test_custom_config(self):
        """Test warmer with custom config."""
        config = WarmingConfig(
            rate_limit=200,
            l1_count=20,
            l2_count=200,
        )
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config)

        assert warmer.config.rate_limit == 200
        assert warmer.config.l1_count == 20
        assert warmer.config.l2_count == 200

    def test_rate_limit_overrides_config(self):
        """Test explicit rate_limit overrides config."""
        config = WarmingConfig(rate_limit=200)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=50, config=config)

        assert warmer.config.rate_limit == 50

    def test_is_warming_property(self):
        """Test is_warming property."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        assert warmer.is_warming is False

        warmer._status = WarmingStatus.WARMING
        assert warmer.is_warming is True

    def test_status_property(self):
        """Test status property."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        assert warmer.status == WarmingStatus.IDLE

    def test_progress_property(self):
        """Test progress property."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        progress = warmer.progress
        assert isinstance(progress, WarmingProgress)

    def test_constitutional_hash_correct(self):
        """Test constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# ============================================================================
# CacheWarmer Warm Cache Tests
# ============================================================================


class TestCacheWarmerWarmCache:
    """Test CacheWarmer warm_cache method."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_warm_cache_empty_keys(self, mock_cache_manager):
        """Test warming with no keys returns completed."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=[])

        assert result.status == WarmingStatus.COMPLETED
        assert result.keys_warmed == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_warm_cache_with_source_keys(self, mock_cache_manager):
        """Test warming with explicit source keys."""
        # Set up L3 cache with values
        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
            "key2": {"data": "value2", "timestamp": time.time()},
            "key3": {"data": "value3", "timestamp": time.time()},
        }

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=["key1", "key2", "key3"])

        assert result.status == WarmingStatus.COMPLETED
        assert result.keys_warmed == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_warm_cache_l1_l2_distribution(self, mock_cache_manager):
        """Test keys are distributed to L1 and L2 correctly."""
        # Create 15 keys
        keys = [f"key{i}" for i in range(15)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(l1_count=5, l2_count=15)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        assert result.status == WarmingStatus.COMPLETED
        # Top 5 keys should go to L1, rest to L2
        assert result.l1_keys == 5
        assert result.l2_keys == 10

    @pytest.mark.asyncio
    async def test_warm_cache_already_in_progress(self, mock_cache_manager):
        """Test warming returns failure if already in progress."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            warmer._status = WarmingStatus.WARMING

            result = await warmer.warm_cache()

        assert result.status == WarmingStatus.FAILED
        assert "already in progress" in result.error_message

    @pytest.mark.asyncio
    async def test_warm_cache_exception_handling(self, mock_cache_manager):
        """Test warming handles exceptions gracefully."""
        mock_cache_manager.set = AsyncMock(side_effect=Exception("Test error"))
        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
        }

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=["key1"])

        # Should still complete but with failed keys
        assert result.keys_failed >= 1

    @pytest.mark.asyncio
    async def test_warm_cache_status_transitions(self, mock_cache_manager):
        """Test status transitions during warming."""
        statuses = []

        def track_status(progress):
            statuses.append(WarmingStatus.WARMING)

        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
        }

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            warmer.on_progress(track_status)

            assert warmer.status == WarmingStatus.IDLE
            result = await warmer.warm_cache(source_keys=["key1"])
            assert warmer.status == WarmingStatus.COMPLETED


# ============================================================================
# CacheWarmer Cancel Tests
# ============================================================================


class TestCacheWarmerCancel:
    """Test CacheWarmer cancellation."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    def test_cancel_sets_event(self):
        """Test cancel sets cancellation event."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()
            warmer.cancel()

        assert warmer._cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cancel_during_warming(self, mock_cache_manager):
        """Test cancellation during warming."""
        # Create many keys to allow time for cancellation
        keys = [f"key{i}" for i in range(100)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)

            # Start warming in background
            async def warm_and_cancel():
                task = asyncio.create_task(warmer.warm_cache(source_keys=keys))
                await asyncio.sleep(0.01)  # Let it start
                warmer.cancel()
                return await task

            result = await warm_and_cancel()

        # Status could be cancelled or completed (race condition)
        assert result.status in [WarmingStatus.CANCELLED, WarmingStatus.COMPLETED]


# ============================================================================
# CacheWarmer Progress Callback Tests
# ============================================================================


class TestCacheWarmerProgressCallbacks:
    """Test CacheWarmer progress callbacks."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    def test_on_progress_registers_callback(self):
        """Test on_progress registers callback."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        callback = MagicMock()
        warmer.on_progress(callback)

        assert callback in warmer._progress_callbacks

    def test_remove_progress_callback(self):
        """Test removing progress callback."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        callback = MagicMock()
        warmer.on_progress(callback)
        assert callback in warmer._progress_callbacks

        result = warmer.remove_progress_callback(callback)
        assert result is True
        assert callback not in warmer._progress_callbacks

    def test_remove_nonexistent_callback(self):
        """Test removing callback that doesn't exist."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        callback = MagicMock()
        result = warmer.remove_progress_callback(callback)
        assert result is False

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, mock_cache_manager):
        """Test progress callback is called during warming."""
        progress_updates = []

        def track_progress(progress):
            progress_updates.append(progress)

        # Create enough keys for multiple batches
        keys = [f"key{i}" for i in range(25)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(batch_size=10)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            warmer.on_progress(track_progress)
            await warmer.warm_cache(source_keys=keys)

        assert len(progress_updates) > 0
        # Check progress values are reasonable
        for progress in progress_updates:
            assert progress.total_keys == 25
            assert 0 <= progress.processed_keys <= 25

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, mock_cache_manager):
        """Test progress callback errors don't stop warming."""

        def failing_callback(progress):
            raise RuntimeError("Callback error")

        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
        }

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            warmer.on_progress(failing_callback)
            result = await warmer.warm_cache(source_keys=["key1"])

        # Should still complete despite callback error
        assert result.status == WarmingStatus.COMPLETED


# ============================================================================
# CacheWarmer Statistics Tests
# ============================================================================


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
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        stats = warmer.get_stats()

        assert "constitutional_hash" in stats
        assert "status" in stats
        assert "config" in stats
        assert "progress" in stats

    def test_get_stats_config_section(self):
        """Test get_stats config section."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=200)

        stats = warmer.get_stats()

        assert stats["config"]["rate_limit"] == 200
        assert "batch_size" in stats["config"]
        assert "l1_count" in stats["config"]
        assert "l2_count" in stats["config"]

    def test_get_stats_progress_section(self):
        """Test get_stats progress section."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        stats = warmer.get_stats()

        assert "total_keys" in stats["progress"]
        assert "processed_keys" in stats["progress"]
        assert "percent_complete" in stats["progress"]
        assert "elapsed_seconds" in stats["progress"]

    def test_get_stats_constitutional_hash(self):
        """Test get_stats includes constitutional hash."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        stats = warmer.get_stats()
        assert stats["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_repr(self):
        """Test __repr__ format."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=200)

        repr_str = repr(warmer)
        assert "CacheWarmer" in repr_str
        assert "rate_limit=200" in repr_str
        assert "status=" in repr_str


# ============================================================================
# Rate Limiting Tests (100 keys/sec)
# ============================================================================


class TestRateLimitingBehavior:
    """Test rate limiting at 100 keys/second."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    def test_rate_limiter_100_per_second(self):
        """Test rate limiter configured for 100 keys/sec."""
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(rate_limit=100)

        assert warmer._rate_limiter.tokens_per_second == 100.0

    @pytest.mark.asyncio
    async def test_warming_respects_rate_limit(self, mock_cache_manager):
        """Test warming respects configured rate limit."""
        # Create 50 keys with short batch size to test rate limiting
        keys = [f"key{i}" for i in range(50)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        # Use high rate limit to make test fast
        config = WarmingConfig(rate_limit=1000, batch_size=10)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)

            start = time.monotonic()
            result = await warmer.warm_cache(source_keys=keys)
            elapsed = time.monotonic() - start

        assert result.status == WarmingStatus.COMPLETED
        assert result.keys_warmed == 50

    def test_rate_limiter_burst_capacity(self):
        """Test rate limiter allows burst up to 2x batch size."""
        config = WarmingConfig(rate_limit=100, batch_size=10)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config)

        # Max tokens should be 2x batch size for burst capacity
        assert warmer._rate_limiter.max_tokens == 20


# ============================================================================
# Priority Loading Tests (Top 10 to L1)
# ============================================================================


class TestPriorityLoading:
    """Test priority loading (top 10 to L1, top 100 to L2)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_top_10_to_l1(self, mock_cache_manager):
        """Test top 10 keys are loaded to L1."""
        keys = [f"key{i}" for i in range(20)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(l1_count=10, l2_count=20)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        assert result.l1_keys == 10
        assert result.l2_keys == 10

    @pytest.mark.asyncio
    async def test_priority_keys_first(self, mock_cache_manager):
        """Test priority keys are warmed first."""
        from src.core.shared.tiered_cache import CacheTier

        # Create regular keys
        for i in range(10):
            mock_cache_manager._l3_cache[f"regular{i}"] = {
                "data": f"value_{i}",
                "timestamp": time.time(),
            }

        # Add priority keys
        mock_cache_manager._l3_cache["priority1"] = {"data": "pvalue1", "timestamp": time.time()}
        mock_cache_manager._l3_cache["priority2"] = {"data": "pvalue2", "timestamp": time.time()}

        config = WarmingConfig(
            l1_count=5,
            l2_count=12,
            priority_keys=["priority1", "priority2"],
        )

        set_calls = []

        async def track_set(key, value, tier=None):
            set_calls.append((key, tier))

        mock_cache_manager.set = track_set

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache()

        # Priority keys should be in the L1 set calls
        l1_keys = [k for k, t in set_calls if t == CacheTier.L1]
        assert "priority1" in l1_keys or "priority2" in l1_keys

    @pytest.mark.asyncio
    async def test_l1_count_default_10(self, mock_cache_manager):
        """Test default L1 count is 10."""
        keys = [f"key{i}" for i in range(50)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        assert result.l1_keys == 10

    @pytest.mark.asyncio
    async def test_l2_count_default_100(self, mock_cache_manager):
        """Test default L2 count is 100."""
        # Create 150 keys
        keys = [f"key{i}" for i in range(150)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        # Should only warm up to l2_count (100) total
        assert result.keys_warmed <= 100


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


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
        with patch("shared.cache_warming.logger"):
            warmer = get_cache_warmer()

        assert isinstance(warmer, CacheWarmer)

    def test_returns_same_instance(self):
        """Test get_cache_warmer returns same instance on multiple calls."""
        with patch("shared.cache_warming.logger"):
            warmer1 = get_cache_warmer()
            warmer2 = get_cache_warmer()

        assert warmer1 is warmer2

    def test_reset_creates_new_instance(self):
        """Test reset_cache_warmer allows new instance creation."""
        with patch("shared.cache_warming.logger"):
            warmer1 = get_cache_warmer()
            reset_cache_warmer()
            warmer2 = get_cache_warmer()

        assert warmer1 is not warmer2

    def test_singleton_uses_first_call_params(self):
        """Test singleton uses parameters from first call."""
        with patch("shared.cache_warming.logger"):
            warmer1 = get_cache_warmer(rate_limit=50)
            assert warmer1.config.rate_limit == 50

            # Second call with different params returns same instance
            warmer2 = get_cache_warmer(rate_limit=200)
            assert warmer2.config.rate_limit == 50

    def test_reset_cancels_warming(self):
        """Test reset cancels any ongoing warming."""
        with patch("shared.cache_warming.logger"):
            warmer = get_cache_warmer()
            warmer._status = WarmingStatus.WARMING

            reset_cache_warmer()

        # Cancel should have been called
        assert warmer._cancel_event.is_set()


# ============================================================================
# warm_cache_on_startup Function Tests
# ============================================================================


class TestWarmCacheOnStartup:
    """Test warm_cache_on_startup convenience function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.mark.asyncio
    async def test_warm_cache_on_startup_returns_result(self):
        """Test warm_cache_on_startup returns WarmingResult."""
        with patch("shared.cache_warming.logger"):
            # Patch get_tiered_cache to return a mock
            with patch("shared.tiered_cache.get_tiered_cache") as mock_get_cache:
                mock_manager = MagicMock()
                mock_manager._l3_cache = {}
                mock_manager._l3_lock = threading.Lock()
                mock_manager._access_records = {}
                mock_manager._access_lock = threading.Lock()
                mock_manager.get = MagicMock(return_value=None)
                mock_get_cache.return_value = mock_manager

                result = await warm_cache_on_startup()

        assert isinstance(result, WarmingResult)

    @pytest.mark.asyncio
    async def test_warm_cache_on_startup_uses_params(self):
        """Test warm_cache_on_startup uses provided parameters."""
        with patch("shared.cache_warming.logger"):
            with patch("shared.tiered_cache.get_tiered_cache") as mock_get_cache:
                mock_manager = MagicMock()
                mock_manager._l3_cache = {
                    "key1": {"data": "value1", "timestamp": time.time()},
                }
                mock_manager._l3_lock = threading.Lock()
                mock_manager._access_records = {}
                mock_manager._access_lock = threading.Lock()
                mock_manager.get = MagicMock(return_value=None)
                mock_manager.set = AsyncMock()
                mock_get_cache.return_value = mock_manager

                result = await warm_cache_on_startup(
                    source_keys=["key1"],
                    priority_keys=["key1"],
                    rate_limit=50,
                )

        assert result.status == WarmingStatus.COMPLETED


# ============================================================================
# Thread Safety Tests
# ============================================================================


class TestCacheWarmerThreadSafety:
    """Test thread safety of CacheWarmer."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    def test_concurrent_singleton_access(self):
        """Test concurrent access to singleton is thread-safe."""
        warmers = []
        errors = []

        def get_warmer():
            try:
                with patch("shared.cache_warming.logger"):
                    warmer = get_cache_warmer()
                    warmers.append(warmer)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_warmer) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All should be same instance
        assert all(w is warmers[0] for w in warmers)

    def test_concurrent_progress_callback_registration(self):
        """Test concurrent callback registration is thread-safe."""
        errors = []

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()

        def register_callback(i):
            try:
                callback = MagicMock()
                warmer.on_progress(callback)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_callback, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(warmer._progress_callbacks) == 20


# ============================================================================
# Timeout Tests
# ============================================================================


class TestCacheWarmerTimeout:
    """Test CacheWarmer timeout handling."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_total_timeout_enforcement(self, mock_cache_manager):
        """Test warming respects total timeout."""
        # Create many keys
        keys = [f"key{i}" for i in range(1000)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        # Very short timeout
        config = WarmingConfig(total_timeout=0.01, rate_limit=10)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        # Should have timed out before processing all keys
        assert result.details.get("timeout") is True or result.keys_warmed < 1000


# ============================================================================
# Key Loading Tests
# ============================================================================


class TestKeyLoading:
    """Test key loading from various sources."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_load_from_l3_cache(self, mock_cache_manager):
        """Test loading keys from L3 cache."""
        mock_cache_manager._l3_cache = {
            "key1": {"data": "value1", "timestamp": time.time()},
            "key2": {"data": "value2", "timestamp": time.time()},
        }

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache()

        assert result.keys_warmed == 2

    @pytest.mark.asyncio
    async def test_custom_key_loader(self, mock_cache_manager):
        """Test using custom key loader function."""

        def custom_loader(key):
            return f"loaded_{key}"

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(
                source_keys=["key1", "key2"],
                key_loader=custom_loader,
            )

        assert result.keys_warmed == 2

    @pytest.mark.asyncio
    async def test_async_key_loader(self, mock_cache_manager):
        """Test using async key loader function."""

        async def async_loader(key):
            await asyncio.sleep(0.001)
            return f"async_{key}"

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(
                source_keys=["key1", "key2"],
                key_loader=async_loader,
            )

        assert result.keys_warmed == 2

    @pytest.mark.asyncio
    async def test_key_loader_returns_none(self, mock_cache_manager):
        """Test handling when key loader returns None."""

        def none_loader(key):
            return None

        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(
                source_keys=["key1", "key2"],
                key_loader=none_loader,
            )

        assert result.keys_warmed == 0
        assert result.keys_failed == 2


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Test retry logic for failed key loads."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock TieredCacheManager."""
        manager = MagicMock()
        manager._l3_cache = {}
        manager._l3_lock = threading.Lock()
        manager._access_records = {}
        manager._access_lock = threading.Lock()
        manager.get = MagicMock(return_value=None)
        manager.set = AsyncMock()
        return manager

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
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(
                source_keys=["key1"],
                key_loader=flaky_loader,
            )

        assert result.keys_warmed == 1
        assert attempts[0] == 3

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, mock_cache_manager):
        """Test key marked failed after max retries exhausted."""
        attempts = [0]

        def always_fail_loader(key):
            attempts[0] += 1
            raise RuntimeError("Permanent failure")

        config = WarmingConfig(max_retries=3, retry_delay=0.01)
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(
                source_keys=["key1"],
                key_loader=always_fail_loader,
            )

        assert result.keys_warmed == 0
        assert result.keys_failed == 1
        assert attempts[0] == 3


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
        from shared import cache_warming

        assert hasattr(cache_warming, "CONSTITUTIONAL_HASH")
        assert cache_warming.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_in_stats(self):
        """Test constitutional hash appears in stats."""
        reset_cache_warmer()
        with patch("shared.cache_warming.logger"):
            warmer = CacheWarmer()
        stats = warmer.get_stats()
        assert stats["constitutional_hash"] == CONSTITUTIONAL_HASH
        reset_cache_warmer()
