"""
ACGS-2 Core Module Coverage Expansion Tests
Constitutional Hash: cdd01ef066bc6cf2

Additional tests for core.py to expand coverage of all exports and feature flags.
"""

import pytest

try:
    from enhanced_agent_bus import core
    from enhanced_agent_bus.core import (  # Constants; Core Classes; Protocol Interfaces; Implementation Classes; Backward Compatibility; Functions
        CIRCUIT_BREAKER_ENABLED,
        CONSTITUTIONAL_HASH,
        DEFAULT_REDIS_URL,
        METERING_AVAILABLE,
        METRICS_ENABLED,
        USE_RUST,
        AgentMessage,
        AgentRegistry,
        CompositeProcessingStrategy,
        ConstitutionalValidationStrategy,
        DecisionLog,
        DirectMessageRouter,
        DynamicPolicyProcessingStrategy,
        DynamicPolicyValidationStrategy,
        EnhancedAgentBus,
        InMemoryAgentRegistry,
        MessagePriority,
        MessageProcessor,
        MessageRouter,
        MessageStatus,
        MessageType,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        Priority,
        ProcessingStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
        ValidationResult,
        ValidationStrategy,
        get_agent_bus,
        reset_agent_bus,
    )
except ImportError:
    import core
    from core import (
        CIRCUIT_BREAKER_ENABLED,
        CONSTITUTIONAL_HASH,
        DEFAULT_REDIS_URL,
        METERING_AVAILABLE,
        METRICS_ENABLED,
        USE_RUST,
        AgentMessage,
        AgentRegistry,
        CompositeProcessingStrategy,
        ConstitutionalValidationStrategy,
        DecisionLog,
        DirectMessageRouter,
        DynamicPolicyProcessingStrategy,
        DynamicPolicyValidationStrategy,
        EnhancedAgentBus,
        InMemoryAgentRegistry,
        MessagePriority,
        MessageProcessor,
        MessageRouter,
        MessageStatus,
        MessageType,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        Priority,
        ProcessingStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
        ValidationResult,
        ValidationStrategy,
        get_agent_bus,
        reset_agent_bus,
    )


class TestCoreStrategyExports:
    """Tests for all strategy class exports from core module."""

    def test_rust_processing_strategy_exported(self):
        """RustProcessingStrategy is exported."""
        assert RustProcessingStrategy is not None
        # Class should exist even if Rust not available
        assert hasattr(RustProcessingStrategy, "__name__")

    def test_rust_validation_strategy_exported(self):
        """RustValidationStrategy is exported."""
        assert RustValidationStrategy is not None
        assert hasattr(RustValidationStrategy, "__name__")

    def test_opa_processing_strategy_exported(self):
        """OPAProcessingStrategy is exported."""
        assert OPAProcessingStrategy is not None
        # Should have process method from protocol
        assert hasattr(OPAProcessingStrategy, "process")

    def test_opa_validation_strategy_exported(self):
        """OPAValidationStrategy is exported."""
        assert OPAValidationStrategy is not None
        # Should have validate method from protocol
        assert hasattr(OPAValidationStrategy, "validate")

    def test_dynamic_policy_processing_strategy_exported(self):
        """DynamicPolicyProcessingStrategy is exported."""
        assert DynamicPolicyProcessingStrategy is not None
        assert hasattr(DynamicPolicyProcessingStrategy, "process")

    def test_dynamic_policy_validation_strategy_exported(self):
        """DynamicPolicyValidationStrategy is exported."""
        assert DynamicPolicyValidationStrategy is not None
        assert hasattr(DynamicPolicyValidationStrategy, "validate")

    def test_composite_processing_strategy_instantiable(self):
        """CompositeProcessingStrategy can be instantiated."""
        # CompositeProcessingStrategy takes list of strategies
        strategy = CompositeProcessingStrategy(strategies=[])
        assert strategy is not None
        assert hasattr(strategy, "process")


