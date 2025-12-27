"""
ACGS-2 Core Module Coverage Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for core.py backward compatibility facade.
"""

import pytest

try:
    from enhanced_agent_bus import core
    from enhanced_agent_bus.core import (
        CONSTITUTIONAL_HASH,
        USE_RUST,
        DEFAULT_REDIS_URL,
        METRICS_ENABLED,
        CIRCUIT_BREAKER_ENABLED,
        METERING_AVAILABLE,
        MessageProcessor,
        EnhancedAgentBus,
        AgentMessage,
        MessageType,
        Priority,
        MessageStatus,
        DecisionLog,
        ValidationResult,
        AgentRegistry,
        MessageRouter,
        ValidationStrategy,
        ProcessingStrategy,
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        PythonProcessingStrategy,
        CompositeProcessingStrategy,
        get_agent_bus,
        reset_agent_bus,
    )
except ImportError:
    import core
    from core import (
        CONSTITUTIONAL_HASH,
        USE_RUST,
        DEFAULT_REDIS_URL,
        METRICS_ENABLED,
        CIRCUIT_BREAKER_ENABLED,
        METERING_AVAILABLE,
        MessageProcessor,
        EnhancedAgentBus,
        AgentMessage,
        MessageType,
        Priority,
        MessageStatus,
        DecisionLog,
        ValidationResult,
        AgentRegistry,
        MessageRouter,
        ValidationStrategy,
        ProcessingStrategy,
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        PythonProcessingStrategy,
        CompositeProcessingStrategy,
        get_agent_bus,
        reset_agent_bus,
    )


