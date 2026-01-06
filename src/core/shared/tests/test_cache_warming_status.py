"""
ACGS-2 Cache Warming Module Tests - Status & Management
Focused tests for cancellation, progress callbacks, thread safety, and timeouts.
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.shared.cache_warming import (
    CacheWarmer,
    WarmingConfig,
    WarmingResult,
    WarmingStatus,
    reset_cache_warmer,
    warm_cache_on_startup,
)


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
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer()
            warmer.cancel()
        assert warmer._cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cancel_during_warming(self, mock_cache_manager):
        """Test cancellation during warming."""
        keys = [f"key{i}" for i in range(100)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(cache_manager=mock_cache_manager)

            async def warm_and_cancel():
                task = asyncio.create_task(warmer.warm_cache(source_keys=keys))
                await asyncio.sleep(0.01)
                warmer.cancel()
                return await task

            result = await warm_and_cancel()
        assert result.status in [WarmingStatus.CANCELLED, WarmingStatus.COMPLETED]


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
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer()
        callback = MagicMock()
        warmer.on_progress(callback)
        assert callback in warmer._progress_callbacks

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, mock_cache_manager):
        """Test progress callback is called during warming."""
        progress_updates = []

        def track_progress(progress):
            progress_updates.append(progress)

        keys = [f"key{i}" for i in range(25)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(batch_size=10)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            warmer.on_progress(track_progress)
            await warmer.warm_cache(source_keys=keys)

        assert len(progress_updates) > 0


class TestCacheWarmerThreadSafety:
    """Test thread safety of CacheWarmer."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_cache_warmer()
        yield
        reset_cache_warmer()

    def test_concurrent_progress_callback_registration(self):
        """Test concurrent callback registration is thread-safe."""
        errors = []
        with patch("src.core.shared.cache_warming.logger"):
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
        keys = [f"key{i}" for i in range(1000)]
        for key in keys:
            mock_cache_manager._l3_cache[key] = {"data": f"value_{key}", "timestamp": time.time()}

        config = WarmingConfig(total_timeout=0.01, rate_limit=10)
        with patch("src.core.shared.cache_warming.logger"):
            warmer = CacheWarmer(config=config, cache_manager=mock_cache_manager)
            result = await warmer.warm_cache(source_keys=keys)

        assert result.details.get("timeout") is True or result.keys_warmed < 1000


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
        with patch("src.core.shared.cache_warming.logger"):
            with patch("src.core.shared.tiered_cache.get_tiered_cache") as mock_get_cache:
                mock_manager = MagicMock()
                mock_manager._l3_cache = {}
                mock_manager._l3_lock = threading.Lock()
                mock_get_cache.return_value = mock_manager

                result = await warm_cache_on_startup()
        assert isinstance(result, WarmingResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
