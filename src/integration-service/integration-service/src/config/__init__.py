"""
Configuration models for integration settings.

Provides Pydantic models for configuring all third-party integrations
including SIEM (Splunk, Sentinel), ticketing (Jira, ServiceNow),
CI/CD (GitHub Actions, GitLab CI), webhooks, and Linear.
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
from .validation import ConfigValidationError, ConfigValidator, validate_integration_config

# Import Linear and Slack configs from the separate config.py file
try:
    import importlib.util
    from pathlib import Path

    # Load config.py from the src directory using importlib
    config_path = Path(__file__).parent.parent / "config.py"
    spec = importlib.util.spec_from_file_location("linear_config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    LinearConfig = config_module.LinearConfig
    SlackConfig = config_module.SlackConfig
    GitHubConfig = config_module.GitHubConfig
    GitLabConfig = config_module.GitLabConfig
    get_linear_config = config_module.get_linear_config
    get_slack_config = config_module.get_slack_config
    get_github_config = config_module.get_github_config
    get_gitlab_config = config_module.get_gitlab_config
    get_service_config = config_module.get_service_config
except (ImportError, AttributeError, FileNotFoundError):
    # If import fails, define placeholder classes
    LinearConfig = None
    SlackConfig = None
    GitHubConfig = None
    GitLabConfig = None
    get_linear_config = None
    get_slack_config = None
    get_github_config = None
    get_gitlab_config = None
    get_service_config = None

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
    # Linear and Slack configs
    "LinearConfig",
    "SlackConfig",
    "GitHubConfig",
    "GitLabConfig",
    "get_linear_config",
    "get_slack_config",
    "get_github_config",
    "get_gitlab_config",
    "get_service_config",
    # Validation
    "ConfigValidator",
    "ConfigValidationError",
    "validate_integration_config",
]