class TestCoreConstants:
    """Tests for core module constants."""

    def test_constitutional_hash_defined(self):
        """Constitutional hash is defined."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_use_rust_is_boolean(self):
        """USE_RUST flag is boolean."""
        assert isinstance(USE_RUST, bool)

    def test_default_redis_url_defined(self):
        """Default Redis URL is defined."""
        assert DEFAULT_REDIS_URL is not None
        assert "redis" in DEFAULT_REDIS_URL.lower()

    def test_metrics_enabled_is_boolean(self):
        """METRICS_ENABLED flag is boolean."""
        assert isinstance(METRICS_ENABLED, bool)

    def test_circuit_breaker_enabled_is_boolean(self):
        """CIRCUIT_BREAKER_ENABLED flag is boolean."""
        assert isinstance(CIRCUIT_BREAKER_ENABLED, bool)

    def test_metering_available_is_boolean(self):
        """METERING_AVAILABLE flag is boolean."""
        assert isinstance(METERING_AVAILABLE, bool)


class TestCoreClassExports:
    """Tests for core class exports."""

    def test_message_processor_exported(self):
        """MessageProcessor class is exported."""
        assert MessageProcessor is not None
        processor = MessageProcessor(isolated_mode=True)
        assert processor is not None

    def test_enhanced_agent_bus_exported(self):
        """EnhancedAgentBus class is exported."""
        assert EnhancedAgentBus is not None

    def test_agent_message_exported(self):
        """AgentMessage class is exported."""
        assert AgentMessage is not None
        msg = AgentMessage(
            content="test",
            from_agent="sender",
            to_agent="receiver",
        )
        assert msg is not None

    def test_message_type_exported(self):
        """MessageType enum is exported."""
        assert MessageType is not None
        assert MessageType.COMMAND is not None
        assert MessageType.QUERY is not None
        assert MessageType.EVENT is not None

    def test_priority_exported(self):
        """Priority enum is exported."""
        assert Priority is not None
        assert Priority.LOW is not None
        assert Priority.NORMAL is not None
        assert Priority.HIGH is not None
        assert Priority.CRITICAL is not None

    def test_message_status_exported(self):
        """MessageStatus enum is exported."""
        assert MessageStatus is not None
        assert MessageStatus.PENDING is not None
        assert MessageStatus.DELIVERED is not None
        assert MessageStatus.FAILED is not None

    def test_decision_log_exported(self):
        """DecisionLog class is exported."""
        assert DecisionLog is not None

    def test_validation_result_exported(self):
        """ValidationResult class is exported."""
        assert ValidationResult is not None
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True


class TestCoreProtocolExports:
    """Tests for protocol interface exports."""

    def test_agent_registry_protocol(self):
        """AgentRegistry protocol is exported."""
        assert AgentRegistry is not None
        assert hasattr(AgentRegistry, 'register')

    def test_message_router_protocol(self):
        """MessageRouter protocol is exported."""
        assert MessageRouter is not None
        assert hasattr(MessageRouter, 'route')

    def test_validation_strategy_protocol(self):
        """ValidationStrategy protocol is exported."""
        assert ValidationStrategy is not None
        assert hasattr(ValidationStrategy, 'validate')

    def test_processing_strategy_protocol(self):
        """ProcessingStrategy protocol is exported."""
        assert ProcessingStrategy is not None
        assert hasattr(ProcessingStrategy, 'process')


class TestCoreImplementationExports:
    """Tests for implementation class exports."""

    def test_in_memory_registry_exported(self):
        """InMemoryAgentRegistry is exported."""
        assert InMemoryAgentRegistry is not None
        registry = InMemoryAgentRegistry()
        assert registry is not None

    def test_direct_message_router_exported(self):
        """DirectMessageRouter is exported."""
        assert DirectMessageRouter is not None

    def test_static_hash_validation_exported(self):
        """StaticHashValidationStrategy is exported."""
        assert StaticHashValidationStrategy is not None

    def test_python_processing_strategy_exported(self):
        """PythonProcessingStrategy is exported."""
        assert PythonProcessingStrategy is not None

    def test_composite_processing_strategy_exported(self):
        """CompositeProcessingStrategy is exported."""
        assert CompositeProcessingStrategy is not None


class TestCoreFunctionExports:
    """Tests for function exports."""

    def test_get_agent_bus_exported(self):
        """get_agent_bus function is exported."""
        assert get_agent_bus is not None
        assert callable(get_agent_bus)

    def test_reset_agent_bus_exported(self):
        """reset_agent_bus function is exported."""
        assert reset_agent_bus is not None
        assert callable(reset_agent_bus)


class TestCoreAllExports:
    """Tests for __all__ exports."""

    def test_all_defined(self):
        """__all__ is defined in core module."""
        assert hasattr(core, '__all__')
        assert len(core.__all__) > 0

    def test_all_contains_constitutional_hash(self):
        """__all__ contains CONSTITUTIONAL_HASH."""
        assert "CONSTITUTIONAL_HASH" in core.__all__

    def test_all_contains_message_processor(self):
        """__all__ contains MessageProcessor."""
        assert "MessageProcessor" in core.__all__

    def test_all_contains_enhanced_agent_bus(self):
        """__all__ contains EnhancedAgentBus."""
        assert "EnhancedAgentBus" in core.__all__

    def test_all_exports_are_accessible(self):
        """All items in __all__ are accessible."""
        for name in core.__all__:
            assert hasattr(core, name), f"{name} not found in core module"


class TestCoreBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    def test_constitutional_validation_alias(self):
        """ConstitutionalValidationStrategy is aliased to StaticHashValidationStrategy."""
        try:
            from enhanced_agent_bus.core import ConstitutionalValidationStrategy
        except ImportError:
            from core import ConstitutionalValidationStrategy

        assert ConstitutionalValidationStrategy is StaticHashValidationStrategy

    def test_message_priority_deprecated_alias(self):
        """MessagePriority is exported for backward compatibility."""
        try:
            from enhanced_agent_bus.core import MessagePriority
        except ImportError:
            from core import MessagePriority

        assert MessagePriority is not None


class TestCoreMeteringExports:
    """Tests for metering integration exports."""

    def test_metering_config_exported(self):
        """MeteringConfig is exported (may be None if unavailable)."""
        try:
            from enhanced_agent_bus.core import MeteringConfig
        except ImportError:
            from core import MeteringConfig

        # MeteringConfig may be None if metering not available
        if METERING_AVAILABLE:
            assert MeteringConfig is not None

    def test_metering_hooks_exported(self):
        """MeteringHooks is exported (may be None if unavailable)."""
        try:
            from enhanced_agent_bus.core import MeteringHooks
        except ImportError:
            from core import MeteringHooks

        if METERING_AVAILABLE:
            assert MeteringHooks is not None

    def test_metered_operation_exported(self):
        """metered_operation decorator is exported."""
        try:
            from enhanced_agent_bus.core import metered_operation
        except ImportError:
            from core import metered_operation

        if METERING_AVAILABLE:
            assert metered_operation is not None
            assert callable(metered_operation)
