"""
Linear integration configuration using pydantic-settings.

Loads Linear API credentials and settings from environment variables
with type validation and secure credential handling.
"""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LinearConfig(BaseSettings):
    """
    Configuration for Linear integration.

    Loads Linear API credentials and settings from environment variables.
    All sensitive fields (API keys, secrets) use SecretStr for secure handling.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Authentication
    linear_api_key: SecretStr = Field(
        ...,
        description="Linear API key (get from Linear Settings > API)",
        json_schema_extra={"env": "LINEAR_API_KEY"},
    )

    linear_webhook_secret: SecretStr = Field(
        ...,
        description="Secret for verifying Linear webhook signatures (HMAC-SHA256)",
        json_schema_extra={"env": "LINEAR_WEBHOOK_SECRET"},
    )

    # Linear team and project settings
    linear_team_id: str = Field(
        ...,
        description="Default Linear team ID for issue creation",
        json_schema_extra={"env": "LINEAR_TEAM_ID"},
    )

    linear_project_id: Optional[str] = Field(
        default=None,
        description="Optional default Linear project ID",
        json_schema_extra={"env": "LINEAR_PROJECT_ID"},
    )

    # Linear API endpoint
    linear_api_url: str = Field(
        default="https://api.linear.app/graphql",
        description="Linear GraphQL API endpoint",
        json_schema_extra={"env": "LINEAR_API_URL"},
    )

    # Request timeout and retry settings
    linear_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Request timeout for Linear API calls in seconds",
        json_schema_extra={"env": "LINEAR_TIMEOUT_SECONDS"},
    )

    linear_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed Linear API calls",
        json_schema_extra={"env": "LINEAR_MAX_RETRIES"},
    )


class SlackConfig(BaseSettings):
    """
    Configuration for Slack integration (used for Linear notifications).

    Loads Slack credentials and settings from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Authentication
    slack_bot_token: Optional[SecretStr] = Field(
        default=None,
        description="Slack Bot User OAuth Token (starts with xoxb-)",
        json_schema_extra={"env": "SLACK_BOT_TOKEN"},
    )

    slack_signing_secret: Optional[SecretStr] = Field(
        default=None,
        description="Slack app signing secret for webhook verification",
        json_schema_extra={"env": "SLACK_SIGNING_SECRET"},
    )

    # Channel settings
    slack_default_channel: Optional[str] = Field(
        default=None,
        description="Default Slack channel ID for Linear notifications",
        json_schema_extra={"env": "SLACK_DEFAULT_CHANNEL"},
    )

    # Request settings
    slack_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Request timeout for Slack API calls in seconds",
        json_schema_extra={"env": "SLACK_TIMEOUT_SECONDS"},
    )

    @property
    def is_configured(self) -> bool:
        """Check if Slack integration is properly configured."""
        return self.slack_bot_token is not None and self.slack_signing_secret is not None


class IntegrationServiceConfig(BaseSettings):
    """
    Main configuration for the Integration Service.

    Aggregates all integration configurations and common settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Common settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for state tracking and caching",
        json_schema_extra={"env": "REDIS_URL"},
    )

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers for event streaming",
        json_schema_extra={"env": "KAFKA_BOOTSTRAP_SERVERS"},
    )

    # Webhook settings
    webhook_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for webhook deliveries",
        json_schema_extra={"env": "WEBHOOK_MAX_RETRIES"},
    )

    webhook_retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial delay between webhook retry attempts",
        json_schema_extra={"env": "WEBHOOK_RETRY_DELAY_SECONDS"},
    )

    webhook_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for webhook responses",
        json_schema_extra={"env": "WEBHOOK_TIMEOUT_SECONDS"},
    )

    # Security
    credential_encryption_key: Optional[SecretStr] = Field(
        default=None,
        description="32-byte hex key for encrypting stored credentials",
        json_schema_extra={"env": "CREDENTIAL_ENCRYPTION_KEY"},
    )

    jwt_secret: Optional[SecretStr] = Field(
        default=None,
        description="Secret key for JWT token signing",
        json_schema_extra={"env": "JWT_SECRET"},
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
        json_schema_extra={"env": "JWT_ALGORITHM"},
    )

    jwt_expiration_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="JWT token expiration time in hours",
        json_schema_extra={"env": "JWT_EXPIRATION_HOURS"},
    )


# Singleton instances for easy access
_linear_config: Optional[LinearConfig] = None
_slack_config: Optional[SlackConfig] = None
_service_config: Optional[IntegrationServiceConfig] = None


def get_linear_config() -> LinearConfig:
    """
    Get the Linear configuration singleton.

    Returns:
        LinearConfig: Configured Linear integration settings

    Raises:
        ValidationError: If required environment variables are missing or invalid
    """
    global _linear_config
    if _linear_config is None:
        _linear_config = LinearConfig()
    return _linear_config


def get_slack_config() -> SlackConfig:
    """
    Get the Slack configuration singleton.

    Returns:
        SlackConfig: Configured Slack integration settings
    """
    global _slack_config
    if _slack_config is None:
        _slack_config = SlackConfig()
    return _slack_config


def get_service_config() -> IntegrationServiceConfig:
    """
    Get the Integration Service configuration singleton.

    Returns:
        IntegrationServiceConfig: Common service configuration settings
    """
    global _service_config
    if _service_config is None:
        _service_config = IntegrationServiceConfig()
    return _service_config


# Convenience function to reset singletons (useful for testing)
def reset_config():
    """Reset all configuration singletons. Useful for testing."""
    global _linear_config, _slack_config, _service_config
    _linear_config = None
    _slack_config = None
    _service_config = None
