"""
ACGS-2 Middleware Package
Constitutional Hash: cdd01ef066bc6cf2

This package provides FastAPI middleware components for ACGS-2 services:
- Correlation ID injection and propagation for distributed tracing
- Request context management for structured logging

Modules:
    - correlation_id: Middleware for X-Request-ID header handling and context binding

Usage:
    from shared.middleware import CorrelationIdMiddleware, correlation_id_middleware

    # Option 1: Use as FastAPI middleware decorator
    @app.middleware("http")
    async def add_correlation_id(request, call_next):
        return await correlation_id_middleware(request, call_next)

    # Option 2: Use as class-based middleware
    app.add_middleware(CorrelationIdMiddleware, service_name="api_gateway")
"""

from .correlation_id import (
    CORRELATION_ID_HEADER,
    CorrelationIdMiddleware,
    add_correlation_id_middleware,
    correlation_id_middleware,
    get_correlation_id,
)

__all__ = [
    # Constants
    "CORRELATION_ID_HEADER",
    # Functions
    "correlation_id_middleware",
    "add_correlation_id_middleware",
    "get_correlation_id",
    # Classes
    "CorrelationIdMiddleware",
]
