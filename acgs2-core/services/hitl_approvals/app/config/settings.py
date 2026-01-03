"""
HITL Approvals Service Configuration
"""

from typing import Any, Dict, Optional

from pydantic import BaseSettings, Field


class NotificationSettings(BaseSettings):
    """Notification provider configurations"""

    # Slack
    slack_webhook_url: Optional[str] = Field(None, env="SLACK_WEBHOOK_URL")

    # Microsoft Teams
    ms_teams_webhook_url: Optional[str] = Field(None, env="MS_TEAMS_WEBHOOK_URL")

    # PagerDuty
    pagerduty_routing_key: Optional[str] = Field(None, env="PAGERDUTY_ROUTING_KEY")

    # Notification settings
    notification_retry_attempts: int = Field(3, env="NOTIFICATION_RETRY_ATTEMPTS")
    notification_retry_delay: float = Field(1.0, env="NOTIFICATION_RETRY_DELAY")


class EscalationSettings(BaseSettings):
    """Escalation policy configurations"""

    # Default timeouts (minutes)
    default_escalation_timeout_minutes: int = Field(30, env="DEFAULT_ESCALATION_TIMEOUT_MINUTES")
    critical_escalation_timeout_minutes: int = Field(15, env="CRITICAL_ESCALATION_TIMEOUT_MINUTES")
    emergency_escalation_timeout_minutes: int = Field(
        60, env="EMERGENCY_ESCALATION_TIMEOUT_MINUTES"
    )

    # Escalation levels
    max_escalation_levels: int = Field(5, env="MAX_ESCALATION_LEVELS")


class ApprovalChainSettings(BaseSettings):
    """Approval chain configurations"""

    # Chain definitions
    approval_chains: Dict[str, Any] = Field(default_factory=dict)

    # Default chain for unspecified types
    default_chain: str = Field("standard", env="DEFAULT_APPROVAL_CHAIN")


class HITLSettings(BaseSettings):
    """Main HITL Approvals service settings"""

    # Service configuration
    service_name: str = "hitl-approvals"
    service_version: str = "1.0.0"
    port: int = Field(8003, env="HITL_APPROVALS_PORT")
    host: str = Field("0.0.0.0", env="HITL_APPROVALS_HOST")

    # Infrastructure
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    kafka_bootstrap_servers: str = Field("kafka:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    opa_url: str = Field("http://opa:8181", env="OPA_URL")

    # External service URLs
    agent_bus_url: str = Field("http://enhanced-agent-bus:8000", env="AGENT_BUS_URL")
    audit_service_url: str = Field("http://audit-service:8080", env="AUDIT_SERVICE_URL")

    # Security
    api_key: Optional[str] = Field(None, env="HITL_API_KEY")

    # Sub-settings
    notifications: NotificationSettings = NotificationSettings()
    escalation: EscalationSettings = EscalationSettings()
    approval_chains: ApprovalChainSettings = ApprovalChainSettings()

    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = HITLSettings()
