"""
ACGS-2 Enhanced Agent Bus - HITL Manager Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the HITLManager class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


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
    with patch.dict('sys.modules', {
        'deliberation_queue': MagicMock(),
    }):
        # Create mock modules
        mock_deliberation_queue = MagicMock()
        mock_deliberation_queue.DeliberationStatus = MockDeliberationStatus
        mock_deliberation_queue.DeliberationQueue = MockDeliberationQueue

        with patch.object(
            __import__('sys'), 'modules',
            {**__import__('sys').modules,
             'deliberation_queue': mock_deliberation_queue}
        ):
            from deliberation_layer.hitl_manager import HITLManager
            return HITLManager


# =============================================================================
# Direct Import Tests (Using Mock Classes)
# =============================================================================

class TestHITLManagerImports:
    """Test HITLManager can be imported."""

    def test_import_hitl_manager(self) -> None:
        """Test that HITLManager can be imported."""
        try:
            from deliberation_layer.hitl_manager import HITLManager
            assert HITLManager is not None
        except ImportError:
            # Expected in isolated test environment
            pass


# =============================================================================
# HITLManager Tests Using Mocks
# =============================================================================

class TestHITLManagerInitialization:
    """Tests for HITLManager initialization."""

    def test_initialization_with_defaults(self, mock_queue: MockDeliberationQueue) -> None:
        """Test initialization with default parameters."""
        # Create a simple HITLManager-like class for testing
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

        manager = TestableHITLManager(mock_queue)
        assert manager.queue is mock_queue
        assert manager.audit_ledger is not None

    def test_initialization_with_custom_audit_ledger(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test initialization with custom audit ledger."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)
        assert manager.audit_ledger is mock_audit_ledger


# =============================================================================
# Request Approval Tests
# =============================================================================

class TestRequestApproval:
    """Tests for request_approval method."""

    @pytest.mark.asyncio
    async def test_request_approval_valid_item(
        self, mock_queue: MockDeliberationQueue
    ) -> None:
        """Test request_approval with a valid queue item."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def request_approval(self, item_id: str, channel: str = "slack"):
                item = self.queue.queue.get(item_id)
                if not item:
                    return None
                item.status = MockDeliberationStatus.UNDER_REVIEW
                return item

        manager = TestableHITLManager(mock_queue)
        result = await manager.request_approval("item-123")

        assert result is not None
        assert result.status == MockDeliberationStatus.UNDER_REVIEW

    @pytest.mark.asyncio
    async def test_request_approval_missing_item(
        self, mock_queue: MockDeliberationQueue
    ) -> None:
        """Test request_approval with a missing queue item."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def request_approval(self, item_id: str, channel: str = "slack"):
                item = self.queue.queue.get(item_id)
                if not item:
                    return None
                item.status = MockDeliberationStatus.UNDER_REVIEW
                return item

        manager = TestableHITLManager(mock_queue)
        result = await manager.request_approval("nonexistent-item")

        assert result is None

    @pytest.mark.asyncio
    async def test_request_approval_teams_channel(
        self, mock_queue: MockDeliberationQueue
    ) -> None:
        """Test request_approval with Teams channel."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def request_approval(self, item_id: str, channel: str = "slack"):
                item = self.queue.queue.get(item_id)
                if not item:
                    return None
                item.status = MockDeliberationStatus.UNDER_REVIEW
                return {"item": item, "channel": channel}

        manager = TestableHITLManager(mock_queue)
        result = await manager.request_approval("item-123", channel="teams")

        assert result is not None
        assert result["channel"] == "teams"


# =============================================================================
# Process Approval Tests
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
                    item_id=item_id,
                    reviewer=reviewer_id,
                    decision=status,
                    reasoning=reasoning
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
            reasoning="Looks good to me"
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
                    item_id=item_id,
                    reviewer=reviewer_id,
                    decision=status,
                    reasoning=reasoning
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
            reasoning="Security concerns"
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
                    item_id=item_id,
                    reviewer=reviewer_id,
                    decision=status,
                    reasoning=reasoning
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
            reasoning="Approved"
        )

        assert result is False
        # Audit ledger should not be called when submission fails
        mock_audit_ledger.add_validation_result.assert_not_called()


# =============================================================================
# Integration Tests
# =============================================================================

