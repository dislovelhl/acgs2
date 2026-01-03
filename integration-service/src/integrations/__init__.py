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
    EventSeverity,
    IntegrationConnectionError,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationStatus,
    IntegrationType,
    RateLimitError,
    ValidationError,
)
from .sentinel_adapter import (
    AzureCloud,
    SentinelAdapter,
    SentinelCredentials,
)
from .splunk_adapter import (
    SplunkAdapter,
    SplunkCredentials,
    SplunkDeploymentType,
)

__all__ = [
    # Base classes and models
    "AuthenticationError",
    "BaseIntegration",
    "DeliveryError",
    "EventSeverity",
    "IntegrationConnectionError",
    "IntegrationCredentials",
    "IntegrationEvent",
    "IntegrationResult",
    "IntegrationStatus",
    "IntegrationType",
    "RateLimitError",
    "ValidationError",
    # Splunk SIEM integration
    "SplunkAdapter",
    "SplunkCredentials",
    "SplunkDeploymentType",
    # Microsoft Sentinel SIEM integration
    "AzureCloud",
    "SentinelAdapter",
    "SentinelCredentials",
]
