"""
ACGS-2 Policy Registry - Cache Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for CacheService including:
- Local cache operations
- Redis integration (mocked)
- TTL and expiration handling
- Policy and public key caching
- Cache invalidation
- Cache statistics
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def cache_service():
    """Create a fresh CacheService instance for testing."""
    from app.services.cache_service import CacheService
    return CacheService(
        redis_url="redis://localhost:6379",
        local_cache_size=100,
        redis_ttl=3600,
        local_ttl=300
    )


@pytest.fixture
def cache_service_short_ttl():
    """Create a CacheService with very short TTL for expiration testing."""
    from app.services.cache_service import CacheService
    return CacheService(
        redis_url="redis://localhost:6379",
        local_cache_size=10,
        redis_ttl=1,
        local_ttl=1  # 1 second TTL for testing expiration
    )


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=1)
    mock.close = AsyncMock()
    mock.info = AsyncMock(return_value={
        "connected_clients": 5,
        "used_memory_human": "10MB"
    })
    return mock


@pytest.fixture
def sample_policy_data():
    """Sample policy data for testing."""
    return {
        "name": "test-policy",
        "version": "1.0.0",
        "rules": ["rule1", "rule2"],
        "metadata": {
            "author": "test",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }


# =============================================================================
# Initialization Tests
# =============================================================================

class TestCacheServiceInitialization:
    """Tests for CacheService initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        from app.services.cache_service import CacheService
        service = CacheService()

        assert service.redis_url == "redis://localhost:6379"
        assert service.redis_ttl == 3600
        assert service.local_ttl == 300
        assert service.redis_client is None
        assert service._local_cache == {}

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        from app.services.cache_service import CacheService
        service = CacheService(
            redis_url="redis://custom:6380",
            local_cache_size=50,
            redis_ttl=7200,
            local_ttl=600
        )

        assert service.redis_url == "redis://custom:6380"
        assert service.redis_ttl == 7200
        assert service.local_ttl == 600

    @pytest.mark.asyncio
    async def test_initialize_without_redis(self, cache_service):
        """Test initialization when Redis is not available."""
        with patch("app.services.cache_service.redis", None):
            from app.services.cache_service import CacheService
            service = CacheService()
            await service.initialize()
            assert service.redis_client is None

    @pytest.mark.asyncio
    async def test_initialize_redis_connection_failure(self, cache_service, mock_redis_client):
        """Test initialization when Redis connection fails."""
        mock_redis_client.ping.side_effect = Exception("Connection refused")

        with patch("app.services.cache_service.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = mock_redis_client
            await cache_service.initialize()
            assert cache_service.redis_client is None

    @pytest.mark.asyncio
    async def test_close_with_redis_client(self, cache_service, mock_redis_client):
        """Test closing cache service with active Redis connection."""
        cache_service.redis_client = mock_redis_client
        await cache_service.close()
        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_redis_client(self, cache_service):
        """Test closing cache service without Redis connection."""
        cache_service.redis_client = None
        await cache_service.close()  # Should not raise


# =============================================================================
# Local Cache Tests
# =============================================================================

class TestLocalCacheOperations:
    """Tests for local cache operations without Redis."""

    @pytest.mark.asyncio
    async def test_set_and_get_policy_local_only(self, cache_service, sample_policy_data):
        """Test setting and getting policy from local cache."""
        cache_service.redis_client = None

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)
        result = await cache_service.get_policy("policy-1", "v1")

        assert result == sample_policy_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_policy(self, cache_service):
        """Test getting a policy that doesn't exist."""
        cache_service.redis_client = None
        result = await cache_service.get_policy("nonexistent", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_local_cache_expiration(self, cache_service_short_ttl, sample_policy_data):
        """Test that local cache entries expire after TTL."""
        service = cache_service_short_ttl
        service.redis_client = None

        await service.set_policy("policy-1", "v1", sample_policy_data)

        # Should be available immediately
        result = await service.get_policy("policy-1", "v1")
        assert result == sample_policy_data

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await service.get_policy("policy-1", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_policies_in_local_cache(self, cache_service):
        """Test storing multiple policies in local cache."""
        cache_service.redis_client = None

        policies = {
            ("policy-1", "v1"): {"name": "policy1"},
            ("policy-1", "v2"): {"name": "policy1-v2"},
            ("policy-2", "v1"): {"name": "policy2"},
        }

        for (policy_id, version), data in policies.items():
            await cache_service.set_policy(policy_id, version, data)

        for (policy_id, version), expected_data in policies.items():
            result = await cache_service.get_policy(policy_id, version)
            assert result == expected_data


# =============================================================================
# Redis Integration Tests (Mocked)
# =============================================================================

class TestRedisIntegration:
    """Tests for Redis integration."""

    @pytest.mark.asyncio
    async def test_set_policy_with_redis(self, cache_service, mock_redis_client, sample_policy_data):
        """Test setting policy stores in both Redis and local cache."""
        cache_service.redis_client = mock_redis_client

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)

        # Verify Redis setex was called
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "policy:policy-1:v1"
        assert call_args[0][1] == cache_service.redis_ttl

        # Verify local cache was also updated
        assert "policy:policy-1:v1" in cache_service._local_cache

    @pytest.mark.asyncio
    async def test_get_policy_from_redis_fallback(self, cache_service, mock_redis_client, sample_policy_data):
        """Test getting policy from Redis when not in local cache."""
        cache_service.redis_client = mock_redis_client

        # Simulate Redis returning cached data
        cached_data = {
            "data": sample_policy_data,
            "timestamp": time.time()
        }
        mock_redis_client.get.return_value = json.dumps(cached_data)

        result = await cache_service.get_policy("policy-1", "v1")

        assert result == sample_policy_data
        # Verify it was also stored in local cache
        assert "policy:policy-1:v1" in cache_service._local_cache

    @pytest.mark.asyncio
    async def test_redis_set_failure_graceful(self, cache_service, mock_redis_client, sample_policy_data):
        """Test that Redis set failure doesn't break local caching."""
        cache_service.redis_client = mock_redis_client
        mock_redis_client.setex.side_effect = Exception("Redis error")

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)

        # Should still work with local cache
        assert "policy:policy-1:v1" in cache_service._local_cache

    @pytest.mark.asyncio
    async def test_redis_get_failure_graceful(self, cache_service, mock_redis_client):
        """Test that Redis get failure returns None gracefully."""
        cache_service.redis_client = mock_redis_client
        mock_redis_client.get.side_effect = Exception("Redis error")

        result = await cache_service.get_policy("policy-1", "v1")

        assert result is None


