"""
ACGS-2 Python SDK
AI Constitutional Governance System

Constitutional Hash: cdd01ef066bc6cf2
"""

from acgs2_sdk.client import ACGS2Client, create_client
from acgs2_sdk.governor import Governor
from acgs2_sdk.config import ACGS2Config, AuthConfig
from acgs2_sdk.constants import CONSTITUTIONAL_HASH
from acgs2_sdk.exceptions import (
    ACGS2Error,
    AuthenticationError,
    AuthorizationError,
    ConstitutionalHashMismatchError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from acgs2_sdk.models import (
    AgentInfo,
    AgentMessage,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    ComplianceResult,
    ComplianceStatus,
    EventCategory,
    EventSeverity,
    GovernanceDecision,
    MessageType,
    PaginatedResponse,
    Policy,
    PolicyStatus,
    Priority,
)
from acgs2_sdk.services import (
    AgentService,
    AuditService,
    ComplianceService,
    GovernanceService,
    PolicyService,
)

__version__ = "2.0.0"
__constitutional_hash__ = CONSTITUTIONAL_HASH

__all__ = [
    # Client
    "ACGS2Client",
    "create_client",
    "Governor",
    # Config
    "ACGS2Config",
    "AuthConfig",
    # Constants
    "CONSTITUTIONAL_HASH",
    # Exceptions
    "ACGS2Error",
    "AuthenticationError",
    "AuthorizationError",
    "ConstitutionalHashMismatchError",
    "NetworkError",
    "RateLimitError",
    "TimeoutError",
    "ValidationError",
    # Models
    "AgentInfo",
    "AgentMessage",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditEvent",
    "ComplianceResult",
    "ComplianceStatus",
    "EventCategory",
    "EventSeverity",
    "GovernanceDecision",
    "MessageType",
    "PaginatedResponse",
    "Policy",
    "PolicyStatus",
    "Priority",
    # Services
    "AgentService",
    "AuditService",
    "ComplianceService",
    "GovernanceService",
    "PolicyService",
]
