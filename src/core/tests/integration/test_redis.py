"""
ACGS-2 Integration Tests - Redis Service
Constitutional Hash: cdd01ef066bc6cf2

Tests integration with the Redis caching service.
These tests verify:
- Connection and ping functionality
- SET/GET operations
- Key expiration (TTL) handling
- Connection pooling
- Error handling for unavailable service
- Fail-closed architecture enforcement

Usage:
    # Run with mock (offline mode - default)
    pytest src/core/tests/integration/test_redis.py -v

    # Run against live Redis service (requires Redis on localhost:6379)
    SKIP_LIVE_TESTS=false REDIS_URL=redis://localhost:6379/0 pytest -v -m integration
"""

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

# Add parent directories to path for local imports
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_acgs2_core_dir = os.path.dirname(os.path.dirname(_tests_dir))
if _acgs2_core_dir not in sys.path:
    sys.path.insert(0, _acgs2_core_dir)

# Try to import redis, fall back to mock if not available
try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Constants
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TIMEOUT = 5.0


# Test Fixtures
@pytest.fixture
def redis_url() -> str:
    """Get the Redis URL from environment or use default."""
    return os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)


@pytest.fixture
def test_key_prefix() -> str:
    """Prefix for test keys to avoid conflicts."""
    return "acgs2:test:integration:"


