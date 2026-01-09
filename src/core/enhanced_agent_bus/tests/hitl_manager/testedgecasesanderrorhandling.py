"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
Tests cover:
- edgecasesanderrorhandling functionality
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


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in HITLManager."""

    @pytest.mark.asyncio
    async def test_empty_content_message(self):
        """Test handling of message with empty content."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
            DeliberationStatus,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={},  # Empty content
        )

        item_id = await queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        task = queue.get_task(item_id)
        assert task.status == DeliberationStatus.UNDER_REVIEW

        await queue.stop()

    @pytest.mark.asyncio
    async def test_special_characters_in_reasoning(self):
        """Test special characters in reasoning field."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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

        special_reasoning = "<script>alert('xss')</script> & 'quotes' \"double\" emoji: 🚨"

        result = await manager.process_approval(
            item_id=item_id, reviewer_id="reviewer", decision="approve", reasoning=special_reasoning
        )

        assert result is True
        assert ledger.results[0].metadata["reasoning"] == special_reasoning

        await queue.stop()

    @pytest.mark.asyncio
    async def test_concurrent_approval_requests(self):
        """Test concurrent approval requests don't interfere."""
        import asyncio

        from enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
            DeliberationStatus,
        )
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue)

        # Create multiple items
        item_ids = []
        for i in range(5):
            message = AgentMessage(
                from_agent=f"agent-{i}",
                to_agent="recipient",
                message_type=MessageType.COMMAND,
                content={"action": f"action-{i}"},
            )
            item_id = await queue.enqueue_for_deliberation(message)
            item_ids.append(item_id)

        # Request approvals concurrently
        await asyncio.gather(*[manager.request_approval(item_id) for item_id in item_ids])

        # Verify all items are under review
        for item_id in item_ids:
            task = queue.get_task(item_id)
            assert task.status == DeliberationStatus.UNDER_REVIEW

        await queue.stop()

    @pytest.mark.asyncio
    async def test_long_content_truncation(self, caplog):
        """Test that long content is truncated in notification."""
        import logging

        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

        queue = DeliberationQueue()
        manager = HITLManager(queue)

        # Create message with very long content
        long_content = "A" * 500
        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content=long_content,
        )

        item_id = await queue.enqueue_for_deliberation(message)

        with caplog.at_level(logging.INFO):
            await manager.request_approval(item_id)

        # Content should be truncated (100 chars + "...")
        assert "..." in caplog.text

        await queue.stop()
