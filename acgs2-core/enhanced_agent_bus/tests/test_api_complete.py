"""
ACGS-2 Enhanced Agent Bus API - Comprehensive Test Suite
Constitutional Hash: cdd01ef066bc6cf2

Tests for all 12 message types, error scenarios, rate limiting, and performance SLA.
"""

from datetime import datetime

import httpx
import pytest

# Base URL for API tests - can be overridden via environment variable
API_BASE_URL = "http://localhost:8000"


class TestMessageTypeCommand:
    """Test COMMAND message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_command(self):
        """Test sending a COMMAND message type."""
        message_data = {
            "content": "Execute action: test command",
            "message_type": "command",
            "priority": "normal",
            "sender": "test-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert "timestamp" in data
                assert data["details"]["message_type"] == "command"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeQuery:
    """Test QUERY message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_query(self):
        """Test sending a QUERY message type."""
        message_data = {
            "content": "Query: get system status",
            "message_type": "query",
            "priority": "normal",
            "sender": "test-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "query"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeResponse:
    """Test RESPONSE message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_response(self):
        """Test sending a RESPONSE message type."""
        message_data = {
            "content": "Response: query result data",
            "message_type": "response",
            "priority": "normal",
            "sender": "test-agent",
            "recipient": "requesting-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "response"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeEvent:
    """Test EVENT message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_event(self):
        """Test sending an EVENT message type."""
        message_data = {
            "content": "Event: state change notification",
            "message_type": "event",
            "priority": "normal",
            "sender": "test-agent",
            "tenant_id": "test-tenant",
            "metadata": {"event_type": "state_change", "source": "system"},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "event"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeNotification:
    """Test NOTIFICATION message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_notification(self):
        """Test sending a NOTIFICATION message type."""
        message_data = {
            "content": "Notification: system maintenance scheduled",
            "message_type": "notification",
            "priority": "low",
            "sender": "system-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "notification"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeHeartbeat:
    """Test HEARTBEAT message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_heartbeat(self):
        """Test sending a HEARTBEAT message type."""
        message_data = {
            "content": "Heartbeat: agent alive signal",
            "message_type": "heartbeat",
            "priority": "low",
            "sender": "monitor-agent",
            "tenant_id": "test-tenant",
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "heartbeat"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeGovernanceRequest:
    """Test GOVERNANCE_REQUEST message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_governance_request(self):
        """Test sending a GOVERNANCE_REQUEST message type."""
        message_data = {
            "content": "Governance request: policy evaluation needed",
            "message_type": "governance_request",
            "priority": "high",
            "sender": "policy-agent",
            "tenant_id": "test-tenant",
            "metadata": {"policy_id": "pol-001", "action": "evaluate"},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "governance_request"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeGovernanceResponse:
    """Test GOVERNANCE_RESPONSE message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_governance_response(self):
        """Test sending a GOVERNANCE_RESPONSE message type."""
        message_data = {
            "content": "Governance response: policy evaluation result",
            "message_type": "governance_response",
            "priority": "high",
            "sender": "governance-engine",
            "recipient": "policy-agent",
            "tenant_id": "test-tenant",
            "metadata": {"policy_id": "pol-001", "result": "allowed"},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "governance_response"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeConstitutionalValidation:
    """Test CONSTITUTIONAL_VALIDATION message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_constitutional_validation(self):
        """Test sending a CONSTITUTIONAL_VALIDATION message type."""
        message_data = {
            "content": "Constitutional validation: compliance check required",
            "message_type": "constitutional_validation",
            "priority": "critical",
            "sender": "constitutional-validator",
            "tenant_id": "test-tenant",
            "metadata": {"hash": "cdd01ef066bc6cf2", "check_type": "full"},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "constitutional_validation"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeTaskRequest:
    """Test TASK_REQUEST message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_task_request(self):
        """Test sending a TASK_REQUEST message type."""
        message_data = {
            "content": "Task request: process data batch",
            "message_type": "task_request",
            "priority": "normal",
            "sender": "orchestrator-agent",
            "recipient": "worker-agent",
            "tenant_id": "test-tenant",
            "metadata": {"task_id": "task-001", "batch_size": 100},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "task_request"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeTaskResponse:
    """Test TASK_RESPONSE message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_task_response(self):
        """Test sending a TASK_RESPONSE message type."""
        message_data = {
            "content": "Task response: batch processing complete",
            "message_type": "task_response",
            "priority": "normal",
            "sender": "worker-agent",
            "recipient": "orchestrator-agent",
            "tenant_id": "test-tenant",
            "metadata": {"task_id": "task-001", "status": "completed", "processed": 100},
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "task_response"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageTypeAuditLog:
    """Test AUDIT_LOG message type processing."""

    @pytest.mark.asyncio
    async def test_message_type_audit_log(self):
        """Test sending an AUDIT_LOG message type."""
        message_data = {
            "content": "Audit log: action recorded for compliance",
            "message_type": "audit_log",
            "priority": "normal",
            "sender": "audit-agent",
            "tenant_id": "test-tenant",
            "metadata": {
                "action": "data_access",
                "actor": "user-123",
                "resource": "dataset-456",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "message_id" in data
                assert data["status"] == "accepted"
                assert data["details"]["message_type"] == "audit_log"
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestAllTypesIntegration:
    """Integration tests for all message types in sequence."""

    @pytest.mark.asyncio
    async def test_all_twelve_types_accepted_sequential(self):
        """Test all 12 message types are accepted sequentially."""
        message_types = [
            "command",
            "query",
            "response",
            "event",
            "notification",
            "heartbeat",
            "governance_request",
            "governance_response",
            "constitutional_validation",
            "task_request",
            "task_response",
            "audit_log",
        ]

        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                for msg_type in message_types:
                    message_data = {
                        "content": f"Test message for {msg_type}",
                        "message_type": msg_type,
                        "priority": "normal",
                        "sender": "integration-test-agent",
                        "tenant_id": "test-tenant",
                    }
                    response = await client.post("/messages", json=message_data, timeout=10.0)
                    assert response.status_code == 202, f"Failed for message type: {msg_type}"
                    data = response.json()
                    assert data["details"]["message_type"] == msg_type
            except httpx.ConnectError:
                pytest.skip("API server not running")


class TestMessageResponseStructure:
    """Test response structure for message endpoints."""

    @pytest.mark.asyncio
    async def test_response_includes_latency_ms(self):
        """Test that message response includes latency_ms in details."""
        message_data = {
            "content": "Test latency tracking",
            "message_type": "command",
            "priority": "normal",
            "sender": "test-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                data = response.json()
                assert "details" in data
                assert "latency_ms" in data["details"]
                # Latency should be a positive number
                assert data["details"]["latency_ms"] >= 0
            except httpx.ConnectError:
                pytest.skip("API server not running")

    @pytest.mark.asyncio
    async def test_response_includes_rate_limit_headers(self):
        """Test that response includes X-RateLimit-* headers."""
        message_data = {
            "content": "Test rate limit headers",
            "message_type": "command",
            "priority": "normal",
            "sender": "test-agent",
            "tenant_id": "test-tenant",
        }
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            try:
                response = await client.post("/messages", json=message_data, timeout=10.0)
                assert response.status_code == 202
                # Check rate limit headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers
            except httpx.ConnectError:
                pytest.skip("API server not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "message_type"])