class TestCoreValidationStrategies:
    """Tests for validation strategy implementations."""

    def test_static_hash_validation_has_validate(self):
        """StaticHashValidationStrategy has validate method."""
        assert hasattr(StaticHashValidationStrategy, "validate")
        strategy = StaticHashValidationStrategy()
        assert strategy is not None

    def test_constitutional_validation_is_alias(self):
        """ConstitutionalValidationStrategy is StaticHashValidationStrategy alias."""
        assert ConstitutionalValidationStrategy is StaticHashValidationStrategy
        # Both should be the same class
        assert ConstitutionalValidationStrategy.__name__ == StaticHashValidationStrategy.__name__


class TestCoreProcessingStrategies:
    """Tests for processing strategy implementations."""

    def test_python_processing_strategy_instantiable(self):
        """PythonProcessingStrategy can be instantiated."""
        strategy = PythonProcessingStrategy()
        assert strategy is not None
        assert hasattr(strategy, "process")

    def test_python_processing_strategy_has_required_methods(self):
        """PythonProcessingStrategy has all required methods."""
        strategy = PythonProcessingStrategy()
        # Check ProcessingStrategy protocol methods
        assert hasattr(strategy, "process")
        assert callable(strategy.process)


class TestCoreMeteringExportsExpanded:
    """Extended tests for metering integration exports."""

    def test_metering_available_affects_exports(self):
        """METERING_AVAILABLE flag indicates metering export availability."""
        try:
            from enhanced_agent_bus.core import (
                AsyncMeteringQueue,
                MeteringConfig,
                MeteringHooks,
                MeteringMixin,
                get_metering_hooks,
                get_metering_queue,
                metered_operation,
                reset_metering,
            )
        except ImportError:
            from core import (
                AsyncMeteringQueue,
                MeteringConfig,
                MeteringHooks,
                MeteringMixin,
                get_metering_hooks,
                get_metering_queue,
                metered_operation,
                reset_metering,
            )

        if METERING_AVAILABLE:
            # All metering exports should be available
            assert MeteringConfig is not None
            assert AsyncMeteringQueue is not None
            assert MeteringHooks is not None
            assert MeteringMixin is not None
            assert get_metering_queue is not None
            assert get_metering_hooks is not None
            assert reset_metering is not None
            assert metered_operation is not None
        else:
            # When metering not available, exports are None
            assert MeteringConfig is None
            assert AsyncMeteringQueue is None

    def test_metering_functions_callable_when_available(self):
        """Metering functions are callable when available."""
        try:
            from enhanced_agent_bus.core import (
                get_metering_hooks,
                get_metering_queue,
                reset_metering,
            )
        except ImportError:
            from core import get_metering_hooks, get_metering_queue, reset_metering

        if METERING_AVAILABLE:
            assert callable(get_metering_hooks)
            assert callable(get_metering_queue)
            assert callable(reset_metering)


class TestCoreFeatureFlags:
    """Tests for feature flag detection and values."""

    def test_metrics_enabled_reflects_imports(self):
        """METRICS_ENABLED reflects whether metrics module is available."""
        # Just verify it's a boolean - actual value depends on environment
        assert isinstance(METRICS_ENABLED, bool)
        # If enabled, the metrics module was imported
        if METRICS_ENABLED:
            try:
                from core.shared.metrics import MESSAGES_TOTAL

                assert MESSAGES_TOTAL is not None
            except ImportError:
                pytest.fail("METRICS_ENABLED is True but metrics import failed")

    def test_circuit_breaker_enabled_reflects_imports(self):
        """CIRCUIT_BREAKER_ENABLED reflects circuit breaker availability."""
        assert isinstance(CIRCUIT_BREAKER_ENABLED, bool)
        if CIRCUIT_BREAKER_ENABLED:
            try:
                from core.shared.circuit_breaker import get_circuit_breaker

                assert get_circuit_breaker is not None
            except ImportError:
                pytest.fail("CIRCUIT_BREAKER_ENABLED is True but import failed")

    def test_use_rust_reflects_rust_binding(self):
        """USE_RUST reflects whether Rust binding is available."""
        assert isinstance(USE_RUST, bool)
        if USE_RUST:
            try:
                import enhanced_agent_bus_rust  # noqa: F401

                assert enhanced_agent_bus_rust is not None
            except ImportError:
                pytest.fail("USE_RUST is True but Rust import failed")


