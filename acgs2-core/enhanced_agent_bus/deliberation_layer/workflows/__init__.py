"""
ACGS-2 Temporal Workflow Patterns for Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2

This module implements Temporal-based workflow orchestration patterns:
1. DeliberationWorkflow - Main workflow for high-impact message processing
2. ConstitutionalSagaWorkflow - Saga pattern with compensation for constitutional operations
3. AgentLifecycleWorkflow - Entity workflow for agent state management
4. HumanApprovalWorkflow - Async callback pattern for HITL approval

Reference: https://docs.temporal.io/workflows
"""

from .constitutional_saga import (
    ConstitutionalSagaWorkflow,
    SagaActivities,
    SagaCompensation,
    SagaStep,
)
from .deliberation_workflow import (
    DeliberationActivities,
    DeliberationWorkflow,
    DeliberationWorkflowInput,
    DeliberationWorkflowResult,
)

# from .agent_lifecycle import (
#     AgentLifecycleWorkflow,
#     AgentState,
#     AgentLifecycleActivities,
# )
# from .human_approval import (
#     HumanApprovalWorkflow,
#     ApprovalRequest,
#     ApprovalDecision,
#     ApprovalActivities,
# )

__all__ = [
    # Deliberation Workflow
    "DeliberationWorkflow",
    "DeliberationActivities",
    "DeliberationWorkflowInput",
    "DeliberationWorkflowResult",
    # Constitutional Saga
    "ConstitutionalSagaWorkflow",
    "SagaStep",
    "SagaCompensation",
    "SagaActivities",
    # Agent Lifecycle
    # "AgentLifecycleWorkflow",
    # "AgentState",
    # "AgentLifecycleActivities",
    # Human Approval
    # "HumanApprovalWorkflow",
    # "ApprovalRequest",
    # "ApprovalDecision",
    # "ApprovalActivities",
]
