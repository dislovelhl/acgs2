"""
ACGS-2 Enhanced Agent Bus - Integration Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for the deliberation layer integration module.
"""

import asyncio
import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import importlib.util

# Add enhanced_agent_bus directory to path
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


# Add deliberation_layer directory to path for fallback imports
deliberation_layer_dir = os.path.join(enhanced_agent_bus_dir, "deliberation_layer")
if deliberation_layer_dir not in sys.path:
    sys.path.insert(0, deliberation_layer_dir)

# Load base models first
_models = _load_module("models", os.path.join(enhanced_agent_bus_dir, "models.py"))

# Create mock parent package
class MockEnhancedAgentBus:
    pass

mock_parent = MockEnhancedAgentBus()
mock_parent.models = _models

# Patch sys.modules for imports
sys.modules['enhanced_agent_bus'] = mock_parent
sys.modules['enhanced_agent_bus.models'] = _models

# Import from models
AgentMessage = _models.AgentMessage
MessageType = _models.MessageType
MessageStatus = _models.MessageStatus
MessagePriority = _models.MessagePriority
CONSTITUTIONAL_HASH = _models.CONSTITUTIONAL_HASH


# Create mock impact_scorer module since it has heavy ML dependencies
class MockImpactScorer:
    """Mock impact scorer for testing without ML dependencies."""

    def __init__(self, model_name: str = 'mock-model'):
        self.model_name = model_name

    def calculate_impact_score(self, content, context=None) -> float:
        """Return mock impact score based on content (dict or str)."""
        content_str = str(content).lower() if content else ""
        # Check for high-risk keywords
        high_risk_keywords = [
            'critical', 'emergency', 'security', 'breach',
            'delete', 'production', 'governance'
        ]
        for keyword in high_risk_keywords:
            if keyword in content_str:
                return 0.9
        return 0.3


def mock_calculate_message_impact(content) -> float:
    """Mock function for calculating message impact from content dict."""
    scorer = MockImpactScorer()
    return scorer.calculate_impact_score(content)


def mock_get_impact_scorer():
    """Return a mock impact scorer instance."""
    return MockImpactScorer()


# Create mock impact_scorer module
class MockImpactScorerModule:
    ImpactScorer = MockImpactScorer
    get_impact_scorer = staticmethod(mock_get_impact_scorer)
    calculate_message_impact = staticmethod(mock_calculate_message_impact)


sys.modules['impact_scorer'] = MockImpactScorerModule()

# Load other dependency modules for integration.py (order matters!)
_adaptive_router = _load_module("adaptive_router", os.path.join(deliberation_layer_dir, "adaptive_router.py"))
_deliberation_queue = _load_module("deliberation_queue", os.path.join(deliberation_layer_dir, "deliberation_queue.py"))
_llm_assistant = _load_module("llm_assistant", os.path.join(deliberation_layer_dir, "llm_assistant.py"))
_redis_integration = _load_module("redis_integration", os.path.join(deliberation_layer_dir, "redis_integration.py"))

# Load the actual integration module
_integration = _load_module(
    "integration",
    os.path.join(deliberation_layer_dir, "integration.py")
)

DeliberationLayer = _integration.DeliberationLayer
get_deliberation_layer = _integration.get_deliberation_layer


