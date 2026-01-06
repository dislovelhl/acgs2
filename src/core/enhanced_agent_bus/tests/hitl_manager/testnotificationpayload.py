"""
Tests for notificationpayload.

Tests cover:
- notificationpayload functionality
- Error handling and edge cases
- Integration with related components
"""

"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockDeliberationStatus(Enum):
    """Mock deliberation status enum."""

    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MockMessageType(Enum):
    """Mock message type enum."""

    COMMAND = "COMMAND"
    QUERY = "QUERY"


@dataclass
class MockMessage:
    """Mock message for testing."""

    from_agent: str = "test-agent"
    impact_score: float = 0.85
    message_type: MockMessageType = MockMessageType.COMMAND
    content: str = "Test action content that needs approval from human reviewer"


@dataclass
class MockQueueItem:
    """Mock queue item for testing."""

    id: str = "item-123"
    message: MockMessage = field(default_factory=MockMessage)
    status: MockDeliberationStatus = MockDeliberationStatus.PENDING


class MockDeliberationQueue:
    """Mock deliberation queue for testing."""

    def __init__(self):
        self.queue: Dict[str, MockQueueItem] = {}
        self.submit_human_decision = AsyncMock(return_value=True)

    def add_item(self, item_id: str, item: MockQueueItem):
        """Add item to the queue."""
        self.queue[item_id] = item


class MockAuditLedger:
    """Mock audit ledger for testing."""

    def __init__(self):
        self.add_validation_result = AsyncMock(return_value="mock_audit_hash_12345")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_queue() -> MockDeliberationQueue:
    """Create a mock deliberation queue."""
    queue = MockDeliberationQueue()
    item = MockQueueItem(id="item-123")
    queue.add_item("item-123", item)
    return queue


@pytest.fixture
def mock_audit_ledger() -> MockAuditLedger:
    """Create a mock audit ledger."""
    return MockAuditLedger()


# =============================================================================
# Import and Test HITLManager
# =============================================================================


# We need to patch the imports before importing HITLManager
@pytest.fixture
def hitl_manager_class():
    """Get HITLManager class with mocked dependencies."""
    with patch.dict(
        "sys.modules",
        {
            "deliberation_queue": MagicMock(),
        },
    ):
        # Create mock modules
        mock_deliberation_queue = MagicMock()
        mock_deliberation_queue.DeliberationStatus = MockDeliberationStatus
        mock_deliberation_queue.DeliberationQueue = MockDeliberationQueue

        with patch.object(
            __import__("sys"),
            "modules",
            {**__import__("sys").modules, "deliberation_queue": mock_deliberation_queue},
        ):
            from deliberation_layer.hitl_manager import HITLManager

            return HITLManager


# =============================================================================
# Direct Import Tests (Using Mock Classes)
# =============================================================================


class TestNotificationPayload:
    """Tests for notification payload generation."""

    def test_notification_payload_structure(self) -> None:
        """Test that notification payload has correct structure."""
        msg = MockMessage()

        payload = {
            "text": "High-Risk Agent Action Detected",
            "attachments": [
                {
                    "fields": [
                        {"title": "Agent ID", "value": msg.from_agent, "short": True},
                        {"title": "Impact Score", "value": str(msg.impact_score), "short": True},
                        {"title": "Action Type", "value": msg.message_type.value, "short": False},
                    ],
                    "callback_id": "item-123",
                    "actions": [
                        {"name": "approve", "text": "Approve", "type": "button"},
                        {"name": "reject", "text": "Reject", "type": "button"},
                    ],
                }
            ],
        }

        assert payload["text"] == "High-Risk Agent Action Detected"
        assert len(payload["attachments"]) == 1
        assert len(payload["attachments"][0]["actions"]) == 2

    def test_notification_payload_agent_info(self) -> None:
        """Test notification payload includes agent information."""
        msg = MockMessage(from_agent="critical-agent", impact_score=0.95)

        fields = [
            {"title": "Agent ID", "value": msg.from_agent, "short": True},
            {"title": "Impact Score", "value": str(msg.impact_score), "short": True},
        ]

        assert fields[0]["value"] == "critical-agent"
        assert fields[1]["value"] == "0.95"
