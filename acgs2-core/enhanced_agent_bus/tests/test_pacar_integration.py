"""
ACGS-2 Enhanced Agent Bus - PACAR Multi-Turn Integration Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests PACAR verifier multi-turn conversation support with API integration.
"""

import importlib.util
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Add enhanced_agent_bus directory to path
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)

# Import the FastAPI app
import api


def _load_module(name, path):
    """Load a module directly from path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class MockRedisClientWithTTL:
    """Mock Redis client that tracks TTL for session expiration testing."""

    def __init__(self):
        self._data = {}
        self._ttls = {}

    async def ping(self):
        return True

    async def close(self):
        pass

    async def get(self, key):
        return self._data.get(key)

    async def setex(self, key, ttl_seconds, value):
        """Store value with TTL tracking."""
        self._data[key] = value
        self._ttls[key] = ttl_seconds
        return True

    async def delete(self, key):
        if key in self._data:
            del self._data[key]
            if key in self._ttls:
                del self._ttls[key]
            return 1
        return 0

    def get_ttl(self, key):
        """Get the TTL that was set for a key."""
        return self._ttls.get(key)


class TestAPISessionHeader:
    """Tests for API session header support with X-Session-ID."""

    @pytest.fixture(autouse=True)
    def mock_agent_bus(self):
        """Mock agent_bus to simulate initialized state."""
        with patch.object(
            api, "agent_bus", {"status": "initialized", "services": ["redis", "kafka", "opa"]}
        ):
            yield

    @pytest.mark.asyncio
    async def test_api_session_header(self):
        """Test /messages endpoint with X-Session-ID header stores session."""
        transport = ASGITransport(app=api.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send message with X-Session-ID header
            response = await client.post(
                "/messages",
                json={
                    "content": "Test message for session tracking",
                    "sender": "test_user",
                    "message_type": "user_request",
                },
                headers={"X-Session-ID": "test-session-123"},
            )

            # Verify response status
            assert response.status_code == 200

            # Verify response contains session_id
            data = response.json()
            assert "message_id" in data
            assert data["status"] == "accepted"
            assert "details" in data
            assert data["details"]["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_api_session_header_optional(self):
        """Test /messages endpoint works without X-Session-ID header (backward compatibility)."""
        transport = ASGITransport(app=api.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send message without session header
            response = await client.post(
                "/messages",
                json={
                    "content": "Test message without session",
                    "sender": "test_user",
                    "message_type": "user_request",
                },
            )

            # Verify response status
            assert response.status_code == 200

            # Verify response works without session_id
            data = response.json()
            assert "message_id" in data
            assert data["status"] == "accepted"
            assert "details" in data
            # session_id should be None when not provided
            assert data["details"]["session_id"] is None

    @pytest.mark.asyncio
    async def test_api_session_body_takes_precedence(self):
        """Test session_id in request body takes precedence over header."""
        transport = ASGITransport(app=api.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send message with session_id in both body and header
            response = await client.post(
                "/messages",
                json={
                    "content": "Test message with body session",
                    "sender": "test_user",
                    "message_type": "user_request",
                    "session_id": "body-session-456",
                },
                headers={"X-Session-ID": "header-session-789"},
            )

            # Verify response status
            assert response.status_code == 200

            # Verify body session_id takes precedence
            data = response.json()
            assert data["details"]["session_id"] == "body-session-456"


class TestSessionTTLExpiration:
    """Tests for session TTL expiration behavior."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client with TTL tracking."""
        return MockRedisClientWithTTL()

    @pytest.fixture
    def mock_llm_assistant(self):
        """Create mock LLM assistant for testing."""
        mock_assistant = AsyncMock()
        mock_assistant.analyze_message_impact.return_value = {
            "risk_level": "low",
            "confidence": 0.9,
            "reasoning": ["Test reasoning"],
            "mitigations": [],
        }
        return mock_assistant

    @pytest.mark.asyncio
    async def test_session_ttl_expiration(self, mock_redis, mock_llm_assistant):
        """Test that session storage uses correct TTL for expiration."""
        # Load PACAR verifier module
        pacar_mod = _load_module(
            "_pacar_ttl_test",
            os.path.join(enhanced_agent_bus_dir, "sdpc", "pacar_verifier.py"),
        )

        verifier = pacar_mod.PACARVerifier()
        verifier.redis_client = mock_redis
        verifier.assistant = mock_llm_assistant

        # Execute verification with session
        session_id = "ttl-test-session-123"
        result = await verifier.verify_with_context(
            content="Test content for TTL verification",
            original_intent="Test intent",
            session_id=session_id,
        )

        # Verify verification succeeded
        assert result["is_valid"] is True
        assert result["session_id"] == session_id

        # Verify TTL was set correctly (default 3600 seconds)
        expected_key = f"{verifier.conversation_key}:{session_id}"
        assert expected_key in mock_redis._data
        assert mock_redis.get_ttl(expected_key) == 3600

    @pytest.mark.asyncio
    async def test_session_ttl_custom_value(self, mock_redis, mock_llm_assistant):
        """Test that custom TTL value from environment is respected."""
        # Load PACAR verifier module
        pacar_mod = _load_module(
            "_pacar_ttl_custom_test",
            os.path.join(enhanced_agent_bus_dir, "sdpc", "pacar_verifier.py"),
        )

        verifier = pacar_mod.PACARVerifier()
        verifier.redis_client = mock_redis
        verifier.assistant = mock_llm_assistant

        # Set custom TTL via environment variable
        custom_ttl = "7200"
        with patch.dict(os.environ, {"PACAR_SESSION_TTL": custom_ttl}):
            session_id = "custom-ttl-session-456"
            result = await verifier.verify_with_context(
                content="Test content with custom TTL",
                original_intent="Test intent",
                session_id=session_id,
            )

        # Verify verification succeeded
        assert result["is_valid"] is True

        # Verify custom TTL was applied
        expected_key = f"{verifier.conversation_key}:{session_id}"
        assert mock_redis.get_ttl(expected_key) == 7200

    @pytest.mark.asyncio
    async def test_session_ttl_refresh_on_update(self, mock_redis, mock_llm_assistant):
        """Test that TTL is refreshed (sliding window) on conversation update."""
        # Load PACAR verifier module
        pacar_mod = _load_module(
            "_pacar_ttl_refresh_test",
            os.path.join(enhanced_agent_bus_dir, "sdpc", "pacar_verifier.py"),
        )

        verifier = pacar_mod.PACARVerifier()
        verifier.redis_client = mock_redis
        verifier.assistant = mock_llm_assistant

        session_id = "refresh-ttl-session-789"

        # First verification
        await verifier.verify_with_context(
            content="First message",
            original_intent="Test intent",
            session_id=session_id,
        )

        expected_key = f"{verifier.conversation_key}:{session_id}"
        first_ttl = mock_redis.get_ttl(expected_key)
        assert first_ttl == 3600

        # Second verification should refresh TTL
        await verifier.verify_with_context(
            content="Second message",
            original_intent="Test intent",
            session_id=session_id,
        )

        # TTL should still be 3600 (refreshed)
        second_ttl = mock_redis.get_ttl(expected_key)
        assert second_ttl == 3600

        # Verify conversation has both messages
        conversation_json = mock_redis._data.get(expected_key)
        assert conversation_json is not None
        conversation = json.loads(conversation_json)
        assert len(conversation["messages"]) == 2

    @pytest.mark.asyncio
    async def test_session_no_ttl_without_redis(self, mock_llm_assistant):
        """Test graceful degradation when Redis is unavailable."""
        # Load PACAR verifier module
        pacar_mod = _load_module(
            "_pacar_no_redis_test",
            os.path.join(enhanced_agent_bus_dir, "sdpc", "pacar_verifier.py"),
        )

        verifier = pacar_mod.PACARVerifier()
        verifier.redis_client = None  # No Redis connection
        verifier.assistant = mock_llm_assistant

        # Execute verification with session
        session_id = "no-redis-session-001"
        result = await verifier.verify_with_context(
            content="Test content without Redis",
            original_intent="Test intent",
            session_id=session_id,
        )

        # Verification should still succeed (graceful degradation)
        assert result["is_valid"] is True
        assert result["session_id"] == session_id


# Entry point for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
