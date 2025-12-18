"""
ACGS-2 Shared Modules Package
Constitutional Hash: cdd01ef066bc6cf2

This package provides common utilities and patterns for ACGS-2 services:

Modules:
    - metrics: Prometheus instrumentation for observability
    - circuit_breaker: Fault tolerance patterns
    - redis_config: Centralized Redis configuration
    - monitoring: System monitoring utilities
    - security: Security utilities and PII protection

Usage:
    from shared.metrics import track_request_metrics, track_constitutional_validation
    from shared.circuit_breaker import with_circuit_breaker, get_circuit_breaker
    from shared.redis_config import get_redis_url

Example:
    @track_request_metrics('my_service', '/api/endpoint')
    @with_circuit_breaker('external_api')
    async def call_external_api():
        ...
"""

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

__version__ = "2.0.0"
__author__ = "ACGS-2 Team"

# Re-export commonly used components
try:
    from .metrics import (
        track_request_metrics,
        track_constitutional_validation,
        track_message_processing,
        get_metrics,
        set_service_info,
    )
except ImportError:
    pass

try:
    from .circuit_breaker import (
        get_circuit_breaker,
        with_circuit_breaker,
        circuit_breaker_health_check,
        CircuitBreakerConfig,
    )
except ImportError:
    pass

try:
    from .redis_config import get_redis_url
except ImportError:
    pass

__all__ = [
    "CONSTITUTIONAL_HASH",
    "__version__",
    # Metrics
    "track_request_metrics",
    "track_constitutional_validation",
    "track_message_processing",
    "get_metrics",
    "set_service_info",
    # Circuit Breaker
    "get_circuit_breaker",
    "with_circuit_breaker",
    "circuit_breaker_health_check",
    "CircuitBreakerConfig",
    # Redis
    "get_redis_url",
]
