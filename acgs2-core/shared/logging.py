"""
ACGS-2 Structured Logging Module
Constitutional Hash: cdd01ef066bc6cf2

Provides standardized structured logging across all ACGS-2 services using structlog.
Includes correlation IDs, service context, and JSON formatting for observability.
"""

import logging
import sys
from typing import Any, Dict, Optional

try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False
    # Fallback to standard logging
    structlog = None

from .constants import CONSTITUTIONAL_HASH


# ============================================================================
# Structured Logging Configuration
# ============================================================================


def configure_structlog(
    service_name: str,
    level: str = "INFO",
    json_format: bool = True,
    include_correlation_id: bool = True,
    include_service_context: bool = True,
) -> None:
    """
    Configure structured logging for an ACGS-2 service.

    Args:
        service_name: Name of the service (e.g., 'api-gateway', 'audit-service')
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output JSON format for log aggregation
        include_correlation_id: Whether to include request correlation IDs
        include_service_context: Whether to include service metadata
    """
    if not HAS_STRUCTLOG:
        # Fallback to standard logging
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format=f"%(asctime)s - {service_name} - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
        return

    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    if include_service_context:
        shared_processors.append(_add_service_context(service_name))

    if include_correlation_id:
        shared_processors.append(_add_correlation_id)

    if json_format:
        # JSON formatter for production/log aggregation
        shared_processors.extend(
            [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ]
        )
        formatter = structlog.writeasjson.JsonFormatter()
    else:
        # Human-readable formatter for development
        shared_processors.extend(
            [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ]
        )
        formatter = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _add_service_context(service_name: str):
    """Add service context to all log entries."""

    def processor(logger, method_name, event_dict):
        event_dict.update(
            {
                "service": service_name,
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "version": "1.0.0",  # Could be parameterized
            }
        )
        return event_dict

    return processor


def _add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries if available in context."""
    from .context import get_correlation_id

    try:
        correlation_id = get_correlation_id()
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
    except (ImportError, AttributeError):
        # Context module not available or correlation ID not set
        pass

    return event_dict


# ============================================================================
# Logger Factory
# ============================================================================


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for a specific module/component.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


# ============================================================================
# Context Management for Correlation IDs
# ============================================================================

# Simple context storage for correlation IDs
# In production, consider using contextvars for async safety
_correlation_id_context = {}


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current request context."""
    import threading

    _correlation_id_context[threading.get_ident()] = correlation_id


def get_correlation_id() -> Optional[str]:
    """Get correlation ID for the current request context."""
    import threading

    return _correlation_id_context.get(threading.get_ident())


def clear_correlation_id() -> None:
    """Clear correlation ID for the current request context."""
    import threading

    _correlation_id_context.pop(threading.get_ident(), None)


# ============================================================================
# FastAPI Integration
# ============================================================================


def create_correlation_middleware():
    """
    Create FastAPI middleware for correlation ID handling.

    Usage:
        from shared.logging import create_correlation_middleware

        app = FastAPI()
        app.middleware("http")(create_correlation_middleware())
    """
    import uuid
    from fastapi import Request, Response

    async def correlation_middleware(request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Set in context
        set_correlation_id(correlation_id)

        # Add to response headers
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id

        # Clean up
        clear_correlation_id()

        return response

    return correlation_middleware


# ============================================================================
# Log Formatting Helpers
# ============================================================================


def log_request_start(
    logger: logging.Logger, method: str, path: str, user_id: Optional[str] = None, **extra
):
    """Log the start of a request."""
    logger.info(
        "Request started", method=method, path=path, user_id=user_id, event="request_start", **extra
    )


def log_request_end(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    user_id: Optional[str] = None,
    **extra,
):
    """Log the end of a request."""
    logger.info(
        "Request completed",
        method=method,
        path=path,
        status_code=status_code,
        duration=duration,
        user_id=user_id,
        event="request_end",
        **extra,
    )


def log_error(
    logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None, **extra
):
    """Log an error with structured context."""
    context = context or {}
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        event="error",
        **context,
        **extra,
    )


def log_business_event(
    logger: logging.Logger,
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    user_id: Optional[str] = None,
    **extra,
):
    """Log business logic events."""
    logger.info(
        f"{event_type} {action}",
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        event="business_event",
        **extra,
    )


# ============================================================================
# Initialization Helper
# ============================================================================


def init_service_logging(
    service_name: str, level: str = "INFO", json_format: bool = False
) -> logging.Logger:
    """
    Initialize logging for a service with sensible defaults.

    Args:
        service_name: Name of the service
        level: Logging level
        json_format: Whether to use JSON formatting

    Returns:
        Configured logger for the service
    """
    configure_structlog(
        service_name=service_name,
        level=level,
        json_format=json_format,
        include_correlation_id=True,
        include_service_context=True,
    )

    return get_logger(service_name)


__all__ = [
    # Configuration
    "configure_structlog",
    "init_service_logging",
    # Logger factory
    "get_logger",
    # Context management
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "create_correlation_middleware",
    # Logging helpers
    "log_request_start",
    "log_request_end",
    "log_error",
    "log_business_event",
    # Constants
    "CONSTITUTIONAL_HASH",
]
