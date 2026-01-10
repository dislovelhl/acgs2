"""
Pydantic configuration models for integration settings.

Defines configuration schemas for all supported integrations with
validation, sensible defaults, and secure credential handling.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional, Union
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from ..integration_types import ValidatorValue


class AuthType(str, Enum):
    """Authentication types supported by integrations."""

    API_KEY = "api_key"
    API_TOKEN = "api_token"  # nosec B105 - Not a hardcoded password, just an enum value
    BASIC = "basic"
    OAUTH2 = "oauth2"
    BEARER = "bearer"
    HMAC = "hmac"
    SERVICE_PRINCIPAL = "service_principal"


class IntegrationState(str, Enum):
    """State of an integration configuration."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    PENDING = "pending"
    ERROR = "error"


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    initial_delay_seconds: float = Field(
        default=1.0, ge=0.1, le=60, description="Initial delay between retries"
    )
    max_delay_seconds: float = Field(
        default=60.0, ge=1, le=600, description="Maximum delay between retries"
    )
    exponential_base: float = Field(
        default=2.0, ge=1.5, le=4.0, description="Exponential backoff multiplier"
    )
    retry_on_status_codes: List[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes to retry on",
    )

    model_config = ConfigDict(frozen=True)


class BaseIntegrationConfig(BaseModel):
    """Base configuration model for all integrations."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this integration configuration",
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the integration"
    )
    enabled: bool = Field(default=False, description="Whether the integration is enabled")
    state: IntegrationState = Field(
        default=IntegrationState.DISABLED, description="Current state of the integration"
    )

    # Common settings
    timeout_seconds: float = Field(
        default=30.0, ge=1.0, le=300.0, description="Request timeout in seconds"
    )
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig, description="Retry configuration"
    )

    # Metadata
    description: Optional[str] = Field(
        None, max_length=1000, description="Description of this integration instance"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Configuration creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Configuration last update timestamp",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: ValidatorValue) -> List[str]:
        """Ensure tags is a list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


# SIEM Configurations


class SIEMIntegrationConfig(BaseIntegrationConfig):
    """Base configuration for SIEM integrations."""

    integration_type: Literal["siem"] = "siem"
    batch_size: int = Field(default=100, ge=1, le=1000, description="Maximum events per batch")
    batch_timeout_seconds: float = Field(
        default=5.0, ge=1.0, le=60.0, description="Timeout to wait before sending batch"
    )
    source_type: str = Field(
        default="governance:event", description="Source type for SIEM categorization"
    )


