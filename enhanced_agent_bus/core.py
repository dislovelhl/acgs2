"""
ACGS-2 Enhanced Agent Bus - Core Module (Backward Compatibility Facade)
Constitutional Hash: cdd01ef066bc6cf2

This module provides backward compatibility by re-exporting classes from
refactored modules. New code should import directly from:
- enhanced_agent_bus.message_processor (MessageProcessor)
- enhanced_agent_bus.agent_bus (EnhancedAgentBus, get_agent_bus, reset_agent_bus)
"""

# Re-export from refactored modules for backward compatibility
try:
    from .message_processor import MessageProcessor
    from .agent_bus import (
        EnhancedAgentBus,
        get_agent_bus,
        reset_agent_bus,
        DEFAULT_REDIS_URL,
    )
except ImportError:
    # Fallback for direct execution or testing
    from message_processor import MessageProcessor  # type: ignore
    from agent_bus import (  # type: ignore
        EnhancedAgentBus,
        get_agent_bus,
        reset_agent_bus,
        DEFAULT_REDIS_URL,
    )

# Re-export models and interfaces
try:
    from .models import (
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from .validators import ValidationResult
    from .interfaces import (
        AgentRegistry,
        MessageRouter,
        ValidationStrategy,
        ProcessingStrategy,
    )
    from .registry import (
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        RustValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        CompositeProcessingStrategy,
    )
except ImportError:
    # Fallback for direct execution or testing
    from models import (  # type: ignore
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from validators import ValidationResult  # type: ignore
    from interfaces import (  # type: ignore
        AgentRegistry,
        MessageRouter,
        ValidationStrategy,
        ProcessingStrategy,
    )
    from registry import (  # type: ignore
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        RustValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
    )

# Re-export feature flags
try:
    from shared.metrics import MESSAGES_TOTAL
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

try:
    from shared.circuit_breaker import get_circuit_breaker
    CIRCUIT_BREAKER_ENABLED = True
except ImportError:
    CIRCUIT_BREAKER_ENABLED = False

try:
    import enhanced_agent_bus_rust as rust_bus
    USE_RUST = True
except ImportError:
    USE_RUST = False
    rust_bus = None

# Backward compatibility alias
ConstitutionalValidationStrategy = StaticHashValidationStrategy

__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    "USE_RUST",
    "DEFAULT_REDIS_URL",
    "METRICS_ENABLED",
    "CIRCUIT_BREAKER_ENABLED",
    # Core Classes
    "MessageProcessor",
    "EnhancedAgentBus",
    # Models
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "DecisionLog",
    "ValidationResult",
    # Protocol Interfaces (DI)
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "ProcessingStrategy",
    # Default Implementations (DI)
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "ConstitutionalValidationStrategy",
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    # Processing Strategies (DI)
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    "OPAProcessingStrategy",
    "OPAValidationStrategy",
    "CompositeProcessingStrategy",
    # Functions
    "get_agent_bus",
    "reset_agent_bus",
]
