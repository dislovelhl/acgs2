"""
ACGS-2 Enhanced Agent Bus - PACAR Multi-Turn Integration Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests PACAR verifier multi-turn conversation support with API integration.
"""

import os
import sys
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

# Add enhanced_agent_bus directory to path
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)

# Import the FastAPI app
import api


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


# Entry point for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
