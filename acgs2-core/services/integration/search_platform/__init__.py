"""
Search Platform Integration for ACGS2

This module provides integration with the Universal Search Platform,
enabling high-performance code search, constitutional compliance checking,
and audit trail searching capabilities.

Constitutional Hash: cdd01ef066bc6cf2
"""

from .client import SearchPlatformClient, SearchPlatformConfig
from .models import (
    SearchRequest,
    SearchResponse,
    SearchMatch,
    SearchStats,
    SearchDomain,
    SearchScope,
    SearchOptions,
)
from .constitutional_search import ConstitutionalCodeSearchService
from .audit_search import AuditTrailSearchService

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
