"""
ACGS-2 Enhanced Agent Bus - Utilities
Constitutional Hash: cdd01ef066bc6cf2
"""

import re
from datetime import datetime, timezone
from typing import Any


def redact_error_message(error: Exception) -> str:
    """Redact sensitive information from error messages (VULN-008)."""
    error_msg = str(error)
    # Redact potential URLs/URIs
    redacted = re.sub(r'[a-zA-Z0-9+.-]+://[^\s<>"]+', "[REDACTED_URI]", error_msg)
    # Redact common credential patterns
    redacted = re.sub(
        r"(?i)(key|secret|token|password|auth|pwd)=[^ \b\n\r\t,;]+", r"\1=[REDACTED]", redacted
    )
    # Redact absolute file paths (Unix-style)
    redacted = re.sub(r"/(?:[a-zA-Z0-9._-]+/)+[a-zA-Z0-9._-]+", "[REDACTED_PATH]", redacted)
    return redacted


def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class LRUCache:
    """Simple LRU cache for validation results."""

    def __init__(self, maxsize: int = 1000):
        from collections import OrderedDict

        self._cache = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: Any) -> Any:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: Any, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()
