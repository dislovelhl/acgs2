"""
ACGS-2 Enhanced Agent Communication Bus
Constitutional Hash: cdd01ef066bc6cf2

High-performance, multi-tenant agent communication infrastructure for ACGS-2
constitutional governance platform.
"""

__version__ = "2.0.0"
__constitutional_hash__ = "cdd01ef066bc6cf2"

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

from .models import (
    AgentMessage,
    MessageType,
    MessagePriority,
    MessageStatus,
    Priority,
    ValidationStatus,
    RoutingContext,
    CONSTITUTIONAL_HASH as MODEL_HASH,
)
from .core import (
    EnhancedAgentBus,
    MessageProcessor,
)
from .validators import (
    ValidationResult,
)
from .validation_integration_example import (
    IntegratedValidationSystem,
)

__all__ = [
    "CONSTITUTIONAL_HASH",
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "Priority",
    "ValidationStatus",
    "RoutingContext",
    "EnhancedAgentBus",
    "MessageProcessor",
    "ValidationResult",
    "IntegratedValidationSystem",
]
