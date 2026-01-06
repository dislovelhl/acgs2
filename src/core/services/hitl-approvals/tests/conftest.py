"""
Pytest configuration and shared fixtures for HITL Approvals tests.

Provides test fixtures for:
- FastAPI test client
- Mock Redis client
- Mock Kafka client
- Mock notification providers
- Test approval chains and policies
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models import (
    ApprovalChain,
    ApprovalLevel,
    ApprovalPriority,
    EscalationPolicy,
)
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client for testing."""
    mock = MagicMock()
    mock.ping = AsyncMock(return_value=True)
    mock.time = AsyncMock(return_value=[int(datetime.now(timezone.utc).timestamp()), 0])
    mock.zadd = AsyncMock(return_value=1)
    mock.zrem = AsyncMock(return_value=1)
    mock.zcard = AsyncMock(return_value=0)
    mock.zrangebyscore = AsyncMock(return_value=[])
    mock.zrange = AsyncMock(return_value=[])
    mock.zrevrangebyscore = AsyncMock(return_value=[])
    mock.zcount = AsyncMock(return_value=0)
    mock.zscore = AsyncMock(return_value=None)
    mock.hset = AsyncMock(return_value=1)
    mock.hgetall = AsyncMock(return_value={})
    mock.hincrby = AsyncMock(return_value=1)
    mock.sadd = AsyncMock(return_value=1)
    mock.scard = AsyncMock(return_value=0)
    mock.smembers = AsyncMock(return_value=set())
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.keys = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    mock.pipeline = MagicMock()

    # Create a mock pipeline context manager
    pipeline_mock = MagicMock()
    pipeline_mock.execute = AsyncMock(return_value=[])
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)

    mock.pipeline.return_value = pipeline_mock

    return mock


@pytest.fixture
def mock_kafka_producer() -> MagicMock:
    """Create a mock Kafka producer for testing."""
    mock = MagicMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.flush = AsyncMock()
    mock.send_and_wait = AsyncMock()
    mock.partitions_for = AsyncMock(return_value={0, 1, 2})
    return mock


@pytest.fixture
def mock_kafka_consumer() -> MagicMock:
    """Create a mock Kafka consumer for testing."""
    mock = MagicMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock


@pytest.fixture
def mock_notification_provider() -> MagicMock:
    """Create a mock notification provider for testing."""
    from app.notifications.base import NotificationResult, NotificationStatus

    mock = MagicMock()
    mock.initialize = AsyncMock(return_value=True)
    mock.is_enabled = True
    mock.is_healthy = True
    mock.provider_name = "mock"
    mock.send_notification = AsyncMock(
        return_value=NotificationResult(
            status=NotificationStatus.SENT,
            provider="mock",
            message_id="mock-msg-123",
        )
    )
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def sample_approval_chain() -> ApprovalChain:
    """Create a sample approval chain for testing."""
    return ApprovalChain(
        chain_id="test-chain",
        name="Test Approval Chain",
        description="A test approval chain for unit tests",
        levels=[
            ApprovalLevel(
                level=1,
                role="reviewer",
                approvers=["user-1", "user-2"],
                timeout_minutes=30,
            ),
            ApprovalLevel(
                level=2,
                role="manager",
                approvers=["manager-1"],
                timeout_minutes=15,
            ),
        ],
        fallback_approver="admin",
    )


@pytest.fixture
def sample_escalation_policy() -> EscalationPolicy:
    """Create a sample escalation policy for testing."""
    return EscalationPolicy(
        policy_id="test-policy",
        name="Test Escalation Policy",
        description="A test escalation policy",
        priority=ApprovalPriority.HIGH,
        timeout_minutes=15,
        max_escalations=3,
        notify_on_escalation=True,
        pagerduty_on_critical=True,
    )


@pytest.fixture
def sample_approval_request_data() -> Dict[str, Any]:
    """Create sample approval request data for API testing."""
    return {
        "decision_id": "test-decision-001",
        "decision_type": "high_risk",
        "content": "Test approval request for e2e testing",
        "impact_level": "high",
        "priority": "high",
        "chain_id": "test-chain",
        "requestor_id": "test-user",
        "requestor_service": "test-service",
        "metadata": {"test_key": "test_value"},
    }


@pytest.fixture
def sample_decision_data() -> Dict[str, Any]:
    """Create sample decision data for API testing."""
    return {
        "reviewer_id": "reviewer-123",
        "decision": "approve",
        "reasoning": "Test approval - all requirements met",
        "reviewer_role": "reviewer",
    }


@pytest.fixture
async def reset_singletons():
    """Reset all singleton instances before and after tests."""
    # Reset before test
    from app.audit.ledger import reset_audit_ledger
    from app.core.approval_engine import reset_approval_engine
    from app.core.escalation import reset_escalation_engine, reset_escalation_manager

    reset_approval_engine()
    reset_escalation_manager()
    reset_escalation_engine()
    reset_audit_ledger()

    yield

    # Reset after test
    reset_approval_engine()
    reset_escalation_manager()
    reset_escalation_engine()
    reset_audit_ledger()


@pytest.fixture
async def test_client(reset_singletons) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for the HITL Approvals API.

    Uses httpx.AsyncClient with ASGITransport for async testing.
    """
    from main import app

    # Patch the lifespan to avoid actual initialization
    with patch("main.initialize_approval_engine", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


@pytest.fixture
def sync_test_client(reset_singletons) -> TestClient:
    """
    Create a synchronous test client for simple API tests.

    Uses FastAPI's TestClient for synchronous testing.
    """
    from main import app

    # Patch the lifespan to avoid actual initialization
    with patch("main.initialize_approval_engine", new_callable=AsyncMock):
        return TestClient(app)


# Event capture helpers for testing
class EventCapture:
    """Helper class to capture and verify events during tests."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.notifications: List[Dict[str, Any]] = []
        self.audit_entries: List[Dict[str, Any]] = []

    def capture_event(self, event: Dict[str, Any]) -> None:
        """Capture a Kafka event."""
        self.events.append(event)

    def capture_notification(self, notification: Dict[str, Any]) -> None:
        """Capture a notification."""
        self.notifications.append(notification)

    def capture_audit_entry(self, entry: Dict[str, Any]) -> None:
        """Capture an audit entry."""
        self.audit_entries.append(entry)

    def clear(self) -> None:
        """Clear all captured events."""
        self.events.clear()
        self.notifications.clear()
        self.audit_entries.clear()


@pytest.fixture
def event_capture() -> EventCapture:
    """Create an event capture helper for testing."""
    return EventCapture()