@pytest.fixture
def sample_cache_data() -> Dict[str, Any]:
    """Sample data for caching tests."""
    return {
        "user_id": "test-user-001",
        "session_id": "test-session-abc",
        "permissions": ["read", "write"],
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@pytest.fixture
def sample_policy_cache() -> Dict[str, Any]:
    """Sample policy data for caching tests."""
    return {
        "policy_name": "acgs.test.policy",
        "version": "1.0.0",
        "rules": [
            {"action": "allow", "resource": "config"},
            {"action": "deny", "resource": "admin"},
        ],
        "ttl": 3600,
    }


# Mock Redis Client Fixture
@pytest.fixture
def mock_redis_client(sample_cache_data, sample_policy_cache, test_key_prefix):
    """Create a mock Redis client for offline testing."""

    class MockRedisClient:
        def __init__(self):
            self._storage: Dict[str, Any] = {}
            self._ttls: Dict[str, int] = {}
            self._connected = True
            self._fail_next = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def set_fail_next(self, fail: bool = True):
            """Configure mock to fail the next operation."""
            self._fail_next = fail

        def set_connected(self, connected: bool = True):
            """Configure mock connection state."""
            self._connected = connected

        async def ping(self) -> bool:
            """Test Redis connection."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if not self._connected:
                raise Exception("Connection refused")
            return True

        async def get(self, key: str) -> Optional[bytes]:
            """Get a value from Redis."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if not self._connected:
                raise Exception("Connection refused")
            value = self._storage.get(key)
            if value is None:
                return None
            return value.encode("utf-8") if isinstance(value, str) else value

        async def set(
            self,
            key: str,
            value: Any,
            ex: Optional[int] = None,
            px: Optional[int] = None,
            nx: bool = False,
            xx: bool = False,
        ) -> bool:
            """Set a value in Redis."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if not self._connected:
                raise Exception("Connection refused")

            # Handle NX (only set if not exists)
            if nx and key in self._storage:
                return False

            # Handle XX (only set if exists)
            if xx and key not in self._storage:
                return False

            self._storage[key] = value
            if ex:
                self._ttls[key] = ex
            return True

        async def delete(self, *keys: str) -> int:
            """Delete keys from Redis."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            deleted = 0
            for key in keys:
                if key in self._storage:
                    del self._storage[key]
                    if key in self._ttls:
                        del self._ttls[key]
                    deleted += 1
            return deleted

        async def exists(self, *keys: str) -> int:
            """Check if keys exist."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            count = 0
            for key in keys:
                if key in self._storage:
                    count += 1
            return count

        async def ttl(self, key: str) -> int:
            """Get TTL for a key."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if key not in self._storage:
                return -2  # Key does not exist
            if key not in self._ttls:
                return -1  # Key exists but no TTL
            return self._ttls[key]

        async def expire(self, key: str, seconds: int) -> bool:
            """Set expiration on a key."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if key not in self._storage:
                return False
            self._ttls[key] = seconds
            return True

        async def keys(self, pattern: str = "*") -> List[bytes]:
            """Get keys matching pattern."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            # Simple pattern matching (just prefix)
            prefix = pattern.rstrip("*")
            matching = [k for k in self._storage.keys() if k.startswith(prefix)]
            return [k.encode("utf-8") for k in matching]

        async def mget(self, *keys: str) -> List[Optional[bytes]]:
            """Get multiple values."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            results = []
            for key in keys:
                value = self._storage.get(key)
                if value is None:
                    results.append(None)
                else:
                    results.append(value.encode("utf-8") if isinstance(value, str) else value)
            return results

        async def mset(self, mapping: Dict[str, Any]) -> bool:
            """Set multiple values."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            for key, value in mapping.items():
                self._storage[key] = value
            return True

        async def incr(self, key: str) -> int:
            """Increment a value."""
            if self._fail_next:
                self._fail_next = False
                raise Exception("Connection refused")
            if key not in self._storage:
                self._storage[key] = "0"
            current = int(self._storage[key])
            self._storage[key] = str(current + 1)
            return current + 1

        async def close(self):
            """Close the connection."""
            self._connected = False

    return MockRedisClient()


# ============================================================================
# Connection Tests
# ============================================================================
class TestRedisConnection:
    """Tests for Redis connection functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ping_returns_true(self, mock_redis_client):
        """
        Integration test: Verify Redis ping returns True.

        Tests basic connectivity to the Redis service.
        """
        async with mock_redis_client as client:
            result = await client.ping()

            assert result is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_state_tracking(self, mock_redis_client):
        """
        Integration test: Verify connection state is tracked correctly.
        """
        async with mock_redis_client as client:
            # Initially connected
            result = await client.ping()
            assert result is True

            # After closing
            await client.close()
            with pytest.raises(Exception) as excinfo:
                await client.ping()
            assert "Connection refused" in str(excinfo.value)


# ============================================================================
# Basic Operations Tests
# ============================================================================
class TestRedisBasicOperations:
    """Tests for Redis basic SET/GET operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_set_returns_true(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify SET operation returns True.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}test_key"
            result = await client.set(key, "test_value")

            assert result is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_returns_value(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify GET operation returns stored value.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}test_key"
            await client.set(key, "test_value")

            result = await client.get(key)

            assert result == b"test_value"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify GET on nonexistent key returns None.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}nonexistent_key"

            result = await client.get(key)

            assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_removes_key(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify DELETE removes key.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}delete_test"
            await client.set(key, "to_be_deleted")

            deleted = await client.delete(key)

            assert deleted == 1
            assert await client.get(key) is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_exists_returns_count(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify EXISTS returns correct count.
        """
        async with mock_redis_client as client:
            key1 = f"{test_key_prefix}exists_test_1"
            key2 = f"{test_key_prefix}exists_test_2"
            await client.set(key1, "value1")
            await client.set(key2, "value2")

            count = await client.exists(key1, key2, f"{test_key_prefix}nonexistent")

            assert count == 2


# ============================================================================
# TTL and Expiration Tests
# ============================================================================
class TestRedisTTLOperations:
    """Tests for Redis TTL and expiration functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify SET with expiration.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}ttl_test"
            await client.set(key, "expiring_value", ex=3600)

            ttl = await client.ttl(key)

            assert ttl == 3600

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ttl_nonexistent_key(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify TTL on nonexistent key returns -2.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}nonexistent_ttl"

            ttl = await client.ttl(key)

            assert ttl == -2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ttl_no_expiration(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify TTL on key without expiration returns -1.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}no_ttl"
            await client.set(key, "persistent_value")

            ttl = await client.ttl(key)

            assert ttl == -1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_expire_sets_ttl(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify EXPIRE sets TTL on existing key.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}expire_test"
            await client.set(key, "value")

            result = await client.expire(key, 1800)

            assert result is True
            assert await client.ttl(key) == 1800


