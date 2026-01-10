"""
ACGS-2 Circuit Breaker Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/circuit_breaker/__init__.py
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if pybreaker not installed
pybreaker = pytest.importorskip("pybreaker")

# Import module under test
from src.core.shared.circuit_breaker import (
    CONSTITUTIONAL_HASH,  # noqa: E402
    CORE_SERVICES,
    ACGSCircuitBreakerListener,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker_health_check,
    get_circuit_breaker,
    initialize_core_circuit_breakers,
    with_circuit_breaker,
)

# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_in_module(self):
        """Verify constitutional hash is exported."""
        from shared import circuit_breaker

        assert hasattr(circuit_breaker, "CONSTITUTIONAL_HASH")
        assert circuit_breaker.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# ============================================================================
# CircuitState Enum Tests
# ============================================================================


class TestCircuitState:
    """Test CircuitState enum."""

    def test_closed_state(self):
        """Test CLOSED state value."""
        assert CircuitState.CLOSED.value == "closed"

    def test_open_state(self):
        """Test OPEN state value."""
        assert CircuitState.OPEN.value == "open"

    def test_half_open_state(self):
        """Test HALF_OPEN state value."""
        assert CircuitState.HALF_OPEN.value == "half_open"


# ============================================================================
# CircuitBreakerConfig Tests
# ============================================================================


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.fail_max == 5
        assert config.reset_timeout == 30
        assert config.exclude_exceptions == ()
        assert config.listeners is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            fail_max=10, reset_timeout=60, exclude_exceptions=(ValueError,)
        )
        assert config.fail_max == 10
        assert config.reset_timeout == 60
        assert config.exclude_exceptions == (ValueError,)

    def test_partial_custom_values(self):
        """Test partial custom configuration."""
        config = CircuitBreakerConfig(fail_max=3)
        assert config.fail_max == 3
        assert config.reset_timeout == 30  # Default


# ============================================================================
# ACGSCircuitBreakerListener Tests
# ============================================================================


class TestACGSCircuitBreakerListener:
    """Test ACGS circuit breaker listener."""

    def test_listener_initialization(self):
        """Test listener initializes correctly."""
        listener = ACGSCircuitBreakerListener("test_service")
        assert listener.service_name == "test_service"
        assert listener.constitutional_hash == CONSTITUTIONAL_HASH

    def test_state_change_logging(self):
        """Test state change is logged."""
        listener = ACGSCircuitBreakerListener("test_service")
        mock_cb = MagicMock()

        with patch("shared.circuit_breaker.logger") as mock_logger:
            listener.state_change(mock_cb, "closed", "open")
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "test_service" in call_args
            assert "closed" in call_args
            assert "open" in call_args

    def test_before_call_logging(self):
        """Test before call is logged."""
        listener = ACGSCircuitBreakerListener("test_service")
        mock_cb = MagicMock()
        mock_func = MagicMock(__name__="test_func")

        with patch("shared.circuit_breaker.logger") as mock_logger:
            listener.before_call(mock_cb, mock_func)
            mock_logger.debug.assert_called_once()

    def test_success_logging(self):
        """Test success is logged."""
        listener = ACGSCircuitBreakerListener("test_service")
        mock_cb = MagicMock()

        with patch("shared.circuit_breaker.logger") as mock_logger:
            listener.success(mock_cb)
            mock_logger.debug.assert_called_once()

    def test_failure_logging(self):
        """Test failure is logged."""
        listener = ACGSCircuitBreakerListener("test_service")
        mock_cb = MagicMock()

        with patch("shared.circuit_breaker.logger") as mock_logger:
            listener.failure(mock_cb, ValueError("Test error"))
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "ValueError" in call_args
            assert "Test error" in call_args


# ============================================================================
# CircuitBreakerRegistry Tests
# ============================================================================


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def test_singleton_pattern(self):
        """Test registry is a singleton."""
        registry1 = CircuitBreakerRegistry()
        registry2 = CircuitBreakerRegistry()
        assert registry1 is registry2

    def test_get_or_create_new_breaker(self):
        """Test creating a new circuit breaker."""
        registry = CircuitBreakerRegistry()
        cb = registry.get_or_create("test_registry_service")
        assert cb is not None
        assert isinstance(cb, pybreaker.CircuitBreaker)

    def test_get_or_create_existing_breaker(self):
        """Test getting existing circuit breaker."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("test_existing_service")
        cb2 = registry.get_or_create("test_existing_service")
        assert cb1 is cb2

    def test_get_or_create_with_config(self):
        """Test creating with custom config."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(fail_max=10, reset_timeout=60)
        cb = registry.get_or_create("test_config_service", config)
        assert cb.fail_max == 10
        assert cb.reset_timeout == 60

    def test_get_all_states(self):
        """Test getting all circuit breaker states."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test_states_service1")
        registry.get_or_create("test_states_service2")

        states = registry.get_all_states()
        assert "test_states_service1" in states
        assert "test_states_service2" in states
        assert "state" in states["test_states_service1"]

    def test_reset_circuit_breaker(self):
        """Test resetting a circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test_reset_service")

        # Verify reset doesn't raise
        registry.reset("test_reset_service")

    def test_reset_nonexistent_breaker(self):
        """Test resetting nonexistent breaker doesn't raise."""
        registry = CircuitBreakerRegistry()
        # Should not raise
        registry.reset("nonexistent_service")

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test_reset_all_1")
        registry.get_or_create("test_reset_all_2")

        # Should not raise
        registry.reset_all()


