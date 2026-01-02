"""
Configuration models for integration settings.

Provides Pydantic models for configuring all third-party integrations
including SIEM (Splunk, Sentinel), ticketing (Jira, ServiceNow),
CI/CD (GitHub Actions, GitLab CI), and webhooks.
"""

from .models import (
    BaseIntegrationConfig,
    CICDIntegrationConfig,
    GitHubActionsConfig,
    GitLabCIConfig,
    IntegrationConfig,
    JiraConfig,
    RetryConfig,
    SentinelConfig,
    ServiceNowConfig,
    SIEMIntegrationConfig,
    SplunkConfig,
    TicketingIntegrationConfig,
    WebhookConfig,
)
from .validation import (
    ConfigValidationError,
    ConfigValidator,
    validate_integration_config,
)

__all__ = [
    # Base configs
    "IntegrationConfig",
    "BaseIntegrationConfig",
    "RetryConfig",
    # SIEM configs
    "SIEMIntegrationConfig",
    "SplunkConfig",
    "SentinelConfig",
    # Ticketing configs
    "TicketingIntegrationConfig",
    "JiraConfig",
    "ServiceNowConfig",
    # CI/CD configs
    "CICDIntegrationConfig",
    "GitHubActionsConfig",
    "GitLabCIConfig",
    # Webhook config
    "WebhookConfig",
    # Validation
    "ConfigValidator",
    "ConfigValidationError",
    "validate_integration_config",
]
