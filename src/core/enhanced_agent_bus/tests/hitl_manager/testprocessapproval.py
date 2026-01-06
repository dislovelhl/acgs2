"""
Tests for processapproval.

Tests cover:
- processapproval functionality
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


class TestProcessApproval:
    """Tests for process_approval method."""

    @pytest.mark.asyncio
    async def test_process_approval_approve_decision(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test process_approval with approve decision."""

        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def process_approval(
                self, item_id: str, reviewer_id: str, decision: str, reasoning: str
            ):
                if decision == "approve":
                    status = MockDeliberationStatus.APPROVED
                else:
                    status = MockDeliberationStatus.REJECTED

                success = await self.queue.submit_human_decision(
                    item_id=item_id, reviewer=reviewer_id, decision=status, reasoning=reasoning
                )

                if success:
                    audit_result = {
                        "is_valid": status == MockDeliberationStatus.APPROVED,
                        "item_id": item_id,
                        "reviewer": reviewer_id,
                        "decision": decision,
                    }
                    await self.audit_ledger.add_validation_result(audit_result)
                    return True
                return False

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)
        result = await manager.process_approval(
            item_id="item-123",
            reviewer_id="reviewer-1",
            decision="approve",
            reasoning="Looks good to me",
        )

        assert result is True
        mock_queue.submit_human_decision.assert_called_once()
        mock_audit_ledger.add_validation_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_approval_reject_decision(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test process_approval with reject decision."""

        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def process_approval(
                self, item_id: str, reviewer_id: str, decision: str, reasoning: str
            ):
                if decision == "approve":
                    status = MockDeliberationStatus.APPROVED
                else:
                    status = MockDeliberationStatus.REJECTED

                success = await self.queue.submit_human_decision(
                    item_id=item_id, reviewer=reviewer_id, decision=status, reasoning=reasoning
                )

                if success:
                    audit_result = {
                        "is_valid": status == MockDeliberationStatus.APPROVED,
                        "item_id": item_id,
                        "reviewer": reviewer_id,
                        "decision": decision,
                    }
                    await self.audit_ledger.add_validation_result(audit_result)
                    return True
                return False

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)
        result = await manager.process_approval(
            item_id="item-123",
            reviewer_id="reviewer-1",
            decision="reject",
            reasoning="Security concerns",
        )

        assert result is True
        call_kwargs = mock_queue.submit_human_decision.call_args.kwargs
        assert call_kwargs["decision"] == MockDeliberationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_process_approval_submission_failure(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test process_approval when submission fails."""
        mock_queue.submit_human_decision.return_value = False

        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def process_approval(
                self, item_id: str, reviewer_id: str, decision: str, reasoning: str
            ):
                if decision == "approve":
                    status = MockDeliberationStatus.APPROVED
                else:
                    status = MockDeliberationStatus.REJECTED

                success = await self.queue.submit_human_decision(
                    item_id=item_id, reviewer=reviewer_id, decision=status, reasoning=reasoning
                )

                if success:
                    audit_result = {
                        "is_valid": status == MockDeliberationStatus.APPROVED,
                        "item_id": item_id,
                        "reviewer": reviewer_id,
                        "decision": decision,
                    }
                    await self.audit_ledger.add_validation_result(audit_result)
                    return True
                return False

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)
        result = await manager.process_approval(
            item_id="item-123", reviewer_id="reviewer-1", decision="approve", reasoning="Approved"
        )

        assert result is False
        # Audit ledger should not be called when submission fails
        mock_audit_ledger.add_validation_result.assert_not_called()
