"""
HITL Approvals Core Module

This module contains the core approval chain engine with routing logic,
status management, integration with notification providers, OPA policy evaluation,
and Redis-backed escalation timer system.
"""

from app.core.approval_engine import (
    ApprovalEngine,
    ApprovalEngineError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ChainNotFoundError,
)
from app.core.escalation import (
    EscalationCallback,
    EscalationEngine,
    EscalationReason,
    EscalationTimer,
    EscalationTimerError,
    EscalationTimerManager,
    RedisConnectionError,
    TimerNotFoundError,
    close_escalation_manager,
    get_escalation_engine,
    get_escalation_manager,
    initialize_escalation_manager,
    reset_escalation_engine,
    reset_escalation_manager,
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
    # Escalation Timer System
    "EscalationTimerManager",
    "EscalationTimer",
    "EscalationTimerError",
    "RedisConnectionError",
    "TimerNotFoundError",
    "EscalationReason",
    "EscalationCallback",
    "EscalationEngine",
    "get_escalation_manager",
    "initialize_escalation_manager",
    "close_escalation_manager",
    "reset_escalation_manager",
    "get_escalation_engine",
    "reset_escalation_engine",
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
