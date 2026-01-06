"""
Escalation Exceptions for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""


class EscalationTimerError(Exception):
    """Base exception for escalation timer errors."""

    pass


class RedisConnectionError(EscalationTimerError):
    """Raised when Redis connection fails."""

    pass


class TimerNotFoundError(EscalationTimerError):
    """Raised when a timer is not found."""

    pass