# =============================================================================
# Cache Invalidation Tests
# =============================================================================

class TestCacheInvalidation:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_specific_version(self, cache_service, sample_policy_data):
        """Test invalidating a specific policy version."""
        cache_service.redis_client = None

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)
        await cache_service.set_policy("policy-1", "v2", {"name": "v2"})

        await cache_service.invalidate_policy("policy-1", "v1")

        # v1 should be gone
        assert await cache_service.get_policy("policy-1", "v1") is None
        # v2 should still be there
        assert await cache_service.get_policy("policy-1", "v2") is not None

    @pytest.mark.asyncio
    async def test_invalidate_all_versions(self, cache_service, sample_policy_data):
        """Test invalidating all versions of a policy."""
        cache_service.redis_client = None

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)
        await cache_service.set_policy("policy-1", "v2", {"name": "v2"})
        await cache_service.set_policy("policy-2", "v1", {"name": "other"})

        await cache_service.invalidate_policy("policy-1")

        # All versions of policy-1 should be gone
        assert await cache_service.get_policy("policy-1", "v1") is None
        assert await cache_service.get_policy("policy-1", "v2") is None
        # policy-2 should still be there
        assert await cache_service.get_policy("policy-2", "v1") is not None

    @pytest.mark.asyncio
    async def test_invalidate_with_redis(self, cache_service, mock_redis_client, sample_policy_data):
        """Test invalidation removes from both local and Redis."""
        cache_service.redis_client = mock_redis_client

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)
        await cache_service.invalidate_policy("policy-1", "v1")

        mock_redis_client.delete.assert_called()
        assert "policy:policy-1:v1" not in cache_service._local_cache

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_policy(self, cache_service):
        """Test invalidating a policy that doesn't exist doesn't raise."""
        cache_service.redis_client = None
        await cache_service.invalidate_policy("nonexistent", "v1")
        # Should not raise


