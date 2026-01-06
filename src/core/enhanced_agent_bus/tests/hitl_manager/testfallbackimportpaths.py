"""
Tests for fallbackimportpaths.

Tests cover:
- fallbackimportpaths functionality
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


class TestFallbackImportPaths:
    """Test the fallback import paths for ValidationResult."""

    def test_module_level_imports(self):
        """Test that the module can be imported successfully."""
        from src.core.enhanced_agent_bus.deliberation_layer import hitl_manager

        # Verify HITLManager class is available
        assert hasattr(hitl_manager, "HITLManager")
        assert hasattr(hitl_manager, "ValidationResult")
        assert hasattr(hitl_manager, "CONSTITUTIONAL_HASH")

    def test_validation_result_interface(self):
        """Test ValidationResult interface from hitl_manager."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult(is_valid=True, constitutional_hash="cdd01ef066bc6cf2")
        assert result.is_valid is True
        assert result.constitutional_hash == "cdd01ef066bc6cf2"

    def test_validation_result_from_module_has_to_dict(self):
        """Test ValidationResult has to_dict method."""
        from src.core.enhanced_agent_bus.deliberation_layer.hitl_manager import ValidationResult

        result = ValidationResult(is_valid=False, errors=["Test error"], metadata={"key": "value"})

        result_dict = result.to_dict()
        assert "is_valid" in result_dict
        assert "errors" in result_dict
        assert "metadata" in result_dict
        assert result_dict["errors"] == ["Test error"]
