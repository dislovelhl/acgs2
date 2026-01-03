"""
ACGS-2 Structured Logging Configuration
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade structured logging with JSON formatting, correlation ID support,
and OpenTelemetry integration for distributed tracing.

This module provides:
    - JSON-formatted log output for enterprise observability (Splunk, ELK, Datadog)
    - Correlation ID binding via contextvars (async-safe)
    - OpenTelemetry trace ID integration
    - RFC 5424 severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Performance optimization with orjson serialization

Usage:
    from shared.logging_config import configure_logging, get_logger

    # Initialize at application startup (ONCE, before any logging)
    configure_logging(service_name="api_gateway")

    # Get a logger instance
    logger = get_logger(__name__)
    logger.info("user_authenticated", user_id=user.id, method="oauth2")

Example with FastAPI:
    app = FastAPI()
    configure_logging(service_name="api_gateway")
    logger = get_logger(__name__)

    @app.get("/")
    async def root():
        logger.info("request_received", endpoint="/")
        return {"status": "ok"}
"""

import logging
import os
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Try to import structlog - fall back to stdlib logging if unavailable
try:
    import structlog
    from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False
    structlog = None  # type: ignore[assignment]

# Try to import orjson for high-performance JSON serialization
try:
    import orjson

    def orjson_dumps(obj: Any, **kwargs: Any) -> str:
        """High-performance JSON serialization using orjson."""
        return orjson.dumps(obj, default=str).decode("utf-8")

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    orjson_dumps = None  # type: ignore[assignment]

# Try to import OpenTelemetry for distributed tracing
try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    trace = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    FastAPIInstrumentor = None  # type: ignore[assignment]


# Module-level state
_configured: bool = False
_service_name: str = "acgs2"

# Context variable for correlation ID (async-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def configure_logging(
    service_name: str = "acgs2",
    log_level: Optional[str] = None,
    json_format: bool = True,
    use_orjson: bool = True,
) -> None:
    """
    Initialize structlog with JSON output and correlation ID support.

    This function MUST be called ONCE at application startup, BEFORE any logger usage.
    Subsequent calls will be ignored to prevent reconfiguration.

    Args:
        service_name: Service identifier for log filtering (e.g., "api_gateway")
        log_level: Log level override. If None, reads from LOG_LEVEL env var (default: INFO)
        json_format: Whether to output JSON (True) or human-readable format (False)
        use_orjson: Whether to use orjson for JSON serialization (recommended for production)

    Environment Variables:
        LOG_LEVEL: Controls log verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        LOG_FORMAT: Set to "console" for human-readable output (default: "json")

    Example:
        # In FastAPI startup
        @app.on_event("startup")
        async def startup():
            configure_logging(service_name="api_gateway")
    """
    global _configured, _service_name

    if _configured:
        return

    _service_name = service_name

    # Determine log level from parameter or environment
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Check environment for format preference
    env_format = os.getenv("LOG_FORMAT", "json").lower()
    if env_format == "console":
        json_format = False

    # Map string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)

    if HAS_STRUCTLOG:
        _configure_structlog(
            service_name=service_name,
            numeric_level=numeric_level,
            json_format=json_format,
            use_orjson=use_orjson and HAS_ORJSON,
        )
    else:
        _configure_stdlib_logging(
            service_name=service_name,
            numeric_level=numeric_level,
            json_format=json_format,
        )

    _configured = True


def _configure_structlog(
    service_name: str,
    numeric_level: int,
    json_format: bool,
    use_orjson: bool,
) -> None:
    """Configure structlog with JSON output and correlation ID support."""
    # Build processor chain
    # CRITICAL: merge_contextvars MUST be first to enable correlation ID binding
    processors = [
        merge_contextvars,  # Enables async-safe correlation ID injection
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service_name,  # Custom processor to add service identifier
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        # Use orjson for production performance if available
        if use_orjson and HAS_ORJSON:
            processors.append(structlog.processors.JSONRenderer(serializer=orjson_dumps))
        else:
            processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable console output for local development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,  # Performance optimization
    )


def _configure_stdlib_logging(
    service_name: str,
    numeric_level: int,
    json_format: bool,
) -> None:
    """Fallback configuration using stdlib logging when structlog is unavailable."""
    import json

    class JSONFormatter(logging.Formatter):
        """JSON formatter for stdlib logging."""

        def format(self, record: logging.LogRecord) -> str:
            log_entry = {
                "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": service_name,
            }

            # Add correlation ID if available
            corr_id = correlation_id_var.get()
            if corr_id:
                log_entry["correlation_id"] = corr_id

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_entry, default=str)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s"
            )
        )

    root_logger.addHandler(handler)