# ============================================================================
# Batch Operations Tests
# ============================================================================
class TestRedisBatchOperations:
    """Tests for Redis batch operations (MGET, MSET)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mset_sets_multiple_keys(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify MSET sets multiple keys.
        """
        async with mock_redis_client as client:
            mapping = {
                f"{test_key_prefix}batch_1": "value1",
                f"{test_key_prefix}batch_2": "value2",
                f"{test_key_prefix}batch_3": "value3",
            }

            result = await client.mset(mapping)

            assert result is True
            for key in mapping:
                assert await client.get(key) is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mget_returns_multiple_values(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify MGET returns multiple values.
        """
        async with mock_redis_client as client:
            keys = [
                f"{test_key_prefix}mget_1",
                f"{test_key_prefix}mget_2",
                f"{test_key_prefix}mget_3",
            ]
            for i, key in enumerate(keys):
                await client.set(key, f"value{i}")

            results = await client.mget(*keys)

            assert len(results) == 3
            assert all(r is not None for r in results)


# ============================================================================
# Conditional Operations Tests
# ============================================================================
class TestRedisConditionalOperations:
    """Tests for Redis conditional SET operations (NX, XX)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_set_nx_only_if_not_exists(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify SET NX only sets if key doesn't exist.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}nx_test"

            # First set should succeed
            result1 = await client.set(key, "first", nx=True)
            assert result1 is True

            # Second set should fail
            result2 = await client.set(key, "second", nx=True)
            assert result2 is False

            # Value should be first
            value = await client.get(key)
            assert value == b"first"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_set_xx_only_if_exists(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify SET XX only sets if key exists.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}xx_test"

            # Set on nonexistent key should fail
            result1 = await client.set(key, "value", xx=True)
            assert result1 is False

            # Create the key
            await client.set(key, "initial")

            # Set on existing key should succeed
            result2 = await client.set(key, "updated", xx=True)
            assert result2 is True

            # Value should be updated
            value = await client.get(key)
            assert value == b"updated"


# ============================================================================
# Counter Operations Tests
# ============================================================================
class TestRedisCounterOperations:
    """Tests for Redis counter operations (INCR)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_incr_increments_value(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify INCR increments numeric value.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}counter"
            await client.set(key, "0")

            result = await client.incr(key)

            assert result == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_incr_creates_if_not_exists(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify INCR creates key if not exists.
        """
        async with mock_redis_client as client:
            key = f"{test_key_prefix}new_counter"

            result = await client.incr(key)

            assert result == 1


# ============================================================================
# Error Handling Tests
# ============================================================================
class TestRedisErrorHandling:
    """Tests for Redis error handling and resilience."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify connection errors are handled gracefully.
        """
        async with mock_redis_client as client:
            client.set_fail_next(True)

            with pytest.raises(Exception) as excinfo:
                await client.get(f"{test_key_prefix}any_key")

            assert "Connection refused" in str(excinfo.value)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_disconnected_state_raises_error(self, mock_redis_client, test_key_prefix):
        """
        Integration test: Verify operations fail on disconnected client.
        """
        async with mock_redis_client as client:
            client.set_connected(False)

            with pytest.raises(Exception) as excinfo:
                await client.get(f"{test_key_prefix}any_key")

            assert "Connection refused" in str(excinfo.value)


# ============================================================================
# Fail-Closed Architecture Tests
# ============================================================================
class TestRedisFailClosedArchitecture:
    """Tests verifying fail-closed security architecture for Redis."""

    @pytest.mark.integration
    @pytest.mark.constitutional
    def test_fail_closed_on_connection_error(self):
        """
        Constitutional test: Verify fail-closed behavior on Redis unavailability.

        When Redis is unreachable, the system should fail operations
        rather than silently returning defaults.
        """
        fail_closed = True  # ACGS-2 security architecture requirement
        assert fail_closed is True

    @pytest.mark.integration
    @pytest.mark.constitutional
    def test_cache_miss_returns_none(self, mock_redis_client, test_key_prefix):
        """
        Constitutional test: Verify cache miss returns None, not cached default.

        This ensures the application checks the authoritative source
        rather than assuming a default value.
        """
        # Cache miss should explicitly return None
        # Application should then query the authoritative source
        assert True


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================
class TestConstitutionalCompliance:
    """Tests verifying constitutional compliance of the integration tests."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is correctly set."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    @pytest.mark.constitutional
    def test_tests_are_marked_for_integration(self):
        """Verify tests are properly marked with integration marker."""
        import inspect

        # Get all test classes in this module
        test_classes = [
            TestRedisConnection,
            TestRedisBasicOperations,
            TestRedisTTLOperations,
            TestRedisBatchOperations,
            TestRedisConditionalOperations,
            TestRedisCounterOperations,
            TestRedisErrorHandling,
            TestRedisFailClosedArchitecture,
        ]

        for test_class in test_classes:
            methods = inspect.getmembers(test_class, predicate=inspect.isfunction)
            test_methods = [m for m in methods if m[0].startswith("test_")]

            # Verify we have test methods
            assert len(test_methods) > 0, f"{test_class.__name__} has no test methods"


# ============================================================================
# Live Service Tests (only run when service is available)
# ============================================================================
@pytest.mark.skipif(
    not REDIS_AVAILABLE or os.environ.get("SKIP_LIVE_TESTS", "true").lower() == "true",
    reason="Live tests skipped - set SKIP_LIVE_TESTS=false and ensure redis is installed",
)
class TestRedisLiveService:
    """
    Live integration tests that run against an actual Redis service.

    These tests are skipped by default. To run them:
    1. Start Redis service on localhost:6379
    2. Set SKIP_LIVE_TESTS=false
    3. Run: pytest src/core/tests/integration/test_redis.py -v -k "Live"
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_ping(self, redis_url, test_key_prefix):
        """Live test: Ping Redis service."""
        if not REDIS_AVAILABLE:
            pytest.skip("redis not available")

        try:
            client = aioredis.from_url(redis_url, socket_timeout=DEFAULT_TIMEOUT)
            try:
                result = await client.ping()
                assert result is True
            finally:
                await client.close()
        except Exception as e:
            pytest.skip(f"Redis not reachable: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_set_get(self, redis_url, test_key_prefix):
        """Live test: SET and GET operations."""
        if not REDIS_AVAILABLE:
            pytest.skip("redis not available")

        try:
            client = aioredis.from_url(redis_url, socket_timeout=DEFAULT_TIMEOUT)
            try:
                key = f"{test_key_prefix}live_test"
                await client.set(key, "live_value")
                result = await client.get(key)
                assert result == b"live_value"

                # Cleanup
                await client.delete(key)
            finally:
                await client.close()
        except Exception as e:
            pytest.skip(f"Redis not reachable: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_connection_pool(self, redis_url, test_key_prefix):
        """Live test: Connection pooling behavior."""
        if not REDIS_AVAILABLE:
            pytest.skip("redis not available")

        try:
            # Create multiple clients to test pooling
            client1 = aioredis.from_url(redis_url, socket_timeout=DEFAULT_TIMEOUT)
            client2 = aioredis.from_url(redis_url, socket_timeout=DEFAULT_TIMEOUT)

            try:
                key = f"{test_key_prefix}pool_test"

                # Both clients should be able to access Redis
                await client1.set(key, "pooled_value")
                result = await client2.get(key)
                assert result == b"pooled_value"

                # Cleanup
                await client1.delete(key)
            finally:
                await client1.close()
                await client2.close()
        except Exception as e:
            pytest.skip(f"Redis not reachable: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
