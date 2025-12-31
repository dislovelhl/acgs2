"""
ACGS-2 Circuit Breaker Module
Constitutional Hash: cdd01ef066bc6cf2

This module provides circuit breaker patterns for fault tolerance in ACGS-2 services.
Based on the pybreaker library with ACGS-2 specific enhancements.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type

import pybreaker

# Constitutional Hash for governance validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    fail_max: int = 5  # Number of failures before opening
    reset_timeout: int = 30  # Seconds before attempting reset
    exclude_exceptions: tuple = ()  # Exceptions that don't count as failures
    listeners: list = None  # Event listeners


# Optimized service-specific configurations based on service characteristics
# These values are tuned based on expected failure patterns and recovery times
OPTIMIZED_CIRCUIT_CONFIGS = {
    # Fast-fail services: Quick detection, fast recovery
    # OPA/Policy services have transient failures from network issues
    "adaptive_governance": CircuitBreakerConfig(
        fail_max=3,  # Lower threshold for fast failover
        reset_timeout=15,  # Quick recovery attempt
    ),
    "policy_registry": CircuitBreakerConfig(
        fail_max=3,
        reset_timeout=15,
    ),
    "opa_client": CircuitBreakerConfig(
        fail_max=3,
        reset_timeout=15,
    ),
    # Critical slow services: Higher tolerance, longer recovery
    # These services are essential but may take longer to respond
    "audit_ledger": CircuitBreakerConfig(
        fail_max=7,  # More tolerance for critical service
        reset_timeout=60,  # Longer recovery for blockchain
    ),
    "deliberation_layer": CircuitBreakerConfig(
        fail_max=7,
        reset_timeout=45,  # AI inference can be slow
    ),
    # Standard services: Default balanced configuration
    "rust_message_bus": CircuitBreakerConfig(
        fail_max=5,
        reset_timeout=30,
    ),
    "constraint_generation": CircuitBreakerConfig(
        fail_max=5,
        reset_timeout=30,
    ),
    "vector_search": CircuitBreakerConfig(
        fail_max=5,
        reset_timeout=30,
    ),
}


class ACGSCircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """
    ACGS-2 Circuit Breaker Listener with constitutional compliance logging.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.constitutional_hash = CONSTITUTIONAL_HASH

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: str, new_state: str):
        """Log state changes with constitutional context."""
        logger.warning(
            f"[{self.constitutional_hash}] Circuit breaker '{self.service_name}' "
            f"state change: {old_state} -> {new_state}"
        )

    def before_call(self, cb: pybreaker.CircuitBreaker, func: Callable, *args, **kwargs):
        """Log before call attempts."""
        logger.debug(
            f"[{self.constitutional_hash}] Circuit breaker '{self.service_name}' "
            f"attempting call to {func.__name__}"
        )

    def success(self, cb: pybreaker.CircuitBreaker):
        """Log successful calls."""
        logger.debug(
            f"[{self.constitutional_hash}] Circuit breaker '{self.service_name}' " f"call succeeded"
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception):
        """Log failures with details."""
        logger.warning(
            f"[{self.constitutional_hash}] Circuit breaker '{self.service_name}' "
            f"call failed: {type(exc).__name__}: {exc}"
        )