# =============================================================================
# Public Key Caching Tests
# =============================================================================

class TestPublicKeyCaching:
    """Tests for public key caching."""

    @pytest.mark.asyncio
    async def test_set_and_get_public_key(self, cache_service):
        """Test setting and getting public key."""
        cache_service.redis_client = None

        public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkq...\n-----END PUBLIC KEY-----"

        await cache_service.set_public_key("key-1", public_key)
        result = await cache_service.get_public_key("key-1")

        assert result == public_key

    @pytest.mark.asyncio
    async def test_get_nonexistent_public_key(self, cache_service):
        """Test getting a public key that doesn't exist."""
        cache_service.redis_client = None
        result = await cache_service.get_public_key("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_public_key_expiration(self, cache_service_short_ttl):
        """Test public key cache expiration."""
        service = cache_service_short_ttl
        service.redis_client = None

        public_key = "test-key-content"
        await service.set_public_key("key-1", public_key)

        # Should be available immediately
        assert await service.get_public_key("key-1") == public_key

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Should be expired
        assert await service.get_public_key("key-1") is None

    @pytest.mark.asyncio
    async def test_public_key_with_redis(self, cache_service, mock_redis_client):
        """Test public key caching uses longer Redis TTL."""
        cache_service.redis_client = mock_redis_client

        await cache_service.set_public_key("key-1", "test-key")

        call_args = mock_redis_client.setex.call_args
        # Should use 24x the normal TTL for public keys
        assert call_args[0][1] == cache_service.redis_ttl * 24

    @pytest.mark.asyncio
    async def test_get_public_key_from_redis_fallback(self, cache_service, mock_redis_client):
        """Test getting public key from Redis when not in local cache."""
        cache_service.redis_client = mock_redis_client

        cached_data = {
            "public_key": "redis-stored-key",
            "timestamp": time.time()
        }
        mock_redis_client.get.return_value = json.dumps(cached_data)

        result = await cache_service.get_public_key("key-1")

        assert result == "redis-stored-key"


# =============================================================================
# Cache Statistics Tests
# =============================================================================

class TestCacheStatistics:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_stats_without_redis(self, cache_service, sample_policy_data):
        """Test getting cache stats without Redis."""
        cache_service.redis_client = None

        await cache_service.set_policy("policy-1", "v1", sample_policy_data)
        await cache_service.set_policy("policy-2", "v1", {"name": "policy2"})

        stats = await cache_service.get_cache_stats()

        assert stats["local_cache_size"] == 2
        assert stats["redis_available"] is False
        assert "redis_connected_clients" not in stats

    @pytest.mark.asyncio
    async def test_stats_with_redis(self, cache_service, mock_redis_client):
        """Test getting cache stats with Redis."""
        cache_service.redis_client = mock_redis_client

        stats = await cache_service.get_cache_stats()

        assert stats["redis_available"] is True
        assert stats["redis_connected_clients"] == 5
        assert stats["redis_used_memory"] == "10MB"

    @pytest.mark.asyncio
    async def test_stats_redis_info_failure(self, cache_service, mock_redis_client):
        """Test stats when Redis info call fails."""
        cache_service.redis_client = mock_redis_client
        mock_redis_client.info.side_effect = Exception("Redis error")

        stats = await cache_service.get_cache_stats()

        assert stats["redis_available"] is True
        assert "redis_connected_clients" not in stats

    @pytest.mark.asyncio
    async def test_stats_empty_cache(self, cache_service):
        """Test stats with empty cache."""
        cache_service.redis_client = None

        stats = await cache_service.get_cache_stats()

        assert stats["local_cache_size"] == 0


# =============================================================================
# LRU Cache Tests
# =============================================================================

class TestLRUCache:
    """Tests for LRU cache functionality."""

    def test_lru_cache_implementation(self, cache_service, sample_policy_data):
        """Test the LRU cache implementation function."""
        cache_key = "policy:test:v1"
        cache_service._local_cache[cache_key] = {
            "data": sample_policy_data,
            "timestamp": time.time()
        }

        result = cache_service._get_cached_policy_impl("test", "v1")
        assert result == sample_policy_data

    def test_lru_cache_expired_entry(self, cache_service_short_ttl, sample_policy_data):
        """Test LRU cache returns None for expired entries."""
        service = cache_service_short_ttl
        cache_key = "policy:test:v1"
        service._local_cache[cache_key] = {
            "data": sample_policy_data,
            "timestamp": time.time() - 10  # 10 seconds ago (expired)
        }

        result = service._get_cached_policy_impl("test", "v1")
        assert result is None

    def test_lru_cache_miss(self, cache_service):
        """Test LRU cache returns None for missing entries."""
        result = cache_service._get_cached_policy_impl("nonexistent", "v1")
        assert result is None


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_policy_id(self, cache_service, sample_policy_data):
        """Test handling empty policy ID."""
        cache_service.redis_client = None

        await cache_service.set_policy("", "v1", sample_policy_data)
        result = await cache_service.get_policy("", "v1")

        assert result == sample_policy_data

    @pytest.mark.asyncio
    async def test_special_characters_in_policy_id(self, cache_service, sample_policy_data):
        """Test handling special characters in policy ID."""
        cache_service.redis_client = None

        policy_id = "policy/with:special-chars_123"
        await cache_service.set_policy(policy_id, "v1", sample_policy_data)
        result = await cache_service.get_policy(policy_id, "v1")

        assert result == sample_policy_data

    @pytest.mark.asyncio
    async def test_large_policy_data(self, cache_service):
        """Test caching large policy data."""
        cache_service.redis_client = None

        large_data = {
            "rules": ["rule"] * 1000,
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)}
        }

        await cache_service.set_policy("large-policy", "v1", large_data)
        result = await cache_service.get_policy("large-policy", "v1")

        assert result == large_data

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache_service, sample_policy_data):
        """Test concurrent cache access."""
        cache_service.redis_client = None

        async def set_and_get(i):
            await cache_service.set_policy(f"policy-{i}", "v1", sample_policy_data)
            return await cache_service.get_policy(f"policy-{i}", "v1")

        results = await asyncio.gather(*[set_and_get(i) for i in range(10)])

        assert all(r == sample_policy_data for r in results)

    @pytest.mark.asyncio
    async def test_overwrite_existing_policy(self, cache_service):
        """Test overwriting an existing policy."""
        cache_service.redis_client = None

        await cache_service.set_policy("policy-1", "v1", {"version": 1})
        await cache_service.set_policy("policy-1", "v1", {"version": 2})

        result = await cache_service.get_policy("policy-1", "v1")
        assert result == {"version": 2}


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================

class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is defined."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_service_module_exists(self):
        """Test that the cache service module can be imported."""
        from app.services.cache_service import CacheService
        assert CacheService is not None

    @pytest.mark.asyncio
    async def test_cache_service_reliability(self, cache_service, sample_policy_data):
        """Test cache service reliability under various conditions."""
        cache_service.redis_client = None

        # Set and verify multiple times
        for i in range(5):
            await cache_service.set_policy(f"reliability-{i}", "v1", sample_policy_data)

        # Verify all can be retrieved
        for i in range(5):
            result = await cache_service.get_policy(f"reliability-{i}", "v1")
            assert result == sample_policy_data
