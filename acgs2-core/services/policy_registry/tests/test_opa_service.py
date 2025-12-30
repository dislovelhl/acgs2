"""
ACGS-2 Policy Registry - OPA Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for OPAService including:
- Authorization checking against OPA
- Caching behavior (hits, misses, expiration)
- Fail-closed vs fail-open modes
- Cache invalidation
- Error handling
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Mock settings for testing
# =============================================================================


class MockOPASettings:
    """Mock OPA settings for testing."""

    def __init__(self, url: str = "http://localhost:8181", fail_closed: bool = True):
        self.url = url
        self.fail_closed = fail_closed


class MockSettings:
    """Mock settings object."""

    def __init__(self, url: str = "http://localhost:8181", fail_closed: bool = True):
        self.opa = MockOPASettings(url, fail_closed)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings_fail_closed():
    """Create mock settings with fail_closed=True."""
    return MockSettings(fail_closed=True)


@pytest.fixture
def mock_settings_fail_open():
    """Create mock settings with fail_closed=False."""
    return MockSettings(fail_closed=False)


@pytest.fixture
def sample_user():
    """Sample user data for authorization tests."""
    return {"agent_id": "agent-001", "role": "admin", "tenant_id": "tenant-001"}


@pytest.fixture
def sample_operator_user():
    """Sample operator user data."""
    return {"agent_id": "agent-002", "role": "operator", "tenant_id": "tenant-001"}


@pytest.fixture
def clear_auth_cache():
    """Clear the authorization cache before each test."""
    import app.services.opa_service as opa_module

    opa_module._auth_cache.clear()
    yield
    opa_module._auth_cache.clear()


# =============================================================================
# Cache Key Generation Tests
# =============================================================================


class TestCacheKeyGeneration:
    """Tests for authorization cache key generation."""

    def test_cache_key_uses_role_not_user_id(self, mock_settings_fail_closed):
        """Test that cache key is based on role, not user ID."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            user1 = {"agent_id": "agent-001", "role": "admin"}
            user2 = {"agent_id": "agent-002", "role": "admin"}

            key1 = service._get_cache_key(user1, "read", "policies")
            key2 = service._get_cache_key(user2, "read", "policies")

            # Same role should produce same cache key
            assert key1 == key2

    def test_cache_key_differs_by_role(self, mock_settings_fail_closed):
        """Test that different roles produce different cache keys."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            admin_user = {"role": "admin"}
            operator_user = {"role": "operator"}

            key1 = service._get_cache_key(admin_user, "read", "policies")
            key2 = service._get_cache_key(operator_user, "read", "policies")

            assert key1 != key2

    def test_cache_key_differs_by_action(self, mock_settings_fail_closed):
        """Test that different actions produce different cache keys."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            user = {"role": "admin"}

            key1 = service._get_cache_key(user, "read", "policies")
            key2 = service._get_cache_key(user, "write", "policies")

            assert key1 != key2

    def test_cache_key_differs_by_resource(self, mock_settings_fail_closed):
        """Test that different resources produce different cache keys."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            user = {"role": "admin"}

            key1 = service._get_cache_key(user, "read", "policies")
            key2 = service._get_cache_key(user, "read", "bundles")

            assert key1 != key2

    def test_cache_key_is_md5_hash(self, mock_settings_fail_closed):
        """Test that cache key is an MD5 hash."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            user = {"role": "admin"}

            key = service._get_cache_key(user, "read", "policies")

            # MD5 hash is 32 hex characters
            assert len(key) == 32
            assert all(c in "0123456789abcdef" for c in key)


# =============================================================================
# Cache Behavior Tests
# =============================================================================


