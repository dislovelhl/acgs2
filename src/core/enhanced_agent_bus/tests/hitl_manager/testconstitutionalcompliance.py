"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
Tests cover:
- constitutionalcompliance functionality
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


class TestConstitutionalCompliance:
    """Test constitutional compliance in HITL operations."""

    @pytest.mark.asyncio
    @pytest.mark.constitutional
    async def test_constitutional_hash_in_audit_trail(self):
        """Verify constitutional hash is maintained in audit trail."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import (
            CONSTITUTIONAL_HASH,
            AgentMessage,
            MessageType,
        )

        class TrackingLedger:
            def __init__(self):
                self.results = []

            async def add_validation_result(self, result):
                self.results.append(result)
                return "hash"

        queue = DeliberationQueue()
        ledger = TrackingLedger()
        manager = HITLManager(queue, audit_ledger=ledger)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        await manager.process_approval(
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning="Compliant with constitutional principles",
        )

        # Verify constitutional hash in audit
        audit_result = ledger.results[0]
        assert audit_result.constitutional_hash == CONSTITUTIONAL_HASH

        await queue.stop()

    @pytest.mark.asyncio
    @pytest.mark.constitutional
    async def test_all_decisions_include_timestamp(self):
        """Verify all decisions include proper timestamps."""

        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        class TrackingLedger:
            def __init__(self):
                self.results = []

            async def add_validation_result(self, result):
                self.results.append(result)
                return "hash"

        queue = DeliberationQueue()
        ledger = TrackingLedger()
        manager = HITLManager(queue, audit_ledger=ledger)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        await manager.process_approval(
            item_id=item_id, reviewer_id="reviewer", decision="approve", reasoning="test"
        )

        audit_result = ledger.results[0]
        assert "timestamp" in audit_result.metadata
        # Verify timestamp is valid ISO format
        timestamp = audit_result.metadata["timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        await queue.stop()
