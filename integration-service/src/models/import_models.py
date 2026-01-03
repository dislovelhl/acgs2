"""
Pydantic models for data import operations.

Defines models for import requests, responses, progress tracking, and source
configuration with comprehensive validation and support for JIRA, ServiceNow,
GitHub, and GitLab integrations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class ImportStatus(str, Enum):
    """Status of an import operation."""

    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_COMPLETED = "partially_completed"


class SourceType(str, Enum):
    """Supported external data sources for import."""

    JIRA = "jira"
    SERVICENOW = "servicenow"
    GITHUB = "github"
    GITLAB = "gitlab"


class DuplicateHandling(str, Enum):
    """Strategy for handling duplicate items during import."""

    SKIP = "skip"
    UPDATE = "update"
    CREATE_NEW = "create_new"
    FAIL = "fail"


class SourceConfig(BaseModel):
    """Configuration for connecting to an external data source."""

    # Authentication - use appropriate fields based on source type
    api_token: Optional[SecretStr] = Field(
        None, description="API token for authentication (GitHub, GitLab)"
    )
    api_key: Optional[SecretStr] = Field(
        None, description="API key for authentication (JIRA)"
    )
    username: Optional[str] = Field(None, description="Username (JIRA, ServiceNow)")
    password: Optional[SecretStr] = Field(None, description="Password (ServiceNow)")
    user_email: Optional[str] = Field(None, description="User email (JIRA)")

    # Connection settings
    base_url: Optional[str] = Field(None, description="Base URL for the service instance")
    instance: Optional[str] = Field(
        None, description="Instance identifier (e.g., ServiceNow instance)"
    )

    # Source-specific filters
    project_key: Optional[str] = Field(None, description="Project key/identifier to import from")
    project_keys: List[str] = Field(
        default_factory=list, description="Multiple project keys (for batch import)"
    )
    repository: Optional[str] = Field(None, description="Repository name (GitHub/GitLab)")
    organization: Optional[str] = Field(None, description="Organization/group name")

    # Data filters
    status_filter: List[str] = Field(
        default_factory=list,
        description="Filter items by status (e.g., ['open', 'in_progress'])",
    )
    label_filter: List[str] = Field(
        default_factory=list, description="Filter items by labels/tags"
    )
    date_from: Optional[datetime] = Field(
        None, description="Import items created/updated after this date"
    )
    date_to: Optional[datetime] = Field(
        None, description="Import items created/updated before this date"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate base URL format."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/") if v else None

    @model_validator(mode="after")
    def validate_auth_config(self) -> "SourceConfig":
        """Validate that at least one authentication method is provided."""
        auth_fields = [
            self.api_token,
            self.api_key,
            self.username and self.password,
        ]
        if not any(auth_fields):
            raise ValueError(
                "At least one authentication method must be provided "
                "(api_token, api_key, or username/password)"
            )
        return self


class ImportOptions(BaseModel):
    """Options for controlling import behavior."""

    duplicate_handling: DuplicateHandling = Field(
        default=DuplicateHandling.SKIP,
        description="Strategy for handling duplicate items",
    )
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Number of items to process per batch"
    )
    max_items: Optional[int] = Field(
        None, ge=1, description="Maximum number of items to import (for testing/preview)"
    )
    include_comments: bool = Field(default=True, description="Include comments/notes in import")
    include_attachments: bool = Field(
        default=False, description="Include file attachments (may increase processing time)"
    )
    include_history: bool = Field(
        default=False, description="Include item history/audit trail"
    )
    dry_run: bool = Field(
        default=False, description="Simulate import without committing changes"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
    )


class ImportRequest(BaseModel):
    """
    Request model for initiating a data import operation.

    Contains source configuration, authentication, filters, and import options.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this import request",
    )
    source_type: SourceType = Field(..., description="Type of external data source")
    source_config: SourceConfig = Field(..., description="Source connection and filter configuration")
    options: ImportOptions = Field(
        default_factory=ImportOptions, description="Import behavior options"
    )

    # Metadata
    requested_by: Optional[str] = Field(None, description="User ID who requested the import")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for request tracing"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the import")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ImportedItem(BaseModel):
    """Represents a single item that was imported."""

    external_id: str = Field(..., description="ID in the external system")
    internal_id: Optional[str] = Field(None, description="ID assigned in ACGS2 system")
    item_type: str = Field(..., description="Type of item (issue, ticket, project, etc.)")
    title: str = Field(..., description="Item title/summary")
    status: str = Field(..., description="Import status for this item")
    error_message: Optional[str] = Field(None, description="Error message if import failed")

    model_config = ConfigDict(populate_by_name=True)


