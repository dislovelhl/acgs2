"""
PagerDuty Integration Models and Constants
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, SecretStr, field_validator, model_validator

from .base import EventSeverity, IntegrationCredentials, IntegrationType

logger = logging.getLogger(__name__)


class PagerDutyAuthType(str, Enum):
    """PagerDuty authentication types"""

    EVENTS_V2 = "events_v2"  # Events API v2 (integration_key)
    REST_API = "rest_api"  # REST API (api_token)
    BOTH = "both"  # Both authentication methods


# Default urgency mapping from ACGS-2 severity to PagerDuty urgency
# PagerDuty has only two urgency levels: high and low
DEFAULT_URGENCY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "high",
    EventSeverity.HIGH: "high",
    EventSeverity.MEDIUM: "low",
    EventSeverity.LOW: "low",
    EventSeverity.INFO: "low",
}

# PagerDuty severity levels (for the payload severity field)
# This is different from urgency - severity is for classification, urgency is for priority
DEFAULT_SEVERITY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "critical",
    EventSeverity.HIGH: "error",
    EventSeverity.MEDIUM: "warning",
    EventSeverity.LOW: "warning",
    EventSeverity.INFO: "info",
}


class PagerDutyCredentials(IntegrationCredentials):
    """
    Credentials for PagerDuty integration.
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.TICKETING,
        description="Integration type (always TICKETING for PagerDuty)",
    )

    # Authentication settings
    auth_type: PagerDutyAuthType = Field(
        default=PagerDutyAuthType.EVENTS_V2,
        description="Authentication type (events_v2, rest_api, or both)",
    )

    # Events API v2 credentials
    integration_key: Optional[SecretStr] = Field(
        None,
        description="PagerDuty Events API v2 integration key (routing key)",
    )

    # REST API credentials
    api_token: Optional[SecretStr] = Field(
        None,
        description="PagerDuty REST API token",
    )

    # Service configuration
    service_id: Optional[str] = Field(
        None,
        description="PagerDuty service ID (for REST API operations)",
    )
    escalation_policy: Optional[str] = Field(
        None,
        description="Default escalation policy ID or name",
    )

    # Incident configuration
    urgency_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to urgency mapping (severity -> 'high' or 'low')",
    )
    severity_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Custom severity to PagerDuty severity mapping "
            "(severity -> 'critical', 'error', 'warning', 'info')"
        ),
    )

    # Custom event fields
    custom_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom details to include in incident payloads",
    )
    default_source: str = Field(
        default="acgs2",
        description="Default source for incidents (e.g., 'acgs2', 'governance-platform')",
    )
    default_component: Optional[str] = Field(
        None,
        description="Default component for incidents",
    )
    default_group: Optional[str] = Field(
        None,
        description="Default logical grouping for incidents",
    )
    default_class: Optional[str] = Field(
        None,
        description="Default class/type for incidents",
    )

    # Incident content settings
    include_event_details: bool = Field(
        default=True,
        description="Include full event details in incident custom_details",
    )
    summary_template: str = Field(
        default="[ACGS-2] {title}",
        description="Template for incident summary (supports {title}, {event_type}, {severity})",
    )

    # Dedup key strategy
    dedup_key_prefix: str = Field(
        default="acgs2",
        description="Prefix for dedup_key generation (format: '{prefix}-{event_id}')",
    )

    @field_validator("integration_key", "api_token")
    @classmethod
    def validate_secret_fields(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validate secret fields are not empty strings."""
        if v is not None:
            secret_value = v.get_secret_value()
            if not secret_value or not secret_value.strip():
                raise ValueError("Secret field cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "PagerDutyCredentials":
        """Validate that appropriate credentials are provided for auth type."""
        if self.auth_type == PagerDutyAuthType.EVENTS_V2:
            if not self.integration_key:
                raise ValueError("integration_key is required for Events API v2 authentication")
        elif self.auth_type == PagerDutyAuthType.REST_API:
            if not self.api_token:
                raise ValueError("api_token is required for REST API authentication")
        elif self.auth_type == PagerDutyAuthType.BOTH:
            if not self.integration_key:
                raise ValueError(
                    "integration_key is required when using both authentication methods"
                )
            if not self.api_token:
                raise ValueError("api_token required when using both auth methods")

        # If using REST API, service_id should be provided for some operations
        if self.auth_type in (PagerDutyAuthType.REST_API, PagerDutyAuthType.BOTH):
            if not self.service_id:
                logger.warning("service_id not provided - some REST API operations may require it")

        return self

    @model_validator(mode="after")
    def validate_urgency_mapping(self) -> "PagerDutyCredentials":
        """Validate urgency mapping values are valid PagerDuty urgency levels."""
        valid_urgencies = {"high", "low"}
        for severity, urgency in self.urgency_mapping.items():
            if urgency not in valid_urgencies:
                raise ValueError(
                    f"Invalid urgency '{urgency}' for severity '{severity}'. "
                    f"Must be one of: {valid_urgencies}"
                )
        return self

    @model_validator(mode="after")
    def validate_severity_mapping(self) -> "PagerDutyCredentials":
        """Validate severity mapping values are valid PagerDuty severity levels."""
        valid_severities = {"critical", "error", "warning", "info"}
        for severity, pd_severity in self.severity_mapping.items():
            if pd_severity not in valid_severities:
                raise ValueError(
                    f"Invalid PagerDuty severity '{pd_severity}' for severity '{severity}'. "
                    f"Must be one of: {valid_severities}"
                )
        return self
