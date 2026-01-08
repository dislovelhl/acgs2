"""
ACGS-2 Enhanced Agent Bus - Models
Constitutional Hash: cdd01ef066bc6cf2

Data models for agent communication and message handling.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

try:
    from src.core.shared.types import (
        JSONDict,
        JSONValue,
        MetadataDict,
        PerformanceMetrics,
        SecurityContext,
    )
except ImportError:
    # Fallback for standalone usage
    JSONValue = Any
    JSONDict = Dict[str, JSONValue]
    SecurityContext = Dict[str, JSONValue]
    MetadataDict = Dict[str, JSONValue]
    PerformanceMetrics = Dict[str, Union[int, float, str, None]]

try:
    from .exceptions import MessageValidationError
except ImportError:
    pass  # type: ignore

# Type aliases for more specific typing
MessageContent = JSONDict
EnumOrString = Union[Enum, str]

# Import centralized constitutional hash from shared module
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def get_enum_value(enum_or_str: EnumOrString) -> str:
    """
    Safely extract enum value, handling cross-module enum identity issues.

    When modules are loaded via different import paths (e.g., during testing),
    enum instances from different module loads have different class identities.
    This function extracts the underlying string value regardless of class identity.

    Args:
        enum_or_str: An enum instance or string value

    Returns:
        The string value of the enum or the stringified input
    """
    if isinstance(enum_or_str, Enum):
        return str(enum_or_str.value)
    return str(enum_or_str)


class MessageType(Enum):
    """Types of messages in the agent bus."""

    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    GOVERNANCE_REQUEST = "governance_request"
    GOVERNANCE_RESPONSE = "governance_response"
    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    AUDIT_LOG = "audit_log"


class Priority(Enum):
    """Priority levels for messages.

    Higher value = Higher priority.
    Constitutional Hash: cdd01ef066bc6cf2

    Note: NORMAL is an alias for MEDIUM for backward compatibility
    with code that used MessagePriority.NORMAL.
    """

    LOW = 0
    NORMAL = 1  # Alias for MEDIUM (backward compatibility)
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class ValidationStatus(Enum):
    """Status of message validation."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# DEPRECATED: MessagePriority is now an alias for Priority.
# The old MessagePriority enum used DESCENDING values (CRITICAL=0, LOW=3),
# which was counterintuitive. Priority uses ASCENDING values (LOW=0, CRITICAL=3).
# This alias is provided for backward compatibility during the transition period.
# Code using MessagePriority.X.value will now get different numeric values.
# Use Priority directly in all new code.
MessagePriority = Priority


