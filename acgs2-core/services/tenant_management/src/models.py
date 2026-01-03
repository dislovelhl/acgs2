"""
ACGS-2 Tenant Management Models
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TenantStatus(str, Enum):
    """Tenant lifecycle status"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING = "pending"


class TenantTier(str, Enum):
    """Tenant service tier"""

    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"


class Tenant(BaseModel):
    """Tenant entity with comprehensive metadata"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None

    # Contact information
    contact_email: str = Field(alias="contactEmail")
    contact_name: Optional[str] = Field(default=None, alias="contactName")
    contact_phone: Optional[str] = Field(default=None, alias="contactPhone")

    # Organization details
    organization_name: Optional[str] = Field(default=None, alias="organizationName")
    organization_size: Optional[str] = Field(
        default=None, alias="organizationSize"
    )  # "1-10", "11-50", "51-200", "201-1000", "1000+"
    industry: Optional[str] = None

    # Service configuration
    tier: TenantTier = TenantTier.FREE
    status: TenantStatus = TenantStatus.PENDING

    # Resource quotas
    max_users: int = Field(default=5, ge=1, alias="maxUsers")
    max_policies: int = Field(default=10, ge=1, alias="maxPolicies")
    max_models: int = Field(default=5, ge=1, alias="maxModels")
    max_approvals_per_month: int = Field(default=100, ge=1, alias="maxApprovalsPerMonth")
    max_api_calls_per_hour: int = Field(default=1000, ge=1, alias="maxApiCallsPerHour")
    storage_limit_gb: float = Field(default=1.0, ge=0.1, alias="storageLimitGb")

    # Usage tracking
    current_users: int = Field(default=0, ge=0, alias="currentUsers")
    current_policies: int = Field(default=0, ge=0, alias="currentPolicies")
    current_models: int = Field(default=0, ge=0, alias="currentModels")
    approvals_this_month: int = Field(default=0, ge=0, alias="approvalsThisMonth")
    api_calls_this_hour: int = Field(default=0, ge=0, alias="apiCallsThisHour")
    storage_used_gb: float = Field(default=0.0, ge=0.0, alias="storageUsedGb")

    # Compliance and security
    data_residency: Optional[str] = Field(default=None, alias="dataResidency")  # Region code
    compliance_requirements: List[str] = Field(
        default_factory=list, alias="complianceRequirements"
    )  # ["SOC2", "GDPR", "HIPAA"]
    security_level: str = Field(
        default="standard", alias="securityLevel"
    )  # "standard", "enhanced", "maximum"

    # Administrative
    created_by: str = Field(alias="createdBy")  # User ID who created the tenant
    owned_by: str = Field(alias="ownedBy")  # Organization or user that owns the tenant
    admin_users: List[str] = Field(
        default_factory=list, alias="adminUsers"
    )  # User IDs with admin access

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    activated_at: Optional[datetime] = Field(default=None, alias="activatedAt")
    suspended_at: Optional[datetime] = Field(default=None, alias="suspendedAt")

    # Constitutional compliance
    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v):
        """Basic email validation"""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v

    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.status == TenantStatus.ACTIVE

    def can_create_user(self) -> bool:
        """Check if tenant can create more users"""
        return self.current_users < self.max_users

    def can_create_policy(self) -> bool:
        """Check if tenant can create more policies"""
        return self.current_policies < self.max_policies

    def can_create_model(self) -> bool:
        """Check if tenant can create more models"""
        return self.current_models < self.max_models

    def can_create_approval(self) -> bool:
        """Check if tenant can create more approvals this month"""
        return self.approvals_this_month < self.max_approvals_per_month

    def has_storage_space(self, additional_gb: float = 0) -> bool:
        """Check if tenant has storage space"""
        return (self.storage_used_gb + additional_gb) <= self.storage_limit_gb


class TenantInvitation(BaseModel):
    """Tenant invitation for user onboarding"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(alias="tenantId")
    email: str
    role: str = "member"  # "admin", "member", "viewer"
    invited_by: str = Field(alias="invitedBy")
    invited_at: datetime = Field(default_factory=datetime.utcnow, alias="invitedAt")
    expires_at: datetime = Field(alias="expiresAt")
    accepted_at: Optional[datetime] = Field(default=None, alias="acceptedAt")
    status: str = "pending"  # "pending", "accepted", "expired", "cancelled"
    token: str  # Secure invitation token

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True


