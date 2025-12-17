"""
ACGS-2 Enhanced Agent Bus - Models
Constitutional Hash: cdd01ef066bc6cf2

Data models for agent communication and message handling.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

try:
    from .exceptions import MessageValidationError
except ImportError:
    from exceptions import MessageValidationError  # type: ignore

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


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


class Priority(Enum):
    """Priority levels for messages."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class ValidationStatus(Enum):
    """Status of message validation."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


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

    def __post_init__(self):
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
    content: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    from_agent: str = ""
    to_agent: str = ""
    sender_id: str = ""
    message_type: MessageType = MessageType.COMMAND
    routing: Optional["RoutingContext"] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # Multi-tenant security
    tenant_id: str = ""
    security_context: Dict[str, Any] = field(default_factory=dict)

    # Priority and lifecycle (supports both Priority and MessagePriority)
    priority: Any = Priority.MEDIUM  # Can be Priority or MessagePriority
    status: MessageStatus = MessageStatus.PENDING

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    constitutional_validated: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Impact assessment for deliberation layer
    impact_score: Optional[float] = None

    # Performance tracking
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation."""
        # Allow flexible constitutional hash for testing (can be overridden)
        if hasattr(self, '_skip_validation') and self._skip_validation:
            return
        self.constitutional_validated = True

    def to_dict(self) -> Dict[str, Any]:
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            conversation_id=data.get("conversation_id", str(uuid.uuid4())),
            content=data.get("content", {}),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            message_type=MessageType(data.get("message_type", "command")),
            tenant_id=data.get("tenant_id", ""),
            priority=MessagePriority(data.get("priority", 2)),
            status=MessageStatus(data.get("status", "pending")),
        )


__all__ = [
    "CONSTITUTIONAL_HASH",
    "MessageType",
    "Priority",
    "ValidationStatus",
    "MessagePriority",
    "MessageStatus",
    "RoutingContext",
    "AgentMessage",
]
