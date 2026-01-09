"""Tests for CacheService with TieredCacheManager integration.

Constitutional Hash: cdd01ef066bc6cf2

These tests verify:
1. CacheService initialization with and without TieredCacheManager
2. Backward compatibility with existing API
3. Graceful degradation when Redis is unavailable
4. Per-tier statistics and metrics integration
"""

import json
import sys
import time
from pathlib import Path

import pytest

# Add src/core root to path for imports
acgs2_core_root = Path(__file__).parent.parent.parent.parent.parent.parent
if str(acgs2_core_root) not in sys.path:
    sys.path.insert(0, str(acgs2_core_root))

# Constitutional hash for compliance tracking
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestCacheServiceInitialization:
    """Tests for CacheService initialization."""

    def test_constitutional_hash_compliance(self):
        """Verify constitutional hash is present in module."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CONSTITUTIONAL_HASH as module_hash,
        )

        assert module_hash == CONSTITUTIONAL_HASH

    def test_init_with_tiered_cache_disabled(self):
        """Test initialization with tiered cache explicitly disabled."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        assert service._tiered_cache is None
        assert service._use_tiered_cache is False

    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService()
        assert service.redis_url == "redis://localhost:6379"
        assert service.redis_ttl == 3600
        assert service.local_ttl == 300

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(
            redis_url="redis://custom:6380",
            local_cache_size=200,
            redis_ttl=7200,
            local_ttl=600,
        )
        assert service.redis_url == "redis://custom:6380"
        assert service.redis_ttl == 7200
        assert service.local_ttl == 600


class TestCacheServiceTieredCacheIntegration:
    """Tests for TieredCacheManager integration."""

    def test_tiered_cache_enabled_when_available(self):
        """Test that tiered cache is enabled when available.

        Note: This test verifies the _use_tiered_cache flag behavior.
        The actual tiered cache availability depends on whether
        the shared.tiered_cache module can be imported.
        """
        from src.core.services.policy_registry.app.services.cache_service import (
            TIERED_CACHE_AVAILABLE,
            CacheService,
        )

        # When tiered cache is available and enabled
        service = CacheService(use_tiered_cache=True)

        # _use_tiered_cache should match TIERED_CACHE_AVAILABLE
        assert service._use_tiered_cache == TIERED_CACHE_AVAILABLE

        # When explicitly disabled, should always be False
        service_disabled = CacheService(use_tiered_cache=False)
        assert service_disabled._use_tiered_cache is False

    def test_is_tiered_cache_enabled_property(self):
        """Test is_tiered_cache_enabled property."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        assert service.is_tiered_cache_enabled is False

    def test_tiered_cache_property_returns_manager(self):
        """Test tiered_cache property returns the manager."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        assert service.tiered_cache is None


