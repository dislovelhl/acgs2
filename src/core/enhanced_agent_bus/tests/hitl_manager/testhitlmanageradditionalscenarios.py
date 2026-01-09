"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
Tests cover:
- hitlmanageradditionalscenarios functionality
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


class TestHITLManagerAdditionalScenarios:
    """Additional test scenarios for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_process_approval_with_various_decisions(self):
        """Test process_approval with different decision types."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue)

        # Create and enqueue a message
        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test_various"},
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        # Test with "deny" decision (should map to rejected)
        result = await manager.process_approval(
            item_id=item_id,
            reviewer_id="reviewer-123",
            decision="deny",
            reasoning="Denied for testing",
        )

        assert result is True
        await queue.stop()

    @pytest.mark.asyncio
    async def test_request_approval_logs_correctly(self, caplog):
        """Test that request_approval logs notification correctly."""
        import logging

        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        with caplog.at_level(logging.INFO):
            queue = DeliberationQueue()
            manager = HITLManager(queue)

            message = AgentMessage(
                from_agent="logging-agent",
                to_agent="recipient",
                message_type=MessageType.COMMAND,
                content={"action": "test_logging"},
                impact_score=0.95,
            )

            item_id = await queue.enqueue_for_deliberation(message)
            await manager.request_approval(item_id)

            # Check that notification was logged
            assert any("Notification sent" in record.message for record in caplog.records)

            await queue.stop()

    @pytest.mark.asyncio
    async def test_process_approval_logs_decision(self, caplog):
        """Test that process_approval logs the decision."""
        import logging

        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        with caplog.at_level(logging.INFO):
            queue = DeliberationQueue()
            manager = HITLManager(queue)

            message = AgentMessage(
                from_agent="logging-agent",
                to_agent="recipient",
                message_type=MessageType.COMMAND,
                content={"action": "test_decision_logging"},
            )

            item_id = await queue.enqueue_for_deliberation(message)
            await manager.request_approval(item_id)

            await manager.process_approval(
                item_id=item_id,
                reviewer_id="reviewer",
                decision="approve",
                reasoning="Approved for testing",
            )

            # Check that decision was logged
            assert any(
                "Decision for" in record.message and "recorded" in record.message
                for record in caplog.records
            )

            await queue.stop()

    @pytest.mark.asyncio
    async def test_multiple_sequential_approvals(self):
        """Test handling multiple sequential approval workflows."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue)

        # Process 3 messages sequentially
        for i in range(3):
            message = AgentMessage(
                from_agent=f"agent-{i}",
                to_agent="recipient",
                message_type=MessageType.COMMAND,
                content={"action": f"test_{i}"},
            )

            item_id = await queue.enqueue_for_deliberation(message)
            await manager.request_approval(item_id)

            decision = "approve" if i % 2 == 0 else "reject"
            result = await manager.process_approval(
                item_id=item_id,
                reviewer_id=f"reviewer-{i}",
                decision=decision,
                reasoning=f"Decision {i}",
            )
            assert result is True

        await queue.stop()