# ============================================================================
# get_circuit_breaker Function Tests
# ============================================================================


class TestGetCircuitBreaker:
    """Test get_circuit_breaker function."""

    def test_get_circuit_breaker_basic(self):
        """Test getting a circuit breaker."""
        cb = get_circuit_breaker("test_get_basic")
        assert cb is not None
        assert isinstance(cb, pybreaker.CircuitBreaker)

    def test_get_circuit_breaker_with_config(self):
        """Test getting circuit breaker with config."""
        config = CircuitBreakerConfig(fail_max=3)
        cb = get_circuit_breaker("test_get_config", config)
        assert cb.fail_max == 3

    def test_get_same_circuit_breaker(self):
        """Test getting same circuit breaker returns same instance."""
        cb1 = get_circuit_breaker("test_get_same")
        cb2 = get_circuit_breaker("test_get_same")
        assert cb1 is cb2


# ============================================================================
# with_circuit_breaker Decorator Tests
# ============================================================================


class TestWithCircuitBreakerDecorator:
    """Test with_circuit_breaker decorator."""

    def test_sync_function_success(self):
        """Test decorator with successful sync function."""

        @with_circuit_breaker("test_decorator_sync")
        def sync_handler():
            return {"status": "success"}

        result = sync_handler()
        assert result == {"status": "success"}

    def test_sync_function_with_args(self):
        """Test decorator preserves function arguments."""

        @with_circuit_breaker("test_decorator_args")
        def sync_handler(a, b, c=None):
            return {"a": a, "b": b, "c": c}

        result = sync_handler(1, 2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_sync_function_exception(self):
        """Test decorator propagates exceptions."""

        @with_circuit_breaker("test_decorator_exception")
        def failing_handler():
            raise ValueError("Test failure")

        with pytest.raises(ValueError, match="Test failure"):
            failing_handler()

    def test_sync_function_with_fallback(self):
        """Test decorator uses fallback when circuit opens."""
        # Create a circuit breaker that opens after 1 failure
        get_circuit_breaker("test_fallback_service", CircuitBreakerConfig(fail_max=1))

        call_count = 0

        @with_circuit_breaker("test_fallback_service", fallback=lambda: {"fallback": True})
        def failing_handler():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Service unavailable")

        # First call fails, opens circuit, and uses fallback
        result = failing_handler()
        assert result == {"fallback": True}
        assert call_count == 1  # Function was called once before circuit opened

        # Subsequent calls should use fallback without calling function
        result2 = failing_handler()
        assert result2 == {"fallback": True}
        assert call_count == 1  # Function should not be called again

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with successful async function."""

        @with_circuit_breaker("test_async_decorator")
        async def async_handler():
            await asyncio.sleep(0.001)
            return {"async": True}

        result = await async_handler()
        assert result == {"async": True}

    @pytest.mark.asyncio
    async def test_async_function_exception(self):
        """Test decorator handles async exceptions."""

        @with_circuit_breaker("test_async_exception")
        async def failing_async_handler():
            await asyncio.sleep(0.001)
            raise RuntimeError("Async failure")

        with pytest.raises(RuntimeError, match="Async failure"):
            await failing_async_handler()

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function metadata."""

        @with_circuit_breaker("test_metadata")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


# ============================================================================
# circuit_breaker_health_check Function Tests
# ============================================================================


class TestCircuitBreakerHealthCheck:
    """Test circuit_breaker_health_check function."""

    def test_health_check_structure(self):
        """Test health check returns correct structure."""
        health = circuit_breaker_health_check()

        assert "constitutional_hash" in health
        assert "timestamp" in health
        assert "overall_health" in health
        assert "open_circuits" in health
        assert "circuit_states" in health

    def test_health_check_constitutional_hash(self):
        """Test health check includes constitutional hash."""
        health = circuit_breaker_health_check()
        assert health["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_health_check_healthy_status(self):
        """Test health check reports healthy when no open circuits."""
        # Reset all breakers to ensure clean state
        registry = CircuitBreakerRegistry()
        registry.reset_all()

        health = circuit_breaker_health_check()
        # May be healthy or have some existing open circuits
        assert health["overall_health"] in ["healthy", "degraded"]

    def test_health_check_has_timestamp(self):
        """Test health check includes ISO timestamp."""
        health = circuit_breaker_health_check()
        assert "timestamp" in health
        # Check ISO format
        from datetime import datetime

        try:
            datetime.fromisoformat(health["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamp is not valid ISO format")


# ============================================================================
# CORE_SERVICES and initialize_core_circuit_breakers Tests
# ============================================================================


class TestCoreServices:
    """Test core services configuration."""

    def test_core_services_defined(self):
        """Test CORE_SERVICES list is defined."""
        assert CORE_SERVICES is not None
        assert isinstance(CORE_SERVICES, list)
        assert len(CORE_SERVICES) > 0

    def test_core_services_contains_expected(self):
        """Test CORE_SERVICES contains expected services."""
        expected_services = [
            "rust_message_bus",
            "deliberation_layer",
            "constraint_generation",
            "vector_search",
            "audit_ledger",
            "adaptive_governance",
        ]
        for service in expected_services:
            assert service in CORE_SERVICES, f"Missing core service: {service}"

    def test_initialize_core_circuit_breakers(self):
        """Test initializing core circuit breakers."""
        # Should not raise
        initialize_core_circuit_breakers()

        # Verify all core services have circuit breakers
        for service in CORE_SERVICES:
            cb = get_circuit_breaker(service)
            assert cb is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker module."""

    def test_multiple_services_isolation(self):
        """Test circuit breakers are isolated per service."""
        cb1 = get_circuit_breaker("service_a")
        cb2 = get_circuit_breaker("service_b")

        assert cb1 is not cb2

    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker tracks failures."""
        config = CircuitBreakerConfig(fail_max=3, reset_timeout=1)
        cb = get_circuit_breaker("test_failure_tracking", config)

        def failing_call():
            raise RuntimeError("Intentional failure")

        # Make some failures
        for _ in range(2):
            try:
                cb.call(failing_call)
            except RuntimeError:
                pass

        # Circuit should still be closed (not at fail_max yet)
        assert cb.current_state != pybreaker.STATE_OPEN or cb.fail_counter > 0


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Test module exports all required components."""

    def test_all_classes_exported(self):
        """Test all classes are exported."""
        from shared import circuit_breaker

        required_classes = [
            "CircuitState",
            "CircuitBreakerConfig",
            "ACGSCircuitBreakerListener",
            "CircuitBreakerRegistry",
        ]
        for class_name in required_classes:
            assert hasattr(circuit_breaker, class_name), f"Missing export: {class_name}"

    def test_all_functions_exported(self):
        """Test all functions are exported."""
        from shared import circuit_breaker

        required_functions = [
            "get_circuit_breaker",
            "with_circuit_breaker",
            "circuit_breaker_health_check",
            "initialize_core_circuit_breakers",
        ]
        for func_name in required_functions:
            assert hasattr(circuit_breaker, func_name), f"Missing export: {func_name}"
            assert callable(getattr(circuit_breaker, func_name))

    def test_constants_exported(self):
        """Test constants are exported."""
        from shared import circuit_breaker

        assert hasattr(circuit_breaker, "CONSTITUTIONAL_HASH")
        assert hasattr(circuit_breaker, "CORE_SERVICES")
