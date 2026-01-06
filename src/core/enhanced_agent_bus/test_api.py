"""Constitutional Hash: cdd01ef066bc6cf2
Basic API tests for development environment
"""

import httpx
import pytest


@pytest.fixture
async def async_client():
    """Async HTTP client for testing"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        yield client


class TestAgentBusAPI:
    """Test cases for Agent Bus API"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "service" in data
            assert "version" in data
            assert data["service"] == "enhanced-agent-bus"

    @pytest.mark.asyncio
    async def test_stats_endpoint(self):
        """Test statistics endpoint"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "active_connections" in data
            assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message"""
        message_data = {
            "content": "Test message",
            "message_type": "user_request",
            "priority": "normal",
            "sender": "test-user",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post("/messages", json=message_data)
            assert response.status_code == 200
            data = response.json()
            assert "message_id" in data
            assert "status" in data
            assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_policy_validation(self):
        """Test policy validation endpoint"""
        policy_data = {
            "policy_name": "test_policy",
            "rules": [{"condition": "user.role == 'admin'", "action": "allow"}],
        }
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post("/policies/validate", json=policy_data)
            assert response.status_code == 200
            data = response.json()
            assert "valid" in data
            assert "policy_hash" in data

    @pytest.mark.asyncio
    async def test_invalid_message_format(self):
        """Test error handling for invalid message format"""
        invalid_data = {"invalid_field": "missing required fields"}
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post("/messages", json=invalid_data)
            # Should return 422 for validation error
            assert response.status_code in [400, 422]


class TestAPIGatewayIntegration:
    """Integration tests with API Gateway"""

    @pytest.mark.asyncio
    async def test_gateway_health(self):
        """Test API Gateway health through direct HTTP"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8080/health", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert data["status"] == "healthy"
            except httpx.ConnectError:
                pytest.skip("API Gateway not running")

    @pytest.mark.asyncio
    async def test_gateway_services_endpoint(self):
        """Test API Gateway services listing"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8080/services", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                # Should contain service information
                assert isinstance(data, dict)
            except httpx.ConnectError:
                pytest.skip("API Gateway not running")


class TestInfrastructureHealth:
    """Test infrastructure services health"""

    @pytest.mark.asyncio
    async def test_redis_health(self):
        """Test Redis connectivity"""
        import redis

        try:
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)
            assert r.ping()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_opa_health(self):
        """Test OPA health"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8181/health", timeout=5.0)
                assert response.status_code == 200
            except (httpx.ConnectError, httpx.TimeoutException):
                pytest.skip("OPA not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
