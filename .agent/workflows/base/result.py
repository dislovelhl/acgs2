"""
ACGS-2 Workflow Result
Constitutional Hash: cdd01ef066bc6cf2

Workflow execution outcome with audit information.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class WorkflowStatus(Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    PARTIALLY_COMPENSATED = "partially_compensated"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class WorkflowResult:
    """
    Result of workflow execution with full audit information.

    Attributes:
        workflow_id: Unique workflow instance identifier
        status: Final execution status
        output: Workflow output data (if successful)
        execution_time_ms: Total execution time in milliseconds
        steps_completed: List of successfully completed steps
        steps_failed: List of failed steps
        compensations_executed: List of executed compensations
        audit_hash: Blockchain audit trail hash
        constitutional_hash: Constitutional hash used
        errors: List of errors during execution
        metadata: Additional result metadata
    """

    workflow_id: str
    status: WorkflowStatus
    output: Optional[Any] = None
    execution_time_ms: float = 0.0
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    compensations_executed: List[str] = field(default_factory=list)
    compensations_failed: List[str] = field(default_factory=list)
    audit_hash: Optional[str] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_successful(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.status in (
            WorkflowStatus.FAILED,
            WorkflowStatus.TIMED_OUT,
            WorkflowStatus.PARTIALLY_COMPENSATED,
        )

    @property
    def is_compensated(self) -> bool:
        """Check if compensations were executed."""
        return self.status in (
            WorkflowStatus.COMPENSATED,
            WorkflowStatus.PARTIALLY_COMPENSATED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "output": self.output,
            "execution_time_ms": self.execution_time_ms,
            "steps_completed": self.steps_completed.copy(),
            "steps_failed": self.steps_failed.copy(),
            "compensations_executed": self.compensations_executed.copy(),
            "compensations_failed": self.compensations_failed.copy(),
            "audit_hash": self.audit_hash,
            "constitutional_hash": self.constitutional_hash,
            "errors": self.errors.copy(),
            "metadata": self.metadata.copy(),
            "completed_at": self.completed_at.isoformat(),
            "is_successful": self.is_successful,
            "is_failed": self.is_failed,
            "is_compensated": self.is_compensated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowResult":
        """Create result from dictionary."""
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        elif completed_at is None:
            completed_at = datetime.now(timezone.utc)

        return cls(
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            output=data.get("output"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            steps_completed=data.get("steps_completed", []),
            steps_failed=data.get("steps_failed", []),
            compensations_executed=data.get("compensations_executed", []),
            compensations_failed=data.get("compensations_failed", []),
            audit_hash=data.get("audit_hash"),
            constitutional_hash=data.get("constitutional_hash", CONSTITUTIONAL_HASH),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
            completed_at=completed_at,
        )

    @classmethod
    def success(
        cls,
        workflow_id: str,
        output: Any,
        execution_time_ms: float,
        steps_completed: List[str],
        audit_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowResult":
        """Factory method for successful result."""
        return cls(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            output=output,
            execution_time_ms=execution_time_ms,
            steps_completed=steps_completed,
            audit_hash=audit_hash,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        workflow_id: str,
        errors: List[str],
        execution_time_ms: float,
        steps_completed: List[str],
        steps_failed: List[str],
        compensations_executed: Optional[List[str]] = None,
        compensations_failed: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowResult":
        """Factory method for failed result."""
        status = WorkflowStatus.FAILED
        if compensations_executed:
            if compensations_failed:
                status = WorkflowStatus.PARTIALLY_COMPENSATED
            else:
                status = WorkflowStatus.COMPENSATED

        return cls(
            workflow_id=workflow_id,
            status=status,
            execution_time_ms=execution_time_ms,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            compensations_executed=compensations_executed or [],
            compensations_failed=compensations_failed or [],
            errors=errors,
            metadata=metadata or {},
        )

    @classmethod
    def timeout(
        cls,
        workflow_id: str,
        execution_time_ms: float,
        steps_completed: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowResult":
        """Factory method for timeout result."""
        return cls(
            workflow_id=workflow_id,
            status=WorkflowStatus.TIMED_OUT,
            execution_time_ms=execution_time_ms,
            steps_completed=steps_completed,
            errors=["Workflow timed out"],
            metadata=metadata or {},
        )


__all__ = ["WorkflowStatus", "WorkflowResult"]
