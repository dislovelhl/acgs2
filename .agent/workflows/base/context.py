"""
ACGS-2 Workflow Context
Constitutional Hash: cdd01ef066bc6cf2

State container passed through workflow execution.
Accumulates results from each step and provides shared state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class WorkflowContext:
    """
    Context passed through workflow execution.

    Accumulates results from each step and provides shared state.
    Thread-safe for concurrent step execution.

    Attributes:
        workflow_id: Unique workflow instance identifier
        constitutional_hash: Expected constitutional hash for validation
        tenant_id: Multi-tenant isolation identifier
        correlation_id: Tracing correlation identifier
        step_results: Results from completed steps
        errors: Accumulated errors during execution
        metadata: Additional context data
        started_at: Workflow start timestamp
    """
    workflow_id: str
    constitutional_hash: str = CONSTITUTIONAL_HASH
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_workflow_id: Optional[str] = None
    trace_id: Optional[str] = None

    def __post_init__(self):
        """Initialize derived fields."""
        if self.trace_id is None:
            self.trace_id = str(uuid.uuid4())
        if self.correlation_id is None:
            self.correlation_id = self.trace_id

    def get_step_result(self, step_name: str) -> Optional[Any]:
        """
        Get result from a previously completed step.

        Args:
            step_name: Name of the step

        Returns:
            Step result if available, None otherwise
        """
        return self.step_results.get(step_name)

    def set_step_result(self, step_name: str, result: Any) -> None:
        """
        Store result from a completed step.

        Args:
            step_name: Name of the step
            result: Step execution result
        """
        self.step_results[step_name] = result

    def has_step_result(self, step_name: str) -> bool:
        """Check if a step has completed with a result."""
        return step_name in self.step_results

    def add_error(self, error: str) -> None:
        """Add an error to the context."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0

    def get_elapsed_time_ms(self) -> float:
        """Get elapsed time since workflow start in milliseconds."""
        elapsed = datetime.now(timezone.utc) - self.started_at
        return elapsed.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "constitutional_hash": self.constitutional_hash,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "step_results": self.step_results.copy(),
            "errors": self.errors.copy(),
            "metadata": self.metadata.copy(),
            "started_at": self.started_at.isoformat(),
            "parent_workflow_id": self.parent_workflow_id,
            "trace_id": self.trace_id,
            "elapsed_time_ms": self.get_elapsed_time_ms(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """Create context from dictionary."""
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        elif started_at is None:
            started_at = datetime.now(timezone.utc)

        return cls(
            workflow_id=data["workflow_id"],
            constitutional_hash=data.get("constitutional_hash", CONSTITUTIONAL_HASH),
            tenant_id=data.get("tenant_id"),
            correlation_id=data.get("correlation_id"),
            step_results=data.get("step_results", {}),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
            started_at=started_at,
            parent_workflow_id=data.get("parent_workflow_id"),
            trace_id=data.get("trace_id"),
        )

    @classmethod
    def create(
        cls,
        tenant_id: Optional[str] = None,
        parent_workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowContext":
        """
        Factory method to create a new workflow context.

        Args:
            tenant_id: Optional tenant identifier
            parent_workflow_id: Optional parent workflow for sub-workflows
            metadata: Optional initial metadata

        Returns:
            New WorkflowContext instance
        """
        return cls(
            workflow_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parent_workflow_id=parent_workflow_id,
            metadata=metadata or {},
        )

    def create_child_context(self, child_workflow_id: Optional[str] = None) -> "WorkflowContext":
        """
        Create a child context for sub-workflow execution.

        Inherits tenant_id, correlation_id, and metadata from parent.

        Args:
            child_workflow_id: Optional specific ID for child workflow

        Returns:
            New child WorkflowContext
        """
        return WorkflowContext(
            workflow_id=child_workflow_id or str(uuid.uuid4()),
            constitutional_hash=self.constitutional_hash,
            tenant_id=self.tenant_id,
            correlation_id=self.correlation_id,
            metadata=self.metadata.copy(),
            parent_workflow_id=self.workflow_id,
            trace_id=self.trace_id,
        )

    def merge_child_results(self, child_context: "WorkflowContext", prefix: str = "") -> None:
        """
        Merge results from a child workflow context.

        Args:
            child_context: Child workflow context
            prefix: Optional prefix for step result keys
        """
        for step_name, result in child_context.step_results.items():
            key = f"{prefix}{step_name}" if prefix else step_name
            self.step_results[key] = result

        self.errors.extend(child_context.errors)


__all__ = ["WorkflowContext"]
