"""
ACGS-2 Anti-Corruption Layer (ACL) Adapters
Constitutional Hash: cdd01ef066bc6cf2

This module provides ACL adapters for external dependencies used in the
breakthrough architecture. Each adapter isolates the core domain from
external system concerns including:

- Circuit breaker protection
- Rate limiting
- Timeout management
- Graceful degradation
- Retry with exponential backoff

Adapters:
- BaseACLAdapter: Abstract base class for all adapters
- Z3Adapter: SMT solver integration with caching
- OPAAdapter: Open Policy Agent with fail-closed mode
- DeepProbLogAdapter: Probabilistic logic programming (placeholder)
- PolisAdapter: Democratic deliberation API (placeholder)

Usage:
    from enhanced_agent_bus.acl_adapters import AdapterRegistry, Z3Adapter

    registry = AdapterRegistry()
    z3 = registry.get_or_create("z3", Z3Adapter, Z3AdapterConfig())
    result = await z3.call(Z3Request(formula="(assert (> x 0))"))
"""

from .base import (
    ACLAdapter,
    AdapterCircuitOpenError,
    AdapterConfig,
    AdapterResult,
    AdapterState,
    AdapterTimeoutError,
    RateLimitExceededError,
)
from .opa_adapter import OPAAdapter, OPAAdapterConfig, OPARequest, OPAResponse
from .registry import AdapterRegistry
from .z3_adapter import Z3Adapter, Z3AdapterConfig, Z3Request, Z3Response

# Constitutional hash for governance validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Base classes
    "ACLAdapter",
    "AdapterConfig",
    "AdapterResult",
    "AdapterState",
    # Exceptions
    "AdapterTimeoutError",
    "AdapterCircuitOpenError",
    "RateLimitExceededError",
    # Adapters
    "Z3Adapter",
    "Z3AdapterConfig",
    "Z3Request",
    "Z3Response",
    "OPAAdapter",
    "OPAAdapterConfig",
    "OPARequest",
    "OPAResponse",
    # Registry
    "AdapterRegistry",
]