class SplunkConfig(SIEMIntegrationConfig):
    """Configuration for Splunk HEC integration."""

    provider: Literal["splunk"] = "splunk"

    # Connection settings
    host: str = Field(..., description="Splunk host (without protocol)")
    port: int = Field(default=8088, ge=1, le=65535, description="HEC port (default 8088)")
    use_ssl: bool = Field(default=True, description="Use HTTPS for HEC connection")
    verify_ssl: bool = Field(
        default=True, description="Verify SSL certificates (set False for self-signed)"
    )

    # Authentication
    hec_token: SecretStr = Field(..., description="HTTP Event Collector token")

    # Event settings
    index: str = Field(default="main", description="Target Splunk index (must exist)")
    source: str = Field(default="acgs2", description="Event source identifier")
    host_field: str = Field(default="integration-service", description="Host field value in events")

    # Cloud vs On-Premise
    is_cloud: bool = Field(default=False, description="Whether this is Splunk Cloud (affects auth)")

    @property
    def hec_url(self) -> str:
        """Construct the HEC endpoint URL."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}/services/collector/event"

    @field_validator("host", mode="before")
    @classmethod
    def strip_protocol(cls, v: str) -> str:
        """Remove protocol prefix if present."""
        if v.startswith("https://"):
            return v[8:]
        if v.startswith("http://"):
            return v[7:]
        return v


class SentinelConfig(SIEMIntegrationConfig):
    """Configuration for Microsoft Sentinel/Azure Monitor integration."""

    provider: Literal["sentinel"] = "sentinel"

    # Azure identity
    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field(..., description="Service principal client ID")
    client_secret: SecretStr = Field(..., description="Service principal secret")

    # Data Collection settings
    dce_endpoint: str = Field(
        ...,
        description="Data Collection Endpoint URL (https://<name>.<region>.ingest.monitor.azure.com)",
    )
    dcr_immutable_id: str = Field(..., description="Data Collection Rule immutable ID")
    stream_name: str = Field(
        default="Custom-GovernanceEvents_CL",
        description="Log Analytics stream name (must match DCR schema)",
    )

    # Azure Cloud settings
    azure_cloud: Literal["public", "china", "germany", "government"] = Field(
        default="public", description="Azure cloud environment"
    )

    @field_validator("dce_endpoint", mode="before")
    @classmethod
    def validate_dce_endpoint(cls, v: str) -> str:
        """Validate DCE endpoint format."""
        if not v.startswith("https://"):
            raise ValueError("DCE endpoint must use HTTPS")
        if not v.endswith(".ingest.monitor.azure.com"):
            raise ValueError("DCE endpoint must end with .ingest.monitor.azure.com")
        return v


# Ticketing Configurations


class TicketingIntegrationConfig(BaseIntegrationConfig):
    """Base configuration for ticketing integrations."""

    integration_type: Literal["ticketing"] = "ticketing"
    default_priority: str = Field(default="medium", description="Default ticket priority")
    auto_create_tickets: bool = Field(
        default=True, description="Automatically create tickets for events"
    )
    severity_priority_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "critical": "highest",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "lowest",
        },
        description="Map event severity to ticket priority",
    )


class JiraConfig(TicketingIntegrationConfig):
    """Configuration for Jira integration."""

    provider: Literal["jira"] = "jira"

    # Connection
    base_url: str = Field(
        ..., description="Jira base URL (e.g., https://your-domain.atlassian.net)"
    )

    # Authentication - Cloud uses API token, Server uses different methods
    auth_type: Literal["api_token", "oauth2", "personal_access_token"] = Field(
        default="api_token", description="Authentication method"
    )
    user_email: Optional[str] = Field(
        None, description="User email for API token auth (Jira Cloud)"
    )
    api_token: Optional[SecretStr] = Field(None, description="API token for authentication")
    personal_access_token: Optional[SecretStr] = Field(
        None, description="Personal Access Token (Jira Server/Data Center)"
    )

    # Project settings
    project_key: str = Field(..., description="Default Jira project key")
    issue_type: str = Field(default="Bug", description="Default issue type")
    labels: List[str] = Field(
        default_factory=lambda: ["governance", "acgs2"],
        description="Labels to add to created issues",
    )

    # Field mappings
    custom_fields: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom field mappings (field_id -> value or template)",
    )

    # Cloud vs Server
    is_cloud: bool = Field(
        default=True, description="Whether this is Jira Cloud (affects auth and API)"
    )

    @model_validator(mode="after")
    def validate_auth_config(self) -> "JiraConfig":
        """Validate authentication configuration."""
        if self.auth_type == "api_token":
            if not self.user_email or not self.api_token:
                raise ValueError("user_email and api_token required for api_token auth")
        elif self.auth_type == "personal_access_token":
            if not self.personal_access_token:
                raise ValueError("personal_access_token required for PAT auth")
        return self

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v.rstrip("/")


class ServiceNowConfig(TicketingIntegrationConfig):
    """Configuration for ServiceNow integration."""

    provider: Literal["servicenow"] = "servicenow"

    # Connection
    instance: str = Field(
        ..., description="ServiceNow instance URL (e.g., https://your-instance.service-now.com)"
    )

    # Authentication
    auth_type: Literal["basic", "oauth2"] = Field(
        default="basic", description="Authentication method"
    )
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[SecretStr] = Field(None, description="Password for basic auth")
    client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    client_secret: Optional[SecretStr] = Field(None, description="OAuth2 client secret")

    # Incident settings
    table_name: str = Field(default="incident", description="Target table for tickets")
    category: str = Field(default="Governance", description="Default category")
    subcategory: str = Field(default="Policy Violation", description="Default subcategory")
    impact: str = Field(default="2", description="Default impact level (1-3)")
    urgency: str = Field(default="2", description="Default urgency level (1-3)")

    # Field mappings
    additional_fields: Dict[str, str] = Field(
        default_factory=dict, description="Additional fields to set on incidents"
    )

    @model_validator(mode="after")
    def validate_auth_config(self) -> "ServiceNowConfig":
        """Validate authentication configuration."""
        if self.auth_type == "basic":
            if not self.username or not self.password:
                raise ValueError("username and password required for basic auth")
        elif self.auth_type == "oauth2":
            if not self.client_id or not self.client_secret:
                raise ValueError("client_id and client_secret required for OAuth2")
        return self

    @field_validator("instance", mode="before")
    @classmethod
    def validate_instance(cls, v: str) -> str:
        """Validate and normalize instance URL."""
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v.rstrip("/")


# CI/CD Configurations


class CICDIntegrationConfig(BaseIntegrationConfig):
    """Base configuration for CI/CD integrations."""

    integration_type: Literal["cicd"] = "cicd"
    fail_on_violation: bool = Field(default=True, description="Fail pipeline on policy violation")
    severity_threshold: str = Field(
        default="medium",
        description="Minimum severity to fail pipeline (critical, high, medium, low)",
    )
    include_annotations: bool = Field(
        default=True, description="Include violation details as annotations/comments"
    )


class GitHubActionsConfig(CICDIntegrationConfig):
    """Configuration for GitHub Actions integration."""

    provider: Literal["github"] = "github"

    # Authentication
    token: SecretStr = Field(..., description="GitHub Personal Access Token or App token")
    app_id: Optional[str] = Field(None, description="GitHub App ID (if using app authentication)")
    app_private_key: Optional[SecretStr] = Field(None, description="GitHub App private key")

    # Repository settings
    owner: Optional[str] = Field(None, description="Repository owner/organization")
    repo: Optional[str] = Field(None, description="Repository name")

    # API settings
    api_url: str = Field(
        default="https://api.github.com",
        description="GitHub API URL (change for Enterprise)",
    )

    # Action settings
    check_name: str = Field(default="ACGS2 Policy Check", description="Name of the check to create")
    status_context: str = Field(
        default="acgs2/policy-validation", description="Status context for commits"
    )


class GitLabCIConfig(CICDIntegrationConfig):
    """Configuration for GitLab CI integration."""

    provider: Literal["gitlab"] = "gitlab"

    # Authentication
    token: SecretStr = Field(..., description="GitLab access token")
    token_type: Literal["personal", "project", "group"] = Field(
        default="personal", description="Type of access token"
    )

    # GitLab settings
    api_url: str = Field(
        default="https://gitlab.com",
        description="GitLab API URL (change for self-hosted)",
    )
    project_id: Optional[str] = Field(
        None, description="GitLab project ID or path (e.g., 'group/project')"
    )

    # Pipeline settings
    job_name: str = Field(default="acgs2-policy-check", description="Name of the policy check job")
    allow_failure: bool = Field(
        default=False, description="Allow job failure without blocking pipeline"
    )


# Webhook Configuration


class WebhookConfig(BaseIntegrationConfig):
    """Configuration for custom webhook integrations."""

    integration_type: Literal["webhook"] = "webhook"
    provider: Literal["webhook"] = "webhook"

    # Endpoint settings
    url: str = Field(..., description="Webhook endpoint URL")
    method: Literal["POST", "PUT"] = Field(
        default="POST", description="HTTP method for webhook delivery"
    )

    # Authentication
    auth_type: AuthType = Field(default=AuthType.API_KEY, description="Authentication type")
    auth_header: str = Field(default="Authorization", description="Header name for authentication")
    auth_value: Optional[SecretStr] = Field(
        None, description="Authentication value (token, API key, etc.)"
    )
    hmac_secret: Optional[SecretStr] = Field(
        None, description="HMAC secret for signature verification"
    )
    hmac_header: str = Field(default="X-Webhook-Signature", description="Header for HMAC signature")
    hmac_algorithm: Literal["sha256", "sha512"] = Field(
        default="sha256", description="HMAC algorithm"
    )

    # Payload settings
    content_type: str = Field(default="application/json", description="Content-Type header value")
    include_headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers to include"
    )

    # Delivery settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum delivery attempts")
    retry_delay_seconds: float = Field(
        default=1.0, ge=0.5, le=60, description="Initial retry delay"
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate webhook URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


# Union type for all integration configs
IntegrationConfig = Union[
    SplunkConfig,
    SentinelConfig,
    JiraConfig,
    ServiceNowConfig,
    GitHubActionsConfig,
    GitLabCIConfig,
    WebhookConfig,
]
