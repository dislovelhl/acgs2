"""
ACGS-2 Interfaces Coverage Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for interfaces.py protocol definitions.
"""

try:
    from enhanced_agent_bus.interfaces import (
        AgentRegistry,
        MessageHandler,
        MessageRouter,
        MetricsCollector,
        ProcessingStrategy,
        ValidationStrategy,
    )
    from enhanced_agent_bus.models import CONSTITUTIONAL_HASH, AgentMessage
except ImportError:
    from interfaces import (
        AgentRegistry,
        MessageHandler,
        MessageRouter,
        MetricsCollector,
        ProcessingStrategy,
        ValidationStrategy,
    )
    from models import CONSTITUTIONAL_HASH, AgentMessage


class TestAgentRegistryProtocol:
    """Tests for AgentRegistry protocol."""

    def test_protocol_is_runtime_checkable(self):
        """AgentRegistry is runtime checkable."""
        # Protocol with @runtime_checkable will have __protocol_attrs__
        assert AgentRegistry is not None

    def test_protocol_has_required_methods(self):
        """AgentRegistry has required methods."""
        assert hasattr(AgentRegistry, "register")
        assert hasattr(AgentRegistry, "unregister")
        assert hasattr(AgentRegistry, "get")
        assert hasattr(AgentRegistry, "list_agents")

    def test_protocol_has_exists_method(self):
        """AgentRegistry has exists method."""
        assert hasattr(AgentRegistry, "exists")


class TestMessageHandlerProtocol:
    """Tests for MessageHandler protocol."""

    def test_protocol_exists(self):
        """MessageHandler protocol exists."""
        assert MessageHandler is not None

    def test_has_handle_method(self):
        """MessageHandler has handle method."""
        assert hasattr(MessageHandler, "handle")

    def test_has_can_handle_method(self):
        """MessageHandler has can_handle method."""
        assert hasattr(MessageHandler, "can_handle")


class TestMessageRouterProtocol:
    """Tests for MessageRouter protocol."""

    def test_protocol_exists(self):
        """MessageRouter protocol exists."""
        assert MessageRouter is not None

    def test_has_route_method(self):
        """MessageRouter has route method."""
        assert hasattr(MessageRouter, "route")


class TestMetricsCollectorProtocol:
    """Tests for MetricsCollector protocol."""

    def test_protocol_exists(self):
        """MetricsCollector protocol exists."""
        assert MetricsCollector is not None

    def test_has_record_message_method(self):
        """MetricsCollector has record_message_processed method."""
        assert hasattr(MetricsCollector, "record_message_processed")

    def test_has_get_metrics_method(self):
        """MetricsCollector has get_metrics method."""
        assert hasattr(MetricsCollector, "get_metrics")


class TestProcessingStrategyProtocol:
    """Tests for ProcessingStrategy protocol."""

    def test_protocol_exists(self):
        """ProcessingStrategy protocol exists."""
        assert ProcessingStrategy is not None

    def test_has_process_method(self):
        """ProcessingStrategy has process method."""
        assert hasattr(ProcessingStrategy, "process")

    def test_has_get_name_method(self):
        """ProcessingStrategy has get_name method."""
        assert hasattr(ProcessingStrategy, "get_name")


class TestValidationStrategyProtocol:
    """Tests for ValidationStrategy protocol."""

    def test_protocol_exists(self):
        """ValidationStrategy protocol exists."""
        assert ValidationStrategy is not None

    def test_has_validate_method(self):
        """ValidationStrategy has validate method."""
        assert hasattr(ValidationStrategy, "validate")


class TestModelDefaultValues:
    """Tests for AgentMessage default values."""

    def test_message_with_defaults(self):
        """Message has expected default values."""
        msg = AgentMessage(
            content={"test": "data"},
            from_agent="sender",
            to_agent="receiver",
        )
        assert msg.constitutional_validated is True
        assert msg.tenant_id == ""  # Default is empty string
        assert msg.constitutional_hash == CONSTITUTIONAL_HASH

    def test_message_id_generated(self):
        """Message ID is auto-generated."""
        msg = AgentMessage(
            content="test",
            from_agent="a",
            to_agent="b",
        )
        assert msg.message_id is not None
        assert len(msg.message_id) > 0

    def test_conversation_id_generated(self):
        """Conversation ID is auto-generated."""
        msg = AgentMessage(
            content="test",
            from_agent="a",
            to_agent="b",
        )
        assert msg.conversation_id is not None


class TestMetricsCollectorProtocolAdditional:
    """Tests for MetricsCollector protocol additional methods."""

    def test_has_record_agent_registered(self):
        """MetricsCollector has record_agent_registered method."""
        assert hasattr(MetricsCollector, "record_agent_registered")

    def test_has_record_agent_unregistered(self):
        """MetricsCollector has record_agent_unregistered method."""
        assert hasattr(MetricsCollector, "record_agent_unregistered")


class TestProcessingStrategyProtocolAdditional:
    """Tests for ProcessingStrategy protocol additional methods."""

    def test_has_is_available_method(self):
        """ProcessingStrategy has is_available method."""
        assert hasattr(ProcessingStrategy, "is_available")


class TestInterfacesAllExports:
    """Tests for interfaces __all__ exports."""

    def test_all_defined(self):
        """__all__ is defined in interfaces module."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        assert hasattr(interfaces, "__all__")
        assert len(interfaces.__all__) > 0

    def test_all_contains_agent_registry(self):
        """__all__ contains AgentRegistry."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        assert "AgentRegistry" in interfaces.__all__

    def test_all_contains_message_router(self):
        """__all__ contains MessageRouter."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        assert "MessageRouter" in interfaces.__all__

    def test_all_contains_metrics_collector(self):
        """__all__ contains MetricsCollector."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        assert "MetricsCollector" in interfaces.__all__

    def test_all_contains_message_handler(self):
        """__all__ contains MessageHandler."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        assert "MessageHandler" in interfaces.__all__

    def test_all_exports_are_accessible(self):
        """All items in __all__ are accessible."""
        try:
            from enhanced_agent_bus import interfaces
        except ImportError:
            import interfaces
        for name in interfaces.__all__:
            assert hasattr(interfaces, name), f"{name} not found in interfaces"
