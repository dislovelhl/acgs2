"""
ACGS-2 Policy Registry - API Endpoint Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for API endpoints including:
- Health check endpoints
- Policy management endpoints
- Error handling and validation
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Mock Services for Testing
# =============================================================================


class MockCryptoService:
    """Mock crypto service for testing."""

    pass


class MockCacheService:
    """Mock cache service for testing."""

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def get_cache_stats(self):
        # Return fields matching actual CacheService implementation
        return {
            "local_cache_size": 50,
            "redis_available": True,
            "redis_connected_clients": 3,
            "redis_used_memory": "10MB",
        }


class MockNotificationService:
    """Mock notification service for testing."""

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    def register_websocket_connection(self, queue):
        """Register a websocket connection."""
        pass

    def unregister_websocket_connection(self, queue):
        """Unregister a websocket connection."""
        pass

    async def get_connection_count(self):
        # Return fields matching actual NotificationService implementation
        return {"websocket_connections": 3, "kafka_available": True}


class MockPolicyService:
    """Mock policy service for testing."""

    def __init__(self):
        self._policies = []

    async def list_policies(self, status=None):
        if status:
            return [p for p in self._policies if p.status.value == status]
        return self._policies

    async def create_policy(self, tenant_id, name, description, format_type, metadata=None):
        from app.models import Policy, PolicyStatus

        policy = Policy(
            policy_id=f"policy-{len(self._policies) + 1}",
            tenant_id=tenant_id,
            name=name,
            description=description,
            format=format_type,
            status=PolicyStatus.DRAFT,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._policies.append(policy)
        return policy

    async def get_policy(self, policy_id):
        for p in self._policies:
            if p.policy_id == policy_id:
                return p
        return None


class MockAuditClient:
    """Mock audit client for testing."""

    async def log_event(self, *args, **kwargs):
        pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_crypto_service():
    return MockCryptoService()


@pytest.fixture
def mock_cache_service():
    return MockCacheService()


@pytest.fixture
def mock_notification_service():
    return MockNotificationService()


@pytest.fixture
def mock_policy_service():
    return MockPolicyService()


@pytest.fixture
def mock_audit_client():
    return MockAuditClient()


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    mock = MagicMock()
    mock.security.cors_origins = ["*"]
    mock.audit.url = "http://localhost:8084"
    return mock


@pytest.fixture
def app_with_mocks(
    mock_crypto_service,
    mock_cache_service,
    mock_notification_service,
    mock_policy_service,
    mock_audit_client,
    mock_settings,
):
    """Create FastAPI app with mocked dependencies."""
    from app.api.v1 import health, policies

    app = FastAPI()

    # Override dependencies
    def get_policy_service():
        return mock_policy_service

    def get_cache_service():
        return mock_cache_service

    def get_notification_service():
        return mock_notification_service

    # Include routers with dependency overrides
    app.include_router(health.router, prefix="/health", tags=["health"])

    # Override the dependencies in the router
    app.dependency_overrides[policies.PolicyService] = get_policy_service

    return app


@pytest.fixture
def client(app_with_mocks):
    """Create test client."""
    return TestClient(app_with_mocks)


# =============================================================================
# Health Endpoint Tests
# =============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_policy_health_endpoint(self, mock_settings):
        """Test policy health endpoint returns correct data."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        # Create mock policy service with policies
        mock_policy_svc = MockPolicyService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_policy_service] = lambda: mock_policy_svc

        client = TestClient(app)

        with patch("app.services.storage_service.settings", mock_settings):
            response = client.get("/health/policies")

        # Should get 200 even with empty policies
        assert response.status_code == 200
        data = response.json()
        assert "total_policies" in data
        assert "active_policies" in data
        assert "policies" in data

    def test_cache_health_endpoint(self, mock_settings):
        """Test cache health endpoint returns stats."""
        from app.api.dependencies import get_cache_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_cache_svc = MockCacheService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_svc

        client = TestClient(app)

        response = client.get("/health/cache")

        assert response.status_code == 200
        data = response.json()
        # Match actual CacheService.get_cache_stats() return fields
        assert "local_cache_size" in data
        assert "redis_available" in data

    def test_connection_health_endpoint(self, mock_settings):
        """Test connection health endpoint returns connection counts."""
        from app.api.dependencies import get_notification_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_notification_svc = MockNotificationService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_notification_service] = lambda: mock_notification_svc

        client = TestClient(app)

        response = client.get("/health/connections")

        assert response.status_code == 200
        data = response.json()
        # Match actual NotificationService.get_connection_count() return fields
        assert "websocket_connections" in data
        assert "kafka_available" in data


