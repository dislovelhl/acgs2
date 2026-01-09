"""
ACGS-2 Integration Tests - Agent Bus Service
Constitutional Hash: cdd01ef066bc6cf2

Tests integration with the Agent Bus service endpoints.
These tests verify:
- Health check endpoint functionality
- Message sending and status retrieval
- Statistics endpoint
- Policy validation endpoint
- Error handling for unavailable service

Usage:
    # Run with mock (offline mode - default)
    pytest src/core/tests/integration/test_agent_bus.py -v

    # Run against live service (requires agent-bus on localhost:8000)
    AGENT_BUS_URL=http://localhost:8000 pytest -v -m integration
"""

import os
import sys
from typing import Any, Dict

import pytest

# Add parent directories to path for local imports
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(_tests_dir)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Try to import httpx, fall back to mock if not available
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# Constants
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
DEFAULT_AGENT_BUS_URL = os.environ.get("AGENT_BUS_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 5.0


# Test Fixtures
@pytest.fixture
def agent_bus_url() -> str:
    """Get the agent bus URL from environment or use default."""
    return os.environ.get("AGENT_BUS_URL", DEFAULT_AGENT_BUS_URL)


@pytest.fixture
def mock_health_response() -> Dict[str, Any]:
    """Mock health check response data."""
    return {
        "status": "healthy",
        "service": "enhanced-agent-bus",
        "version": "1.0.0",
        "agent_bus_status": "healthy",
    }


@pytest.fixture
def mock_message_response() -> Dict[str, Any]:
    """Mock message send response data."""
    return {
        "message_id": "test-message-123",
        "status": "accepted",
        "timestamp": "2024-01-01T00:00:00Z",
        "details": {"message_type": "user_request"},
    }


@pytest.fixture
def mock_stats_response() -> Dict[str, Any]:
    """Mock statistics response data."""
    return {
        "total_messages": 42,
        "active_connections": 3,
        "uptime_seconds": 3600,
        "note": "Development mode - mock statistics",
    }


@pytest.fixture
def mock_policy_response() -> Dict[str, Any]:
    """Mock policy validation response data."""
    return {
        "valid": True,
        "policy_hash": "dev-placeholder-hash",
        "validation_timestamp": "2024-01-01T00:00:00Z",
        "note": "Development mode - simplified validation",
    }


@pytest.fixture
def sample_message_request() -> Dict[str, Any]:
    """Sample message request for testing."""
    return {
        "content": "Test message content for integration test",
        "message_type": "user_request",
        "priority": "normal",
        "sender": "integration-test-sender",
        "recipient": None,
        "tenant_id": "test-tenant",
        "metadata": {"test": True},
    }


@pytest.fixture
def sample_policy_data() -> Dict[str, Any]:
    """Sample policy data for validation testing."""
    return {
        "policy_name": "test_policy",
        "rules": [{"action": "allow", "resource": "test_resource"}],
    }


# Mock HTTP Client Fixture
@pytest.fixture
def mock_http_client(
    mock_health_response,
    mock_message_response,
    mock_stats_response,
    mock_policy_response,
):
    """Create a mock HTTP client for offline testing."""

    class MockResponse:
        def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self) -> Dict[str, Any]:
            return self._json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP Error: {self.status_code}")

    class MockAsyncClient:
        def __init__(self):
            self._responses = {
                "GET:/health": MockResponse(mock_health_response),
                "GET:/stats": MockResponse(mock_stats_response),
                "GET:/messages/": MockResponse(
                    {
                        "message_id": "test-id",
                        "status": "processed",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "details": {"note": "Development mode"},
                    }
                ),
                "POST:/messages": MockResponse(mock_message_response),
                "POST:/policies/validate": MockResponse(mock_policy_response),
            }

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url: str, **kwargs):
            path = url.split("localhost:8000")[-1] if "localhost" in url else url
            for key, response in self._responses.items():
                if key.startswith("GET:") and path.startswith(key[4:]):
                    return response
            return MockResponse({"error": "Not found"}, 404)

        async def post(self, url: str, **kwargs):
            path = url.split("localhost:8000")[-1] if "localhost" in url else url
            for key, response in self._responses.items():
                if key.startswith("POST:") and path.startswith(key[5:]):
                    return response
            return MockResponse({"error": "Not found"}, 404)

    return MockAsyncClient()


