"""
ACGS-2 Enhanced Agent Communication Bus
Constitutional Hash: cdd01ef066bc6cf2

High-performance, multi-tenant agent communication infrastructure for ACGS-2
constitutional governance platform.
"""

__version__ = "2.0.0"
__constitutional_hash__ = "cdd01ef066bc6cf2"

# Import centralized constitutional hash from shared module
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
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
from .interfaces import (
    AgentRegistry,
    MessageRouter,
    ValidationStrategy,
    MessageHandler,
    MetricsCollector,
)
from .registry import (
    InMemoryAgentRegistry,
    DirectMessageRouter,
    CapabilityBasedRouter,
    StaticHashValidationStrategy,
    DynamicPolicyValidationStrategy,
    RustValidationStrategy,
    CompositeValidationStrategy,
    RedisAgentRegistry,
)
from .validators import (
    ValidationResult,
)
from .validation_integration_example import (
    IntegratedValidationSystem,
)
from .exceptions import (
    # Base
    AgentBusError,
    # Constitutional
    ConstitutionalError,
    ConstitutionalHashMismatchError,
    ConstitutionalValidationError,
    # Message
    MessageError,
    MessageValidationError,
    MessageDeliveryError,
    MessageTimeoutError,
    MessageRoutingError,
    # Agent
    AgentError,
    AgentNotRegisteredError,
    AgentAlreadyRegisteredError,
    AgentCapabilityError,
    # Policy/OPA
    PolicyError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    OPAConnectionError,
    OPANotInitializedError,
    # Deliberation
    DeliberationError,
    DeliberationTimeoutError,
    SignatureCollectionError,
    ReviewConsensusError,
    # Bus Operations
    BusOperationError,
    BusNotStartedError,
    BusAlreadyStartedError,
    HandlerExecutionError,
    # Configuration
    ConfigurationError,
)

__all__ = [
    "CONSTITUTIONAL_HASH",
    # Models
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "Priority",
    "ValidationStatus",
    "RoutingContext",
    # Core
    "EnhancedAgentBus",
    "MessageProcessor",
    "ValidationResult",
    "IntegratedValidationSystem",
    # Protocol Interfaces (DI)
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "MessageHandler",
    "MetricsCollector",
    # Default Implementations (DI)
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
    "RedisAgentRegistry",
    # Exceptions - Base
    "AgentBusError",
    # Exceptions - Constitutional
    "ConstitutionalError",
    "ConstitutionalHashMismatchError",
    "ConstitutionalValidationError",
    # Exceptions - Message
    "MessageError",
    "MessageValidationError",
    "MessageDeliveryError",
    "MessageTimeoutError",
    "MessageRoutingError",
    # Exceptions - Agent
    "AgentError",
    "AgentNotRegisteredError",
    "AgentAlreadyRegisteredError",
    "AgentCapabilityError",
    # Exceptions - Policy/OPA
    "PolicyError",
    "PolicyEvaluationError",
    "PolicyNotFoundError",
    "OPAConnectionError",
    "OPANotInitializedError",
    # Exceptions - Deliberation
    "DeliberationError",
    "DeliberationTimeoutError",
    "SignatureCollectionError",
    "ReviewConsensusError",
    # Exceptions - Bus Operations
    "BusOperationError",
    "BusNotStartedError",
    "BusAlreadyStartedError",
    "HandlerExecutionError",
    # Exceptions - Configuration
    "ConfigurationError",
]
