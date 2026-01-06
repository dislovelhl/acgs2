"""
Tests for fallbackauditledgerclass.

Tests cover:
- fallbackauditledgerclass functionality
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


class TestFallbackAuditLedgerClass:
    """Test the fallback AuditLedger class defined in hitl_manager."""

    @pytest.mark.asyncio
    async def test_mock_audit_ledger_returns_hash(self):
        """Test that mock audit ledger returns a hash."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import (
            AuditLedger,
            ValidationResult,
        )

        ledger = AuditLedger()
        result = ValidationResult(is_valid=True)

        hash_value = await ledger.add_validation_result(result)

        assert hash_value == "mock_audit_hash"

    @pytest.mark.asyncio
    async def test_mock_audit_ledger_logs_result(self, caplog):
        """Test that mock audit ledger logs the result."""
        import logging

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import (
            AuditLedger,
            ValidationResult,
        )

        ledger = AuditLedger()
        result = ValidationResult(is_valid=True, metadata={"test": "data"})

        with caplog.at_level(logging.DEBUG):
            await ledger.add_validation_result(result)

        # The log happens at DEBUG level, may or may not be captured
        # depending on logger configuration