class TestDeliberationLayerInitialization:
    """Tests for DeliberationLayer initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        layer = DeliberationLayer()

        assert layer.impact_threshold == 0.8
        assert layer.deliberation_timeout == 300
        assert layer.enable_redis is False
        assert layer.enable_learning is True
        assert layer.enable_llm is True

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        layer = DeliberationLayer(
            impact_threshold=0.5,
            deliberation_timeout=120,
            enable_redis=False,
            enable_learning=False,
            enable_llm=False
        )

        assert layer.impact_threshold == 0.5
        assert layer.deliberation_timeout == 120
        assert layer.enable_redis is False
        assert layer.enable_learning is False
        assert layer.enable_llm is False
        assert layer.llm_assistant is None

    def test_components_initialized(self):
        """Test that all required components are initialized."""
        layer = DeliberationLayer()

        assert layer.impact_scorer is not None
        assert layer.adaptive_router is not None
        assert layer.deliberation_queue is not None

    def test_redis_disabled_by_default(self):
        """Test Redis components are None when disabled."""
        layer = DeliberationLayer(enable_redis=False)

        assert layer.redis_queue is None
        assert layer.redis_voting is None

    def test_callbacks_initially_none(self):
        """Test callbacks are None by default."""
        layer = DeliberationLayer()

        assert layer.fast_lane_callback is None
        assert layer.deliberation_callback is None


class TestMessageProcessing:
    """Tests for message processing."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer for testing."""
        return DeliberationLayer(
            impact_threshold=0.5,
            deliberation_timeout=10,
            enable_learning=False,
            enable_llm=False,
            enable_opa_guard=False
        )

    @pytest.fixture
    def low_risk_message(self):
        """Create a low-risk message."""
        return AgentMessage(
            from_agent="test_agent",
            to_agent="target_agent",
            sender_id="test_sender",
            message_type=MessageType.QUERY,
            content={"action": "ping"},
        )

    @pytest.fixture
    def high_risk_message(self):
        """Create a high-risk message."""
        return AgentMessage(
            from_agent="test_agent",
            to_agent="target_agent",
            sender_id="test_sender",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "delete", "scope": "production"},
        )

    @pytest.mark.asyncio
    async def test_process_message_returns_result(self, layer, low_risk_message):
        """Test process_message returns a result dictionary."""
        result = await layer.process_message(low_risk_message)

        assert isinstance(result, dict)
        assert 'success' in result
        assert 'processing_time' in result

    @pytest.mark.asyncio
    async def test_process_message_calculates_impact_score(self, layer, low_risk_message):
        """Test impact score is calculated if not present."""
        assert low_risk_message.impact_score is None

        await layer.process_message(low_risk_message)

        assert low_risk_message.impact_score is not None

    @pytest.mark.asyncio
    async def test_process_low_risk_to_fast_lane(self, layer, low_risk_message):
        """Test low-risk messages go to fast lane."""
        # Set low impact score
        low_risk_message.impact_score = 0.2

        result = await layer.process_message(low_risk_message)

        assert result.get('lane') == 'fast'
        assert result.get('status') == 'delivered'

    @pytest.mark.asyncio
    async def test_process_high_risk_to_deliberation(self, layer, high_risk_message):
        """Test high-risk messages go to deliberation."""
        # Set high impact score
        high_risk_message.impact_score = 0.9

        result = await layer.process_message(high_risk_message)

        assert result.get('lane') == 'deliberation'
        assert result.get('status') == 'queued'
        assert 'item_id' in result


