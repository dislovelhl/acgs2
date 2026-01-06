"""
Escalation System for HITL Approvals (Compatibility Layer).
Constitutional Hash: cdd01ef066bc6cf2

All core logic has been moved to app.core.escalation package.
"""

from .escalation import (
    EscalationEngine,
    EscalationPolicyManager,
    EscalationReason,
    EscalationTimer,
    EscalationTimerError,
    EscalationTimerManager,
    RedisConnectionError,
    SLABreach,
    SLAConfig,
    SLAMetrics,
    SLAStatus,
    TimerNotFoundError,
    close_escalation_manager,
    get_escalation_engine,
    get_escalation_manager,
    get_policy_manager,
    initialize_escalation_manager,
    reset_escalation_engine,
    reset_escalation_manager,
    reset_policy_manager,
)

__all__ = [
    "EscalationReason",
    "SLAStatus",
    "EscalationTimerError",
    "RedisConnectionError",
    "TimerNotFoundError",
    "SLAConfig",
    "SLAMetrics",
    "SLABreach",
    "EscalationTimer",
    "EscalationTimerManager",
    "get_escalation_manager",
    "initialize_escalation_manager",
    "close_escalation_manager",
    "reset_escalation_manager",
    "EscalationPolicyManager",
    "get_policy_manager",
    "reset_policy_manager",
    "EscalationEngine",
    "get_escalation_engine",
    "reset_escalation_engine",
]
