"""
ACGS-2 Kafka Bus Coverage Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for kafka_bus.py to increase coverage.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from enhanced_agent_bus.exceptions import MessageDeliveryError
    from enhanced_agent_bus.kafka_bus import (
        KAFKA_AVAILABLE,
        Blackboard,
        KafkaEventBus,
        Orchestrator,
    )
    from enhanced_agent_bus.models import CONSTITUTIONAL_HASH, AgentMessage, MessageType
except ImportError:
    from exceptions import MessageDeliveryError
    from kafka_bus import KAFKA_AVAILABLE, Blackboard, KafkaEventBus, Orchestrator
    from models import AgentMessage


class TestKafkaEventBusInit:
    """Tests for KafkaEventBus initialization."""

    def test_default_init(self):
        """KafkaEventBus initializes with defaults."""
        bus = KafkaEventBus()
        assert bus.bootstrap_servers == "localhost:9092"
        assert bus.client_id == "acgs2-bus"
        assert bus.producer is None
        assert bus._consumers == {}
        assert bus._running is False

    def test_custom_init(self):
        """KafkaEventBus with custom parameters."""
        bus = KafkaEventBus(bootstrap_servers="kafka.example.com:9092", client_id="custom-client")
        assert bus.bootstrap_servers == "kafka.example.com:9092"
        assert bus.client_id == "custom-client"


class TestKafkaEventBusTopicNaming:
    """Tests for topic naming."""

    def test_topic_name_basic(self):
        """Topic name with basic tenant ID."""
        bus = KafkaEventBus()
        topic = bus._get_topic_name("tenant1", "command")
        assert topic == "acgs.tenant.tenant1.command"

    def test_topic_name_empty_tenant(self):
        """Topic name with empty tenant defaults to 'default'."""
        bus = KafkaEventBus()
        topic = bus._get_topic_name("", "event")
        assert topic == "acgs.tenant.default.event"

    def test_topic_name_sanitizes_dots(self):
        """Topic name sanitizes dots in tenant ID."""
        bus = KafkaEventBus()
        topic = bus._get_topic_name("tenant.with.dots", "query")
        assert topic == "acgs.tenant.tenant_with_dots.query"

    def test_topic_name_lowercases_type(self):
        """Topic name lowercases message type."""
        bus = KafkaEventBus()
        topic = bus._get_topic_name("tenant", "COMMAND")
        assert topic == "acgs.tenant.tenant.command"


class TestKafkaEventBusSendMessage:
    """Tests for send_message method."""

    @pytest.mark.asyncio
    async def test_send_raises_when_not_started(self):
        """send_message raises when producer not started."""
        bus = KafkaEventBus()
        message = AgentMessage(
            content={"action": "test"},
            from_agent="sender",
            to_agent="receiver",
        )

        with pytest.raises(MessageDeliveryError) as exc_info:
            await bus.send_message(message)

        assert "not started" in str(exc_info.value).lower()


class TestKafkaEventBusStartStop:
    """Tests for start and stop methods."""

    @pytest.mark.asyncio
    async def test_start_without_kafka_logs_error(self):
        """start logs error when aiokafka not available."""
        bus = KafkaEventBus()

        # If KAFKA_AVAILABLE is False, start should just return
        if not KAFKA_AVAILABLE:
            await bus.start()
            assert bus.producer is None
            assert bus._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        """stop is safe when not started."""
        bus = KafkaEventBus()
        # Should not raise
        await bus.stop()
        assert bus._running is False


class TestOrchestrator:
    """Tests for Orchestrator class."""

    def test_orchestrator_init(self):
        """Orchestrator initializes with bus and tenant."""
        bus = KafkaEventBus()
        orch = Orchestrator(bus, "tenant1")

        assert orch.bus is bus
        assert orch.tenant_id == "tenant1"

    @pytest.mark.asyncio
    async def test_dispatch_task(self):
        """dispatch_task creates and sends message."""
        bus = KafkaEventBus()
        bus.producer = MagicMock()
        bus._running = True
        bus.send_message = AsyncMock(return_value=True)

        orch = Orchestrator(bus, "tenant1")
        await orch.dispatch_task({"task": "process"}, "worker-type")

        # Verify send_message was called
        bus.send_message.assert_called_once()
        call_args = bus.send_message.call_args[0][0]
        assert isinstance(call_args, AgentMessage)
        assert call_args.content == {"task": "process"}
        assert call_args.to_agent == "worker-worker-type"


class TestBlackboard:
    """Tests for Blackboard class."""

    def test_blackboard_init(self):
        """Blackboard initializes correctly."""
        bus = KafkaEventBus()
        board = Blackboard(bus, "tenant1", "shared-state")

        assert board.bus is bus
        assert board.tenant_id == "tenant1"
        assert board.topic == "acgs.blackboard.tenant1.shared-state"
        assert board.state == {}

    @pytest.mark.asyncio
    async def test_blackboard_update(self):
        """update sends message to blackboard."""
        bus = KafkaEventBus()
        bus.producer = MagicMock()
        bus._running = True
        bus.send_message = AsyncMock(return_value=True)

        board = Blackboard(bus, "tenant1", "state")
        await board.update("key1", "value1")

        # Verify send_message was called with correct content
        bus.send_message.assert_called_once()
        call_args = bus.send_message.call_args[0][0]
        assert isinstance(call_args, AgentMessage)
        assert call_args.content == {"key": "key1", "value": "value1"}
        assert call_args.payload == {"blackboard_update": True}


class TestKafkaConstants:
    """Tests for module constants."""

    def test_kafka_available_is_bool(self):
        """KAFKA_AVAILABLE is a boolean."""
        assert isinstance(KAFKA_AVAILABLE, bool)