class TestCoreRegistryExports:
    """Tests for registry class exports."""

    def test_in_memory_agent_registry_functional(self):
        """InMemoryAgentRegistry is functional."""
        registry = InMemoryAgentRegistry()
        assert registry is not None
        # Should have register method from AgentRegistry protocol
        assert hasattr(registry, "register")
        assert callable(registry.register)

    def test_direct_message_router_exported(self):
        """DirectMessageRouter is properly exported."""
        assert DirectMessageRouter is not None
        # Should have route method from MessageRouter protocol
        assert hasattr(DirectMessageRouter, "route")


class TestCoreModelExports:
    """Tests for model class exports and usage."""

    def test_agent_message_fields(self):
        """AgentMessage has expected fields."""
        msg = AgentMessage(
            content="test content",
            from_agent="agent_a",
            to_agent="agent_b",
        )
        assert msg.content == "test content"
        assert msg.from_agent == "agent_a"
        assert msg.to_agent == "agent_b"

    def test_agent_message_with_type_and_priority(self):
        """AgentMessage can use MessageType and Priority."""
        msg = AgentMessage(
            content="command",
            from_agent="sender",
            to_agent="receiver",
            message_type=MessageType.COMMAND,
            priority=Priority.HIGH,
        )
        assert msg.message_type == MessageType.COMMAND
        assert msg.priority == Priority.HIGH

    def test_message_priority_deprecated_alias(self):
        """MessagePriority is available for backward compatibility."""
        # MessagePriority is now an alias for Priority
        assert MessagePriority is Priority
        # Should have same attributes
        assert hasattr(MessagePriority, "LOW")
        assert hasattr(MessagePriority, "NORMAL")
        assert hasattr(MessagePriority, "HIGH")
        assert hasattr(MessagePriority, "CRITICAL")

    def test_decision_log_instantiation(self):
        """DecisionLog can be instantiated."""
        log = DecisionLog(
            trace_id="trace-123",
            span_id="span-456",
            agent_id="agent-001",
            tenant_id="tenant-001",
            policy_version="1.0.0",
            risk_score=0.1,
            decision="ALLOW",
        )
        assert log is not None
        assert log.trace_id == "trace-123"
        assert log.decision == "ALLOW"

    def test_validation_result_with_all_fields(self):
        """ValidationResult accepts all fields."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["minor issue"],
        )
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1

    def test_validation_result_invalid(self):
        """ValidationResult can represent invalid state."""
        result = ValidationResult(
            is_valid=False,
            errors=["Constitutional hash mismatch"],
        )
        assert result.is_valid is False
        assert "Constitutional" in result.errors[0]

    def test_message_status_all_values(self):
        """MessageStatus has all expected values."""
        assert MessageStatus.PENDING is not None
        assert MessageStatus.DELIVERED is not None
        assert MessageStatus.FAILED is not None
        # Should have PROCESSING status (not PROCESSED)
        assert hasattr(MessageStatus, "PROCESSING")

    def test_message_type_all_values(self):
        """MessageType has all expected values."""
        assert MessageType.COMMAND is not None
        assert MessageType.QUERY is not None
        assert MessageType.EVENT is not None
        assert MessageType.RESPONSE is not None


class TestCoreProtocolInterfaces:
    """Tests for protocol interface definitions."""

    def test_agent_registry_is_protocol(self):
        """AgentRegistry is a protocol/ABC."""
        # Should have abstract methods defined
        assert hasattr(AgentRegistry, "register")
        assert hasattr(AgentRegistry, "unregister")
        assert hasattr(AgentRegistry, "get")

    def test_message_router_is_protocol(self):
        """MessageRouter is a protocol/ABC."""
        assert hasattr(MessageRouter, "route")

    def test_validation_strategy_is_protocol(self):
        """ValidationStrategy is a protocol/ABC."""
        assert hasattr(ValidationStrategy, "validate")

    def test_processing_strategy_is_protocol(self):
        """ProcessingStrategy is a protocol/ABC."""
        assert hasattr(ProcessingStrategy, "process")


class TestCoreAllExportsComplete:
    """Tests that verify all __all__ items are importable and usable."""

    def test_all_items_count(self):
        """__all__ contains expected number of exports."""
        # core.py has 44 items in __all__
        assert len(core.__all__) >= 40  # At least 40 exports

    def test_all_constants_in_all(self):
        """All constants are in __all__."""
        constants = [
            "CONSTITUTIONAL_HASH",
            "USE_RUST",
            "DEFAULT_REDIS_URL",
            "METRICS_ENABLED",
            "CIRCUIT_BREAKER_ENABLED",
            "METERING_AVAILABLE",
        ]
        for const in constants:
            assert const in core.__all__, f"{const} not in __all__"

    def test_all_core_classes_in_all(self):
        """All core classes are in __all__."""
        classes = [
            "MessageProcessor",
            "EnhancedAgentBus",
            "AgentMessage",
            "DecisionLog",
            "ValidationResult",
        ]
        for cls in classes:
            assert cls in core.__all__, f"{cls} not in __all__"

    def test_all_strategies_in_all(self):
        """All strategy classes are in __all__."""
        strategies = [
            "StaticHashValidationStrategy",
            "ConstitutionalValidationStrategy",
            "DynamicPolicyValidationStrategy",
            "PythonProcessingStrategy",
            "RustProcessingStrategy",
            "DynamicPolicyProcessingStrategy",
            "OPAProcessingStrategy",
            "OPAValidationStrategy",
            "CompositeProcessingStrategy",
        ]
        for strategy in strategies:
            assert strategy in core.__all__, f"{strategy} not in __all__"

    def test_all_metering_exports_in_all(self):
        """All metering exports are in __all__."""
        metering = [
            "MeteringConfig",
            "AsyncMeteringQueue",
            "MeteringHooks",
            "MeteringMixin",
            "get_metering_queue",
            "get_metering_hooks",
            "reset_metering",
            "metered_operation",
        ]
        for item in metering:
            assert item in core.__all__, f"{item} not in __all__"

    def test_all_functions_in_all(self):
        """All functions are in __all__."""
        functions = [
            "get_agent_bus",
            "reset_agent_bus",
        ]
        for func in functions:
            assert func in core.__all__, f"{func} not in __all__"


class TestCoreFunctionalUsage:
    """Tests that verify functional usage of core exports."""

    def test_reset_agent_bus_callable(self):
        """reset_agent_bus can be called."""
        # Should not raise
        reset_agent_bus()

    def test_get_agent_bus_returns_instance(self):
        """get_agent_bus returns an EnhancedAgentBus instance."""
        reset_agent_bus()  # Reset first
        bus = get_agent_bus()
        assert bus is not None
        assert isinstance(bus, EnhancedAgentBus)
        reset_agent_bus()  # Clean up

    def test_message_processor_isolated_mode(self):
        """MessageProcessor works in isolated mode."""
        processor = MessageProcessor(isolated_mode=True)
        assert processor is not None
        assert hasattr(processor, "process")

    def test_constitutional_hash_value(self):
        """CONSTITUTIONAL_HASH has expected value."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
        assert len(CONSTITUTIONAL_HASH) == 16

    def test_default_redis_url_format(self):
        """DEFAULT_REDIS_URL has valid Redis URL format."""
        assert DEFAULT_REDIS_URL.startswith("redis://")
        assert "localhost" in DEFAULT_REDIS_URL or "127.0.0.1" in DEFAULT_REDIS_URL


class TestCoreModuleAttributes:
    """Tests for core module attributes and structure."""

    def test_module_has_docstring(self):
        """Core module has docstring."""
        assert core.__doc__ is not None
        assert "ACGS-2" in core.__doc__
        assert "cdd01ef066bc6cf2" in core.__doc__

    def test_module_name(self):
        """Core module has correct name."""
        assert "core" in core.__name__

    def test_all_is_list(self):
        """__all__ is a list."""
        assert isinstance(core.__all__, list)

    def test_all_items_are_strings(self):
        """All items in __all__ are strings."""
        for item in core.__all__:
            assert isinstance(item, str)