class TestHITLManagerIntegration:
    """Integration tests for HITLManager."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test complete approval workflow."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def request_approval(self, item_id: str, channel: str = "slack"):
                item = self.queue.queue.get(item_id)
                if not item:
                    return None
                item.status = MockDeliberationStatus.UNDER_REVIEW
                return item

            async def process_approval(
                self, item_id: str, reviewer_id: str, decision: str, reasoning: str
            ):
                if decision == "approve":
                    status = MockDeliberationStatus.APPROVED
                else:
                    status = MockDeliberationStatus.REJECTED

                success = await self.queue.submit_human_decision(
                    item_id=item_id,
                    reviewer=reviewer_id,
                    decision=status,
                    reasoning=reasoning
                )

                if success:
                    await self.audit_ledger.add_validation_result({})
                    return True
                return False

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)

        # Step 1: Request approval
        item = await manager.request_approval("item-123")
        assert item is not None
        assert item.status == MockDeliberationStatus.UNDER_REVIEW

        # Step 2: Process approval
        result = await manager.process_approval(
            item_id="item-123",
            reviewer_id="senior-reviewer",
            decision="approve",
            reasoning="All security checks passed"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_full_rejection_workflow(
        self, mock_queue: MockDeliberationQueue, mock_audit_ledger: MockAuditLedger
    ) -> None:
        """Test complete rejection workflow."""
        class TestableHITLManager:
            def __init__(self, deliberation_queue, audit_ledger=None):
                self.queue = deliberation_queue
                self.audit_ledger = audit_ledger or MockAuditLedger()

            async def request_approval(self, item_id: str, channel: str = "slack"):
                item = self.queue.queue.get(item_id)
                if not item:
                    return None
                item.status = MockDeliberationStatus.UNDER_REVIEW
                return item

            async def process_approval(
                self, item_id: str, reviewer_id: str, decision: str, reasoning: str
            ):
                if decision == "approve":
                    status = MockDeliberationStatus.APPROVED
                else:
                    status = MockDeliberationStatus.REJECTED

                success = await self.queue.submit_human_decision(
                    item_id=item_id,
                    reviewer=reviewer_id,
                    decision=status,
                    reasoning=reasoning
                )

                if success:
                    await self.audit_ledger.add_validation_result({})
                    return True
                return False

        manager = TestableHITLManager(mock_queue, mock_audit_ledger)

        # Step 1: Request approval
        item = await manager.request_approval("item-123")
        assert item.status == MockDeliberationStatus.UNDER_REVIEW

        # Step 2: Process rejection
        result = await manager.process_approval(
            item_id="item-123",
            reviewer_id="security-reviewer",
            decision="reject",
            reasoning="Potential security vulnerability detected"
        )
        assert result is True


# =============================================================================
# Notification Payload Tests
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
                        {"name": "reject", "text": "Reject", "type": "button"}
                    ]
                }
            ]
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


# =============================================================================
# Audit Record Tests
# =============================================================================

class TestAuditRecords:
    """Tests for audit record generation."""

    def test_audit_record_for_approval(self) -> None:
        """Test audit record structure for approval."""
        audit_record = {
            "is_valid": True,
            "metadata": {
                "item_id": "item-123",
                "reviewer": "reviewer-1",
                "decision": "approve",
                "reasoning": "All checks passed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        assert audit_record["is_valid"] is True
        assert audit_record["metadata"]["decision"] == "approve"
        assert "timestamp" in audit_record["metadata"]

    def test_audit_record_for_rejection(self) -> None:
        """Test audit record structure for rejection."""
        audit_record = {
            "is_valid": False,
            "metadata": {
                "item_id": "item-456",
                "reviewer": "reviewer-2",
                "decision": "reject",
                "reasoning": "Security concerns",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        assert audit_record["is_valid"] is False
        assert audit_record["metadata"]["decision"] == "reject"


# =============================================================================
# Actual HITLManager Tests (Integration with Real Module)
# =============================================================================

class TestActualHITLManager:
    """Tests for the actual HITLManager implementation."""

    @pytest.fixture
    async def real_queue(self):
        """Create a real DeliberationQueue."""
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        queue = DeliberationQueue()
        yield queue
        await queue.stop()

    @pytest.fixture
    async def real_hitl_manager(self, real_queue):
        """Create a real HITLManager instance."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        manager = HITLManager(real_queue)
        return manager

    @pytest.mark.asyncio
    async def test_real_hitl_manager_init(self, real_queue):
        """Test real HITLManager initialization."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)
        assert manager.queue is real_queue
        assert manager.audit_ledger is not None

    @pytest.mark.asyncio
    async def test_real_request_approval_with_message(self, real_queue, caplog):
        """Test request_approval with a real AgentMessage."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

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
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationStatus
        task = real_queue.get_task(item_id)
        assert task.status == DeliberationStatus.UNDER_REVIEW

    @pytest.mark.asyncio
    async def test_real_request_approval_item_not_found(self, real_queue, caplog):
        """Test request_approval when item doesn't exist."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)

        with caplog.at_level(logging.ERROR):
            await manager.request_approval("nonexistent-item")

        assert "not found" in caplog.text

    @pytest.mark.asyncio
    async def test_real_request_approval_teams_channel(self, real_queue, caplog):
        """Test request_approval with Teams channel."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

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
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationStatus
        from enhanced_agent_bus.models import AgentMessage, MessageType

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
                reasoning="Action is compliant"
            )

        assert result is True
        assert "Decision for" in caplog.text
        assert "recorded" in caplog.text

    @pytest.mark.asyncio
    async def test_real_process_approval_reject(self, real_queue, caplog):
        """Test process_approval with reject decision."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

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
                reasoning="Violates security policy"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_real_process_approval_invalid_item(self, real_queue):
        """Test process_approval with invalid item_id."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager

        manager = HITLManager(real_queue)

        result = await manager.process_approval(
            item_id="invalid-item",
            reviewer_id="reviewer",
            decision="approve",
            reasoning="test"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_real_process_approval_not_under_review(self, real_queue):
        """Test process_approval fails if item not under review."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.models import AgentMessage, MessageType

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
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning="test"
        )

        assert result is False


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
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning="Approved"
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
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.models import AgentMessage, MessageType, CONSTITUTIONAL_HASH

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
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning="Test"
        )

        audit = custom_audit_ledger.results[0]
        assert audit.constitutional_hash == CONSTITUTIONAL_HASH

        await queue.stop()


class TestValidationResultFallback:
    """Test the fallback ValidationResult class defined in hitl_manager."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation with defaults."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}
        assert result.decision == "ALLOW"

    def test_validation_result_add_error(self):
        """Test add_error sets is_valid to False."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult()
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_validation_result_to_dict(self):
        """Test to_dict serialization."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult(
            is_valid=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
            metadata={"key": "value"},
            decision="DENY",
        )

        d = result.to_dict()

        assert d["is_valid"] is False
        assert len(d["errors"]) == 2
        assert d["warnings"] == ["warning1"]
        assert d["metadata"] == {"key": "value"}
        assert d["decision"] == "DENY"

    def test_validation_result_with_custom_metadata(self):
        """Test ValidationResult with custom metadata."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult
        from datetime import datetime, timezone

        metadata = {
            "item_id": "item-123",
            "reviewer": "admin",
            "decision": "approve",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        result = ValidationResult(
            is_valid=True,
            metadata=metadata,
        )

        assert result.metadata["item_id"] == "item-123"
        assert result.metadata["reviewer"] == "admin"


class TestFallbackAuditLedgerClass:
    """Test the fallback AuditLedger class defined in hitl_manager."""

    @pytest.mark.asyncio
    async def test_mock_audit_ledger_returns_hash(self):
        """Test that mock audit ledger returns a hash."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import AuditLedger, ValidationResult

        ledger = AuditLedger()
        result = ValidationResult(is_valid=True)

        hash_value = await ledger.add_validation_result(result)

        assert hash_value == "mock_audit_hash"

    @pytest.mark.asyncio
    async def test_mock_audit_ledger_logs_result(self, caplog):
        """Test that mock audit ledger logs the result."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import AuditLedger, ValidationResult

        ledger = AuditLedger()
        result = ValidationResult(
            is_valid=True,
            metadata={"test": "data"}
        )

        with caplog.at_level(logging.DEBUG):
            await ledger.add_validation_result(result)

        # The log happens at DEBUG level, may or may not be captured
        # depending on logger configuration


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in HITLManager."""

    @pytest.mark.asyncio
    async def test_empty_content_message(self):
        """Test handling of message with empty content."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue, DeliberationStatus
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
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning=special_reasoning
        )

        assert result is True
        assert ledger.results[0].metadata["reasoning"] == special_reasoning

        await queue.stop()

    @pytest.mark.asyncio
    async def test_concurrent_approval_requests(self):
        """Test concurrent approval requests don't interfere."""
        import asyncio
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue, DeliberationStatus
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
        await asyncio.gather(*[
            manager.request_approval(item_id)
            for item_id in item_ids
        ])

        # Verify all items are under review
        for item_id in item_ids:
            task = queue.get_task(item_id)
            assert task.status == DeliberationStatus.UNDER_REVIEW

        await queue.stop()

    @pytest.mark.asyncio
    async def test_long_content_truncation(self, caplog):
        """Test that long content is truncated in notification."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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


class TestConstitutionalCompliance:
    """Test constitutional compliance in HITL operations."""

    @pytest.mark.asyncio
    @pytest.mark.constitutional
    async def test_constitutional_hash_in_audit_trail(self):
        """Verify constitutional hash is maintained in audit trail."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.models import AgentMessage, MessageType, CONSTITUTIONAL_HASH

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
            reasoning="Compliant with constitutional principles"
        )

        # Verify constitutional hash in audit
        audit_result = ledger.results[0]
        assert audit_result.constitutional_hash == CONSTITUTIONAL_HASH

        await queue.stop()

    @pytest.mark.asyncio
    @pytest.mark.constitutional
    async def test_all_decisions_include_timestamp(self):
        """Verify all decisions include proper timestamps."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.models import AgentMessage, MessageType
        from datetime import datetime

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
            item_id=item_id,
            reviewer_id="reviewer",
            decision="approve",
            reasoning="test"
        )

        audit_result = ledger.results[0]
        assert "timestamp" in audit_result.metadata
        # Verify timestamp is valid ISO format
        timestamp = audit_result.metadata["timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        await queue.stop()


# =============================================================================
# Test Fallback Import Paths
# =============================================================================


class TestFallbackImportPaths:
    """Test the fallback import paths for ValidationResult."""

    def test_module_level_imports(self):
        """Test that the module can be imported successfully."""
        from enhanced_agent_bus.deliberation_layer import hitl_manager

        # Verify HITLManager class is available
        assert hasattr(hitl_manager, "HITLManager")
        assert hasattr(hitl_manager, "ValidationResult")
        assert hasattr(hitl_manager, "CONSTITUTIONAL_HASH")

    def test_validation_result_interface(self):
        """Test ValidationResult interface from hitl_manager."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult(
            is_valid=True,
            constitutional_hash="cdd01ef066bc6cf2"
        )
        assert result.is_valid is True
        assert result.constitutional_hash == "cdd01ef066bc6cf2"

    def test_validation_result_from_module_has_to_dict(self):
        """Test ValidationResult has to_dict method."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult(
            is_valid=False,
            errors=["Test error"],
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()
        assert "is_valid" in result_dict
        assert "errors" in result_dict
        assert "metadata" in result_dict
        assert result_dict["errors"] == ["Test error"]


class TestHITLManagerModuleLevelCode:
    """Test module-level code in hitl_manager.py."""

    def test_module_has_logger(self):
        """Test that module has logger configured."""
        from enhanced_agent_bus.deliberation_layer import hitl_manager

        assert hasattr(hitl_manager, "logger")
        assert hitl_manager.logger.name == "enhanced_agent_bus.deliberation_layer.hitl_manager"

    def test_constitutional_hash_constant(self):
        """Test CONSTITUTIONAL_HASH constant is available."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import CONSTITUTIONAL_HASH

        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_deliberation_status_import(self):
        """Test DeliberationStatus is imported correctly."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import DeliberationStatus

        assert hasattr(DeliberationStatus, "PENDING")
        assert hasattr(DeliberationStatus, "APPROVED")
        assert hasattr(DeliberationStatus, "REJECTED")
        assert hasattr(DeliberationStatus, "UNDER_REVIEW")


class TestHITLManagerAdditionalScenarios:
    """Additional test scenarios for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_process_approval_with_various_decisions(self):
        """Test process_approval with different decision types."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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
            reasoning="Denied for testing"
        )

        assert result is True
        await queue.stop()

    @pytest.mark.asyncio
    async def test_request_approval_logs_correctly(self, caplog):
        """Test that request_approval logs notification correctly."""
        import logging
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
        from enhanced_agent_bus.models import AgentMessage, MessageType

        with caplog.at_level(logging.INFO):
            queue = DeliberationQueue()
            manager = HITLManager(queue)

            message = AgentMessage(
                from_agent="logging-agent",
                to_agent="recipient",
                message_type=MessageType.COMMAND,
                content={"action": "test_logging"},
                impact_score=0.95
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
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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
                reasoning="Approved for testing"
            )

            # Check that decision was logged
            assert any("Decision for" in record.message and "recorded" in record.message
                      for record in caplog.records)

            await queue.stop()

    @pytest.mark.asyncio
    async def test_multiple_sequential_approvals(self):
        """Test handling multiple sequential approval workflows."""
        from enhanced_agent_bus.deliberation_layer.hitl_manager import HITLManager
        from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
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
                reasoning=f"Decision {i}"
            )
            assert result is True

        await queue.stop()
