"""
Pydantic schemas for Policy Marketplace Service

Exports all request/response schemas for API validation
"""

from .template import (
    AnalyticsDashboard,
    AnalyticsEvent,
    AnalyticsEventType,
    AnalyticsResponse,
    AnalyticsTrend,
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    RatingCreate,
    RatingResponse,
    ReviewAction,
    ReviewRequest,
    ReviewResponse,
    TemplateAnalyticsSummary,
    TemplateBase,
    TemplateCategory,
    TemplateCreate,
    TemplateFormat,
    TemplateListItem,
    TemplateListResponse,
    TemplateResponse,
    TemplateSearchParams,
    TemplateStatus,
    TemplateUpdate,
    VersionBase,
    VersionCreate,
    VersionListItem,
    VersionListResponse,
    VersionResponse,
)

__all__ = [
    # Template schemas
    "TemplateBase",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListItem",
    "TemplateListResponse",
    "TemplateSearchParams",
    # Enums
    "TemplateStatus",
    "TemplateFormat",
    "TemplateCategory",
    # Version schemas
    "VersionBase",
    "VersionCreate",
    "VersionResponse",
    "VersionListItem",
    "VersionListResponse",
    # Rating schemas
    "RatingCreate",
    "RatingResponse",
    # Analytics schemas
    "AnalyticsEvent",
    "AnalyticsEventType",
    "AnalyticsResponse",
    "TemplateAnalyticsSummary",
    "AnalyticsTrend",
    "AnalyticsDashboard",
    # Review schemas
    "ReviewAction",
    "ReviewRequest",
    "ReviewResponse",
    # Pagination schemas
    "PaginationMeta",
    "PaginatedResponse",
    # Error schemas
    "ErrorDetail",
    "ErrorResponse",
    # Message schemas
    "MessageResponse",
]
