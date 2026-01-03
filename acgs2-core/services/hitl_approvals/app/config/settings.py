"""
HITL Approvals Service Configuration
"""

from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationSettings(BaseSettings):
    """Notification provider configurations"""

    model_config = SettingsConfigDict(env_prefix="NOTIFICATION_", case_sensitive=False)

    # Slack
    slack_webhook_url: Optional[str] = Field(None, validation_alias="SLACK_WEBHOOK_URL")

    # Microsoft Teams
    ms_teams_webhook_url: Optional[str] = Field(None, validation_alias="MS_TEAMS_WEBHOOK_URL")

    # PagerDuty
    pagerduty_routing_key: Optional[str] = Field(None, validation_alias="PAGERDUTY_ROUTING_KEY")

    # Notification settings
    retry_attempts: int = Field(3, validation_alias="NOTIFICATION_RETRY_ATTEMPTS")
    retry_delay: float = Field(1.0, validation_alias="NOTIFICATION_RETRY_DELAY")


class EscalationSettings(BaseSettings):
    """Escalation policy configurations"""

    model_config = SettingsConfigDict(env_prefix="ESCALATION_", case_sensitive=False)

    # Default timeouts (minutes)
    default_timeout_minutes: int = Field(30, validation_alias="DEFAULT_ESCALATION_TIMEOUT_MINUTES")
    critical_timeout_minutes: int = Field(
        15, validation_alias="CRITICAL_ESCALATION_TIMEOUT_MINUTES"
    )
    emergency_timeout_minutes: int = Field(
        60, validation_alias="EMERGENCY_ESCALATION_TIMEOUT_MINUTES"
    )

    # Escalation levels
    max_levels: int = Field(5, validation_alias="MAX_ESCALATION_LEVELS")


class ApprovalChainSettings(BaseSettings):
    """Approval chain configurations"""

    model_config = SettingsConfigDict(env_prefix="APPROVAL_CHAIN_", case_sensitive=False)

    # Chain definitions
    chains: Dict[str, Any] = Field(default_factory=dict)

    # Default chain for unspecified types
    default_chain: str = Field("standard", validation_alias="DEFAULT_APPROVAL_CHAIN")


class HITLSettings(BaseSettings):
    """Main HITL Approvals service settings"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Service configuration
    service_name: str = "hitl-approvals"
    service_version: str = "1.0.0"
    port: int = Field(8003, validation_alias="HITL_APPROVALS_PORT")
    host: str = Field("0.0.0.0", validation_alias="HITL_APPROVALS_HOST")

    # Infrastructure
    redis_url: str = Field("redis://redis:6379/0", validation_alias="REDIS_URL")
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/hitl_approvals",
        validation_alias="DATABASE_URL",
    )
    kafka_bootstrap_servers: str = Field("kafka:29092", validation_alias="KAFKA_BOOTSTRAP_SERVERS")
    opa_url: str = Field("http://opa:8181", validation_alias="OPA_URL")

    # External service URLs
    agent_bus_url: str = Field("http://enhanced-agent-bus:8000", validation_alias="AGENT_BUS_URL")
    audit_service_url: str = Field(
        "http://audit-service:8080", validation_alias="AUDIT_SERVICE_URL"
    )

    # Security
    api_key: Optional[str] = Field(None, validation_alias="HITL_API_KEY")

    # Sub-settings
    notifications: NotificationSettings = NotificationSettings()
    escalation: EscalationSettings = EscalationSettings()
    approval_chains: ApprovalChainSettings = ApprovalChainSettings()

    # Environment
    environment: str = Field("development", validation_alias="ENVIRONMENT")
    debug: bool = Field(False, validation_alias="DEBUG")


# Global settings instance
settings = HITLSettings()