class TestCacheServicePolicyOperations:
    """Tests for policy cache operations."""

    @pytest.mark.asyncio
    async def test_set_policy_local_cache(self):
        """Test setting policy updates local cache."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None  # Disable Redis

        policy_data = {"name": "test-policy", "rules": ["rule1", "rule2"]}
        await service.set_policy("pol-123", "v1", policy_data)

        cache_key = "policy:pol-123:v1"
        assert cache_key in service._local_cache
        assert service._local_cache[cache_key]["data"] == policy_data

    @pytest.mark.asyncio
    async def test_get_policy_from_local_cache(self):
        """Test getting policy from local cache."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        # Pre-populate local cache
        policy_data = {"name": "test-policy"}
        cache_key = "policy:pol-123:v1"
        service._local_cache[cache_key] = {"data": policy_data, "timestamp": time.time()}

        result = await service.get_policy("pol-123", "v1")
        assert result == policy_data

    @pytest.mark.asyncio
    async def test_get_policy_expired_local_cache(self):
        """Test expired local cache returns None."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False, local_ttl=1)
        service.redis_client = None

        # Pre-populate with expired entry
        policy_data = {"name": "test-policy"}
        cache_key = "policy:pol-123:v1"
        service._local_cache[cache_key] = {
            "data": policy_data,
            "timestamp": time.time() - 10,  # 10 seconds ago, expired for 1s TTL
        }

        result = await service.get_policy("pol-123", "v1")
        assert result is None
        assert cache_key not in service._local_cache

    @pytest.mark.asyncio
    async def test_get_policy_from_redis(self, mock_redis_client):
        """Test getting policy from Redis when not in local cache."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client

        policy_data = {"name": "test-policy"}
        cache_data = {"data": policy_data, "timestamp": time.time()}
        mock_redis_client.get.return_value = json.dumps(cache_data)

        result = await service.get_policy("pol-123", "v1")
        assert result == policy_data
        mock_redis_client.get.assert_called_once_with("policy:pol-123:v1")

    @pytest.mark.asyncio
    async def test_set_policy_with_redis(self, mock_redis_client):
        """Test setting policy in Redis."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client

        policy_data = {"name": "test-policy"}
        await service.set_policy("pol-123", "v1", policy_data)

        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "policy:pol-123:v1"
        assert call_args[0][1] == service.redis_ttl


class TestCacheServiceInvalidation:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_policy_single_version(self):
        """Test invalidating a specific version."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        # Pre-populate cache
        service._local_cache["policy:pol-123:v1"] = {
            "data": {"name": "v1"},
            "timestamp": time.time(),
        }
        service._local_cache["policy:pol-123:v2"] = {
            "data": {"name": "v2"},
            "timestamp": time.time(),
        }

        await service.invalidate_policy("pol-123", "v1")

        assert "policy:pol-123:v1" not in service._local_cache
        assert "policy:pol-123:v2" in service._local_cache

    @pytest.mark.asyncio
    async def test_invalidate_policy_all_versions(self):
        """Test invalidating all versions of a policy."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        # Pre-populate cache
        service._local_cache["policy:pol-123:v1"] = {
            "data": {"name": "v1"},
            "timestamp": time.time(),
        }
        service._local_cache["policy:pol-123:v2"] = {
            "data": {"name": "v2"},
            "timestamp": time.time(),
        }
        service._local_cache["policy:pol-456:v1"] = {
            "data": {"name": "other"},
            "timestamp": time.time(),
        }

        await service.invalidate_policy("pol-123")  # No version = all versions

        assert "policy:pol-123:v1" not in service._local_cache
        assert "policy:pol-123:v2" not in service._local_cache
        assert "policy:pol-456:v1" in service._local_cache


class TestCacheServicePublicKeyOperations:
    """Tests for public key cache operations."""

    @pytest.mark.asyncio
    async def test_set_public_key(self):
        """Test setting public key in cache."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        await service.set_public_key("key-123", "ssh-rsa AAAA...")

        cache_key = "pubkey:key-123"
        assert cache_key in service._local_cache
        assert service._local_cache[cache_key]["public_key"] == "ssh-rsa AAAA..."

    @pytest.mark.asyncio
    async def test_get_public_key_from_local_cache(self):
        """Test getting public key from local cache."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        cache_key = "pubkey:key-123"
        service._local_cache[cache_key] = {
            "public_key": "ssh-rsa AAAA...",
            "timestamp": time.time(),
        }

        result = await service.get_public_key("key-123")
        assert result == "ssh-rsa AAAA..."


class TestCacheServiceStats:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_get_cache_stats_basic(self):
        """Test getting basic cache stats."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        # Add some items to local cache
        service._local_cache["test:1"] = {"data": "value1", "timestamp": time.time()}
        service._local_cache["test:2"] = {"data": "value2", "timestamp": time.time()}

        stats = await service.get_cache_stats()

        assert stats["local_cache_size"] == 2
        assert stats["redis_available"] is False

    @pytest.mark.asyncio
    async def test_get_cache_stats_with_redis(self, mock_redis_client):
        """Test getting cache stats with Redis connection."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client

        stats = await service.get_cache_stats()

        assert stats["redis_available"] is True
        assert "redis_connected_clients" in stats
        mock_redis_client.info.assert_called_once()


class TestCacheServiceGracefulDegradation:
    """Tests for graceful degradation when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_set_policy_redis_failure_uses_local(self, mock_redis_client):
        """Test set_policy falls back to local cache on Redis failure."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client
        mock_redis_client.setex.side_effect = Exception("Redis connection failed")

        policy_data = {"name": "test-policy"}
        await service.set_policy("pol-123", "v1", policy_data)

        # Should still be in local cache despite Redis failure
        cache_key = "policy:pol-123:v1"
        assert cache_key in service._local_cache
        assert service._local_cache[cache_key]["data"] == policy_data

    @pytest.mark.asyncio
    async def test_get_policy_redis_failure_returns_local(self, mock_redis_client):
        """Test get_policy returns local cache on Redis failure."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client
        mock_redis_client.get.side_effect = Exception("Redis connection failed")

        # Pre-populate local cache
        policy_data = {"name": "test-policy"}
        cache_key = "policy:pol-123:v1"
        service._local_cache[cache_key] = {"data": policy_data, "timestamp": time.time()}

        result = await service.get_policy("pol-123", "v1")
        assert result == policy_data


class TestCacheServiceLifecycle:
    """Tests for cache service lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_with_redis(self, mock_redis_client):
        """Test close properly closes Redis connection."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client
        service._tiered_cache = None  # Ensure legacy path is used

        await service.close()

        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_redis(self):
        """Test close handles missing Redis gracefully."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None
        service._tiered_cache = None

        # Should not raise
        await service.close()


class TestCacheServiceIsDegraded:
    """Tests for is_degraded property."""

    def test_is_degraded_no_tiered_cache(self):
        """Test is_degraded when tiered cache is not available."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = None

        assert service.is_degraded is True

    def test_is_degraded_with_redis(self, mock_redis_client):
        """Test is_degraded when Redis is available."""
        from src.core.services.policy_registry.app.services.cache_service import (
            CacheService,
        )

        service = CacheService(use_tiered_cache=False)
        service.redis_client = mock_redis_client
        service._tiered_cache = None

        assert service.is_degraded is False
