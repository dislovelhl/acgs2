"""
Escalation Package for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

from .engine import EscalationEngine, get_escalation_engine, reset_escalation_engine
from .enums import EscalationReason, SLAStatus
from .exceptions import EscalationTimerError, RedisConnectionError, TimerNotFoundError
from .models import EscalationTimer, SLABreach, SLAConfig, SLAMetrics
from .policy_manager import EscalationPolicyManager, get_policy_manager, reset_policy_manager
from .timer_manager import (
    EscalationTimerManager,
    close_escalation_manager,
    get_escalation_manager,
    initialize_escalation_manager,
    reset_escalation_manager,
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
