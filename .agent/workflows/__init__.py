"""
ACGS-2 Agent Workflows
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive workflow orchestration for constitutional AI governance.

This package provides:
- Base workflow abstractions (BaseWorkflow, WorkflowStep, WorkflowContext)
- Constitutional validation workflows
- Multi-agent coordination workflows (voting, handoff)
- Distributed transaction sagas with LIFO compensation
- DAG-based parallel orchestration
- YAML template engine for declarative workflows

Example:
    from .agent.workflows import (
        WorkflowContext,
        ConstitutionalValidationWorkflow,
        DAGExecutor,
        DAGNode,
        BaseSaga,
        SagaStep,
    )

    # DAG-based parallel validation
    dag = DAGExecutor("validation-dag")
    dag.add_node(DAGNode("hash_check", "Validate Hash", validate_hash))
    dag.add_node(DAGNode("policy_check", "Check Policy", evaluate_policy, ["hash_check"]))
    result = await dag.execute(context)

    # Saga-based distributed transaction
    saga = BaseSaga("order-saga")
    saga.add_step(SagaStep("reserve", reserve_inventory, release_inventory))
    saga.add_step(SagaStep("charge", charge_payment, refund_payment))
    result = await saga.execute(context, {"order_id": "123"})
"""

from .config import (
    CONSTITUTIONAL_HASH,
    WorkflowType,
    FailurePolicy,
    WorkflowConfig,
    StepConfig,
    DAGConfig,
    SagaConfig,
    DEFAULT_WORKFLOW_CONFIG,
    PERFORMANCE_THRESHOLDS,
)

# Base abstractions
from .base import (
    BaseWorkflow,
    WorkflowStatus,
    WorkflowStep,
    StepStatus,
    WorkflowContext,
    WorkflowResult,
    BaseActivities,
)

# DAG orchestration
from .dags import (
    DAGNode,
    DAGExecutor,
    DAGResult,
)

# Saga pattern
from .sagas import (
    BaseSaga,
    SagaStep,
    SagaResult,
)

# Constitutional workflows
from .constitutional import (
    ConstitutionalValidationWorkflow,
    ValidationResult,
)

# Cyclic Orchestration (CEOS V1.0)
from .cyclic import (
    GlobalState,
    StateGraph,
)

# Coordination workflows
from .coordination import (
    VotingWorkflow,
    VotingResult,
    VotingStrategy,
    HandoffWorkflow,
    HandoffResult,
    SupervisorNode,
    WorkerNode,
)

# Template engine
from .templates import (
    TemplateEngine,
    WorkflowTemplate,
)

__version__ = "1.1.0"
__constitutional_hash__ = CONSTITUTIONAL_HASH

__all__ = [
    # Configuration
    "CONSTITUTIONAL_HASH",
    "WorkflowType",
    "FailurePolicy",
    "WorkflowConfig",
    "StepConfig",
    "DAGConfig",
    "SagaConfig",
    "DEFAULT_WORKFLOW_CONFIG",
    "PERFORMANCE_THRESHOLDS",
    # Base abstractions
    "BaseWorkflow",
    "WorkflowStatus",
    "WorkflowStep",
    "StepStatus",
    "WorkflowContext",
    "WorkflowResult",
    "BaseActivities",
    # DAG orchestration
    "DAGNode",
    "DAGExecutor",
    "DAGResult",
    # Saga pattern
    "BaseSaga",
    "SagaStep",
    "SagaResult",
    # Constitutional workflows
    "ConstitutionalValidationWorkflow",
    "ValidationResult",
    # Coordination workflows
    "VotingWorkflow",
    "VotingResult",
    "VotingStrategy",
    "HandoffWorkflow",
    "HandoffResult",
    # Template engine
    "TemplateEngine",
    "WorkflowTemplate",
    # Version
    "__version__",
    "__constitutional_hash__",
]
