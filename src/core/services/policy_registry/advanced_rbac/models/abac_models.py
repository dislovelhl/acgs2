"""
ACGS-2 Advanced RBAC Models
Attribute-Based Access Control (ABAC) Implementation
Constitutional Hash: cdd01ef066bc6cf2
"""

# ruff: noqa: E402
# Import type aliases from shared types
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

# Add src/core/shared to path for type imports
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from types import AttributeMap, ConfigDict, JSONDict, JSONValue, MetadataDict


class AttributeCategory(Enum):
    """Categories of attributes for ABAC"""

    SUBJECT = "subject"
    RESOURCE = "resource"
    ACTION = "action"
    ENVIRONMENT = "environment"
    CONTEXT = "context"


class AttributeType(Enum):
    """Types of attributes"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    LIST = "list"
    JSON = "json"


class ComparisonOperator(Enum):
    """Comparison operators for ABAC policies"""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    REGEX_MATCH = "regex"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class LogicalOperator(Enum):
    """Logical operators for combining conditions"""

    AND = "and"
    OR = "or"
    NOT = "not"


class DelegationScope(Enum):
    """Delegation scope levels"""

    LIMITED = "limited"
    BROAD = "broad"
    FULL = "full"


class DelegationType(Enum):
    """Types of delegation"""

    TEMPORARY = "temporary"
    CONDITIONAL = "conditional"
    REVOCABLE = "revocable"
    CASCADE = "cascade"


@dataclass
class Attribute:
    """An attribute for ABAC"""

    name: str
    value: JSONValue
    attr_type: AttributeType
    category: AttributeCategory
    metadata: MetadataDict = field(default_factory=dict)
    confidence: float = 1.0  # Confidence score for attribute value
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AttributeCondition:
    """A condition for attribute matching"""

    attribute_name: str
    operator: ComparisonOperator
    expected_value: JSONValue
    case_sensitive: bool = True
    weight: float = 1.0  # Weight for scoring


@dataclass
class ABACRule:
    """An ABAC rule"""

    rule_id: str
    name: str
    description: str
    effect: str  # "allow" or "deny"
    conditions: List[AttributeCondition]
    logical_operator: LogicalOperator = LogicalOperator.AND
    priority: int = 0
    enabled: bool = True
    metadata: MetadataDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ABACPolicy:
    """An ABAC policy containing multiple rules"""

    policy_id: str
    name: str
    description: str
    rules: List[ABACRule]
    combining_algorithm: str = (
        "first-applicable"  # first-applicable, deny-overrides, permit-overrides
    )
    target_conditions: List[AttributeCondition] = field(default_factory=list)
    enabled: bool = True
    metadata: MetadataDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def allow_rules(self) -> List[ABACRule]:
        """Get all allow rules"""
        return [rule for rule in self.rules if rule.effect == "allow"]

    @property
    def deny_rules(self) -> List[ABACRule]:
        """Get all deny rules"""
        return [rule for rule in self.rules if rule.effect == "deny"]


@dataclass
class AccessRequest:
    """An access request for ABAC evaluation"""

    request_id: str
    subject_attributes: Dict[str, Attribute]
    resource_attributes: Dict[str, Attribute]
    action_attributes: Dict[str, Attribute]
    environment_attributes: Dict[str, Attribute]
    context_attributes: Dict[str, Attribute] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyDecision:
    """ABAC policy decision"""

    decision: str  # "allow", "deny", "indeterminate", "not_applicable"
    confidence_score: float
    matched_rules: List[str]
    denied_rules: List[str]
    obligations: List[JSONDict] = field(default_factory=list)
    advice: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluation_time_ms: float = 0.0


@dataclass
class DelegationGrant:
    """A delegation grant"""

    grant_id: str
    delegator_id: str
    delegatee_id: str
    delegation_type: DelegationType
    scope: DelegationScope
    permissions: List[str]
    conditions: List[AttributeCondition] = field(default_factory=list)
    constraints: JSONDict = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    revocable: bool = True
    cascade_allowed: bool = False
    metadata: MetadataDict = field(default_factory=dict)
    granted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DelegationChain:
    """A chain of delegations"""

    chain_id: str
    root_delegator: str
    current_delegatee: str
    grants: List[DelegationGrant]
    depth: int
    max_depth: int = 3
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AttributeSource:
    """Source for attribute values"""

    source_id: str
    name: str
    source_type: str  # ldap, database, api, computed, etc.
    attributes: List[str]
    refresh_interval_seconds: int = 300
    cache_ttl_seconds: int = 300
    enabled: bool = True
    config: ConfigDict = field(default_factory=dict)
    last_updated: Optional[datetime] = None


@dataclass
class AttributeResolutionContext:
    """Context for attribute resolution"""

    request_id: str
    subject_id: str
    resource_id: str
    action: str
    resolved_attributes: Dict[str, Attribute] = field(default_factory=dict)
    failed_sources: List[str] = field(default_factory=list)
    resolution_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class ABACAuditEvent:
    """Audit event for ABAC decisions"""

    event_id: str
    request_id: str
    subject_id: str
    resource_id: str
    action: str
    decision: str
    confidence_score: float
    matched_policies: List[str]
    matched_rules: List[str]
    attributes_used: AttributeMap
    delegation_chain: Optional[str] = None
    evaluation_time_ms: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# Pydantic models for API
class AttributeModel(BaseModel):
    name: str
    value: JSONValue
    attr_type: AttributeType
    category: AttributeCategory
    metadata: MetadataDict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        use_enum_values = True


class AttributeConditionModel(BaseModel):
    attribute_name: str
    operator: ComparisonOperator
    expected_value: JSONValue
    case_sensitive: bool = True
    weight: float = Field(default=1.0, gt=0.0)

    class Config:
        use_enum_values = True


class ABACRuleModel(BaseModel):
    rule_id: str
    name: str
    description: str
    effect: str = Field(regex="^(allow|deny)$")
    conditions: List[AttributeConditionModel]
    logical_operator: LogicalOperator = LogicalOperator.AND
    priority: int = 0
    enabled: bool = True
    metadata: MetadataDict = Field(default_factory=dict)

    @validator("conditions")
    def validate_conditions(cls, v):
        if not v:
            raise ValueError("At least one condition is required")
        return v

    class Config:
        use_enum_values = True


class ABACPolicyModel(BaseModel):
    policy_id: str
    name: str
    description: str
    rules: List[ABACRuleModel]
    combining_algorithm: str = "first-applicable"
    target_conditions: List[AttributeConditionModel] = Field(default_factory=list)
    enabled: bool = True
    metadata: MetadataDict = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AccessRequestModel(BaseModel):
    request_id: str
    subject_attributes: Dict[str, AttributeModel]
    resource_attributes: Dict[str, AttributeModel]
    action_attributes: Dict[str, AttributeModel]
    environment_attributes: Dict[str, AttributeModel]
    context_attributes: Dict[str, AttributeModel] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class DelegationGrantModel(BaseModel):
    grant_id: str
    delegator_id: str
    delegatee_id: str
    delegation_type: DelegationType
    scope: DelegationScope
    permissions: List[str]
    conditions: List[AttributeConditionModel] = Field(default_factory=list)
    constraints: JSONDict = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    revocable: bool = True
    cascade_allowed: bool = False
    metadata: MetadataDict = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AttributeSourceModel(BaseModel):
    source_id: str
    name: str
    source_type: str
    attributes: List[str]
    refresh_interval_seconds: int = Field(default=300, gt=0)
    cache_ttl_seconds: int = Field(default=300, gt=0)
    enabled: bool = True
    config: ConfigDict = Field(default_factory=dict)

    class Config:
        use_enum_values = True
