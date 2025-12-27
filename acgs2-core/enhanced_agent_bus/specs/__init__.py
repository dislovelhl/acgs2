"""
ACGS-2 Executable Specifications Module
Constitutional Hash: cdd01ef066bc6cf2

This module provides pytest fixtures and base classes for specification-based
testing following Gojko Adzic's Specification by Example methodology.
"""

from .fixtures import (
    constitutional_hash,
    timeout_budget_manager,
    metrics_registry,
    circuit_breaker,
    maci_framework,
    saga_manager,
    timeline,
    architecture_context,
    chaos_controller,
)

__all__ = [
    "constitutional_hash",
    "timeout_budget_manager",
    "metrics_registry",
    "circuit_breaker",
    "maci_framework",
    "saga_manager",
    "timeline",
    "architecture_context",
    "chaos_controller",
]