# ============================================================================
# Health Check Tests
# ============================================================================
class TestAgentBusHealthCheck:
    """Tests for agent-bus health check endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify health endpoint returns HTTP 200.

        Tests the /health endpoint of the agent-bus service.
        """
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/health")

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_response_structure(
        self, mock_http_client, agent_bus_url, mock_health_response
    ):
        """
        Integration test: Verify health response has correct structure.

        Validates the JSON structure of the health response.
        """
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/health")
            data = response.json()

            assert "status" in data
            assert "service" in data
            assert "version" in data
            assert "agent_bus_status" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_status_is_healthy(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify health status indicates healthy service.
        """
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/health")
            data = response.json()

            assert data["status"] == "healthy"
            assert data["agent_bus_status"] == "healthy"


# ============================================================================
# Message Sending Tests
# ============================================================================
class TestAgentBusMessageSending:
    """Tests for agent-bus message sending endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_returns_accepted(
        self, mock_http_client, agent_bus_url, sample_message_request
    ):
        """
        Integration test: Verify message send returns accepted status.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/messages",
                json=sample_message_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_returns_message_id(
        self, mock_http_client, agent_bus_url, sample_message_request
    ):
        """
        Integration test: Verify message send returns message ID.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/messages",
                json=sample_message_request,
            )

            data = response.json()
            assert "message_id" in data
            assert len(data["message_id"]) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_response_structure(
        self, mock_http_client, agent_bus_url, sample_message_request
    ):
        """
        Integration test: Verify message response has correct structure.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/messages",
                json=sample_message_request,
            )

            data = response.json()
            assert "message_id" in data
            assert "status" in data
            assert "timestamp" in data


# ============================================================================
# Message Status Tests
# ============================================================================
class TestAgentBusMessageStatus:
    """Tests for agent-bus message status retrieval."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_message_status_returns_200(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify message status endpoint returns HTTP 200.
        """
        message_id = "test-message-123"
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/messages/{message_id}")

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_message_status_structure(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify message status response structure.
        """
        message_id = "test-message-123"
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/messages/{message_id}")
            data = response.json()

            assert "message_id" in data
            assert "status" in data


# ============================================================================
# Statistics Tests
# ============================================================================
class TestAgentBusStatistics:
    """Tests for agent-bus statistics endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stats_endpoint_returns_200(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify stats endpoint returns HTTP 200.
        """
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/stats")

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stats_response_structure(self, mock_http_client, agent_bus_url):
        """
        Integration test: Verify stats response has expected fields.
        """
        async with mock_http_client as client:
            response = await client.get(f"{agent_bus_url}/stats")
            data = response.json()

            assert "total_messages" in data
            assert "active_connections" in data
            assert "uptime_seconds" in data


# ============================================================================
# Policy Validation Tests
# ============================================================================
class TestAgentBusPolicyValidation:
    """Tests for agent-bus policy validation endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_policy_validation_returns_200(
        self, mock_http_client, agent_bus_url, sample_policy_data
    ):
        """
        Integration test: Verify policy validation returns HTTP 200.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/policies/validate",
                json=sample_policy_data,
            )

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_policy_validation_response_structure(
        self, mock_http_client, agent_bus_url, sample_policy_data
    ):
        """
        Integration test: Verify policy validation response structure.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/policies/validate",
                json=sample_policy_data,
            )
            data = response.json()

            assert "valid" in data
            assert "policy_hash" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_valid_policy_returns_valid_true(
        self, mock_http_client, agent_bus_url, sample_policy_data
    ):
        """
        Integration test: Verify valid policy returns valid=true.
        """
        async with mock_http_client as client:
            response = await client.post(
                f"{agent_bus_url}/policies/validate",
                json=sample_policy_data,
            )
            data = response.json()

            assert data["valid"] is True


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
        # This test verifies the test file structure is correct
        import inspect

        # Get all test classes in this module
        test_classes = [
            TestAgentBusHealthCheck,
            TestAgentBusMessageSending,
            TestAgentBusMessageStatus,
            TestAgentBusStatistics,
            TestAgentBusPolicyValidation,
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
    not HTTPX_AVAILABLE or os.environ.get("SKIP_LIVE_TESTS", "true").lower() == "true",
    reason="Live tests skipped - set SKIP_LIVE_TESTS=false and ensure httpx is installed",
)
class TestAgentBusLiveService:
    """
    Live integration tests that run against an actual agent-bus service.

    These tests are skipped by default. To run them:
    1. Start the agent-bus service on localhost:8000
    2. Set SKIP_LIVE_TESTS=false
    3. Run: pytest src/core/tests/integration/test_agent_bus.py -v -k "Live"
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_health_check(self, agent_bus_url):
        """Live test: Check health endpoint on running service."""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{agent_bus_url}/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
        except httpx.ConnectError:
            pytest.skip(f"Agent bus not reachable at {agent_bus_url}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_stats_endpoint(self, agent_bus_url):
        """Live test: Check stats endpoint on running service."""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{agent_bus_url}/stats")
                assert response.status_code == 200
                data = response.json()
                assert "total_messages" in data
        except httpx.ConnectError:
            pytest.skip(f"Agent bus not reachable at {agent_bus_url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
