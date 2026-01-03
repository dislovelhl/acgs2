"""Pytest fixtures for cache service tests.

Constitutional Hash: cdd01ef066bc6cf2
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add acgs2-core root to path for imports
acgs2_core_root = Path(__file__).parent.parent.parent.parent.parent.parent
if str(acgs2_core_root) not in sys.path:
    sys.path.insert(0, str(acgs2_core_root))


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis async client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.close = AsyncMock()
    client.info = AsyncMock(return_value={"connected_clients": 5, "used_memory_human": "1M"})
    return client


@pytest.fixture
def mock_tiered_cache_manager():
    """Create a mock TieredCacheManager."""
    manager = MagicMock()
    manager.initialize = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    manager.get_async = AsyncMock(return_value=None)
    manager.set = AsyncMock()
    manager.delete = AsyncMock(return_value=True)
    manager.get_stats = MagicMock(
        return_value={
            "tiers": {
                "l1": {"hits": 10, "misses": 2},
                "l2": {"hits": 20, "misses": 5, "available": True},
                "l3": {"hits": 5, "misses": 1},
            }
        }
    )
    manager._l2_client = MagicMock()
    manager.is_degraded = False
    return manager


@pytest.fixture
def patched_tiered_cache_available():
    """Patch TIERED_CACHE_AVAILABLE to True."""
    with patch(
        "services.policy_registry.app.services.cache_service.TIERED_CACHE_AVAILABLE",
        True,
    ):
        yield


@pytest.fixture
def patched_tiered_cache_unavailable():
    """Patch TIERED_CACHE_AVAILABLE to False."""
    with patch(
        "services.policy_registry.app.services.cache_service.TIERED_CACHE_AVAILABLE",
        False,
    ):
        yield