class TenantAuditEvent(BaseModel):
    """Tenant-specific audit events"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(alias="tenantId")
    event_type: str = Field(alias="eventType")  # "user_action", "resource_change", "security_event"
    action: str  # "create", "update", "delete", "access", etc.
    resource_type: str = Field(alias="resourceType")  # "user", "policy", "model", etc.
    resource_id: str = Field(alias="resourceId")
    user_id: str = Field(alias="userId")
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = Field(default=None, alias="ipAddress")
    user_agent: Optional[str] = Field(default=None, alias="userAgent")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True


class TenantUsageMetrics(BaseModel):
    """Tenant usage metrics for monitoring"""

    tenant_id: str = Field(alias="tenantId")
    period_start: datetime = Field(alias="periodStart")
    period_end: datetime = Field(alias="periodEnd")

    # Usage counts
    total_users: int = Field(default=0, alias="totalUsers")
    total_policies: int = Field(default=0, alias="totalPolicies")
    total_models: int = Field(default=0, alias="totalModels")
    total_approvals: int = Field(default=0, alias="totalApprovals")
    total_api_calls: int = Field(default=0, alias="totalApiCalls")

    # Resource utilization percentages
    user_utilization: float = Field(default=0.0, alias="userUtilization")
    policy_utilization: float = Field(default=0.0, alias="policyUtilization")
    model_utilization: float = Field(default=0.0, alias="modelUtilization")
    approval_utilization: float = Field(default=0.0, alias="approvalUtilization")
    storage_utilization: float = Field(default=0.0, alias="storageUtilization")

    # Performance metrics
    avg_response_time: float = Field(default=0.0, alias="avgResponseTime")
    error_rate: float = Field(default=0.0, alias="errorRate")
    uptime_percentage: float = Field(default=100.0, alias="uptimePercentage")

    recorded_at: datetime = Field(default_factory=datetime.utcnow, alias="recordedAt")

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True


# Request/Response models for API
class CreateTenantRequest(BaseModel):
    """Request to create a new tenant"""

    name: str
    display_name: str
    description: Optional[str] = None
    contact_email: str = Field(alias="contactEmail")
    contact_name: Optional[str] = Field(default=None, alias="contactName")
    contact_phone: Optional[str] = Field(default=None, alias="contactPhone")
    organization_name: Optional[str] = Field(default=None, alias="organizationName")
    organization_size: Optional[str] = Field(default=None, alias="organizationSize")
    industry: Optional[str] = None
    tier: TenantTier = TenantTier.FREE
    data_residency: Optional[str] = Field(default=None, alias="dataResidency")
    compliance_requirements: List[str] = Field(default_factory=list, alias="complianceRequirements")
    created_by: str = Field(alias="createdBy")
    owned_by: str = Field(alias="ownedBy")

    class Config:
        populate_by_name = True


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = Field(default=None, alias="contactEmail")
    contact_name: Optional[str] = Field(default=None, alias="contactName")
    contact_phone: Optional[str] = Field(default=None, alias="contactPhone")
    organization_name: Optional[str] = Field(default=None, alias="organizationName")
    organization_size: Optional[str] = Field(default=None, alias="organizationSize")
    industry: Optional[str] = None
    tier: Optional[TenantTier] = None
    status: Optional[TenantStatus] = None
    data_residency: Optional[str] = Field(default=None, alias="dataResidency")
    compliance_requirements: Optional[List[str]] = Field(
        default=None, alias="complianceRequirements"
    )
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    class Config:
        populate_by_name = True


class TenantResourceQuota(BaseModel):
    """Tenant resource quota configuration"""

    tenant_id: str = Field(alias="tenantId")
    resource_type: str = Field(alias="resourceType")  # "users", "policies", "models", etc.
    limit: int
    current_usage: int = Field(default=0, alias="currentUsage")
    reset_period: Optional[str] = Field(
        default=None, alias="resetPeriod"
    )  # "hourly", "daily", "monthly", "never"
    last_reset: Optional[datetime] = Field(default=None, alias="lastReset")

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True


class TenantAccessPolicy(BaseModel):
    """Tenant-specific access control policy"""

    tenant_id: str = Field(alias="tenantId")
    resource_type: str = Field(alias="resourceType")  # "policy", "model", "approval", etc.
    resource_id: Optional[str] = Field(
        default=None, alias="resourceId"
    )  # Specific resource or None for all
    user_id: str = Field(alias="userId")
    role: str  # "owner", "admin", "editor", "viewer"
    permissions: List[str] = Field(default_factory=list)  # ["read", "write", "delete", "execute"]
    granted_by: str = Field(alias="grantedBy")
    granted_at: datetime = Field(default_factory=datetime.utcnow, alias="grantedAt")
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
