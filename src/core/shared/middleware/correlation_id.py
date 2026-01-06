"""
ACGS-2 Correlation ID Middleware
Constitutional Hash: cdd01ef066bc6cf2

FastAPI middleware for injecting and propagating correlation IDs across services.
This enables distributed tracing by ensuring every request has a unique identifier
that appears in all logs and is propagated via HTTP headers.

Features:
    - Extracts X-Request-ID from incoming requests or generates UUID if missing
    - Integrates with OpenTelemetry trace IDs for observability correlation
    - Binds correlation ID to structlog context (async-safe via contextvars)
    - Propagates correlation ID in response headers for client-side tracing
    - Clears context between requests to prevent leakage

Usage:
    from src.core.shared.middleware.correlation_id import correlation_id_middleware

    # As decorator
    @app.middleware("http")
    async def add_correlation_id(request, call_next):
        return await correlation_id_middleware(request, call_next)

    # Or use the class-based middleware
    from src.core.shared.middleware.correlation_id import CorrelationIdMiddleware
    app.add_middleware(CorrelationIdMiddleware, service_name="api_gateway")

    # Or use the convenience function
    from src.core.shared.middleware.correlation_id import add_correlation_id_middleware
    add_correlation_id_middleware(app, service_name="api_gateway")
"""

import uuid
from typing import Any, Callable, Optional

from src.core.shared.acgs_logging_config import (
    bind_correlation_id,
    clear_correlation_context,
    get_current_trace_id,
    get_logger,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Header name for correlation ID (follows common conventions)
CORRELATION_ID_HEADER = "X-Request-ID"

# Alternative header names that may be used by different systems
ALTERNATIVE_HEADERS = [
    "X-Correlation-ID",
    "X-Trace-ID",
    "Request-Id",
]

# Module-level logger
logger = get_logger(__name__)


def get_correlation_id(request: Request) -> str:
    """
    Extract correlation ID from request headers or generate a new one.

    Checks the primary X-Request-ID header first, then falls back to
    alternative header names for compatibility with various tracing systems.

    Args:
        request: FastAPI/Starlette request object

    Returns:
        Correlation ID string (either extracted or newly generated UUID)
    """
    # Try primary header first
    correlation_id = request.headers.get(CORRELATION_ID_HEADER)

    # Fall back to alternative headers
    if not correlation_id:
        for header in ALTERNATIVE_HEADERS:
            correlation_id = request.headers.get(header)
            if correlation_id:
                break

    # Generate new UUID if no header found
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        logger.debug(
            "correlation_id_generated",
            correlation_id=correlation_id,
            path=str(request.url.path),
        )

    return correlation_id


async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Any],
    service_name: Optional[str] = None,
) -> Response:
    """
    FastAPI middleware function for correlation ID injection and propagation.

    This middleware should be registered EARLY in the middleware stack,
    before any other middleware that performs logging.

    Args:
        request: FastAPI/Starlette request object
        call_next: Next middleware or route handler
        service_name: Optional service identifier for logs

    Returns:
        Response with X-Request-ID header set

    Example:
        @app.middleware("http")
        async def add_correlation_id(request, call_next):
            return await correlation_id_middleware(request, call_next, "api_gateway")
    """
    # Clear previous request context to prevent leakage
    clear_correlation_context()

    # Extract or generate correlation ID
    correlation_id = get_correlation_id(request)

    # Get OpenTelemetry trace ID if available
    trace_id = get_current_trace_id()

    # Build context for logging
    log_context = {"correlation_id": correlation_id}
    if trace_id:
        log_context["trace_id"] = trace_id
    if service_name:
        log_context["service"] = service_name

    # Bind to structlog context (async-safe via contextvars)
    bind_correlation_id(correlation_id, trace_id=trace_id)

    # Log request received (DEBUG level to avoid log spam)
    logger.debug(
        "request_received",
        method=request.method,
        path=str(request.url.path),
        **log_context,
    )

    try:
        # Process request
        response = await call_next(request)

        # Log request completed
        logger.debug(
            "request_completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            **log_context,
        )

    except Exception as exc:
        # Log exception with correlation ID for tracing
        logger.error(
            "request_failed",
            method=request.method,
            path=str(request.url.path),
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
            **log_context,
        )
        raise

    # Propagate correlation ID in response headers
    response.headers[CORRELATION_ID_HEADER] = correlation_id

    return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Class-based middleware for correlation ID injection and propagation.

    This provides an alternative to the function-based middleware for
    cases where class-based middleware is preferred.

    Args:
        app: FastAPI/Starlette application
        service_name: Service identifier for logs

    Usage:
        app.add_middleware(CorrelationIdMiddleware, service_name="api_gateway")
    """

    def __init__(self, app: Any, service_name: Optional[str] = None):
        """
        Initialize the correlation ID middleware.

        Args:
            app: FastAPI/Starlette application
            service_name: Service identifier for logs
        """
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with correlation ID handling.

        Args:
            request: FastAPI/Starlette request object
            call_next: Next middleware or route handler

        Returns:
            Response with X-Request-ID header set
        """
        return await correlation_id_middleware(
            request,
            call_next,
            service_name=self.service_name,
        )


def add_correlation_id_middleware(
    app: Any,
    service_name: Optional[str] = None,
) -> None:
    """
    Convenience function to add correlation ID middleware to a FastAPI app.

    This registers the middleware at the appropriate position in the
    middleware stack (should be called early, before other middleware).

    Args:
        app: FastAPI application instance
        service_name: Service identifier for logs

    Example:
        from fastapi import FastAPI
        from src.core.shared.middleware.correlation_id import add_correlation_id_middleware

        app = FastAPI()
        add_correlation_id_middleware(app, service_name="api_gateway")
    """
    app.add_middleware(CorrelationIdMiddleware, service_name=service_name)
    logger.info(
        "correlation_id_middleware_registered",
        service_name=service_name or "unknown",
    )


# Export public API
__all__ = [
    # Constants
    "CORRELATION_ID_HEADER",
    "ALTERNATIVE_HEADERS",
    # Functions
    "get_correlation_id",
    "correlation_id_middleware",
    "add_correlation_id_middleware",
    # Classes
    "CorrelationIdMiddleware",
]
