"""
ACGS-2 Enhanced Agent Bus - Workflow Module
Constitutional Hash: cdd01ef066bc6cf2

Entity Workflow patterns for agent lifecycle management.
Implements the Actor Model pattern with signals, queries, and activities.
"""

from .agent_entity_workflow import (
    AgentState,
    AgentConfig,
    AgentStatus,
    AgentResult,
    ShutdownRequest,
    Task,
    TaskResult,
    AgentEntityWorkflow,
    WorkflowActivity,
    initialize_agent_activity,
    execute_task_activity,
    checkpoint_agent_activity,
    shutdown_agent_activity,
)
from .workflow_base import (
    WorkflowDefinition,
    Signal,
    Query,
    Activity,
    WorkflowContext,
    WorkflowExecutor,
    InMemoryWorkflowExecutor,
)

__all__ = [
    # Agent Entity Workflow
    "AgentState",
    "AgentConfig",
    "AgentStatus",
    "AgentResult",
    "ShutdownRequest",
    "Task",
    "TaskResult",
    "AgentEntityWorkflow",
    "WorkflowActivity",
    "initialize_agent_activity",
    "execute_task_activity",
    "checkpoint_agent_activity",
    "shutdown_agent_activity",
    # Workflow Base
    "WorkflowDefinition",
    "Signal",
    "Query",
    "Activity",
    "WorkflowContext",
    "WorkflowExecutor",
    "InMemoryWorkflowExecutor",
]
