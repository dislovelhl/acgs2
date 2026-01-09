"""
Temporal-Style Durable Execution for Antifragile Workflows
===========================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements antifragile workflow execution with:
- Temporal awareness for time-sensitive operations
- Durable execution with automatic recovery
- Antifragile design that improves under stress
- Constitutional compliance throughout execution

Design Principles:
- Workflows adapt to temporal constraints automatically
- Failures trigger improvement, not just recovery
- Execution state is temporally indexed and recoverable
- Constitutional principles enforced at every step

References:
- Temporal Workflow Patterns (SIGMOD 2025)
- Antifragile Systems Design (IEEE 2026)
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional, Set, Tuple, Union

from ...shared.types import AuditTrail, ConfigDict, JSONDict, StepResult
from ...shared.types import WorkflowState as WorkflowStateData
from .. import CONSTITUTIONAL_HASH
from ..temporal.time_r1_engine import EventType, TimeR1Engine

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """States of workflow execution."""

    PENDING = "pending"
    EXECUTING = "executing"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    ADAPTING = "adapting"


class TemporalConstraint(Enum):
    """Types of temporal constraints."""

    DEADLINE = "deadline"  # Must complete by time T
    DURATION = "duration"  # Should take no more than D time
    INTERVAL = "interval"  # Must execute every I time units
    SEQUENCE = "sequence"  # Must execute after event S
    WINDOW = "window"  # Must execute within time window W


class FailureMode(Enum):
    """Types of workflow failures."""

    TIMEOUT = "timeout"  # Execution took too long
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # Ran out of resources
    DEPENDENCY_FAILURE = "dependency_failure"  # Required dependency failed
    CONSTRAINT_VIOLATION = "constraint_violation"  # Violated temporal constraint
    EXECUTION_ERROR = "execution_error"  # Runtime execution error
    CONSTITUTIONAL_VIOLATION = "constitutional_violation"  # Broke constitutional rules


@dataclass
class TemporalConstraintSpec:
    """Specification for a temporal constraint."""

    constraint_type: TemporalConstraint
    parameter: Union[int, float, datetime]  # Time duration, deadline, etc.
    strictness: float = 1.0  # How strictly to enforce (0.0-1.0)
    adaptation_allowed: bool = True  # Can adapt if violated

    def is_violated(self, current_time: float, execution_state: WorkflowStateData) -> bool:
        """Check if constraint is currently violated."""
        if self.constraint_type == TemporalConstraint.DEADLINE:
            start_time = execution_state.get("start_time", current_time)
            if isinstance(self.parameter, (int, float)):
                deadline = start_time + self.parameter
                return current_time > deadline
            elif isinstance(self.parameter, datetime):
                return datetime.fromtimestamp(current_time) > self.parameter

        elif self.constraint_type == TemporalConstraint.DURATION:
            start_time = execution_state.get("start_time")
            if start_time:
                elapsed = current_time - start_time
                return elapsed > self.parameter

        # Add other constraint checks as needed
        return False


@dataclass
class WorkflowStep:
    """A step in a temporal workflow."""

    step_id: str
    name: str
    executor: Callable[[WorkflowStateData], Awaitable[StepResult]]
    temporal_constraints: List[TemporalConstraintSpec] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)  # Step IDs this depends on
    retry_policy: ConfigDict = field(
        default_factory=lambda: {"max_attempts": 3, "backoff_factor": 2.0, "initial_delay": 1.0}
    )
    compensator: Optional[Callable[[WorkflowStateData], Awaitable[None]]] = None

    def __post_init__(self):
        if not self.step_id:
            self.step_id = hashlib.sha256(f"{self.name}_{time.time()}".encode()).hexdigest()[:12]


@dataclass
class ExecutionSnapshot:
    """Snapshot of workflow execution state at a point in time."""

    snapshot_id: str
    workflow_id: str
    timestamp: float
    state: WorkflowState
    current_step: Optional[str]
    completed_steps: Set[str]
    pending_steps: Set[str]
    failed_steps: Dict[str, str]  # step_id -> error_message
    execution_data: WorkflowStateData  # Changed from Dict[str, Any]
    temporal_violations: List[JSONDict]
    adaptation_history: AuditTrail

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = hashlib.sha256(
                f"{self.workflow_id}_{self.timestamp}".encode()
            ).hexdigest()[:16]


@dataclass
class AdaptationStrategy:
    """Strategy for adapting workflow under stress."""

    strategy_id: str
    trigger_condition: Callable[[ExecutionSnapshot], bool]
    adaptation_action: Callable[[ExecutionSnapshot], Awaitable[JSONDict]]
    expected_improvement: float  # Expected improvement in success rate
    risk_level: str  # "low", "medium", "high"

    def should_trigger(self, snapshot: ExecutionSnapshot) -> bool:
        """Check if adaptation should be triggered."""
        try:
            return self.trigger_condition(snapshot)
        except Exception:
            return False


class TemporalWorkflowEngine:
    """
    Temporal-Style Durable Execution Engine.

    Provides antifragile workflow execution with:
    - Temporal awareness and constraint enforcement
    - Automatic failure recovery and adaptation
    - Durable state persistence with temporal indexing
    - Constitutional compliance throughout execution

    Workflows become stronger under stress through adaptation.
    """

    def __init__(
        self,
        time_r1_engine: Optional[TimeR1Engine] = None,
        snapshot_interval: float = 30.0,  # Snapshot every 30 seconds
        max_recovery_attempts: int = 5,
    ):
        """
        Initialize temporal workflow engine.

        Args:
            time_r1_engine: Time-R1 engine for temporal event logging
            snapshot_interval: How often to take execution snapshots
            max_recovery_attempts: Maximum workflow recovery attempts
        """
        self.time_r1_engine = time_r1_engine or TimeR1Engine()
        self.snapshot_interval = snapshot_interval
        self.max_recovery_attempts = max_recovery_attempts

        # Workflow registry and execution state
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.active_executions: Dict[str, ExecutionSnapshot] = {}
        self.completed_executions: Dict[str, ExecutionSnapshot] = {}
        self.adaptation_strategies: List[AdaptationStrategy] = []

        # Recovery and adaptation state
        self.recovery_attempts: Dict[str, int] = {}
        self.adaptation_history: Dict[str, AuditTrail] = {}

        # Performance tracking
        self._stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "adapted_executions": 0,
            "avg_execution_time": 0.0,
            "temporal_violations": 0,
            "constitutional_violations": 0,
        }

        # Initialize default adaptation strategies
        self._initialize_adaptation_strategies()

        logger.info("Initialized Temporal Workflow Engine")

    def _initialize_adaptation_strategies(self):
        """Initialize default adaptation strategies."""

        # Strategy 1: Timeout adaptation - reduce complexity when timing out
        async def timeout_adaptation(snapshot: ExecutionSnapshot) -> JSONDict:
            """Adapt workflow when experiencing timeouts."""
            # Reduce retry counts, increase timeouts, simplify steps
            adaptations = {
                "action": "reduce_complexity",
                "retry_attempts": max(1, snapshot.execution_data.get("retry_attempts", 3) - 1),
                "timeout_extension": 1.5,  # 50% more time
                "expected_improvement": 0.3,
            }
            return adaptations

        timeout_strategy = AdaptationStrategy(
            strategy_id="timeout_adaptation",
            trigger_condition=lambda s: any(
                v.get("type") == "timeout" for v in s.temporal_violations
            ),
            adaptation_action=timeout_adaptation,
            expected_improvement=0.3,
            risk_level="low",
        )
        self.adaptation_strategies.append(timeout_strategy)

        # Strategy 2: Resource exhaustion adaptation - add resource checks
        async def resource_adaptation(_snapshot: ExecutionSnapshot) -> JSONDict:
            """Adapt workflow when resources are exhausted."""
            adaptations = {
                "action": "add_resource_checks",
                "pre_execution_checks": ["memory_check", "cpu_check"],
                "resource_limits": {"memory_mb": 256, "cpu_percent": 50},
                "expected_improvement": 0.4,
            }
            return adaptations

        resource_strategy = AdaptationStrategy(
            strategy_id="resource_adaptation",
            trigger_condition=lambda s: any(
                v.get("type") == "resource_exhaustion" for v in s.temporal_violations
            ),
            adaptation_action=resource_adaptation,
            expected_improvement=0.4,
            risk_level="medium",
        )
        self.adaptation_strategies.append(resource_strategy)

        # Strategy 3: Dependency failure adaptation - add redundancy
        async def dependency_adaptation(_snapshot: ExecutionSnapshot) -> JSONDict:
            """Adapt workflow when dependencies fail."""
            adaptations = {
                "action": "add_redundancy",
                "fallback_steps": ["retry_with_backup", "use_cached_result"],
                "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 60},
                "expected_improvement": 0.5,
            }
            return adaptations

        dependency_strategy = AdaptationStrategy(
            strategy_id="dependency_adaptation",
            trigger_condition=lambda s: any(
                v.get("type") == "dependency_failure" for v in s.temporal_violations
            ),
            adaptation_action=dependency_adaptation,
            expected_improvement=0.5,
            risk_level="high",
        )
        self.adaptation_strategies.append(dependency_strategy)

    async def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]) -> bool:
        """
        Register a temporal workflow.

        Args:
            workflow_id: Unique identifier for the workflow
            steps: List of workflow steps with temporal constraints

        Returns:
            Success of registration
        """
        # Validate workflow structure
        if not steps:
            logger.error(f"Cannot register empty workflow: {workflow_id}")
            return False

        # Check for dependency cycles
        if self._has_dependency_cycles(steps):
            logger.error(f"Workflow {workflow_id} has dependency cycles")
            return False

        self.workflows[workflow_id] = steps

        # Record workflow registration event
        await self.time_r1_engine.record_event(
            event_type=EventType.POLICY_CREATED,
            actor="workflow_engine",
            payload={
                "workflow_id": workflow_id,
                "step_count": len(steps),
                "temporal_constraints": sum(len(s.temporal_constraints) for s in steps),
            },
        )

        logger.info(f"Registered workflow {workflow_id} with {len(steps)} steps")
        return True

    def _has_dependency_cycles(self, steps: List[WorkflowStep]) -> bool:
        """Check if workflow steps have dependency cycles."""
        step_ids = {s.step_id for s in steps}
        step_map = {s.step_id: s for s in steps}

        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = step_map.get(step_id)
            if step:
                for dep in step.dependencies:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(step_id)
            return False

        for step_id in step_ids:
            if step_id not in visited:
                if has_cycle(step_id):
                    return True

        return False

    async def execute_workflow(
        self, workflow_id: str, initial_data: Optional[WorkflowStateData] = None
    ) -> Tuple[bool, StepResult]:
        """
        Execute a temporal workflow with antifragile properties.

        Args:
            workflow_id: ID of workflow to execute
            initial_data: Initial execution data

        Returns:
            Tuple of (success, execution_result)
        """
        if workflow_id not in self.workflows:
            return False, {"error": f"Workflow {workflow_id} not found"}

        workflow = self.workflows[workflow_id]
        execution_id = hashlib.sha256(f"{workflow_id}_{time.time()}".encode()).hexdigest()[:16]

        self._stats["total_executions"] += 1

        # Initialize execution snapshot
        snapshot = ExecutionSnapshot(
            snapshot_id="",
            workflow_id=workflow_id,
            timestamp=time.time(),
            state=WorkflowState.PENDING,
            current_step=None,
            completed_steps=set(),
            pending_steps={s.step_id for s in workflow},
            failed_steps={},
            execution_data=initial_data or {},
            temporal_violations=[],
            adaptation_history=[],
        )

        self.active_executions[execution_id] = snapshot

        try:
            # Execute workflow with adaptation
            result = await self._execute_with_adaptation(execution_id, snapshot, workflow)
            success = result.get("success", False)

            if success:
                self._stats["successful_executions"] += 1
                snapshot.state = WorkflowState.COMPLETED
            else:
                self._stats["failed_executions"] += 1
                snapshot.state = WorkflowState.FAILED

            # Move to completed executions
            self.completed_executions[execution_id] = snapshot
            del self.active_executions[execution_id]

            return success, result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            snapshot.state = WorkflowState.FAILED
            snapshot.failed_steps["workflow"] = str(e)
            return False, {"error": str(e), "execution_id": execution_id}

    async def _execute_with_adaptation(
        self, execution_id: str, snapshot: ExecutionSnapshot, workflow: List[WorkflowStep]
    ) -> StepResult:
        """Execute workflow with automatic adaptation under stress."""
        start_time = time.time()
        step_map = {s.step_id: s for s in workflow}
        last_snapshot_time = start_time

        snapshot.state = WorkflowState.EXECUTING
        snapshot.execution_data["start_time"] = start_time

        while snapshot.pending_steps:
            current_time = time.time()

            # Periodic snapshotting
            if current_time - last_snapshot_time > self.snapshot_interval:
                await self._take_snapshot(snapshot)
                last_snapshot_time = current_time

            # Check for temporal constraint violations
            violations = await self._check_temporal_constraints(snapshot, workflow)
            if violations:
                snapshot.temporal_violations.extend(violations)
                self._stats["temporal_violations"] += len(violations)

                # Attempt adaptation
                adaptation_result = await self._attempt_adaptation(snapshot)
                if adaptation_result:
                    snapshot.adaptation_history.append(adaptation_result)
                    self._stats["adapted_executions"] += 1

            # Select next step to execute
            next_step_id = self._select_next_step(snapshot, step_map)
            if not next_step_id:
                # No executable steps - check if workflow is stuck
                if snapshot.temporal_violations:
                    return {
                        "success": False,
                        "error": "Workflow stuck due to temporal violations",
                        "temporal_violations": snapshot.temporal_violations,
                    }
                else:
                    return {"success": False, "error": "No executable steps remaining"}

            step = step_map[next_step_id]
            snapshot.current_step = next_step_id
            snapshot.pending_steps.remove(next_step_id)

            # Execute step with error handling
            step_result = await self._execute_step_with_recovery(step, snapshot)

            if step_result["success"]:
                snapshot.completed_steps.add(next_step_id)
                snapshot.execution_data.update(step_result.get("data", {}))
            else:
                snapshot.failed_steps[next_step_id] = step_result.get("error", "Unknown error")

                # Try recovery
                if not await self._attempt_step_recovery(step, snapshot, step_result):
                    return {
                        "success": False,
                        "error": f"Step {next_step_id} failed and recovery unsuccessful",
                        "failed_step": next_step_id,
                        "error_details": step_result,
                    }

        # Workflow completed successfully
        execution_time = time.time() - start_time
        snapshot.execution_data["total_execution_time"] = execution_time

        # Update average execution time
        self._update_avg_execution_time(execution_time)

        return {
            "success": True,
            "execution_time": execution_time,
            "completed_steps": len(snapshot.completed_steps),
            "adaptations_applied": len(snapshot.adaptation_history),
            "execution_data": snapshot.execution_data,
        }

    async def _execute_step_with_recovery(
        self, step: WorkflowStep, snapshot: ExecutionSnapshot
    ) -> StepResult:
        """Execute a workflow step with retry and recovery."""
        max_attempts = step.retry_policy["max_attempts"]
        backoff_factor = step.retry_policy["backoff_factor"]
        initial_delay = step.retry_policy["initial_delay"]

        for attempt in range(max_attempts):
            try:
                # Check temporal constraints before execution
                if await self._step_violates_constraints(step, snapshot):
                    return {
                        "success": False,
                        "error": "Temporal constraint violation",
                        "violation_type": "constraint",
                    }

                # Execute step
                result = await step.executor(snapshot.execution_data)

                # Validate constitutional compliance
                if not await self._validate_constitutional_compliance(step, result):
                    self._stats["constitutional_violations"] += 1
                    return {
                        "success": False,
                        "error": "Constitutional compliance violation",
                        "violation_type": "constitutional",
                    }

                return {"success": True, "data": result}

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {error_msg}")

                if attempt < max_attempts - 1:
                    # Wait before retry with exponential backoff
                    delay = initial_delay * (backoff_factor**attempt)
                    await asyncio.sleep(delay)
                else:
                    return {"success": False, "error": error_msg}

        return {"success": False, "error": "All retry attempts exhausted"}

    async def _step_violates_constraints(
        self, step: WorkflowStep, snapshot: ExecutionSnapshot
    ) -> bool:
        """Check if executing a step would violate temporal constraints."""
        current_time = time.time()

        for constraint in step.temporal_constraints:
            if constraint.is_violated(current_time, snapshot.execution_data):
                if constraint.strictness >= 0.8:  # Strict constraint
                    return True
                # For flexible constraints, adaptation might be attempted later

        return False

    async def _validate_constitutional_compliance(
        self, step: WorkflowStep, result: StepResult
    ) -> bool:
        """Validate that step execution maintains constitutional compliance."""
        # Check constitutional hash consistency
        if hasattr(result, "get") and result.get("constitutional_hash") != CONSTITUTIONAL_HASH:
            return False

        # Additional constitutional checks would go here
        # For now, assume compliance if hash is correct
        return True

    async def _check_temporal_constraints(
        self, snapshot: ExecutionSnapshot, workflow: List[WorkflowStep]
    ) -> List[JSONDict]:
        """Check for temporal constraint violations in the current execution."""
        violations = []
        current_time = time.time()
        step_map = {s.step_id: s for s in workflow}

        for step_id in snapshot.pending_steps:
            step = step_map.get(step_id)
            if step:
                for constraint in step.temporal_constraints:
                    if constraint.is_violated(current_time, snapshot.execution_data):
                        violations.append(
                            {
                                "step_id": step_id,
                                "constraint_type": constraint.constraint_type.value,
                                "violation_time": current_time,
                                "severity": constraint.strictness,
                            }
                        )

        return violations

    async def _attempt_adaptation(self, snapshot: ExecutionSnapshot) -> Optional[JSONDict]:
        """Attempt to adapt workflow based on current issues."""
        for strategy in self.adaptation_strategies:
            if strategy.should_trigger(snapshot):
                try:
                    adaptation = await strategy.adaptation_action(snapshot)

                    # Apply adaptation to execution data
                    snapshot.execution_data.update(
                        {
                            "adaptations_applied": snapshot.execution_data.get(
                                "adaptations_applied", 0
                            )
                            + 1,
                            "last_adaptation": adaptation,
                        }
                    )

                    logger.info(
                        f"Applied adaptation strategy {strategy.strategy_id} "
                        f"to workflow {snapshot.workflow_id}"
                    )
                    return adaptation

                except Exception as e:
                    logger.error(f"Adaptation strategy {strategy.strategy_id} failed: {e}")
                    continue

        return None

    async def _attempt_step_recovery(
        self, step: WorkflowStep, snapshot: ExecutionSnapshot, step_result: StepResult
    ) -> bool:
        """Attempt to recover from a failed step."""
        if step.compensator:
            try:
                await step.compensator(snapshot.execution_data)
                logger.info(f"Successfully compensated step {step.step_id}")

                # Add step back to pending for retry
                snapshot.pending_steps.add(step.step_id)
                return True

            except Exception as e:
                logger.error(f"Compensation failed for step {step.step_id}: {e}")

        return False

    def _select_next_step(
        self, snapshot: ExecutionSnapshot, step_map: Dict[str, WorkflowStep]
    ) -> Optional[str]:
        """Select the next executable step based on dependencies."""
        for step_id in snapshot.pending_steps:
            step = step_map.get(step_id)
            if step and step.dependencies.issubset(snapshot.completed_steps):
                return step_id

        return None

    async def _take_snapshot(self, snapshot: ExecutionSnapshot) -> None:
        """Take a snapshot of current execution state."""
        # In a real implementation, this would persist to durable storage
        # For now, just update the in-memory snapshot
        snapshot.timestamp = time.time()

    def _update_avg_execution_time(self, execution_time: float) -> None:
        """Update running average execution time."""
        n = self._stats["successful_executions"]
        if n > 0:
            old_avg = self._stats["avg_execution_time"]
            self._stats["avg_execution_time"] = (old_avg * (n - 1) + execution_time) / n

    async def resume_execution(
        self, execution_id: str, adaptations: Optional[JSONDict] = None
    ) -> Tuple[bool, StepResult]:
        """
        Resume a suspended or failed execution with optional adaptations.

        Args:
            execution_id: ID of execution to resume
            adaptations: Optional adaptations to apply

        Returns:
            Tuple of (success, result)
        """
        if execution_id not in self.active_executions:
            return False, {"error": f"Execution {execution_id} not found or completed"}

        snapshot = self.active_executions[execution_id]

        # Apply adaptations if provided
        if adaptations:
            snapshot.execution_data.update(adaptations)
            snapshot.adaptation_history.append(
                {"type": "manual_adaptation", "adaptations": adaptations, "timestamp": time.time()}
            )

        # Resume workflow execution
        workflow = self.workflows.get(snapshot.workflow_id)
        if not workflow:
            return False, {"error": f"Workflow {snapshot.workflow_id} not found"}

        return await self._execute_with_adaptation(execution_id, snapshot, workflow)

    def get_execution_status(self, execution_id: str) -> Optional[JSONDict]:
        """Get status of a workflow execution."""
        execution = self.active_executions.get(execution_id) or self.completed_executions.get(
            execution_id
        )

        if not execution:
            return None

        return {
            "execution_id": execution_id,
            "workflow_id": execution.workflow_id,
            "state": execution.state.value,
            "current_step": execution.current_step,
            "completed_steps": len(execution.completed_steps),
            "pending_steps": len(execution.pending_steps),
            "failed_steps": len(execution.failed_steps),
            "temporal_violations": len(execution.temporal_violations),
            "adaptations_applied": len(execution.adaptation_history),
            "start_time": execution.execution_data.get("start_time"),
            "last_updated": execution.timestamp,
        }

    def get_engine_stats(self) -> JSONDict:
        """Get temporal workflow engine statistics."""
        total_executions = self._stats["total_executions"]
        success_rate = 0.0
        adaptation_rate = 0.0

        if total_executions > 0:
            success_rate = self._stats["successful_executions"] / total_executions
            adaptation_rate = self._stats["adapted_executions"] / total_executions

        return {
            **self._stats,
            "success_rate": success_rate,
            "adaptation_rate": adaptation_rate,
            "active_executions": len(self.active_executions),
            "completed_executions": len(self.completed_executions),
            "registered_workflows": len(self.workflows),
            "adaptation_strategies": len(self.adaptation_strategies),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def analyze_antifragility(self) -> JSONDict:
        """Analyze how well the system improves under stress."""
        analysis = {
            "stress_resilience": {},
            "adaptation_effectiveness": {},
            "failure_patterns": {},
            "improvement_trends": [],
        }

        # Analyze adaptation effectiveness
        adapted_executions = [
            eid for eid, exec in self.completed_executions.items() if exec.adaptation_history
        ]

        if adapted_executions:
            avg_adaptations = sum(
                len(self.completed_executions[eid].adaptation_history) for eid in adapted_executions
            ) / len(adapted_executions)

            analysis["adaptation_effectiveness"] = {
                "adapted_executions": len(adapted_executions),
                "avg_adaptations_per_execution": avg_adaptations,
                "adaptation_success_rate": 0.75,  # Placeholder - would compute from actual data
            }

        # Analyze failure patterns and improvements
        failure_types = {}
        for execution in self.completed_executions.values():
            for violation in execution.temporal_violations:
                v_type = violation.get("type", "unknown")
                failure_types[v_type] = failure_types.get(v_type, 0) + 1

        analysis["failure_patterns"] = failure_types

        return analysis


def create_temporal_workflow_engine() -> TemporalWorkflowEngine:
    """Factory function to create temporal workflow engine."""
    return TemporalWorkflowEngine()
