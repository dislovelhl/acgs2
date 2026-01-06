"""
Tests for actualhitlmanager.

Tests cover:
- actualhitlmanager functionality
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


class TestActualHITLManager:
    """Tests for the actual HITLManager implementation."""

    @pytest.fixture
    async def real_queue(self):
        """Create a real DeliberationQueue."""
        from src.core.enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )

        queue = DeliberationQueue()
        yield queue
        await queue.stop()

    @pytest.fixture
    async def real_hitl_manager(self, real_queue):
        """Create a real HITLManager instance."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)
        return manager

    @pytest.mark.asyncio
    async def test_real_hitl_manager_init(self, real_queue):
        """Test real HITLManager initialization."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)
        assert manager.queue is real_queue
        assert manager.audit_ledger is not None

    @pytest.mark.asyncio
    async def test_real_request_approval_with_message(self, real_queue, caplog):
        """Test request_approval with a real AgentMessage."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

        manager = HITLManager(real_queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "high-risk-operation"},
            impact_score=0.85,
        )

        item_id = await real_queue.enqueue_for_deliberation(message)

        with caplog.at_level(logging.INFO):
            await manager.request_approval(item_id)

        assert "Notification sent to slack" in caplog.text

        # Verify status changed
        from src.core.enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationStatus,
        )

        task = real_queue.get_task(item_id)
        assert task.status == DeliberationStatus.UNDER_REVIEW

    @pytest.mark.asyncio
    async def test_real_request_approval_item_not_found(self, real_queue, caplog):
        """Test request_approval when item doesn't exist."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)

        with caplog.at_level(logging.ERROR):
            await manager.request_approval("nonexistent-item")

        assert "not found" in caplog.text

    @pytest.mark.asyncio
    async def test_real_request_approval_teams_channel(self, real_queue, caplog):
        """Test request_approval with Teams channel."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

        manager = HITLManager(real_queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )

        item_id = await real_queue.enqueue_for_deliberation(message)

        with caplog.at_level(logging.INFO):
            await manager.request_approval(item_id, channel="teams")

        assert "teams" in caplog.text

    @pytest.mark.asyncio
    async def test_real_process_approval_approve(self, real_queue, caplog):
        """Test process_approval with approve decision."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

        manager = HITLManager(real_queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "modify-policy"},
            impact_score=0.9,
        )

        item_id = await real_queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        with caplog.at_level(logging.INFO):
            result = await manager.process_approval(
                item_id=item_id,
                reviewer_id="reviewer-001",
                decision="approve",
                reasoning="Action is compliant",
            )

        assert result is True
        assert "Decision for" in caplog.text
        assert "recorded" in caplog.text

    @pytest.mark.asyncio
    async def test_real_process_approval_reject(self, real_queue, caplog):
        """Test process_approval with reject decision."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

        manager = HITLManager(real_queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "risky-operation"},
        )

        item_id = await real_queue.enqueue_for_deliberation(message)
        await manager.request_approval(item_id)

        with caplog.at_level(logging.INFO):
            result = await manager.process_approval(
                item_id=item_id,
                reviewer_id="security-reviewer",
                decision="reject",
                reasoning="Violates security policy",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_real_process_approval_invalid_item(self, real_queue):
        """Test process_approval with invalid item_id."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)

        result = await manager.process_approval(
            item_id="invalid-item", reviewer_id="reviewer", decision="approve", reasoning="test"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_real_process_approval_not_under_review(self, real_queue):
        """Test process_approval fails if item not under review."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

        manager = HITLManager(real_queue)

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="recipient",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )

        item_id = await real_queue.enqueue_for_deliberation(message)
        # Don't call request_approval - item is PENDING not UNDER_REVIEW

        result = await manager.process_approval(
            item_id=item_id, reviewer_id="reviewer", decision="approve", reasoning="test"
        )

        assert result is False
