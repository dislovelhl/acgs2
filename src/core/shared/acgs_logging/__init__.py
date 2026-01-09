"""
ACGS-2 Logging Module
Constitutional Hash: cdd01ef066bc6cf2

Centralized logging utilities for the ACGS-2 platform:
- Tenant-scoped audit logging with access controls
- Structured logging for compliance and security
- Audit trail for multi-tenant operations
"""

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .audit_logger import (
    AUDIT_LOGGER_AVAILABLE,
    AuditAction,
    AuditEntry,
    AuditLogConfig,
    AuditLogStore,
    AuditQueryParams,
    AuditQueryResult,
    AuditSeverity,
    InMemoryAuditStore,
    RedisAuditStore,
    TenantAuditLogger,
    create_tenant_audit_logger,
    get_tenant_audit_logger,
)

# Context variable for correlation ID
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name. If None, returns root logger.

    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current context."""
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)


class StructuredLogger:
    """Wrapper for structured logging with JSON output."""

    def __init__(self, name: str, service: str, json_format: bool = True):
        self.name = name
        self.service = service
        self.json_format = json_format
        self._logger = logging.getLogger(name)

    def _log(self, level: str, event: str, **kwargs: Any) -> None:
        """Log a structured event."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": self.service,
            "event": event,
            **kwargs,
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            record["correlation_id"] = correlation_id

        if self.json_format:
            self._logger.debug(json.dumps(record))
        else:
            self._logger.log(getattr(logging, level), str(record))

    def info(self, event: str, **kwargs: Any) -> None:
        self._log("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log("ERROR", event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log("DEBUG", event, **kwargs)


def init_service_logging(
    service_name: str,
    level: str = "INFO",
    json_format: bool = True,
) -> StructuredLogger:
    """
    Initialize structured logging for a service.

    Args:
        service_name: Name of the service for log identification
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Whether to output logs in JSON format

    Returns:
        Configured StructuredLogger instance
    """
    logging.basicConfig(level=getattr(logging, level))
    return StructuredLogger(service_name, service_name, json_format)


def create_correlation_middleware() -> Callable:
    """
    Create a FastAPI middleware for correlation ID propagation.

    Returns:
        Middleware function for FastAPI
    """

    async def correlation_middleware(request: Any, call_next: Callable) -> Any:
        import uuid

        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            clear_correlation_id()

    return correlation_middleware



__all__ = [
    # Standard logger
    "get_logger",
    # Structured logging
    "init_service_logging",
    "StructuredLogger",
    # Correlation ID
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "create_correlation_middleware",
    # Main logger
    "TenantAuditLogger",
    "create_tenant_audit_logger",
    "get_tenant_audit_logger",
    # Configuration
    "AuditLogConfig",
    # Audit entries
    "AuditEntry",
    "AuditAction",
    "AuditSeverity",
    # Query
    "AuditQueryParams",
    "AuditQueryResult",
    # Storage backends
    "AuditLogStore",
    "InMemoryAuditStore",
    "RedisAuditStore",
    # Feature flags
    "AUDIT_LOGGER_AVAILABLE",
]
