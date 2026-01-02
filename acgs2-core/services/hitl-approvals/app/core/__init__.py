"""
HITL Approvals Core Module

This module contains the core approval chain engine with routing logic,
status management, integration with notification providers, and OPA policy evaluation.
"""

from app.core.approval_engine import (
    ApprovalEngine,
    ApprovalEngineError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ChainNotFoundError,
)
from app.core.opa_client import (
    OPAClient,
    OPAClientError,
    OPAConnectionError,
    OPANotInitializedError,
    PolicyEvaluationError,
    close_opa_client,
    get_opa_client,
    initialize_opa_client,
    reset_opa_client,
)

__all__ = [
    # Approval Engine
    "ApprovalEngine",
    "ApprovalEngineError",
    "ApprovalNotFoundError",
    "ApprovalStateError",
    "ChainNotFoundError",
    # OPA Client
    "OPAClient",
    "OPAClientError",
    "OPAConnectionError",
    "OPANotInitializedError",
    "PolicyEvaluationError",
    "get_opa_client",
    "initialize_opa_client",
    "close_opa_client",
    "reset_opa_client",
]
