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
    - logging_config: Structured logging with JSON output and correlation IDs
    - middleware: FastAPI middleware components (correlation ID, request tracing)

Usage:
    from shared.metrics import track_request_metrics, track_constitutional_validation
    from shared.circuit_breaker import with_circuit_breaker, get_circuit_breaker
    from shared.redis_config import get_redis_url
    from shared.logging_config import configure_logging, get_logger
    from shared.middleware import add_correlation_id_middleware

Example:
    # Structured logging with correlation IDs
    configure_logging(service_name="my_service")
    logger = get_logger(__name__)
    logger.info("operation_started", user_id=user.id)

    # Add correlation ID middleware to FastAPI app
    app = FastAPI()
    add_correlation_id_middleware(app, service_name="my_service")

    @track_request_metrics('my_service', '/api/endpoint')
    @with_circuit_breaker('external_api')
    async def call_external_api():
        ...
"""

# Import from dedicated constants module
from .constants import CONSTITUTIONAL_HASH, DEFAULT_REDIS_URL

__version__ = "2.0.0"
__author__ = "ACGS-2 Team"

# Re-export commonly used components
try:
    from .metrics import (
        get_metrics,
        set_service_info,
        track_constitutional_validation,
        track_message_processing,
        track_request_metrics,
    )
except ImportError:
    pass

try:
    from .circuit_breaker import (
        CircuitBreakerConfig,
        circuit_breaker_health_check,
        get_circuit_breaker,
        with_circuit_breaker,
    )
except ImportError:
    pass

try:
    from .redis_config import get_redis_url
except ImportError:
    pass

try:
    from .logging_config import (
        bind_correlation_id,
        clear_correlation_context,
        configure_logging,
        get_logger,
        instrument_fastapi,
        setup_opentelemetry,
    )
except ImportError:
    pass

try:
    from .middleware import (
        CORRELATION_ID_HEADER,
        CorrelationIdMiddleware,
        add_correlation_id_middleware,
        correlation_id_middleware,
        get_correlation_id,
    )
except ImportError:
    pass

__all__ = [
    "CONSTITUTIONAL_HASH",
    "DEFAULT_REDIS_URL",
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
    # Logging
    "configure_logging",
    "get_logger",
    "bind_correlation_id",
    "clear_correlation_context",
    "setup_opentelemetry",
    "instrument_fastapi",
    # Middleware
    "CORRELATION_ID_HEADER",
    "CorrelationIdMiddleware",
    "correlation_id_middleware",
    "add_correlation_id_middleware",
    "get_correlation_id",
]
