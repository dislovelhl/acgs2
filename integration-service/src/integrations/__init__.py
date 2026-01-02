"""
ACGS-2 Integration Service - Integration Adapters

This module provides base classes and implementations for third-party integrations
including SIEM systems (Splunk, Microsoft Sentinel), ticketing platforms (Jira, ServiceNow),
and CI/CD pipelines (GitHub Actions, GitLab CI).
"""

from .base import (
    AuthenticationError,
    BaseIntegration,
    DeliveryError,
    IntegrationConnectionError,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationStatus,
    IntegrationType,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "BaseIntegration",
    "DeliveryError",
    "IntegrationConnectionError",
    "IntegrationCredentials",
    "IntegrationEvent",
    "IntegrationResult",
    "IntegrationStatus",
    "IntegrationType",
    "RateLimitError",
    "ValidationError",
]