class TestCallbacks:
    """Tests for callback functionality."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            impact_threshold=0.5,
            enable_learning=False,
            enable_llm=False,
            enable_opa_guard=False
        )

    @pytest.fixture
    def test_message(self):
        """Create a test message."""
        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.QUERY, content={}
        )
        msg.impact_score = 0.2  # Low risk for fast lane
        return msg

    def test_set_fast_lane_callback(self, layer):
        """Test setting fast lane callback."""
        callback = MagicMock()
        layer.set_fast_lane_callback(callback)

        assert layer.fast_lane_callback == callback

    def test_set_deliberation_callback(self, layer):
        """Test setting deliberation callback."""
        callback = MagicMock()
        layer.set_deliberation_callback(callback)

        assert layer.deliberation_callback == callback

    @pytest.mark.asyncio
    async def test_fast_lane_callback_executed(self, layer, test_message):
        """Test fast lane callback is executed on fast lane messages."""
        callback = AsyncMock()
        layer.set_fast_lane_callback(callback)

        await layer.process_message(test_message)

        callback.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_deliberation_callback_executed(self, layer):
        """Test deliberation callback is executed on deliberation messages."""
        callback = AsyncMock()
        layer.set_deliberation_callback(callback)

        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.GOVERNANCE_REQUEST, content={}
        )
        msg.impact_score = 0.9  # High risk for deliberation

        await layer.process_message(msg)

        assert callback.called


class TestHumanDecision:
    """Tests for human decision submission."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            enable_learning=False,
            enable_llm=False,
            enable_opa_guard=False
        )

    @pytest.fixture
    async def queued_item(self, layer):
        """Create a queued deliberation item."""
        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.GOVERNANCE_REQUEST, content={}
        )
        msg.impact_score = 0.9

        result = await layer.process_message(msg)
        return result.get('item_id')

    @pytest.mark.asyncio
    async def test_submit_human_decision_approved(self, layer, queued_item):
        """Test submitting approved decision."""
        # First set the item to under_review status
        item = layer.deliberation_queue.queue.get(queued_item)
        if item:
            # Use the already loaded module's DeliberationStatus
            DeliberationStatus = _deliberation_queue.DeliberationStatus
            item.status = DeliberationStatus.UNDER_REVIEW

            result = await layer.submit_human_decision(
                item_id=queued_item,
                reviewer="human_reviewer",
                decision="approved",
                reasoning="Approved after review"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_submit_human_decision_rejected(self, layer, queued_item):
        """Test submitting rejected decision."""
        item = layer.deliberation_queue.queue.get(queued_item)
        if item:
            # Use the already loaded module's DeliberationStatus
            DeliberationStatus = _deliberation_queue.DeliberationStatus
            item.status = DeliberationStatus.UNDER_REVIEW

            result = await layer.submit_human_decision(
                item_id=queued_item,
                reviewer="human_reviewer",
                decision="rejected",
                reasoning="Rejected due to policy violation"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_submit_human_decision_nonexistent_item(self, layer):
        """Test decision for nonexistent item returns False."""
        result = await layer.submit_human_decision(
            item_id="nonexistent",
            reviewer="human_reviewer",
            decision="approved",
            reasoning="Test"
        )

        assert result is False


class TestAgentVote:
    """Tests for agent vote submission."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            enable_learning=False,
            enable_llm=False,
            enable_redis=False,
            enable_opa_guard=False
        )

    @pytest.fixture
    async def queued_item(self, layer):
        """Create a queued deliberation item."""
        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.GOVERNANCE_REQUEST, content={}
        )
        msg.impact_score = 0.9

        result = await layer.process_message(msg)
        return result.get('item_id')

    @pytest.mark.asyncio
    async def test_submit_agent_vote(self, layer, queued_item):
        """Test submitting agent vote."""
        result = await layer.submit_agent_vote(
            item_id=queued_item,
            agent_id="agent1",
            vote="approve",
            reasoning="Valid operation",
            confidence=0.9
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_submit_multiple_agent_votes(self, layer, queued_item):
        """Test submitting multiple agent votes."""
        await layer.submit_agent_vote(
            item_id=queued_item, agent_id="agent1",
            vote="approve", reasoning="Good"
        )
        await layer.submit_agent_vote(
            item_id=queued_item, agent_id="agent2",
            vote="approve", reasoning="Valid"
        )
        await layer.submit_agent_vote(
            item_id=queued_item, agent_id="agent3",
            vote="reject", reasoning="Concerns"
        )

        item = layer.deliberation_queue.queue.get(queued_item)
        assert len(item.current_votes) == 3

    @pytest.mark.asyncio
    async def test_submit_agent_vote_nonexistent_item(self, layer):
        """Test vote for nonexistent item returns False."""
        result = await layer.submit_agent_vote(
            item_id="nonexistent",
            agent_id="agent1",
            vote="approve",
            reasoning="Test"
        )

        assert result is False


class TestLayerStats:
    """Tests for layer statistics."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            impact_threshold=0.5,
            deliberation_timeout=60,
            enable_redis=False,
            enable_learning=True,
            enable_llm=True,
            enable_opa_guard=False
        )

    def test_get_layer_stats_structure(self, layer):
        """Test layer stats returns correct structure."""
        stats = layer.get_layer_stats()

        assert 'layer_status' in stats
        assert 'impact_threshold' in stats
        assert 'deliberation_timeout' in stats
        assert 'features' in stats
        assert 'router_stats' in stats
        assert 'queue_stats' in stats

    def test_get_layer_stats_features(self, layer):
        """Test features are reported correctly."""
        stats = layer.get_layer_stats()

        assert stats['features']['redis_enabled'] is False
        assert stats['features']['learning_enabled'] is True
        assert stats['features']['llm_enabled'] is True

    def test_get_layer_stats_threshold(self, layer):
        """Test threshold is reported correctly."""
        stats = layer.get_layer_stats()

        assert stats['impact_threshold'] == 0.5
        assert stats['deliberation_timeout'] == 60


class TestForceDeliberation:
    """Tests for force deliberation functionality."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            impact_threshold=0.9,  # High threshold
            enable_learning=False,
            enable_llm=False,
            enable_opa_guard=False
        )

    @pytest.fixture
    def low_risk_message(self):
        """Create a low-risk message."""
        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.QUERY, content={"action": "ping"}
        )
        msg.impact_score = 0.2
        return msg

    @pytest.mark.asyncio
    async def test_force_deliberation(self, layer, low_risk_message):
        """Test forcing a low-risk message into deliberation."""
        result = await layer.force_deliberation(
            low_risk_message,
            reason="manual_override"
        )

        assert result.get('lane') == 'deliberation'
        assert result.get('forced') is True
        assert result.get('force_reason') == 'manual_override'

    @pytest.mark.asyncio
    async def test_force_deliberation_preserves_original_score(self, layer, low_risk_message):
        """Test original impact score is preserved after forcing."""
        original_score = low_risk_message.impact_score

        await layer.force_deliberation(low_risk_message, "test")

        assert low_risk_message.impact_score == original_score


class TestTrendAnalysis:
    """Tests for trend analysis."""

    @pytest.fixture
    def layer_with_llm(self):
        """Create a layer with LLM enabled."""
        return DeliberationLayer(enable_llm=True)

    @pytest.fixture
    def layer_without_llm(self):
        """Create a layer without LLM."""
        return DeliberationLayer(enable_llm=False)

    @pytest.mark.asyncio
    async def test_analyze_trends_without_llm(self, layer_without_llm):
        """Test trend analysis returns error without LLM."""
        result = await layer_without_llm.analyze_trends()

        assert 'error' in result
        assert 'not enabled' in result['error']

    @pytest.mark.asyncio
    async def test_analyze_trends_with_llm(self, layer_with_llm):
        """Test trend analysis works with LLM."""
        result = await layer_with_llm.analyze_trends()

        # Should return analysis structure
        assert isinstance(result, dict)


class TestGlobalSingleton:
    """Tests for global singleton instance."""

    def test_get_deliberation_layer_singleton(self):
        """Test deliberation layer singleton."""
        # Reset global instance
        _integration._deliberation_layer = None

        layer1 = get_deliberation_layer()
        layer2 = get_deliberation_layer()

        assert layer1 is layer2


class TestErrorHandling:
    """Tests for error handling in message processing."""

    @pytest.fixture
    def layer(self):
        """Create a deliberation layer."""
        return DeliberationLayer(
            enable_learning=False,
            enable_llm=False,
            enable_opa_guard=False
        )

    @pytest.mark.asyncio
    async def test_process_message_handles_error(self, layer):
        """Test message processing handles errors gracefully."""
        msg = AgentMessage(
            from_agent="a", to_agent="b", sender_id="s",
            message_type=MessageType.QUERY, content={}
        )

        # This should succeed even with minimal content
        result = await layer.process_message(msg)

        assert 'processing_time' in result


class TestAsyncInitialize:
    """Tests for async initialization."""

    @pytest.mark.asyncio
    async def test_initialize_without_redis(self):
        """Test initialization without Redis."""
        layer = DeliberationLayer(enable_redis=False)

        # Should complete without error
        await layer.initialize()

        assert layer.redis_queue is None
        assert layer.redis_voting is None


# Entry point for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
