"""
Governance Metrics Data Models for Executive Dashboard

Provides Pydantic models for governance KPIs, trend analysis, and compliance metrics.
Supports SOC 2, ISO 27001, GDPR, and ISO 42001 compliance frameworks.

Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer, field_validator


class TrendDirection(str, Enum):
    """Trend direction for governance metrics."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    ISO42001 = "iso42001"


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GovernanceMetrics(BaseModel):
    """
    Point-in-time governance metrics snapshot.

    Stores compliance score and control status for trend analysis.
    Can be stored in audit_ledger or separate metrics table.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., min_length=1, max_length=255, description="Tenant identifier")

    # Date for the metrics snapshot
    date: date = Field(..., description="Date of the metrics snapshot")

    # Core compliance metrics
    compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall compliance score as percentage (0-100)",
    )
    controls_passing: int = Field(..., ge=0, description="Number of passing controls")
    controls_failing: int = Field(..., ge=0, description="Number of failing controls")
    controls_total: int = Field(default=0, ge=0, description="Total number of controls")

    # Risk and incident metrics
    high_risk_incidents: int = Field(default=0, ge=0, description="Count of high-risk incidents")
    audit_count: int = Field(default=0, ge=0, description="Number of audits in period")

    # Framework-specific metrics
    framework: Optional[ComplianceFramework] = Field(
        default=None, description="Compliance framework for these metrics"
    )
    framework_specific_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional framework-specific metrics",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("controls_total", mode="before")
    @classmethod
    def compute_controls_total(cls, v, info):
        """Compute total controls if not provided."""
        if v == 0 and info.data:
            passing = info.data.get("controls_passing", 0)
            failing = info.data.get("controls_failing", 0)
            return passing + failing
        return v

    @field_serializer("date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return value.isoformat()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "date": self.date.isoformat(),
            "compliance_score": self.compliance_score,
            "controls_passing": self.controls_passing,
            "controls_failing": self.controls_failing,
            "controls_total": self.controls_total,
            "high_risk_incidents": self.high_risk_incidents,
            "audit_count": self.audit_count,
            "framework": self.framework.value if self.framework else None,
            "framework_specific_data": self.framework_specific_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GovernanceKPIs(BaseModel):
    """
    Current governance KPIs for executive dashboard.

    Provides real-time compliance status and trend direction.
    """

    tenant_id: str = Field(..., min_length=1, max_length=255)

    # Core KPIs
    compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Current overall compliance score (0-100)",
    )
    controls_passing: int = Field(..., ge=0, description="Number of passing controls")
    controls_failing: int = Field(..., ge=0, description="Number of failing controls")
    controls_total: int = Field(default=0, ge=0, description="Total number of controls")

    # Activity metrics
    recent_audits: int = Field(default=0, ge=0, description="Number of audits in last 30 days")
    high_risk_incidents: int = Field(default=0, ge=0, description="Active high-risk incidents")

    # Trend analysis
    trend_direction: TrendDirection = Field(
        default=TrendDirection.STABLE,
        description="Direction of compliance trend",
    )
    trend_change_percent: float = Field(
        default=0.0,
        description="Percentage change from previous period",
    )

    # Data freshness
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_stale_warning: bool = Field(
        default=False,
        description="True if data hasn't been updated in >7 days",
    )

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    @field_validator("controls_total", mode="before")
    @classmethod
    def compute_controls_total(cls, v, info):
        """Compute total controls if not provided."""
        if v == 0 and info.data:
            passing = info.data.get("controls_passing", 0)
            failing = info.data.get("controls_failing", 0)
            return passing + failing
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "tenant_id": self.tenant_id,
            "compliance_score": self.compliance_score,
            "controls_passing": self.controls_passing,
            "controls_failing": self.controls_failing,
            "controls_total": self.controls_total,
            "recent_audits": self.recent_audits,
            "high_risk_incidents": self.high_risk_incidents,
            "trend_direction": self.trend_direction.value,
            "trend_change_percent": self.trend_change_percent,
            "last_updated": self.last_updated.isoformat(),
            "data_stale_warning": self.data_stale_warning,
        }


class GovernanceTrendPoint(BaseModel):
    """Single data point in governance trend series."""

    date: date = Field(..., description="Date of the data point")
    compliance_score: float = Field(
        ..., ge=0.0, le=100.0, description="Compliance score on this date"
    )
    controls_passing: int = Field(default=0, ge=0)
    controls_failing: int = Field(default=0, ge=0)
    controls_total: int = Field(default=0, ge=0)
    audit_count: int = Field(default=0, ge=0)

    @field_serializer("date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()


class GovernanceTrends(BaseModel):
    """
    Historical trend data for governance dashboard charts.

    Provides time-series data for 30, 60, or 90 day analysis.
    """

    tenant_id: str = Field(..., min_length=1, max_length=255)
    days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Number of days of trend data",
    )

    # Time series data
    data_points: List[GovernanceTrendPoint] = Field(
        default_factory=list,
        description="List of daily trend data points",
    )

    # Aggregated statistics
    period_start: date = Field(..., description="Start date of trend period")
    period_end: date = Field(..., description="End date of trend period")
    avg_compliance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Average compliance score over period",
    )
    min_compliance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Minimum compliance score in period",
    )
    max_compliance_score: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Maximum compliance score in period",
    )

    # Trend direction
    trend_direction: TrendDirection = Field(default=TrendDirection.STABLE)
    trend_slope: float = Field(
        default=0.0,
        description="Slope of trend line (positive = improving)",
    )

    @field_serializer("period_start", "period_end")
    def serialize_dates(self, value: date) -> str:
        return value.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "tenant_id": self.tenant_id,
            "days": self.days,
            "dates": [dp.date.isoformat() for dp in self.data_points],
            "compliance_scores": [dp.compliance_score for dp in self.data_points],
            "control_counts": [
                {
                    "passing": dp.controls_passing,
                    "failing": dp.controls_failing,
                    "total": dp.controls_total,
                }
                for dp in self.data_points
            ],
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "avg_compliance_score": self.avg_compliance_score,
            "min_compliance_score": self.min_compliance_score,
            "max_compliance_score": self.max_compliance_score,
            "trend_direction": self.trend_direction.value,
            "trend_slope": self.trend_slope,
        }


class FrameworkComplianceStatus(BaseModel):
    """Compliance status for a specific framework."""

    framework: ComplianceFramework = Field(..., description="Compliance framework")
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    controls_passing: int = Field(default=0, ge=0)
    controls_failing: int = Field(default=0, ge=0)
    controls_total: int = Field(default=0, ge=0)
    last_audit_date: Optional[date] = Field(
        default=None, description="Date of last audit for this framework"
    )
    next_audit_due: Optional[date] = Field(default=None, description="Due date for next audit")
    certification_status: Optional[str] = Field(
        default=None, description="Current certification status"
    )

    @field_serializer("last_audit_date", "next_audit_due")
    def serialize_optional_date(self, value: Optional[date]) -> Optional[str]:
        return value.isoformat() if value else None


class MultiFrameworkKPIs(BaseModel):
    """
    KPIs across multiple compliance frameworks.

    Used for organizations tracking compliance with multiple standards.
    """

    tenant_id: str = Field(..., min_length=1, max_length=255)
    frameworks: List[FrameworkComplianceStatus] = Field(
        default_factory=list,
        description="Status for each tracked framework",
    )
    overall_compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted average across all frameworks",
    )
    lowest_framework: Optional[ComplianceFramework] = Field(
        default=None, description="Framework with lowest compliance score"
    )
    highest_framework: Optional[ComplianceFramework] = Field(
        default=None, description="Framework with highest compliance score"
    )
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class GovernanceAlert(BaseModel):
    """Alert for governance issues requiring attention."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., min_length=1, max_length=255)
    alert_type: str = Field(..., description="Type of alert (compliance_drop, audit_due, etc.)")
    severity: RiskLevel = Field(default=RiskLevel.MEDIUM)
    title: str = Field(..., max_length=255)
    description: str = Field(..., max_length=1000)
    framework: Optional[ComplianceFramework] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = Field(default=False)
    acknowledged_at: Optional[datetime] = Field(default=None)
    acknowledged_by: Optional[str] = Field(default=None)

    @field_serializer("created_at", "acknowledged_at")
    def serialize_optional_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


# Export all models
__all__ = [
    "TrendDirection",
    "ComplianceFramework",
    "RiskLevel",
    "GovernanceMetrics",
    "GovernanceKPIs",
    "GovernanceTrendPoint",
    "GovernanceTrends",
    "FrameworkComplianceStatus",
    "MultiFrameworkKPIs",
    "GovernanceAlert",
]
