"""
Usage Metering Models
Constitutional Hash: cdd01ef066bc6cf2

Defines metering events, aggregations, and billing dimensions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class MeterableOperation(str, Enum):
    """Operations tracked for usage-based billing."""

    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    AGENT_MESSAGE = "agent_message"
    POLICY_EVALUATION = "policy_evaluation"
    COMPLIANCE_CHECK = "compliance_check"
    AUDIT_WRITE = "audit_write"
    DELIBERATION_REQUEST = "deliberation_request"
    HITL_APPROVAL = "hitl_approval"
    BLOCKCHAIN_ANCHOR = "blockchain_anchor"


class MeteringTier(str, Enum):
    """Pricing tiers based on constitutional complexity."""

    STANDARD = "standard"  # Basic validation
    ENHANCED = "enhanced"  # With ML scoring
    DELIBERATION = "deliberation"  # Human-in-the-loop
    ENTERPRISE = "enterprise"  # Full governance suite


class UsageEvent(BaseModel):
    """Individual metered operation event."""

    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Identification
    tenant_id: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None

    # Operation details
    operation: MeterableOperation
    tier: MeteringTier = MeteringTier.STANDARD

    # Usage dimensions
    units: int = 1  # Number of operations
    tokens_processed: int = 0  # For AI operations
    latency_ms: float = 0.0

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    compliance_score: float = 1.0  # 0.0 to 1.0

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class UsageAggregation(BaseModel):
    """Aggregated usage for billing period."""

    aggregation_id: UUID = Field(default_factory=uuid4)
    tenant_id: str

    # Time window
    period_start: datetime
    period_end: datetime

    # Aggregated counts by operation
    operation_counts: Dict[str, int] = Field(default_factory=dict)

    # Aggregated by tier
    tier_counts: Dict[str, int] = Field(default_factory=dict)

    # Total metrics
    total_operations: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    avg_compliance_score: float = 1.0

    # Constitutional validation
    constitutional_hash: str = CONSTITUTIONAL_HASH

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class MeteringQuota(BaseModel):
    """Usage quota and limits for a tenant."""

    tenant_id: str

    # Quotas per operation type
    monthly_validation_limit: Optional[int] = None
    monthly_message_limit: Optional[int] = None
    monthly_deliberation_limit: Optional[int] = None

    # Overall limits
    monthly_total_limit: Optional[int] = None
    rate_limit_per_second: int = 100

    # Current usage (updated periodically)
    current_period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_usage: Dict[str, int] = Field(default_factory=dict)

    # Constitutional
    constitutional_hash: str = CONSTITUTIONAL_HASH


class BillingRate(BaseModel):
    """Pricing rates per operation and tier."""

    operation: MeterableOperation
    tier: MeteringTier

    # Base rate in smallest currency unit (cents)
    base_rate_cents: int

    # Volume discounts (units threshold -> discount percentage)
    volume_discounts: Dict[int, float] = Field(default_factory=dict)

    # Effective date
    effective_from: datetime
    effective_until: Optional[datetime] = None

    constitutional_hash: str = CONSTITUTIONAL_HASH