# =============================================================================
# Policy Creation Tests
# =============================================================================


class TestPolicyCreation:
    """Tests for policy creation endpoints."""

    def test_create_policy_endpoint_structure(self, mock_settings):
        """Test that policy creation endpoint is properly structured."""
        from app.api.v1 import policies

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        # Check that routes are registered
        routes = [r.path for r in app.routes]
        assert any("/policies" in str(r) for r in routes)


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for API error handling."""

    def test_404_for_nonexistent_endpoint(self, mock_settings):
        """Test that nonexistent endpoints return 404."""
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        client = TestClient(app)

        response = client.get("/health/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self, mock_settings):
        """Test that wrong HTTP methods return 405."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_policy_svc = MockPolicyService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_policy_service] = lambda: mock_policy_svc

        client = TestClient(app)

        # POST to a GET-only endpoint
        response = client.post("/health/policies")

        assert response.status_code == 405


# =============================================================================
# Response Format Tests
# =============================================================================


class TestResponseFormat:
    """Tests for API response format."""

    def test_health_response_is_json(self, mock_settings):
        """Test that health endpoints return valid JSON."""
        from app.api.dependencies import get_cache_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_cache_svc = MockCacheService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_svc

        client = TestClient(app)

        response = client.get("/health/cache")

        assert response.headers["content-type"] == "application/json"
        # Should be parseable as JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_policy_list_response_structure(self, mock_settings):
        """Test that policy list response has correct structure."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_policy_svc = MockPolicyService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_policy_service] = lambda: mock_policy_svc

        client = TestClient(app)

        response = client.get("/health/policies")

        assert response.status_code == 200
        data = response.json()

        # Verify expected fields exist
        assert "total_policies" in data
        assert "active_policies" in data
        assert isinstance(data["total_policies"], int)
        assert isinstance(data["active_policies"], int)


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


class TestConstitutionalCompliance:
    """Tests for constitutional compliance in API responses."""

    def test_health_endpoint_available(self, mock_settings):
        """Test that health endpoints are available for monitoring."""
        from app.api.dependencies import get_cache_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_cache_svc = MockCacheService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_svc

        client = TestClient(app)

        # All health endpoints should be available
        response = client.get("/health/cache")
        assert response.status_code == 200


# =============================================================================
# Integration-style Tests (Unit with FastAPI TestClient)
# =============================================================================


class TestAPIIntegration:
    """Integration-style tests for API endpoints."""

    def test_multiple_health_endpoints_work(self, mock_settings):
        """Test that multiple health endpoints work together."""
        from app.api.dependencies import (
            get_cache_service,
            get_notification_service,
            get_policy_service,
        )
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_policy_svc = MockPolicyService()
        mock_cache_svc = MockCacheService()
        mock_notification_svc = MockNotificationService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory functions, not the classes
        app.dependency_overrides[get_policy_service] = lambda: mock_policy_svc
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_svc
        app.dependency_overrides[get_notification_service] = lambda: mock_notification_svc

        client = TestClient(app)

        # All three health endpoints should work
        responses = [
            client.get("/health/policies"),
            client.get("/health/cache"),
            client.get("/health/connections"),
        ]

        for response in responses:
            assert response.status_code == 200
            assert isinstance(response.json(), dict)

    def test_health_endpoints_return_numeric_metrics(self, mock_settings):
        """Test that health endpoints return numeric metrics."""
        from app.api.dependencies import get_cache_service
        from app.api.v1 import health
        from fastapi.testclient import TestClient

        mock_cache_svc = MockCacheService()

        app = FastAPI()
        app.include_router(health.router, prefix="/health")

        # Override the factory function, not the class
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_svc

        client = TestClient(app)

        response = client.get("/health/cache")
        data = response.json()

        # Numeric fields should be numbers (matching actual CacheService fields)
        assert isinstance(data["local_cache_size"], (int, float))
        assert isinstance(data["redis_connected_clients"], (int, float))
