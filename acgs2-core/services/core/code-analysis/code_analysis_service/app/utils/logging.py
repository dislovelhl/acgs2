"""
ACGS Code Analysis Engine - Structured Logging Utilities
Provides structured logging with constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import sys
from typing import Any, Optional

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ConstitutionalFormatter(logging.Formatter):
    """Custom formatter that includes constitutional hash."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "constitutional_hash"):
            record.constitutional_hash = CONSTITUTIONAL_HASH
        return super().format(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger with constitutional compliance."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = ConstitutionalFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger


def performance_logger(name: str = "performance") -> logging.Logger:
    """Get a logger for performance metrics."""
    return get_logger(f"acgs.{name}")


def log_api_request(
    method: str,
    path: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log an API request."""
    logger = get_logger("api.request")
    logger.info(
        f"API Request: {method} {path}",
        extra={
            "method": method,
            "path": path,
            "user_id": user_id,
            "request_id": request_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            **kwargs,
        },
    )


def log_api_response(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log an API response."""
    logger = get_logger("api.response")
    logger.info(
        f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "request_id": request_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            **kwargs,
        },
    )
