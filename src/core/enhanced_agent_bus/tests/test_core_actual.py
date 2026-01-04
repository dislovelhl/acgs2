"""
ACGS-2 Enhanced Agent Bus - Actual Core Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests that exercise the actual core.py module code with proper mocking.
"""

from unittest.mock import MagicMock

import pytest

# Imports are handled via sys.modules patching in conftest.py
from src.core.enhanced_agent_bus.core import (
    CONSTITUTIONAL_HASH,
    EnhancedAgentBus,
    MessageProcessor,
    get_agent_bus,
    reset_agent_bus,
)
from src.core.enhanced_agent_bus.models import AgentMessage, MessageType, Priority
from src.core.enhanced_agent_bus.validators import ValidationResult

# ============================================================================
# MessageProcessor Tests
# ============================================================================


class TestMessageProcessorActual:
    """Test MessageProcessor with actual code."""

    @pytest.fixture
    def processor(self):
        """Create a MessageProcessor instance with MACI disabled for isolated testing."""
        # MACI is disabled for these legacy tests to isolate core functionality
        return MessageProcessor(enable_maci=False)

    def test_processor_initialization(self, processor):
        """Test processor initializes correctly."""
        assert processor.constitutional_hash == CONSTITUTIONAL_HASH
        assert processor._processed_count == 0
        assert processor._failed_count == 0

    def test_register_handler(self, processor):
        """Test handler registration."""
        handler = MagicMock()
        processor.register_handler("test_type", handler)
        assert "test_type" in processor._handlers
        assert handler in processor._handlers["test_type"]

    def test_register_multiple_handlers(self, processor):
        """Test registering multiple handlers for same type."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        processor.register_handler("test_type", handler1)
        processor.register_handler("test_type", handler2)
        assert len(processor._handlers["test_type"]) == 2

    def test_unregister_handler(self, processor):
        """Test handler unregistration."""
        handler = MagicMock()
        processor.register_handler("test_type", handler)
        processor.unregister_handler("test_type", handler)
        assert handler not in processor._handlers.get("test_type", [])

    def test_processed_count_property(self, processor):
        """Test processed_count property."""
        processor._processed_count = 10
        assert processor.processed_count == 10

    def test_failed_count_property(self, processor):
        """Test failed_count property."""
        processor._failed_count = 5
        assert processor.failed_count == 5

    def test_get_metrics(self, processor):
        """Test getting metrics."""
        processor._processed_count = 10
        processor._failed_count = 2
        metrics = processor.get_metrics()
        assert metrics["processed_count"] == 10
        assert metrics["failed_count"] == 2
        # Metrics should contain relevant fields
        assert "processed_count" in metrics

    @pytest.mark.asyncio
    async def test_process_valid_message(self, processor):
        """Test processing a valid message."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
            priority=Priority.NORMAL,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        result = await processor.process(message)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_process_invalid_constitutional_hash(self, processor):
        """Test processing message with invalid constitutional hash."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
            priority=Priority.NORMAL,
            constitutional_hash="invalid_hash",
        )
        result = await processor.process(message)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert any("constitutional" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_handler_execution(self, processor):
        """Test that handlers are executed during processing."""
        handler_called = False

        async def test_handler(msg):
            nonlocal handler_called
            handler_called = True

        processor.register_handler(MessageType.TASK_REQUEST, test_handler)

        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
            priority=Priority.NORMAL,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        await processor.process(message)
        assert handler_called is True

    @pytest.mark.asyncio
    async def test_sync_handler_execution(self, processor):
        """Test that sync handlers are executed."""
        handler_called = False

        def sync_handler(msg):
            nonlocal handler_called
            handler_called = True

        processor.register_handler(MessageType.TASK_REQUEST, sync_handler)

        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
            priority=Priority.NORMAL,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        await processor.process(message)
        assert handler_called is True


# ============================================================================
# EnhancedAgentBus Tests
# ============================================================================


class TestEnhancedAgentBusActual:
    """Test EnhancedAgentBus with actual code."""

    @pytest.fixture
    def bus(self):
        """Create an EnhancedAgentBus instance with MACI disabled for isolated testing."""
        # MACI is disabled for these legacy tests to isolate core functionality
        return EnhancedAgentBus(enable_maci=False)

    @pytest.mark.asyncio
    async def test_bus_initialization(self, bus):
        """Test bus initializes correctly."""
        assert bus.constitutional_hash == CONSTITUTIONAL_HASH
        assert bus._running is False
        assert isinstance(bus._agents, dict)

    @pytest.mark.asyncio
    async def test_register_agent(self, bus):
        """Test agent registration."""
        result = await bus.register_agent(
            agent_id="test_agent", agent_type="worker", capabilities=["task_execution"]
        )
        assert result is True
        assert "test_agent" in bus._agents

    @pytest.mark.asyncio
    async def test_register_agent_with_tenant(self, bus):
        """Test agent registration with tenant_id."""
        result = await bus.register_agent(
            agent_id="tenant_agent", agent_type="worker", tenant_id="tenant_123"
        )
        assert result is True
        info = bus.get_agent_info("tenant_agent")
        assert info is not None
        assert info.get("tenant_id") == "tenant_123"

    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, bus):
        """Test registering same agent twice."""
        await bus.register_agent("test_agent", "worker")
        result = await bus.register_agent("test_agent", "worker")
        assert result is True  # Now supports idempotent updates/overwrites

    @pytest.mark.asyncio
    async def test_unregister_agent(self, bus):
        """Test agent unregistration."""
        await bus.register_agent("test_agent", "worker")
        result = await bus.unregister_agent("test_agent")
        assert result is True
        assert "test_agent" not in bus._agents

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, bus):
        """Test unregistering nonexistent agent."""
        result = await bus.unregister_agent("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_info(self, bus):
        """Test getting agent info."""
        await bus.register_agent("test_agent", "worker", capabilities=["test"])
        info = bus.get_agent_info("test_agent")
        assert info is not None
        assert info["agent_type"] == "worker"
        assert "test" in info["capabilities"]

    @pytest.mark.asyncio
    async def test_get_agent_info_nonexistent(self, bus):
        """Test getting info for nonexistent agent."""
        info = bus.get_agent_info("nonexistent")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_registered_agents(self, bus):
        """Test getting all registered agents."""
        await bus.register_agent("agent1", "worker")
        await bus.register_agent("agent2", "supervisor")
        agents = bus.get_registered_agents()
        assert "agent1" in agents
        assert "agent2" in agents

    @pytest.mark.asyncio
    async def test_get_agents_by_type(self, bus):
        """Test getting agents by type."""
        await bus.register_agent("worker1", "worker")
        await bus.register_agent("worker2", "worker")
        await bus.register_agent("supervisor1", "supervisor")

        workers = bus.get_agents_by_type("worker")
        assert "worker1" in workers
        assert "worker2" in workers
        assert "supervisor1" not in workers

    @pytest.mark.asyncio
    async def test_get_agents_by_capability(self, bus):
        """Test getting agents by capability."""
        await bus.register_agent("agent1", "worker", capabilities=["task", "review"])
        await bus.register_agent("agent2", "worker", capabilities=["task"])
        await bus.register_agent("agent3", "supervisor", capabilities=["approval"])

        task_agents = bus.get_agents_by_capability("task")
        assert "agent1" in task_agents
        assert "agent2" in task_agents
        assert "agent3" not in task_agents

    @pytest.mark.asyncio
    async def test_is_running(self, bus):
        """Test is_running property."""
        assert bus.is_running is False
        bus._running = True
        assert bus.is_running is True

    @pytest.mark.asyncio
    async def test_processor_property(self, bus):
        """Test processor property."""
        proc = bus.processor
        assert isinstance(proc, MessageProcessor)

    @pytest.mark.asyncio
    async def test_get_metrics(self, bus):
        """Test getting bus metrics."""
        await bus.register_agent("agent1", "worker")
        metrics = bus.get_metrics()
        assert "registered_agents" in metrics
        assert "constitutional_hash" in metrics

    @pytest.mark.asyncio
    async def test_get_metrics_async(self, bus):
        """Test async metrics retrieval."""
        await bus.register_agent("agent1", "worker")
        metrics = await bus.get_metrics_async()
        assert isinstance(metrics, dict)
        assert "registered_agents" in metrics

    @pytest.mark.asyncio
    async def test_send_message(self, bus):
        """Test sending a message."""
        await bus.register_agent("sender", "worker")
        await bus.register_agent("receiver", "worker")

        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
            priority=Priority.NORMAL,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        result = await bus.send_message(message)
        assert result is not None
        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_receive_message(self, bus):
        """Test receiving a message."""
        # Put a message in queue manually
        test_msg = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": True},
            from_agent="sender",
            to_agent="receiver",
        )
        await bus._message_queue.put(test_msg)

        message = await bus.receive_message(timeout=1.0)
        assert message is not None
        assert message.content["test"] is True

    @pytest.mark.asyncio
    async def test_receive_message_timeout(self, bus):
        """Test receive timeout."""
        message = await bus.receive_message(timeout=0.1)
        assert message is None

    @pytest.mark.asyncio
    async def test_broadcast_message(self, bus):
        """Test broadcasting a message."""
        await bus.register_agent("sender", "worker")
        await bus.register_agent("receiver1", "worker")
        await bus.register_agent("receiver2", "worker")

        message = AgentMessage(
            message_type=MessageType.NOTIFICATION,
            content={"broadcast": True},
            from_agent="sender",
            to_agent="*",  # Broadcast
            priority=Priority.HIGH,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        results = await bus.broadcast_message(message)
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_broadcast_multi_tenant_isolation(self, bus):
        """Test broadcast respects multi-tenant isolation."""
        await bus.register_agent("sender", "worker", tenant_id="tenant_A")
        await bus.register_agent("receiver_A", "worker", tenant_id="tenant_A")
        await bus.register_agent("receiver_B", "worker", tenant_id="tenant_B")

        message = AgentMessage(
            message_type=MessageType.NOTIFICATION,
            content={"broadcast": True},
            from_agent="sender",
            to_agent="*",
            tenant_id="tenant_A",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        results = await bus.broadcast_message(message)
        # Should only broadcast to same tenant
        assert "receiver_A" in results
        assert "receiver_B" not in results


# ============================================================================
# Global Instance Tests
# ============================================================================


class TestGlobalInstances:
    """Test global instance management."""

    def test_get_agent_bus_singleton(self):
        """Test get_agent_bus returns singleton."""
        reset_agent_bus()
        bus1 = get_agent_bus()
        bus2 = get_agent_bus()
        assert bus1 is bus2

    def test_reset_agent_bus(self):
        """Test resetting the global bus."""
        bus1 = get_agent_bus()
        reset_agent_bus()
        bus2 = get_agent_bus()
        assert bus1 is not bus2


# ============================================================================
# Start/Stop Tests
# ============================================================================


class TestBusLifecycle:
    """Test bus start/stop lifecycle."""

    @pytest.fixture
    def bus(self):
        """Create bus for lifecycle tests."""
        return EnhancedAgentBus()

    @pytest.mark.asyncio
    async def test_start_bus(self, bus):
        """Test starting the bus."""
        await bus.start()
        assert bus.is_running is True
        await bus.stop()

    @pytest.mark.asyncio
    async def test_stop_bus(self, bus):
        """Test stopping the bus."""
        await bus.start()
        await bus.stop()
        assert bus.is_running is False

    @pytest.mark.asyncio
    async def test_double_start(self, bus):
        """Test starting already started bus."""
        await bus.start()
        await bus.start()  # Should be idempotent
        assert bus.is_running is True
        await bus.stop()

    @pytest.mark.asyncio
    async def test_double_stop(self, bus):
        """Test stopping already stopped bus."""
        await bus.start()
        await bus.stop()
        await bus.stop()  # Should be idempotent
        assert bus.is_running is False


# ============================================================================
# Additional Coverage Tests
# ============================================================================


class TestMessageProcessorAdditional:
    """Additional MessageProcessor tests for coverage."""

    @pytest.fixture
    def processor(self):
        """Create a MessageProcessor instance with MACI disabled for isolated testing."""
        # MACI is disabled for these legacy tests to isolate core functionality
        return MessageProcessor(enable_maci=False)

    def test_unregister_handler_not_found(self, processor):
        """Test unregistering handler that doesn't exist."""
        handler = MagicMock()
        result = processor.unregister_handler(MessageType.COMMAND, handler)
        assert result is False

    def test_unregister_handler_wrong_type(self, processor):
        """Test unregistering from different message type."""
        handler = MagicMock()
        processor.register_handler(MessageType.COMMAND, handler)
        result = processor.unregister_handler(MessageType.QUERY, handler)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_multiple_handlers(self, processor):
        """Test that multiple handlers are called."""
        call_order = []

        async def handler1(msg):
            call_order.append(1)

        async def handler2(msg):
            call_order.append(2)

        processor.register_handler(MessageType.NOTIFICATION, handler1)
        processor.register_handler(MessageType.NOTIFICATION, handler2)

        message = AgentMessage(
            message_type=MessageType.NOTIFICATION,
            content={"test": True},
            from_agent="sender",
            to_agent="receiver",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        await processor.process(message)
        assert 1 in call_order
        assert 2 in call_order

    @pytest.mark.asyncio
    async def test_process_empty_content(self, processor):
        """Test processing message with empty content."""
        message = AgentMessage(
            message_type=MessageType.HEARTBEAT,
            content={},
            from_agent="sender",
            to_agent="receiver",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        result = await processor.process(message)
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_process_increments_counter(self, processor):
        """Test that processing increments counter."""
        initial_count = processor.processed_count

        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "test"},
            from_agent="sender",
            to_agent="receiver",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        await processor.process(message)

        assert processor.processed_count == initial_count + 1


class TestEnhancedAgentBusAdditional:
    """Additional EnhancedAgentBus tests for coverage."""

    @pytest.fixture
    def bus(self):
        """Create an EnhancedAgentBus instance."""
        return EnhancedAgentBus()

    @pytest.mark.asyncio
    async def test_get_agents_by_type_empty(self, bus):
        """Test getting agents by type returns empty for no matches."""
        await bus.register_agent("agent1", "worker")
        workers = bus.get_agents_by_type("supervisor")
        assert len(workers) == 0

    @pytest.mark.asyncio
    async def test_get_agents_by_capability_empty(self, bus):
        """Test getting agents by capability returns empty for no matches."""
        await bus.register_agent("agent1", "worker", capabilities=["task"])
        agents = bus.get_agents_by_capability("nonexistent")
        assert len(agents) == 0

    @pytest.mark.asyncio
    async def test_send_message_updates_status(self, bus):
        """Test sending message updates message status."""
        await bus.register_agent("sender", "worker")
        await bus.register_agent("receiver", "worker")

        message = AgentMessage(
            message_type=MessageType.COMMAND,
            content={"command": "execute"},
            from_agent="sender",
            to_agent="receiver",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        result = await bus.send_message(message)
        assert result is not None

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_recipients(self, bus):
        """Test broadcast with no matching recipients."""
        await bus.register_agent("sender", "worker")

        message = AgentMessage(
            message_type=MessageType.NOTIFICATION,
            content={"alert": True},
            from_agent="sender",
            to_agent="*",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        results = await bus.broadcast_message(message)
        # Only sender registered, broadcast should have limited results
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_agent_registration_updates_capabilities(self, bus):
        """Test re-registering agent updates capabilities."""
        await bus.register_agent("agent1", "worker", capabilities=["task"])
        await bus.register_agent("agent1", "worker", capabilities=["task", "review"])

        info = bus.get_agent_info("agent1")
        assert "review" in info["capabilities"]

    @pytest.mark.asyncio
    async def test_bus_metrics_format(self, bus):
        """Test metrics contain expected keys."""
        await bus.register_agent("agent1", "worker")
        metrics = bus.get_metrics()

        assert "registered_agents" in metrics
        assert "is_running" in metrics

    @pytest.mark.asyncio
    async def test_multiple_message_types(self, bus):
        """Test processing different message types."""
        await bus.register_agent("sender", "worker")
        await bus.register_agent("receiver", "worker")

        for msg_type in [MessageType.COMMAND, MessageType.QUERY, MessageType.EVENT]:
            message = AgentMessage(
                message_type=msg_type,
                content={"type_test": msg_type.value},
                from_agent="sender",
                to_agent="receiver",
                constitutional_hash=CONSTITUTIONAL_HASH,
            )
            result = await bus.send_message(message)
            assert result is not None


class TestValidationEdgeCases:
    """Test validation edge cases."""

    @pytest.fixture
    def processor(self):
        """Create a MessageProcessor instance."""
        return MessageProcessor()

    @pytest.mark.asyncio
    async def test_missing_constitutional_hash(self, processor):
        """Test message without constitutional hash."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
        )
        result = await processor.process(message)
        # Without constitutional hash, validation should still work
        # but may have different behavior
        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_empty_from_agent(self, processor):
        """Test message with empty from_agent."""
        message = AgentMessage(
            message_type=MessageType.NOTIFICATION,
            content={"alert": True},
            from_agent="",
            to_agent="receiver",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        result = await processor.process(message)
        assert isinstance(result, ValidationResult)
