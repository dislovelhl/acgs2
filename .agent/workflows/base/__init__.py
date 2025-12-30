"""
ACGS-2 Base Workflow Abstractions
Constitutional Hash: cdd01ef066bc6cf2

Core abstractions for all workflow types:
- BaseWorkflow: Abstract base class for workflows
- WorkflowStep: Individual step with compensation
- WorkflowContext: State container for execution
- WorkflowResult: Outcome with audit information
- Activities: Interface for external operations
"""

from .activities import BaseActivities
from .context import WorkflowContext
from .result import WorkflowResult
from .step import StepStatus, WorkflowStep
from .workflow import BaseWorkflow, WorkflowStatus

__all__ = [
    "BaseWorkflow",
    "WorkflowStatus",
    "WorkflowStep",
    "StepStatus",
    "WorkflowContext",
    "WorkflowResult",
    "BaseActivities",
]
