"""
ACGS-2 Workflow Configuration
Constitutional Hash: cdd01ef066bc6cf2

Central configuration for all workflow components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class WorkflowType(Enum):
    """Types of workflow execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DAG = "dag"
    SAGA = "saga"


class FailurePolicy(Enum):
    """How to handle failures in workflows."""

    FAIL_CLOSED = "fail_closed"  # Reject on any failure (default, secure)
    FAIL_OPEN = "fail_open"  # Allow on failure (audit only)
    COMPENSATE = "compensate"  # Run compensations on failure


@dataclass
class WorkflowConfig:
    """
    Configuration for workflow execution.

    Attributes:
        timeout_seconds: Maximum workflow execution time
        max_retries: Maximum retry attempts per step
        require_constitutional_validation: Enforce hash validation
        constitutional_hash: Expected constitutional hash
        enable_audit_trail: Record to blockchain audit
        failure_policy: How to handle failures
        enable_metrics: Emit Prometheus metrics
        enable_tracing: Emit OpenTelemetry traces
    """

    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    require_constitutional_validation: bool = True
    constitutional_hash: str = CONSTITUTIONAL_HASH
    enable_audit_trail: bool = True
    failure_policy: FailurePolicy = FailurePolicy.FAIL_CLOSED
    enable_metrics: bool = True
    enable_tracing: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_fail_closed(self) -> bool:
        """Check if workflow uses fail-closed policy."""
        return self.failure_policy == FailurePolicy.FAIL_CLOSED


@dataclass
class StepConfig:
    """
    Configuration for individual workflow steps.

    Attributes:
        timeout_seconds: Maximum step execution time
        max_retries: Maximum retry attempts
        is_optional: Whether step failure should stop workflow
        requires_constitutional_check: Validate hash before step
        enable_compensation: Register compensation for rollback
    """

    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    is_optional: bool = False
    requires_constitutional_check: bool = True
    enable_compensation: bool = True


@dataclass
class DAGConfig:
    """
    Configuration for DAG execution.

    Attributes:
        max_parallel_nodes: Maximum concurrent node execution
        enable_checkpointing: Save state for recovery
        checkpoint_interval_seconds: How often to checkpoint
    """

    max_parallel_nodes: int = 10
    enable_checkpointing: bool = True
    checkpoint_interval_seconds: int = 30
    topological_sort_algorithm: str = "kahn"  # kahn or dfs


@dataclass
class SagaConfig:
    """
    Configuration for saga execution.

    Attributes:
        compensation_timeout_seconds: Max time for compensations
        parallel_compensation: Run compensations in parallel
        checkpoint_before_compensation: Save state before rollback
    """

    compensation_timeout_seconds: int = 60
    parallel_compensation: bool = False  # LIFO is safer
    checkpoint_before_compensation: bool = True
    max_compensation_retries: int = 5


# Default configurations
DEFAULT_WORKFLOW_CONFIG = WorkflowConfig()
DEFAULT_STEP_CONFIG = StepConfig()
DEFAULT_DAG_CONFIG = DAGConfig()
DEFAULT_SAGA_CONFIG = SagaConfig()


# Performance thresholds (from ACGS-2 requirements)
PERFORMANCE_THRESHOLDS = {
    "p99_latency_ms": 5.0,  # Target: <5ms
    "throughput_rps": 100,  # Target: >100 RPS
    "cache_hit_rate": 0.85,  # Target: >85%
    "constitutional_compliance": 1.0,  # Target: 100%
}


# Workflow registry configuration
WORKFLOW_REGISTRY = {
    "constitutional": {
        "validation": "constitutional.validation.ConstitutionalValidationWorkflow",
        "compliance": "constitutional.compliance.ComplianceCheckWorkflow",
        "policy_evaluation": "constitutional.policy_evaluation.PolicyEvaluationWorkflow",
        "governance_decision": "constitutional.governance_decision.GovernanceDecisionWorkflow",
    },
    "coordination": {
        "voting": "coordination.voting.MultiAgentVotingWorkflow",
        "discovery": "coordination.discovery.AgentDiscoveryWorkflow",
        "handoff": "coordination.handoff.AgentHandoffWorkflow",
        "swarm": "coordination.swarm.SwarmCoordinationWorkflow",
    },
    "sagas": {
        "distributed_tx": "sagas.distributed_tx.DistributedTransactionSaga",
        "policy_update": "sagas.policy_update.PolicyUpdateSaga",
        "registration": "sagas.registration.AgentRegistrationSaga",
    },
}


__all__ = [
    "CONSTITUTIONAL_HASH",
    "WorkflowType",
    "FailurePolicy",
    "WorkflowConfig",
    "StepConfig",
    "DAGConfig",
    "SagaConfig",
    "DEFAULT_WORKFLOW_CONFIG",
    "DEFAULT_STEP_CONFIG",
    "DEFAULT_DAG_CONFIG",
    "DEFAULT_SAGA_CONFIG",
    "PERFORMANCE_THRESHOLDS",
    "WORKFLOW_REGISTRY",
]
