"""
Linear (Linear.app) integration for ACGS2 governance events.

Provides integration with Linear for issue tracking and project management,
allowing governance events to be automatically converted to Linear issues.
"""

from .client import LinearClient
from .credentials import LinearCredentials

__all__ = ["LinearClient", "LinearCredentials"]
