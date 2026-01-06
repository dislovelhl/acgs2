"""
Linear (Linear.app) integration for ACGS2 governance events.

Provides integration with Linear for issue tracking and project management,
allowing governance events to be automatically converted to Linear issues.
"""

from .client import (
    LinearAuthenticationError,
    LinearClient,
    LinearClientError,
    LinearNotFoundError,
    LinearRateLimitError,
    LinearValidationError,
)
from .credentials import LinearCredentials

__all__ = [
    "LinearAuthenticationError",
    "LinearClient",
    "LinearClientError",
    "LinearNotFoundError",
    "LinearRateLimitError",
    "LinearValidationError",
    "LinearCredentials",
]
