"""
ACGS-2 Pytest Fixtures for Executable Specifications
Constitutional Hash: cdd01ef066bc6cf2

Provides reusable fixtures for specification-based testing across all
architectural layers.
"""

from .architecture import architecture_context, layer_context
from .constitutional import constitutional_hash, hash_validator
from .governance import consensus_checker, policy_verifier
from .observability import metrics_registry, timeout_budget_manager, tracing_context
from .resilience import chaos_controller, circuit_breaker, saga_manager
from .temporal import causal_validator, timeline
from .verification import maci_framework, z3_solver_context

__all__ = [
    # Constitutional
    "constitutional_hash",
    "hash_validator",
    # Observability
    "timeout_budget_manager",
    "metrics_registry",
    "tracing_context",
    # Resilience
    "circuit_breaker",
    "chaos_controller",
    "saga_manager",
    # Verification
    "maci_framework",
    "z3_solver_context",
    # Temporal
    "timeline",
    "causal_validator",
    # Governance
    "consensus_checker",
    "policy_verifier",
    # Architecture
    "architecture_context",
    "layer_context",
]
