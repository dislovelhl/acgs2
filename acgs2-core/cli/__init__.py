"""
ACGS-2 CLI Module

Provides command-line interface tools for policy validation and testing.
Integrates with OPA (Open Policy Agent) for Rego policy evaluation.
"""

from .opa_service import OPAService

__all__ = ["OPAService"]
