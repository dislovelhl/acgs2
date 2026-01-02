"""
Pydantic schemas for Policy Marketplace request/response validation

Following Pydantic v2 patterns with ConfigDict and field_serializer
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class TemplateStatus(str, Enum):
    """Template status enumeration"""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TemplateFormat(str, Enum):
    """Supported template file formats"""

    JSON = "json"
    YAML = "yaml"
    REGO = "rego"


class TemplateCategory(str, Enum):
    """Template category enumeration"""

    COMPLIANCE = "compliance"
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    AUDIT = "audit"
    RATE_LIMITING = "rate_limiting"
    MULTI_TENANT = "multi_tenant"
    API_SECURITY = "api_security"
    DATA_RETENTION = "data_retention"
    CUSTOM = "custom"


# ====================
# Template Base Schemas
# ====================


class TemplateBase(BaseModel):
    """Base schema for template data"""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str = Field(..., min_length=1, max_length=5000, description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    format: TemplateFormat = Field(default=TemplateFormat.JSON, description="Template file format")


class TemplateCreate(TemplateBase):
    """Schema for creating a new template"""

    content: str = Field(..., min_length=1, description="Template content (JSON, YAML, or Rego)")
    is_public: bool = Field(default=True, description="Whether template is publicly visible")
    organization_id: Optional[str] = Field(
        None, max_length=100, description="Organization ID for private templates"
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Validate that content is not just whitespace"""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v


class TemplateUpload(BaseModel):
    """Schema for uploading a template file"""

    file: str = Field(..., min_length=1, max_length=255, description="Filename or file content")
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str = Field(..., min_length=1, max_length=5000, description="Template description")
    category: TemplateCategory = Field(..., description="Template category")

    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        """Validate file has valid extension"""
        valid_extensions = (".json", ".yaml", ".yml", ".rego")
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(
                f"File must have one of these extensions: {', '.join(valid_extensions)}"
            )
        return v


class TemplateUpdate(BaseModel):
    """Schema for updating an existing template"""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(
        None, min_length=1, max_length=5000, description="Template description"
    )
    category: Optional[TemplateCategory] = Field(None, description="Template category")
    content: Optional[str] = Field(None, min_length=1, description="Template content")
    is_public: Optional[bool] = Field(None, description="Whether template is publicly visible")
    status: Optional[TemplateStatus] = Field(None, description="Template status")