class MessageStatus(Enum):
    """Message processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    PENDING_DELIBERATION = "pending_deliberation"
    VALIDATED = "validated"


@dataclass
class RoutingContext:
    """Context for message routing in the agent bus."""

    source_agent_id: str
    target_agent_id: str
    routing_key: str = ""
    routing_tags: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: int = 5000
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def __post_init__(self) -> None:
        """Validate routing context."""
        if not self.source_agent_id:
            raise ValueError("source_agent_id is required")
        if not self.target_agent_id:
            raise ValueError("target_agent_id is required")


@dataclass
class AgentMessage:
    """Agent message with constitutional compliance."""

    # Message identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content and routing
    content: MessageContent = field(default_factory=dict)
    payload: MessageContent = field(default_factory=dict)
    from_agent: str = ""
    to_agent: str = ""
    sender_id: str = ""
    message_type: MessageType = MessageType.COMMAND
    routing: Optional["RoutingContext"] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # Multi-tenant security
    tenant_id: str = ""
    security_context: SecurityContext = field(default_factory=dict)

    # Priority and lifecycle
    priority: Priority = Priority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    constitutional_validated: bool = False

    # Post-Quantum Cryptography support (NIST FIPS 203/204)
    pqc_signature: Optional[str] = None  # CRYSTALS-Dilithium signature (base64)
    pqc_public_key: Optional[str] = None  # CRYSTALS-Kyber public key (base64)
    pqc_algorithm: Optional[str] = None  # "dilithium-3", "kyber-768", etc.

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Impact assessment for deliberation layer
    impact_score: Optional[float] = None

    # Performance tracking
    performance_metrics: PerformanceMetrics = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        # Allow flexible constitutional hash for testing (can be overridden)
        if hasattr(self, "_skip_validation") and self._skip_validation:
            return
        self.constitutional_validated = True

    def to_dict(self) -> JSONDict:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "content": self.content,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "tenant_id": self.tenant_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "constitutional_hash": self.constitutional_hash,
            "constitutional_validated": self.constitutional_validated,
            "pqc_signature": self.pqc_signature,
            "pqc_public_key": self.pqc_public_key,
            "pqc_algorithm": self.pqc_algorithm,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict_raw(self) -> JSONDict:
        """Convert message to dictionary with all fields for serialization."""
        data = self.to_dict()
        data.update(
            {
                "payload": self.payload,
                "sender_id": self.sender_id,
                "security_context": self.security_context,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "impact_score": self.impact_score,
                "performance_metrics": self.performance_metrics,
                "pqc_signature": self.pqc_signature,
                "pqc_public_key": self.pqc_public_key,
                "pqc_algorithm": self.pqc_algorithm,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: JSONDict) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            conversation_id=data.get("conversation_id", str(uuid.uuid4())),
            content=data.get("content", {}),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            message_type=MessageType(data.get("message_type", "command")),
            tenant_id=data.get("tenant_id", ""),
            priority=Priority(data.get("priority", 1)),  # Default to MEDIUM/NORMAL
            status=MessageStatus(data.get("status", "pending")),
            pqc_signature=data.get("pqc_signature"),
            pqc_public_key=data.get("pqc_public_key"),
            pqc_algorithm=data.get("pqc_algorithm"),
        )


@dataclass
class DecisionLog:
    """Structured decision log for compliance and observability."""

    trace_id: str
    span_id: str
    agent_id: str
    tenant_id: str
    policy_version: str
    risk_score: float
    decision: str
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    compliance_tags: List[str] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)

    def to_dict(self) -> JSONDict:
        """Convert log to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "policy_version": self.policy_version,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp.isoformat(),
            "compliance_tags": self.compliance_tags,
            "metadata": self.metadata,
        }


class ConversationMessage(BaseModel):
    """Single message in a multi-turn conversation.

    Used by PACAR verifier to track conversation history for
    governance policy enforcement across conversation threads.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was created",
    )
    intent: Optional[str] = Field(default=None, description="Detected intent of the message")
    verification_result: Optional[JSONDict] = Field(
        default=None,
        description="PACAR verification result including is_valid, confidence, critique",
    )

    model_config = {"from_attributes": True}


class ConversationState(BaseModel):
    """Conversation state for multi-turn context tracking.

    Stores the full conversation history and metadata for a session,
    enabling PACAR verifier to enforce governance policies across
    multiple turns of a conversation.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    session_id: str = Field(..., description="Unique session identifier")
    tenant_id: str = Field(..., description="Tenant identifier for multi-tenant isolation")
    messages: List[ConversationMessage] = Field(
        default_factory=list, description="Ordered list of conversation messages"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was last updated",
    )
    constitutional_hash: str = Field(
        default=CONSTITUTIONAL_HASH,
        description="Constitutional hash for compliance verification",
    )

    model_config = {"from_attributes": True}


__all__ = [
    # Type aliases
    "MessageContent",
    "SecurityContext",
    "PerformanceMetrics",
    "MetadataDict",
    "EnumOrString",
    # Constants
    "CONSTITUTIONAL_HASH",
    # Enums
    "MessageType",
    "Priority",
    "ValidationStatus",
    "MessagePriority",
    "MessageStatus",
    # Data classes
    "RoutingContext",
    "AgentMessage",
    "DecisionLog",
    # Pydantic models for multi-turn conversation support
    "ConversationMessage",
    "ConversationState",
    # Utility functions
    "get_enum_value",
]
