"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 CLI Module

Provides command-line interface tools for policy validation and testing.
Integrates with OPA (Open Policy Agent) for Rego policy evaluation.

Usage:
    python -m cli.policy_cli --help
    python -m cli.policy_cli validate <policy_file>
    python -m cli.policy_cli test <policy_file> --input <json_input>
"""

from .opa_service import (
    OPAConnectionError,
    OPAService,
    OPAServiceError,
    PolicyEvaluationResult,
    PolicyValidationResult,
)
from .policy_cli import app as cli_app

__all__ = [
    "OPAService",
    "OPAServiceError",
    "OPAConnectionError",
    "PolicyValidationResult",
    "PolicyEvaluationResult",
    "cli_app",
]
