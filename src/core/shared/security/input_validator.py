"""
ACGS-2 Centralized Input Validation Framework
Constitutional Hash: cdd01ef066bc6cf2

Provides utilities for sanitizing input, preventing path traversal,
enforcing size limits, and detecting injection patterns.
"""

import logging
import re
from pathlib import Path
from typing import Any, List, Union

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Injection patterns
SQL_INJECTION_PATTERNS = [
    r"UNION\s+SELECT",
    r"SELECT\s+.*\s+FROM",
    r"INSERT\s+INTO",
    r"UPDATE\s+.*\s+SET",
    r"DELETE\s+FROM",
    r"DROP\s+TABLE",
    r"OR\s+['\"].*?['\"]\s*=\s*['\"].*?['\"]",
]

NOSQL_INJECTION_PATTERNS = [
    r"\$gt",
    r"\$lt",
    r"\$ne",
    r"\$in",
    r"\$nin",
    r"\$or",
    r"\$and",
]

XSS_PATTERNS = [
    r"<script.*?>",
    r"javascript:",
    r"on\w+\s*=",
]


class InputValidator:
    """Centralized input validation and sanitization."""

    @staticmethod
    def sanitize_string(text: str) -> str:
        """Basic string sanitization."""
        if not isinstance(text, str):
            return text
        # Remove null bytes
        text = text.replace("\x00", "")
        return text.strip()

    @staticmethod
    def validate_path(path_str: str, base_dir: Union[str, Path]) -> Path:
        """
        Prevent path traversal by ensuring the path is within base_dir.
        """
        base_path = Path(base_dir).resolve()
        target_path = Path(path_str).resolve()

        try:
            target_path.relative_to(base_path)
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {path_str} outside of {base_dir}")
            raise HTTPException(status_code=400, detail="Invalid path")

        return target_path

    @staticmethod
    def check_injection(text: str, patterns: List[str] = None) -> bool:
        """
        Check if text matches any injection patterns.
        """
        if not isinstance(text, str):
            return False

        if patterns is None:
            patterns = SQL_INJECTION_PATTERNS + NOSQL_INJECTION_PATTERNS + XSS_PATTERNS

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def enforce_size_limit(data: Any, max_bytes: int):
        """Enforce size limit on input data."""
        import sys

        if sys.getsizeof(data) > max_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")


async def validate_request_body(request: Request):
    """Middleware-style function to validate request body for injections."""
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
            if _contains_injection(body):
                logger.warning(f"Injection detected in request body from {request.client.host}")
                raise HTTPException(status_code=400, detail="Potential injection detected")
        except (ValueError, RuntimeError):
            pass  # Not a JSON body or already consumed


def _contains_injection(data: Any) -> bool:
    """Recursively check for injections in data structures."""
    if isinstance(data, str):
        return InputValidator.check_injection(data)
    elif isinstance(data, dict):
        return any(_contains_injection(v) for v in data.values())
    elif isinstance(data, list):
        return any(_contains_injection(item) for item in data)
    return False


__all__ = ["InputValidator", "validate_request_body"]
