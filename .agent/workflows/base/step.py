"""
ACGS-2 Workflow Step
Constitutional Hash: cdd01ef066bc6cf2

Individual workflow step with compensation support.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


T = TypeVar("T")


class StepStatus(Enum):
    """Status of individual workflow step."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


@dataclass
class StepCompensation:
    """
    Compensation action for a workflow step.

    Compensations are idempotent operations that undo the effects of a step.
    They must be safe to call multiple times.

    CRITICAL: Register compensation BEFORE executing the step.

    Attributes:
        name: Unique name for the compensation
        execute: Async function that performs the compensation
        description: Human-readable description
        idempotency_key: Key for deduplication
        max_retries: Maximum retry attempts
        retry_delay_seconds: Delay between retries
    """

    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[bool]]
    description: str = ""
    idempotency_key: Optional[str] = None
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    def __hash__(self):
        return hash(self.name)


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.

    Each step has:
    - An execution function (activity)
    - An optional compensation function (for rollback)
    - Configuration for retries and timeouts
    - Constitutional validation option

    IMPORTANT: The saga pattern requires registering compensation BEFORE
    executing the step. This ensures proper LIFO rollback on failure.

    Attributes:
        name: Unique step name within workflow
        execute: Async function that performs the step
        compensation: Optional compensation for rollback
        description: Human-readable description
        timeout_seconds: Maximum execution time
        max_retries: Maximum retry attempts
        is_optional: If True, failure doesn't stop workflow
        requires_constitutional_check: Validate hash before execution
        depends_on: List of step names this step depends on
    """

    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[T]]
    compensation: Optional[StepCompensation] = None
    description: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    is_optional: bool = False
    requires_constitutional_check: bool = True
    requires_previous: bool = True
    depends_on: list = field(default_factory=list)

    # Runtime state (not for initialization)
    status: StepStatus = field(default=StepStatus.PENDING, init=False)
    result: Optional[Any] = field(default=None, init=False)
    error: Optional[str] = field(default=None, init=False)
    started_at: Optional[datetime] = field(default=None, init=False)
    completed_at: Optional[datetime] = field(default=None, init=False)
    execution_time_ms: float = field(default=0.0, init=False)
    attempt_count: int = field(default=0, init=False)

    def __hash__(self):
        return hash(self.name)

    def mark_executing(self) -> None:
        """Mark step as executing."""
        self.status = StepStatus.EXECUTING
        self.started_at = datetime.now(timezone.utc)
        self.attempt_count += 1

    def mark_completed(self, result: Any) -> None:
        """Mark step as completed with result."""
        self.status = StepStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            self.execution_time_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def mark_failed(self, error: str) -> None:
        """Mark step as failed with error."""
        self.status = StepStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            self.execution_time_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def mark_skipped(self) -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED

    def mark_compensating(self) -> None:
        """Mark step compensation as in progress."""
        self.status = StepStatus.COMPENSATING

    def mark_compensated(self) -> None:
        """Mark step as compensated."""
        self.status = StepStatus.COMPENSATED

    def mark_compensation_failed(self) -> None:
        """Mark step compensation as failed."""
        self.status = StepStatus.COMPENSATION_FAILED

    def can_retry(self) -> bool:
        """Check if step can be retried."""
        return self.attempt_count < self.max_retries

    def reset(self) -> None:
        """Reset step state for re-execution."""
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.execution_time_ms = 0.0
        self.attempt_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "attempt_count": self.attempt_count,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "is_optional": self.is_optional,
            "requires_constitutional_check": self.requires_constitutional_check,
            "has_compensation": self.compensation is not None,
            "depends_on": self.depends_on,
        }


def step(
    name: str,
    description: str = "",
    timeout_seconds: int = 30,
    max_retries: int = 3,
    is_optional: bool = False,
    requires_constitutional_check: bool = True,
    depends_on: Optional[list] = None,
):
    """
    Decorator to create a workflow step from a function.

    Example:
        @step("validate_input", description="Validate input data")
        async def validate_input(context: Dict[str, Any]) -> bool:
            return context.get("input") is not None
    """

    def decorator(func: Callable[[Dict[str, Any]], Awaitable[T]]) -> WorkflowStep:
        return WorkflowStep(
            name=name,
            execute=func,
            description=description,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            is_optional=is_optional,
            requires_constitutional_check=requires_constitutional_check,
            depends_on=depends_on or [],
        )

    return decorator


def with_compensation(
    compensation_name: str,
    description: str = "",
    max_retries: int = 3,
):
    """
    Decorator to add compensation to a workflow step.

    Example:
        @with_compensation("release_lock", description="Release acquired lock")
        async def release_lock(context: Dict[str, Any]) -> bool:
            lock_id = context.get("acquire_lock", {}).get("lock_id")
            return await release(lock_id)
    """

    def decorator(func: Callable[[Dict[str, Any]], Awaitable[bool]]) -> StepCompensation:
        return StepCompensation(
            name=compensation_name,
            execute=func,
            description=description,
            max_retries=max_retries,
        )

    return decorator


__all__ = [
    "StepStatus",
    "StepCompensation",
    "WorkflowStep",
    "step",
    "with_compensation",
]