class ImportProgress(BaseModel):
    """Detailed progress information for an import operation."""

    total_items: int = Field(0, ge=0, description="Total number of items to import")
    processed_items: int = Field(0, ge=0, description="Number of items processed so far")
    successful_items: int = Field(0, ge=0, description="Number of successfully imported items")
    failed_items: int = Field(0, ge=0, description="Number of failed items")
    skipped_items: int = Field(0, ge=0, description="Number of skipped items (duplicates)")

    percentage: float = Field(
        0.0, ge=0.0, le=100.0, description="Percentage complete (0-100)"
    )
    estimated_time_remaining: Optional[int] = Field(
        None, ge=0, description="Estimated seconds remaining"
    )

    current_batch: int = Field(0, ge=0, description="Current batch number being processed")
    total_batches: int = Field(0, ge=0, description="Total number of batches")

    model_config = ConfigDict(populate_by_name=True)


class ImportResponse(BaseModel):
    """
    Response model for import operations.

    Contains job tracking information, status, progress, and results.
    """

    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for tracking this import job",
    )
    request_id: str = Field(..., description="ID of the original import request")
    status: ImportStatus = Field(..., description="Current status of the import operation")
    source_type: SourceType = Field(..., description="Type of external data source")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the import job was created",
    )
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last status update timestamp",
    )

    # Progress information
    progress: ImportProgress = Field(
        default_factory=ImportProgress, description="Detailed progress information"
    )

    # Results
    imported_items: List[ImportedItem] = Field(
        default_factory=list, description="List of imported items (populated on completion)"
    )

    # Error details
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional error details"
    )

    # Metadata
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ImportResponse":
        """Validate timestamp ordering."""
        if self.started_at and self.started_at < self.created_at:
            raise ValueError("started_at cannot be before created_at")
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")
        return self


class PreviewItem(BaseModel):
    """Represents a sample item in the preview response."""

    external_id: str = Field(..., description="ID in the external system")
    item_type: str = Field(..., description="Type of item (issue, ticket, project, etc.)")
    title: str = Field(..., description="Item title/summary")
    status: Optional[str] = Field(None, description="Current status")
    assignee: Optional[str] = Field(None, description="Assigned user")
    created_at: Optional[datetime] = Field(None, description="Creation date")
    updated_at: Optional[datetime] = Field(None, description="Last update date")
    labels: List[str] = Field(default_factory=list, description="Labels/tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional item metadata"
    )

    model_config = ConfigDict(populate_by_name=True)


class PreviewResponse(BaseModel):
    """
    Response model for preview operations.

    Contains sample data from the external source without committing changes.
    """

    source_type: SourceType = Field(..., description="Type of external data source")
    total_available: int = Field(
        0, ge=0, description="Total number of items available for import"
    )
    preview_items: List[PreviewItem] = Field(
        default_factory=list, description="Sample items (typically first 10-50)"
    )
    preview_count: int = Field(0, ge=0, description="Number of items in preview")

    # Source metadata
    source_name: Optional[str] = Field(None, description="Name of the source (project, repo, etc.)")
    source_url: Optional[str] = Field(None, description="URL to the external source")

    # Statistics
    item_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of items by type (e.g., {'issue': 100, 'bug': 25})",
    )
    status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of items by status (e.g., {'open': 50, 'closed': 50})",
    )

    # Warnings
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about the import (e.g., missing fields, rate limits)",
    )

    model_config = ConfigDict(populate_by_name=True)


class ImportListResponse(BaseModel):
    """Response model for listing import jobs."""

    jobs: List[ImportResponse] = Field(default_factory=list, description="List of import jobs")
    total: int = Field(0, ge=0, description="Total number of jobs matching filters")
    limit: int = Field(10, ge=1, le=100, description="Number of jobs per page")
    offset: int = Field(0, ge=0, description="Offset for pagination")

    model_config = ConfigDict(populate_by_name=True)
