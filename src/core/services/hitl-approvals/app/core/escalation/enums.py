"""
Escalation Enums for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

from enum import Enum


class EscalationReason(str, Enum):
    """Reasons for escalation."""

    TIMEOUT = "timeout"
    MANUAL = "manual"
    SLA_BREACH = "sla_breach"
    NO_RESPONSE = "no_response"


class SLAStatus(str, Enum):
    """SLA compliance status."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    BREACHED = "breached"
    CRITICAL = "critical"