def _add_service_name(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Structlog processor to add service name to all log entries."""
    event_dict["service"] = _service_name
    return event_dict


def get_logger(name: str) -> Any:
    """
    Get a logger instance for the given module name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance (structlog or stdlib)

    Example:
        logger = get_logger(__name__)
        logger.info("operation_completed", duration_ms=150)
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


def bind_correlation_id(correlation_id: str, trace_id: Optional[str] = None) -> None:
    """
    Bind correlation ID to the current async context.

    This function should be called in request middleware to associate
    all subsequent logs with the request's correlation ID.

    Args:
        correlation_id: Unique request identifier (from X-Request-ID header or generated UUID)
        trace_id: Optional OpenTelemetry trace ID for distributed tracing correlation

    Example:
        @app.middleware("http")
        async def correlation_id_middleware(request, call_next):
            correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            bind_correlation_id(correlation_id)
            response = await call_next(request)
            return response
    """
    if HAS_STRUCTLOG:
        context = {"correlation_id": correlation_id}
        if trace_id:
            context["trace_id"] = trace_id
        bind_contextvars(**context)

    # Also set in ContextVar for stdlib logging fallback
    correlation_id_var.set(correlation_id)


def clear_correlation_context() -> None:
    """
    Clear correlation context at the start of a new request.

    This MUST be called at the beginning of each request to prevent
    context leakage between requests.

    Example:
        @app.middleware("http")
        async def correlation_id_middleware(request, call_next):
            clear_correlation_context()
            # ... bind new correlation ID
    """
    if HAS_STRUCTLOG:
        clear_contextvars()
    correlation_id_var.set(None)


def get_current_trace_id() -> Optional[str]:
    """
    Get the current OpenTelemetry trace ID if available.

    Returns:
        32-character hex trace ID string, or None if tracing is not active.
    """
    if not HAS_OPENTELEMETRY or trace is None:
        return None

    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().trace_id, "032x")
    return None


def setup_opentelemetry(service_name: str) -> None:
    """
    Initialize OpenTelemetry TracerProvider for distributed tracing.

    This function should be called ONCE at application startup, BEFORE
    any tracing operations. For gunicorn/uwsgi deployments, call this
    in the post_fork hook.

    Args:
        service_name: Service identifier for trace spans

    Example:
        # In FastAPI startup
        @app.on_event("startup")
        async def startup():
            setup_opentelemetry("api_gateway")
    """
    if not HAS_OPENTELEMETRY:
        return

    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)


def instrument_fastapi(app: Any) -> None:
    """
    Auto-instrument a FastAPI application with OpenTelemetry.

    This adds automatic span creation for all HTTP requests and
    propagates trace context through the application.

    Args:
        app: FastAPI application instance

    Example:
        app = FastAPI()
        setup_opentelemetry("api_gateway")
        instrument_fastapi(app)
    """
    if not HAS_OPENTELEMETRY or FastAPIInstrumentor is None:
        return

    FastAPIInstrumentor().instrument_app(app)


# Convenience function for logging errors with exception info
def log_error(
    logger: Any,
    event: str,
    error: Optional[Exception] = None,
    **context: Any,
) -> None:
    """
    Log an error with optional exception information.

    Args:
        logger: Logger instance from get_logger()
        event: Event name describing the error
        error: Optional exception to include with stack trace
        **context: Additional context fields

    Example:
        try:
            process_payment(order_id)
        except Exception as e:
            log_error(logger, "payment_failed", error=e, order_id=order_id)
    """
    if error:
        logger.error(event, exc_info=True, error_type=type(error).__name__, **context)
    else:
        logger.error(event, **context)


# Convenience function for logging success with structured data
def log_success(
    logger: Any,
    event: str,
    **context: Any,
) -> None:
    """
    Log a successful operation with structured context.

    Args:
        logger: Logger instance from get_logger()
        event: Event name describing the success
        **context: Additional context fields

    Example:
        log_success(logger, "user_created", user_id=new_user.id, method="oauth")
    """
    logger.info(event, success=True, **context)


# Export public API
__all__ = [
    # Core configuration
    "configure_logging",
    "get_logger",
    # Correlation ID management
    "bind_correlation_id",
    "clear_correlation_context",
    "correlation_id_var",
    # OpenTelemetry integration
    "setup_opentelemetry",
    "instrument_fastapi",
    "get_current_trace_id",
    # Convenience functions
    "log_error",
    "log_success",
    # Feature flags
    "HAS_STRUCTLOG",
    "HAS_OPENTELEMETRY",
    "HAS_ORJSON",
]