class TemplateResponse(TemplateBase):
    """Schema for template response"""

    id: int = Field(..., description="Template ID")
    content: str = Field(..., description="Template content")
    status: TemplateStatus = Field(..., description="Template status")
    is_verified: bool = Field(..., description="Whether template is verified")
    is_public: bool = Field(..., description="Whether template is publicly visible")
    organization_id: Optional[str] = Field(
        None, description="Organization ID for private templates"
    )
    author_id: Optional[str] = Field(None, description="Author user ID")
    author_name: Optional[str] = Field(None, description="Author display name")
    current_version: str = Field(..., description="Current version number")
    downloads: int = Field(..., description="Total download count")
    rating: Optional[float] = Field(None, description="Average rating (1-5)")
    rating_count: int = Field(..., description="Number of ratings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


class TemplateListItem(BaseModel):
    """Schema for template list item (lighter than full response)"""

    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    format: TemplateFormat = Field(..., description="Template file format")
    status: TemplateStatus = Field(..., description="Template status")
    is_verified: bool = Field(..., description="Whether template is verified")
    is_public: bool = Field(..., description="Whether template is publicly visible")
    author_name: Optional[str] = Field(None, description="Author display name")
    current_version: str = Field(..., description="Current version number")
    downloads: int = Field(..., description="Total download count")
    rating: Optional[float] = Field(None, description="Average rating (1-5)")
    rating_count: int = Field(..., description="Number of ratings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


# ====================
# Version Schemas
# ====================


class VersionBase(BaseModel):
    """Base schema for version data"""

    changelog: Optional[str] = Field(
        None, max_length=5000, description="Version changelog/release notes"
    )


class VersionCreate(VersionBase):
    """Schema for creating a new version"""

    content: str = Field(..., min_length=1, description="Version content")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Validate that content is not just whitespace"""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v


class VersionResponse(VersionBase):
    """Schema for version response"""

    id: int = Field(..., description="Version ID")
    template_id: int = Field(..., description="Parent template ID")
    version: str = Field(..., description="Version number (semver)")
    content: str = Field(..., description="Version content")
    content_hash: str = Field(..., description="SHA-256 hash of content")
    created_by: Optional[str] = Field(None, description="User ID who created version")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


class VersionListItem(BaseModel):
    """Schema for version list item (without content)"""

    id: int = Field(..., description="Version ID")
    version: str = Field(..., description="Version number (semver)")
    changelog: Optional[str] = Field(None, description="Version changelog")
    created_by: Optional[str] = Field(None, description="User ID who created version")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


# ====================
# Rating Schemas
# ====================


class RatingCreate(BaseModel):
    """Schema for creating a rating"""

    rating: int = Field(..., ge=1, le=5, description="Rating value (1-5)")
    comment: Optional[str] = Field(None, max_length=2000, description="Optional review comment")


class RatingResponse(BaseModel):
    """Schema for rating response"""

    id: int = Field(..., description="Rating ID")
    template_id: int = Field(..., description="Template ID")
    user_id: str = Field(..., description="User ID who rated")
    rating: int = Field(..., description="Rating value (1-5)")
    comment: Optional[str] = Field(None, description="Review comment")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


# ====================
# Analytics Schemas
# ====================


class AnalyticsEventType(str, Enum):
    """Analytics event types"""

    VIEW = "view"
    DOWNLOAD = "download"
    CLONE = "clone"


class AnalyticsEvent(BaseModel):
    """Schema for analytics event"""

    event_type: AnalyticsEventType = Field(..., description="Type of analytics event")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")


class AnalyticsResponse(BaseModel):
    """Schema for analytics response"""

    id: int = Field(..., description="Analytics event ID")
    template_id: int = Field(..., description="Template ID")
    event_type: str = Field(..., description="Event type")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    created_at: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


class TemplateAnalyticsSummary(BaseModel):
    """Schema for template analytics summary"""

    template_id: int = Field(..., description="Template ID")
    total_views: int = Field(default=0, description="Total view count")
    total_downloads: int = Field(default=0, description="Total download count")
    total_clones: int = Field(default=0, description="Total clone count")
    average_rating: Optional[float] = Field(None, description="Average rating")
    rating_count: int = Field(default=0, description="Number of ratings")


class AnalyticsTrend(BaseModel):
    """Schema for analytics trend data point"""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    views: int = Field(default=0, description="View count for date")
    downloads: int = Field(default=0, description="Download count for date")


class AnalyticsDashboard(BaseModel):
    """Schema for analytics dashboard response"""

    start_date: str = Field(..., description="Start date of analytics period")
    end_date: str = Field(..., description="End date of analytics period")
    total_templates: int = Field(..., description="Total template count")
    total_downloads: int = Field(..., description="Total downloads in period")
    total_views: int = Field(..., description="Total views in period")
    top_templates: List[TemplateListItem] = Field(
        default_factory=list, description="Top templates by downloads"
    )
    trends: List[AnalyticsTrend] = Field(default_factory=list, description="Daily trend data")


# ====================
# Review Workflow Schemas
# ====================


class ReviewAction(str, Enum):
    """Review action types"""

    APPROVE = "approve"
    REJECT = "reject"


class ReviewRequest(BaseModel):
    """Schema for review action request"""

    action: ReviewAction = Field(..., description="Review action to take")
    feedback: Optional[str] = Field(None, max_length=2000, description="Review feedback/reason")


class ReviewResponse(BaseModel):
    """Schema for review action response"""

    template_id: int = Field(..., description="Template ID")
    action: ReviewAction = Field(..., description="Action taken")
    new_status: TemplateStatus = Field(..., description="New template status")
    reviewed_by: str = Field(..., description="Reviewer user ID")
    reviewed_at: datetime = Field(..., description="Review timestamp")
    feedback: Optional[str] = Field(None, description="Review feedback")

    @field_serializer("reviewed_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format"""
        return value.isoformat()


# ====================
# Pagination Schemas
# ====================


T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Schema for pagination metadata"""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses"""

    items: List[T] = Field(default_factory=list, description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class TemplateListResponse(BaseModel):
    """Schema for paginated template list response"""

    items: List[TemplateListItem] = Field(default_factory=list, description="List of templates")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class VersionListResponse(BaseModel):
    """Schema for paginated version list response"""

    items: List[VersionListItem] = Field(default_factory=list, description="List of versions")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


# ====================
# Search and Filter Schemas
# ====================


class TemplateSearchParams(BaseModel):
    """Schema for template search parameters"""

    query: Optional[str] = Field(None, max_length=255, description="Search query string")
    category: Optional[TemplateCategory] = Field(None, description="Filter by category")
    format: Optional[TemplateFormat] = Field(None, description="Filter by format")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    organization_id: Optional[str] = Field(
        None, max_length=100, description="Filter by organization"
    )
    sort_by: Optional[str] = Field(
        "created_at", description="Sort field (created_at, downloads, rating, name)"
    )
    sort_order: Optional[str] = Field("desc", description="Sort order (asc, desc)")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort_by field"""
        allowed = {"created_at", "downloads", "rating", "name", "updated_at"}
        if v and v not in allowed:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed)}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort_order field"""
        if v and v.lower() not in {"asc", "desc"}:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower() if v else v


# ====================
# Error Response Schemas
# ====================


class ErrorDetail(BaseModel):
    """Schema for error detail"""

    loc: List[str] = Field(default_factory=list, description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Schema for error response"""

    detail: str = Field(..., description="Error message")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Detailed validation errors")


# ====================
# Message Response Schema
# ====================


class MessageResponse(BaseModel):
    """Schema for simple message response"""

    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success status")
