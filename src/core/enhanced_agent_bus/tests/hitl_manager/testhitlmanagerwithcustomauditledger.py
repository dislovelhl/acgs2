"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
Tests cover:
- hitlmanagerwithcustomauditledger functionality
- Error handling and edge cases
- Integration with related components
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


class TestHITLManagerWithCustomAuditLedger:
    """Tests for HITLManager with custom audit ledger."""

    @pytest.fixture
    async def custom_audit_ledger(self):
        """Create a custom audit ledger that tracks calls."""

        class TrackingAuditLedger:
            def __init__(self):
                self.results = []

            async def add_validation_result(self, result):
                self.results.append(result)
                return f"audit_hash_{len(self.results)}"

        return TrackingAuditLedger()

    @pytest.mark.asyncio
    async def test_custom_audit_ledger_receives_results(self, custom_audit_ledger):
        """Test that custom audit ledger receives validation results."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue, audit_ledger=custom_audit_ledger)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        await manager.process_approval(
            item_id=item_id, reviewer_id="reviewer", decision="approve", reasoning="Approved"
        )

        assert len(custom_audit_ledger.results) == 1
        audit = custom_audit_ledger.results[0]
        assert audit.is_valid is True
        assert audit.metadata["reviewer"] == "reviewer"
        assert audit.metadata["decision"] == "approve"

        await queue.stop()

    @pytest.mark.asyncio
    async def test_audit_records_constitutional_hash(self, custom_audit_ledger):
        """Test that audit records include constitutional hash."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import (
            CONSTITUTIONAL_HASH,
            AgentMessage,
            MessageType,
        )

        queue = DeliberationQueue()
        manager = HITLManager(queue, audit_ledger=custom_audit_ledger)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        await manager.process_approval(
            item_id=item_id, reviewer_id="reviewer", decision="approve", reasoning="Test"
        )

        audit = custom_audit_ledger.results[0]
        assert audit.constitutional_hash == CONSTITUTIONAL_HASH

        await queue.stop()