class CircuitBreakerRegistry:
    """
    Registry for managing circuit breakers across ACGS-2 services.

    Usage:
        registry = CircuitBreakerRegistry()
        cb = registry.get_or_create('policy_service')

        @cb
        def call_policy_service():
            ...
    """

    _instance = None
    _breakers: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._breakers = {}
        return cls._instance

    def get_or_create(
        self, service_name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> pybreaker.CircuitBreaker:
        """
        Get or create a circuit breaker for a service.

        Args:
            service_name: Name of the service
            config: Optional configuration

        Returns:
            Circuit breaker instance
        """
        if service_name not in self._breakers:
            config = config or CircuitBreakerConfig()
            listener = ACGSCircuitBreakerListener(service_name)

            self._breakers[service_name] = pybreaker.CircuitBreaker(
                fail_max=config.fail_max,
                reset_timeout=config.reset_timeout,
                exclude=config.exclude_exceptions,
                listeners=[listener],
            )
            logger.info(f"[{CONSTITUTIONAL_HASH}] Created circuit breaker for '{service_name}'")

        return self._breakers[service_name]

    def get_all_states(self) -> dict:
        """Get states of all circuit breakers."""
        return {
            name: {
                "state": cb.current_state,
                "fail_counter": cb.fail_counter,
                "success_counter": cb.success_counter,
            }
            for name, cb in self._breakers.items()
        }

    def reset(self, service_name: str):
        """Reset a circuit breaker to closed state."""
        if service_name in self._breakers:
            self._breakers[service_name].close()
            logger.info(f"[{CONSTITUTIONAL_HASH}] Reset circuit breaker for '{service_name}'")

    def reset_all(self):
        """Reset all circuit breakers."""
        for name in self._breakers:
            self.reset(name)


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    service_name: str, config: Optional[CircuitBreakerConfig] = None
) -> pybreaker.CircuitBreaker:
    """
    Get or create a circuit breaker for a service.

    Uses optimized service-specific configurations from OPTIMIZED_CIRCUIT_CONFIGS
    if no explicit config is provided and the service has an optimized config.

    Args:
        service_name: Name of the service
        config: Optional configuration (overrides optimized defaults)

    Returns:
        Circuit breaker instance
    """
    # Use optimized config if available and no explicit config provided
    if config is None and service_name in OPTIMIZED_CIRCUIT_CONFIGS:
        config = OPTIMIZED_CIRCUIT_CONFIGS[service_name]
        logger.debug(
            f"[{CONSTITUTIONAL_HASH}] Using optimized config for '{service_name}': "
            f"fail_max={config.fail_max}, reset_timeout={config.reset_timeout}"
        )
    return _registry.get_or_create(service_name, config)


def with_circuit_breaker(
    service_name: str,
    fallback: Optional[Callable] = None,
    config: Optional[CircuitBreakerConfig] = None,
):
    """
    Decorator to wrap a function with circuit breaker protection.

    Args:
        service_name: Name of the service for the circuit breaker
        fallback: Optional fallback function when circuit is open
        config: Optional circuit breaker configuration

    Usage:
        @with_circuit_breaker('policy_service', fallback=lambda: {'status': 'unavailable'})
        def call_policy_service(policy_id):
            # Call external service
            ...
    """

    def decorator(func: Callable):
        cb = get_circuit_breaker(service_name, config)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return cb.call(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Circuit open for '{service_name}', " f"using fallback"
                )
                if fallback:
                    return fallback(*args, **kwargs)
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await cb.call(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Circuit open for '{service_name}', " f"using fallback"
                )
                if fallback:
                    result = fallback(*args, **kwargs)
                    if hasattr(result, "__await__"):
                        return await result
                    return result
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def circuit_breaker_health_check() -> dict:
    """
    Get health status of all circuit breakers.

    Returns:
        Dictionary with circuit breaker states and overall health
    """
    states = _registry.get_all_states()
    open_circuits = [
        name for name, state in states.items() if state["state"] == pybreaker.STATE_OPEN
    ]

    return {
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_health": "degraded" if open_circuits else "healthy",
        "open_circuits": open_circuits,
        "circuit_states": states,
    }


# Pre-configured circuit breakers for ACGS-2 core services
CORE_SERVICES = [
    "rust_message_bus",
    "deliberation_layer",
    "constraint_generation",
    "vector_search",
    "audit_ledger",
    "adaptive_governance",
]


def initialize_core_circuit_breakers():
    """Initialize circuit breakers for all core ACGS-2 services."""
    for service in CORE_SERVICES:
        get_circuit_breaker(service)
    logger.info(
        f"[{CONSTITUTIONAL_HASH}] Initialized circuit breakers for {len(CORE_SERVICES)} core services"
    )


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    "CORE_SERVICES",
    "OPTIMIZED_CIRCUIT_CONFIGS",
    # Classes
    "CircuitState",
    "CircuitBreakerConfig",
    "ACGSCircuitBreakerListener",
    "CircuitBreakerRegistry",
    # Functions
    "get_circuit_breaker",
    "with_circuit_breaker",
    "circuit_breaker_health_check",
    "initialize_core_circuit_breakers",
]