class TestCacheBehavior:
    """Tests for authorization caching behavior."""

    def test_cache_miss_returns_none(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that cache miss returns None."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            result = service._check_cache("nonexistent-key")

            assert result is None

    def test_cache_hit_returns_result(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that cache hit returns cached result."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            # Cache a result
            cache_key = "test-key"
            service._cache_result(cache_key, True)

            # Check cache
            result = service._check_cache(cache_key)

            assert result is True

    def test_cache_stores_false_values(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that cache correctly stores False values."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            cache_key = "test-key-false"
            service._cache_result(cache_key, False)

            result = service._check_cache(cache_key)

            assert result is False

    def test_expired_cache_returns_none(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that expired cache entry returns None."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService, _auth_cache

            service = OPAService()

            # Manually insert expired entry
            cache_key = "expired-key"
            expired_time = datetime.now(timezone.utc).timestamp() - 100  # 100 seconds ago
            _auth_cache[cache_key] = (True, expired_time)

            result = service._check_cache(cache_key)

            assert result is None
            # Entry should be removed
            assert cache_key not in _auth_cache


# =============================================================================
# Authorization Check Tests
# =============================================================================


class TestAuthorizationCheck:
    """Tests for OPA authorization checking."""

    @pytest.mark.asyncio
    async def test_authorization_allowed(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test successful authorization check that allows access."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            # Mock OPA response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": True}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "read", "policies")

                assert result is True

    @pytest.mark.asyncio
    async def test_authorization_denied(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test authorization check that denies access."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": False}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "delete", "system")

                assert result is False

    @pytest.mark.asyncio
    async def test_authorization_uses_cache(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test that subsequent authorization checks use cache."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": True}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                # First call
                result1 = await service.check_authorization(sample_user, "read", "policies")

                # Second call (should use cache)
                result2 = await service.check_authorization(sample_user, "read", "policies")

                assert result1 is True
                assert result2 is True
                # OPA should only be called once
                assert mock_instance.post.call_count == 1

    @pytest.mark.asyncio
    async def test_authorization_sends_correct_request(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test that authorization sends correct request to OPA."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": True}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await service.check_authorization(sample_user, "write", "bundles")

                # Verify the request
                call_args = mock_instance.post.call_args
                url = call_args[0][0]
                json_data = call_args[1]["json"]

                assert "/v1/data/acgs/rbac/allow" in url
                assert json_data["input"]["user"] == sample_user
                assert json_data["input"]["action"] == "write"
                assert json_data["input"]["resource"] == "bundles"


# =============================================================================
# Fail-Closed vs Fail-Open Tests
# =============================================================================


class TestFailBehavior:
    """Tests for fail-closed and fail-open behavior."""

    @pytest.mark.asyncio
    async def test_fail_closed_on_opa_error(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test that fail_closed=True denies access on OPA error."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            service.fail_closed = True

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.side_effect = Exception("Connection error")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "read", "policies")

                assert result is False

    @pytest.mark.asyncio
    async def test_fail_open_on_opa_error(
        self, mock_settings_fail_open, sample_user, clear_auth_cache
    ):
        """Test that fail_closed=False allows access on OPA error."""
        with patch("app.services.opa_service.settings", mock_settings_fail_open):
            from app.services.opa_service import OPAService

            service = OPAService()
            service.fail_closed = False

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.side_effect = Exception("Connection error")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "read", "policies")

                assert result is True

    @pytest.mark.asyncio
    async def test_fail_closed_on_non_200_response(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test that fail_closed=True denies access on non-200 response."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            service.fail_closed = True

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "read", "policies")

                assert result is False

    @pytest.mark.asyncio
    async def test_fail_open_on_non_200_response(
        self, mock_settings_fail_open, sample_user, clear_auth_cache
    ):
        """Test that fail_closed=False allows access on non-200 response."""
        with patch("app.services.opa_service.settings", mock_settings_fail_open):
            from app.services.opa_service import OPAService

            service = OPAService()
            service.fail_closed = False

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await service.check_authorization(sample_user, "read", "policies")

                assert result is True


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_entire_cache(self, mock_settings_fail_closed, clear_auth_cache):
        """Test invalidating the entire cache."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            import app.services.opa_service as opa_module
            from app.services.opa_service import OPAService

            service = OPAService()

            # Add some cache entries
            service._cache_result("key1", True)
            service._cache_result("key2", False)
            service._cache_result("key3", True)

            assert len(opa_module._auth_cache) == 3

            count = service.invalidate_cache()

            assert count == 3
            # After invalidation, module-level cache should be empty
            assert len(opa_module._auth_cache) == 0

    def test_invalidate_cache_returns_count(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that invalidate_cache returns correct count."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            # Add some cache entries
            for i in range(5):
                service._cache_result(f"key{i}", True)

            count = service.invalidate_cache()

            assert count == 5

    def test_invalidate_empty_cache(self, mock_settings_fail_closed, clear_auth_cache):
        """Test invalidating an empty cache."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            count = service.invalidate_cache()

            assert count == 0

    def test_invalidate_by_role_clears_all(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that invalidate_by_role clears entire cache (current implementation)."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            import app.services.opa_service as opa_module
            from app.services.opa_service import OPAService

            service = OPAService()

            # Add cache entries
            service._cache_result("key1", True)
            service._cache_result("key2", False)

            # Invalidate for specific role (currently clears all)
            count = service.invalidate_cache(role="admin")

            assert count == 2
            assert len(opa_module._auth_cache) == 0


# =============================================================================
# Cache Cleanup Tests
# =============================================================================


class TestCacheCleanup:
    """Tests for cache cleanup behavior."""

    def test_cleanup_expired_entries(self, mock_settings_fail_closed, clear_auth_cache):
        """Test that expired entries are cleaned up."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService, _auth_cache

            service = OPAService()

            # Add expired and valid entries
            now = datetime.now(timezone.utc).timestamp()
            _auth_cache["expired1"] = (True, now - 100)  # Expired
            _auth_cache["expired2"] = (False, now - 50)  # Expired
            _auth_cache["valid"] = (True, now + 1000)  # Valid

            service._cleanup_expired_cache()

            assert "expired1" not in _auth_cache
            assert "expired2" not in _auth_cache
            assert "valid" in _auth_cache


# =============================================================================
# Initialization Tests
# =============================================================================


class TestOPAServiceInitialization:
    """Tests for OPA service initialization."""

    def test_init_with_settings(self, mock_settings_fail_closed):
        """Test initialization with settings."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            assert service.opa_url == "http://localhost:8181"
            assert service.fail_closed is True

    def test_init_with_custom_url(self):
        """Test initialization with custom OPA URL."""
        custom_settings = MockSettings(url="http://opa.example.com:8181")

        with patch("app.services.opa_service.settings", custom_settings):
            from app.services.opa_service import OPAService

            service = OPAService()

            assert service.opa_url == "http://opa.example.com:8181"

    def test_init_without_settings_uses_defaults(self):
        """Test initialization without settings uses defaults."""
        with patch("app.services.opa_service.settings", None):
            from app.services.opa_service import OPAService

            service = OPAService()

            assert service.opa_url == "http://localhost:8181"
            assert service.fail_closed is True


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


class TestConstitutionalCompliance:
    """Tests for constitutional compliance in OPA operations."""

    @pytest.mark.asyncio
    async def test_authorization_logs_include_context(
        self, mock_settings_fail_closed, sample_user, clear_auth_cache
    ):
        """Test that authorization logging includes relevant context."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": True}

            with (
                patch("httpx.AsyncClient") as mock_client,
                patch("app.services.opa_service.logger") as mock_logger,
            ):
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await service.check_authorization(sample_user, "read", "policies")

                # Verify logging was called with authorization details
                mock_logger.info.assert_called()
                log_message = mock_logger.info.call_args[0][0]
                assert "agent-001" in log_message or "admin" in log_message

    def test_cache_key_is_deterministic(self, mock_settings_fail_closed):
        """Test that cache key generation is deterministic."""
        with patch("app.services.opa_service.settings", mock_settings_fail_closed):
            from app.services.opa_service import OPAService

            service = OPAService()
            user = {"role": "admin", "agent_id": "test"}

            # Generate key multiple times
            keys = [service._get_cache_key(user, "read", "policies") for _ in range(10)]

            # All keys should be identical
            assert len(set(keys)) == 1
