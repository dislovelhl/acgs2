"""
ACGS-2 Structured Logging Module
Constitutional Hash: cdd01ef066bc6cf2

Provides standardized structured logging across all ACGS-2 services using structlog.
Includes correlation IDs, service context, and JSON formatting for observability.
"""

import logging
import sys
from contextvars import ContextVar
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
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if include_service_context:
        shared_processors.append(_add_service_context(service_name))

    # Configure structlog
    processors = shared_processors.copy()
    if include_correlation_id:
        processors.append(structlog.contextvars.merge_contextvars)
        processors.append(_add_otel_trace_id)

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # If you still need standard logging intercepted:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

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


def _add_otel_trace_id(logger, method_name, event_dict):
    """Add OpenTelemetry trace ID to log entries if available."""
    try:
        from .otel_config import get_current_trace_id

        trace_id = get_current_trace_id()
        if trace_id:
            event_dict["trace_id"] = trace_id
    except (ImportError, AttributeError):
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

# contextvars-based context storage for async-safe correlation ID binding
_correlation_id_context: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current request context."""
    _correlation_id_context.set(correlation_id)
    if HAS_STRUCTLOG:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID for the current request context."""
    return _correlation_id_context.get()


def clear_correlation_id() -> None:
    """Clear correlation ID for the current request context."""
    _correlation_id_context.set(None)


# ============================================================================
# FastAPI Integration
# ============================================================================


def create_correlation_middleware():
    """
    Create FastAPI middleware for correlation ID handling.

    Usage:
        from src.core.shared.acgs_structured_logging import create_correlation_middleware

        app = FastAPI()
        app.middleware("http")(create_correlation_middleware())
    """
    import uuid

    from fastapi import Request

    async def correlation_middleware(request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get("x-request-id")
            or request.headers.get("x-correlation-id")
            or str(uuid.uuid4())
        )

        # Set in structlog contextvars and our local contextvar
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        set_correlation_id(correlation_id)

        # Add to response headers
        response = await call_next(request)
        response.headers["x-request-id"] = correlation_id

        # Clean up
        clear_correlation_id()
        structlog.contextvars.clear_contextvars()

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
