"""
Search Platform Integration for ACGS2

This module provides integration with the Universal Search Platform,
enabling high-performance code search, constitutional compliance checking,
and audit trail searching capabilities.

Constitutional Hash: cdd01ef066bc6cf2
"""

from .audit_search import AuditTrailSearchService
from .client import SearchPlatformClient, SearchPlatformConfig
from .constitutional_search import ConstitutionalCodeSearchService
from .models import (
    SearchDomain,
    SearchMatch,
    SearchOptions,
    SearchRequest,
    SearchResponse,
    SearchScope,
    SearchStats,
)

__all__ = [
    # Client
    "SearchPlatformClient",
    "SearchPlatformConfig",
    # Models
    "SearchRequest",
    "SearchResponse",
    "SearchMatch",
    "SearchStats",
    "SearchDomain",
    "SearchScope",
    "SearchOptions",
    # Services
    "ConstitutionalCodeSearchService",
    "AuditTrailSearchService",
]

__version__ = "1.0.0"
