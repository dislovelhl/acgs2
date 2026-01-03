"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals Service Configuration

Uses pydantic-settings for type-safe environment configuration.
Extends shared configuration with service-specific settings.
"""

import os
from typing import List, Optional

from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings

    class SettingsConfigDict(dict):
        pass


class HITLApprovalsSettings(BaseSettings):
    """HITL Approvals Service Settings."""

    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

    # Environment
    env: str = Field("development", validation_alias="APP_ENV")
    debug: bool = Field(False, validation_alias="APP_DEBUG")

    # Service Configuration
    hitl_approvals_port: int = Field(8003, validation_alias="HITL_APPROVALS_PORT")

    # CORS
    cors_origins: List[str] = Field(["*"], validation_alias="CORS_ORIGINS")

    # Redis Configuration (for escalation timers)
    redis_url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")

    # Kafka Configuration (for event streaming)
    kafka_bootstrap_servers: str = Field(
        "localhost:9092", validation_alias="KAFKA_BOOTSTRAP_SERVERS"
    )

    # OPA Configuration (for role-based routing)
    opa_url: str = Field("http://localhost:8181", validation_alias="OPA_URL")

    # Notification Integrations
    slack_webhook_url: Optional[str] = Field(None, validation_alias="SLACK_WEBHOOK_URL")
    ms_teams_webhook_url: Optional[str] = Field(None, validation_alias="MS_TEAMS_WEBHOOK_URL")
    pagerduty_routing_key: Optional[str] = Field(None, validation_alias="PAGERDUTY_ROUTING_KEY")

    # Escalation Policies
    default_escalation_timeout_minutes: int = Field(
        30, validation_alias="DEFAULT_ESCALATION_TIMEOUT_MINUTES"
    )
    critical_escalation_timeout_minutes: int = Field(
        15, validation_alias="CRITICAL_ESCALATION_TIMEOUT_MINUTES"
    )


if not HAS_PYDANTIC_SETTINGS:
    # Fallback implementation using os.getenv
    from dataclasses import dataclass, field

    @dataclass
    class HITLApprovalsSettings:
        """HITL Approvals Service Settings (fallback)."""

        env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
        debug: bool = field(
            default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true"
        )
        hitl_approvals_port: int = field(
            default_factory=lambda: int(os.getenv("HITL_APPROVALS_PORT", "8003"))
        )
        cors_origins: List[str] = field(
            default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
        )
        redis_url: str = field(
            default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        kafka_bootstrap_servers: str = field(
            default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        )
        opa_url: str = field(default_factory=lambda: os.getenv("OPA_URL", "http://localhost:8181"))
        slack_webhook_url: Optional[str] = field(
            default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL")
        )
        ms_teams_webhook_url: Optional[str] = field(
            default_factory=lambda: os.getenv("MS_TEAMS_WEBHOOK_URL")
        )
        pagerduty_routing_key: Optional[str] = field(
            default_factory=lambda: os.getenv("PAGERDUTY_ROUTING_KEY")
        )
        default_escalation_timeout_minutes: int = field(
            default_factory=lambda: int(os.getenv("DEFAULT_ESCALATION_TIMEOUT_MINUTES", "30"))
        )
        critical_escalation_timeout_minutes: int = field(
            default_factory=lambda: int(os.getenv("CRITICAL_ESCALATION_TIMEOUT_MINUTES", "15"))
        )


# Global settings instance
settings = HITLApprovalsSettings()
