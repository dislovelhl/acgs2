"""
ACGS-2 Enhanced Agent Bus - Deliberation Layer Feedback Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for Deliberation Layer Feedback Loop integration.
"""

import importlib.util
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

# Add enhanced_agent_bus directory to path for standalone execution
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)


def _load_module(name, path):
    """Load a module directly from path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load base modules first
_models = _load_module("_test_models_feedback", os.path.join(enhanced_agent_bus_dir, "models.py"))


# Create a mock parent package for relative imports
class MockPackage:
    pass


mock_parent = MockPackage()
mock_parent.models = _models
mock_parent.AgentMessage = _models.AgentMessage
mock_parent.MessageType = _models.MessageType
mock_parent.CONSTITUTIONAL_HASH = _models.CONSTITUTIONAL_HASH

# Patch sys.modules for both direct and relative imports
sys.modules["models"] = _models
sys.modules["enhanced_agent_bus"] = mock_parent
sys.modules["enhanced_agent_bus.models"] = _models

# Import from loaded models
AgentMessage = _models.AgentMessage
MessageType = _models.MessageType
Priority = _models.Priority
CONSTITUTIONAL_HASH = _models.CONSTITUTIONAL_HASH

# Load deliberation layer components directly (bypass __init__.py)
delib_dir = os.path.join(enhanced_agent_bus_dir, "deliberation_layer")

_deliberation_queue = _load_module(
    "_test_delib_queue_fb", os.path.join(delib_dir, "deliberation_queue.py")
)
_integration = _load_module("_test_integration_fb", os.path.join(delib_dir, "integration.py"))

DeliberationLayer = _integration.DeliberationLayer
DeliberationTask = _deliberation_queue.DeliberationTask


class TestDeliberationFeedback:
    @pytest.mark.asyncio
    async def test_feedback_loop_integration(self):
        """Test that resolving a deliberation item triggers router feedback."""
        # Mock dependencies
        mock_queue = AsyncMock()
        mock_router = AsyncMock()
        mock_scorer = Mock()

        # Setup DeliberationLayer with mocks
        layer = DeliberationLayer(
            impact_scorer=mock_scorer,
            adaptive_router=mock_router,
            deliberation_queue=mock_queue,
            enable_redis=False,
        )

        # Mock task data
        message = AgentMessage(
            content="test",
            message_type=MessageType.TASK_REQUEST,
            from_agent="tester",
            to_agent="system",
            priority=Priority.HIGH,
        )
        task = DeliberationTask(
            task_id="task-123", message=message, created_at=datetime.now(timezone.utc)
        )

        # Configure queue mock
        mock_queue.resolve_task = AsyncMock()
        mock_queue.get_task = Mock(return_value=task)

        # Action: Resolve item
        await layer.resolve_deliberation_item(item_id="task-123", approved=True, feedback_score=0.9)

        # Assertions
        # 1. Queue should be resolved
        mock_queue.resolve_task.assert_called_with("task-123", True)

        # 2. Router should receive feedback
        # Verify call args
        call_args = mock_router.update_performance_feedback.call_args
        assert call_args is not None
        _, kwargs = call_args

        assert kwargs["message_id"] == message.message_id
        assert kwargs["actual_outcome"] == "approved"
        assert kwargs["feedback_score"] == 0.9
        assert "processing_time" in kwargs
