"""
Tests for validationresultfallback.

Tests cover:
- validationresultfallback functionality
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


class TestValidationResultFallback:
    """Test the fallback ValidationResult class defined in hitl_manager."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation with defaults."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}
        assert result.decision == "ALLOW"

    def test_validation_result_add_error(self):
        """Test add_error sets is_valid to False."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult()
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_validation_result_to_dict(self):
        """Test to_dict serialization."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

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

        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        metadata = {
            "item_id": "item-123",
            "reviewer": "admin",
            "decision": "approve",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = ValidationResult(
            is_valid=True,
            metadata=metadata,
        )

        assert result.metadata["item_id"] == "item-123"
        assert result.metadata["reviewer"] == "admin"
