"""
Guardrail Models for Runtime Safety.
Constitutional Hash: cdd01ef066bc6cf2
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from .enums import GuardrailLayer, SafetyAction, ViolationSeverity


@dataclass
class Violation:
    """A safety violation detected by guardrails."""

    layer: GuardrailLayer
    violation_type: str
    severity: ViolationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer.value,
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
        }


@dataclass
class GuardrailResult:
    """Result from a guardrail layer."""

    action: SafetyAction
    allowed: bool
    violations: List[Violation] = field(default_factory=list)
    modified_data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "modified_data": self.modified_data,
            "metadata": self.metadata,
            "processing_time_ms": self.processing_time_ms,
            "trace_id": self.trace_id,
        }
