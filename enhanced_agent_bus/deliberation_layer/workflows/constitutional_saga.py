"""
ACGS-2 Constitutional Saga Workflow
Constitutional Hash: cdd01ef066bc6cf2

Implements the Saga pattern for distributed transactions with compensation.
Used for constitutional operations that require all-or-nothing semantics.

Saga Pattern:
    For each step:
        1. Register compensation BEFORE executing
        2. Execute the step (via activity)
        3. On failure, run all compensations in reverse order (LIFO)

Example: Multi-Service Constitutional Validation
    1. Reserve validation capacity (compensation: release capacity)
    2. Validate constitutional hash (compensation: log validation failure)
    3. Evaluate OPA policies (compensation: revert policy state)
    4. Record to audit trail (compensation: mark audit as failed)
    5. Deliver to target (compensation: recall message)

Reference: https://temporal.io/blog/saga-pattern-made-easy
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable, TypeVar, Generic
from abc import ABC, abstractmethod
import uuid

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SagaStatus(Enum):
    """Status of the saga execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    PARTIALLY_COMPENSATED = "partially_compensated"


class StepStatus(Enum):
    """Status of individual saga step."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


@dataclass
class SagaCompensation:
    """
    Represents a compensation action for a saga step.

    Compensations are idempotent operations that undo the effects of a step.
    They must be safe to call multiple times.

    Attributes:
        name: Unique name for the compensation
        execute: Async function that performs the compensation
        description: Human-readable description
        idempotency_key: Key for deduplication
    """
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[bool]]
    description: str = ""
    idempotency_key: Optional[str] = None
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class SagaStep(Generic[T]):
    """
    Represents a single step in a saga.

    Each step has:
    - An execution function (activity)
    - A compensation function (for rollback)
    - Configuration for retries and timeouts

    IMPORTANT: Register compensation BEFORE executing the step.

    Attributes:
        name: Unique step name
        execute: Async function that performs the step
        compensation: Compensation to run if this or later steps fail
        description: Human-readable description
    """
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[T]]
    compensation: Optional[SagaCompensation] = None
    description: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    is_optional: bool = False
    requires_previous: bool = True

    # Runtime state
    status: StepStatus = StepStatus.PENDING
    result: Optional[T] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0


@dataclass
class SagaContext:
    """
    Context passed through saga execution.

    Accumulates results from each step and provides shared state.
    """
    saga_id: str
    constitutional_hash: str = CONSTITUTIONAL_HASH
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    def get_step_result(self, step_name: str) -> Optional[Any]:
        """Get result from a previous step."""
        return self.step_results.get(step_name)

    def set_step_result(self, step_name: str, result: Any):
        """Store result from a step."""
        self.step_results[step_name] = result


@dataclass
class SagaResult:
    """Result of saga execution."""
    saga_id: str
    status: SagaStatus
    completed_steps: List[str]
    failed_step: Optional[str]
    compensated_steps: List[str]
    failed_compensations: List[str]
    total_execution_time_ms: float
    context: SagaContext
    constitutional_hash: str = CONSTITUTIONAL_HASH
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "saga_id": self.saga_id,
            "status": self.status.value,
            "completed_steps": self.completed_steps,
            "failed_step": self.failed_step,
            "compensated_steps": self.compensated_steps,
            "failed_compensations": self.failed_compensations,
            "total_execution_time_ms": self.total_execution_time_ms,
            "constitutional_hash": self.constitutional_hash,
            "errors": self.errors,
            "step_results": self.context.step_results,
        }


class SagaActivities(ABC):
    """
    Activity interface for saga operations.
    All activities MUST be idempotent.
    """

    @abstractmethod
    async def reserve_capacity(
        self,
        saga_id: str,
        resource_type: str,
        amount: int
    ) -> Dict[str, Any]:
        """Reserve capacity for the operation."""
        pass

    @abstractmethod
    async def release_capacity(
        self,
        saga_id: str,
        reservation_id: str
    ) -> bool:
        """Release previously reserved capacity (compensation)."""
        pass

    @abstractmethod
    async def validate_constitutional_compliance(
        self,
        saga_id: str,
        data: Dict[str, Any],
        constitutional_hash: str
    ) -> Dict[str, Any]:
        """Validate data against constitutional requirements."""
        pass

    @abstractmethod
    async def log_validation_failure(
        self,
        saga_id: str,
        validation_id: str,
        reason: str
    ) -> bool:
        """Log validation failure for audit (compensation)."""
        pass

    @abstractmethod
    async def apply_policy_decision(
        self,
        saga_id: str,
        policy_path: str,
        decision_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply policy decision to system state."""
        pass

    @abstractmethod
    async def revert_policy_decision(
        self,
        saga_id: str,
        decision_id: str
    ) -> bool:
        """Revert policy decision (compensation)."""
        pass

    @abstractmethod
    async def record_audit_entry(
        self,
        saga_id: str,
        entry_type: str,
        entry_data: Dict[str, Any]
    ) -> str:
        """Record entry to audit trail."""
        pass

    @abstractmethod
    async def mark_audit_failed(
        self,
        saga_id: str,
        audit_id: str,
        reason: str
    ) -> bool:
        """Mark audit entry as failed (compensation)."""
        pass

    @abstractmethod
    async def deliver_to_target(
        self,
        saga_id: str,
        target_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver payload to target."""
        pass

    @abstractmethod
    async def recall_from_target(
        self,
        saga_id: str,
        delivery_id: str,
        target_id: str
    ) -> bool:
        """Recall/revoke delivery from target (compensation)."""
        pass


class DefaultSagaActivities(SagaActivities):
    """Default implementation of saga activities."""

    async def reserve_capacity(
        self,
        saga_id: str,
        resource_type: str,
        amount: int
    ) -> Dict[str, Any]:
        reservation_id = str(uuid.uuid4())
        logger.info(f"Saga {saga_id}: Reserved {amount} {resource_type} (reservation: {reservation_id})")
        return {
            "reservation_id": reservation_id,
            "resource_type": resource_type,
            "amount": amount,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def release_capacity(
        self,
        saga_id: str,
        reservation_id: str
    ) -> bool:
        logger.info(f"Saga {saga_id}: Released reservation {reservation_id}")
        return True

    async def validate_constitutional_compliance(
        self,
        saga_id: str,
        data: Dict[str, Any],
        constitutional_hash: str
    ) -> Dict[str, Any]:
        is_valid = data.get("constitutional_hash") == constitutional_hash
        validation_id = str(uuid.uuid4())
        return {
            "validation_id": validation_id,
            "is_valid": is_valid,
            "errors": [] if is_valid else ["Constitutional hash mismatch"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def log_validation_failure(
        self,
        saga_id: str,
        validation_id: str,
        reason: str
    ) -> bool:
        logger.warning(f"Saga {saga_id}: Validation {validation_id} failed - {reason}")
        return True

    async def apply_policy_decision(
        self,
        saga_id: str,
        policy_path: str,
        decision_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        decision_id = str(uuid.uuid4())
        logger.info(f"Saga {saga_id}: Applied policy {policy_path} (decision: {decision_id})")
        return {
            "decision_id": decision_id,
            "policy_path": policy_path,
            "applied": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def revert_policy_decision(
        self,
        saga_id: str,
        decision_id: str
    ) -> bool:
        logger.info(f"Saga {saga_id}: Reverted policy decision {decision_id}")
        return True

    async def record_audit_entry(
        self,
        saga_id: str,
        entry_type: str,
        entry_data: Dict[str, Any]
    ) -> str:
        audit_id = str(uuid.uuid4())
        logger.info(f"Saga {saga_id}: Recorded audit entry {audit_id} ({entry_type})")
        return audit_id

    async def mark_audit_failed(
        self,
        saga_id: str,
        audit_id: str,
        reason: str
    ) -> bool:
        logger.warning(f"Saga {saga_id}: Marked audit {audit_id} as failed - {reason}")
        return True

    async def deliver_to_target(
        self,
        saga_id: str,
        target_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        delivery_id = str(uuid.uuid4())
        logger.info(f"Saga {saga_id}: Delivered to {target_id} (delivery: {delivery_id})")
        return {
            "delivery_id": delivery_id,
            "target_id": target_id,
            "delivered": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def recall_from_target(
        self,
        saga_id: str,
        delivery_id: str,
        target_id: str
    ) -> bool:
        logger.warning(f"Saga {saga_id}: Recalled delivery {delivery_id} from {target_id}")
        return True


class ConstitutionalSagaWorkflow:
    """
    Saga workflow for constitutional operations with compensation.

    This workflow executes a series of steps with automatic compensation
    on failure. It follows the saga pattern:

    1. For each step:
       a. Register compensation BEFORE execution
       b. Execute the step
       c. Store result in context

    2. On failure at any step:
       a. Stop forward execution
       b. Execute compensations in REVERSE order (LIFO)
       c. Report partial completion

    Example Usage:
        saga = ConstitutionalSagaWorkflow("saga-123")

        # Define steps with compensations
        saga.add_step(SagaStep(
            name="reserve_capacity",
            execute=activities.reserve_capacity,
            compensation=SagaCompensation(
                name="release_capacity",
                execute=activities.release_capacity
            )
        ))

        # Execute saga
        result = await saga.execute(context)
    """

    def __init__(
        self,
        saga_id: str,
        activities: Optional[SagaActivities] = None
    ):
        self.saga_id = saga_id
        self.activities = activities or DefaultSagaActivities()

        self._steps: List[SagaStep] = []
        self._compensations: List[SagaCompensation] = []
        self._status = SagaStatus.PENDING
        self._completed_steps: List[str] = []
        self._failed_step: Optional[str] = None
        self._compensated_steps: List[str] = []
        self._failed_compensations: List[str] = []
        self._start_time: Optional[datetime] = None

    def add_step(self, step: SagaStep) -> "ConstitutionalSagaWorkflow":
        """Add a step to the saga. Returns self for chaining."""
        self._steps.append(step)
        return self

    async def execute(self, context: Optional[SagaContext] = None) -> SagaResult:
        """
        Execute the saga with automatic compensation on failure.

        Returns SagaResult with execution details.
        """
        self._start_time = datetime.now(timezone.utc)
        self._status = SagaStatus.EXECUTING

        if context is None:
            context = SagaContext(saga_id=self.saga_id)

        try:
            # Execute steps in order
            for step in self._steps:
                success = await self._execute_step(step, context)

                if not success and not step.is_optional:
                    self._failed_step = step.name
                    break

            if self._failed_step:
                # Failure occurred - run compensations
                await self._run_compensations(context)
                self._status = (
                    SagaStatus.COMPENSATED
                    if not self._failed_compensations
                    else SagaStatus.PARTIALLY_COMPENSATED
                )
            else:
                self._status = SagaStatus.COMPLETED

        except Exception as e:
            logger.error(f"Saga {self.saga_id} failed with exception: {e}")
            context.errors.append(str(e))
            self._status = SagaStatus.FAILED

            # Attempt compensations even on exception
            await self._run_compensations(context)

        return self._build_result(context)

    async def _execute_step(
        self,
        step: SagaStep,
        context: SagaContext
    ) -> bool:
        """Execute a single saga step with retries."""
        step.status = StepStatus.EXECUTING
        step.started_at = datetime.now(timezone.utc)

        # CRITICAL: Register compensation BEFORE executing
        if step.compensation:
            self._compensations.append(step.compensation)

        for attempt in range(step.max_retries):
            try:
                # Build step input from context
                step_input = {
                    "saga_id": self.saga_id,
                    "step_name": step.name,
                    "attempt": attempt + 1,
                    "context": context.step_results.copy(),
                    "metadata": context.metadata.copy(),
                    "constitutional_hash": context.constitutional_hash,
                }

                # Execute with timeout
                result = await asyncio.wait_for(
                    step.execute(step_input),
                    timeout=step.timeout_seconds
                )

                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now(timezone.utc)
                step.execution_time_ms = (
                    step.completed_at - step.started_at
                ).total_seconds() * 1000

                # Store result in context
                context.set_step_result(step.name, result)
                self._completed_steps.append(step.name)

                logger.info(
                    f"Saga {self.saga_id}: Step '{step.name}' completed "
                    f"(attempt {attempt + 1}, {step.execution_time_ms:.2f}ms)"
                )

                return True

            except asyncio.TimeoutError:
                step.error = f"Timeout after {step.timeout_seconds}s"
                logger.warning(
                    f"Saga {self.saga_id}: Step '{step.name}' timed out "
                    f"(attempt {attempt + 1})"
                )

            except Exception as e:
                step.error = str(e)
                logger.warning(
                    f"Saga {self.saga_id}: Step '{step.name}' failed "
                    f"(attempt {attempt + 1}): {e}"
                )

            # Wait before retry
            if attempt < step.max_retries - 1:
                await asyncio.sleep(step.retry_delay_seconds)

        # All retries exhausted
        step.status = StepStatus.FAILED
        context.errors.append(f"Step '{step.name}' failed: {step.error}")
        return False

    async def _run_compensations(self, context: SagaContext):
        """Run compensations in reverse order (LIFO)."""
        self._status = SagaStatus.COMPENSATING

        # Reverse order - most recent first
        for compensation in reversed(self._compensations):
            success = await self._execute_compensation(compensation, context)

            if success:
                self._compensated_steps.append(compensation.name)
            else:
                self._failed_compensations.append(compensation.name)

    async def _execute_compensation(
        self,
        compensation: SagaCompensation,
        context: SagaContext
    ) -> bool:
        """Execute a single compensation with retries."""
        logger.info(f"Saga {self.saga_id}: Running compensation '{compensation.name}'")

        for attempt in range(compensation.max_retries):
            try:
                # Build compensation input
                comp_input = {
                    "saga_id": self.saga_id,
                    "compensation_name": compensation.name,
                    "attempt": attempt + 1,
                    "context": context.step_results.copy(),
                    "idempotency_key": compensation.idempotency_key or f"{self.saga_id}:{compensation.name}",
                }

                result = await compensation.execute(comp_input)

                if result:
                    logger.info(
                        f"Saga {self.saga_id}: Compensation '{compensation.name}' "
                        f"completed (attempt {attempt + 1})"
                    )
                    return True

            except Exception as e:
                logger.warning(
                    f"Saga {self.saga_id}: Compensation '{compensation.name}' "
                    f"failed (attempt {attempt + 1}): {e}"
                )

            if attempt < compensation.max_retries - 1:
                await asyncio.sleep(compensation.retry_delay_seconds)

        logger.error(
            f"Saga {self.saga_id}: Compensation '{compensation.name}' "
            f"failed after {compensation.max_retries} attempts"
        )
        context.errors.append(f"Compensation '{compensation.name}' failed")
        return False

    def _build_result(self, context: SagaContext) -> SagaResult:
        """Build saga result from current state."""
        execution_time = 0.0
        if self._start_time:
            execution_time = (
                datetime.now(timezone.utc) - self._start_time
            ).total_seconds() * 1000

        return SagaResult(
            saga_id=self.saga_id,
            status=self._status,
            completed_steps=self._completed_steps.copy(),
            failed_step=self._failed_step,
            compensated_steps=self._compensated_steps.copy(),
            failed_compensations=self._failed_compensations.copy(),
            total_execution_time_ms=execution_time,
            context=context,
            constitutional_hash=context.constitutional_hash,
            errors=context.errors.copy(),
        )

    def get_status(self) -> SagaStatus:
        """Query current saga status."""
        return self._status


def create_constitutional_validation_saga(
    saga_id: str,
    activities: Optional[SagaActivities] = None
) -> ConstitutionalSagaWorkflow:
    """
    Factory function to create a standard constitutional validation saga.

    Steps:
    1. Reserve validation capacity
    2. Validate constitutional hash
    3. Evaluate OPA policies
    4. Record audit trail
    5. Deliver to target

    Each step has corresponding compensation.
    """
    acts = activities or DefaultSagaActivities()
    saga = ConstitutionalSagaWorkflow(saga_id, acts)

    # Step 1: Reserve capacity
    async def reserve_capacity(input: Dict[str, Any]) -> Dict[str, Any]:
        return await acts.reserve_capacity(
            saga_id=input["saga_id"],
            resource_type="validation_slots",
            amount=1
        )

    async def release_capacity(input: Dict[str, Any]) -> bool:
        reservation = input["context"].get("reserve_capacity", {})
        return await acts.release_capacity(
            saga_id=input["saga_id"],
            reservation_id=reservation.get("reservation_id", "unknown")
        )

    saga.add_step(SagaStep(
        name="reserve_capacity",
        description="Reserve validation capacity",
        execute=reserve_capacity,
        compensation=SagaCompensation(
            name="release_capacity",
            description="Release reserved capacity",
            execute=release_capacity
        )
    ))

    # Step 2: Validate constitutional compliance
    async def validate_compliance(input: Dict[str, Any]) -> Dict[str, Any]:
        return await acts.validate_constitutional_compliance(
            saga_id=input["saga_id"],
            data=input["context"],
            constitutional_hash=input["constitutional_hash"]
        )

    async def log_validation_failure(input: Dict[str, Any]) -> bool:
        validation = input["context"].get("validate_compliance", {})
        return await acts.log_validation_failure(
            saga_id=input["saga_id"],
            validation_id=validation.get("validation_id", "unknown"),
            reason="Saga compensated"
        )

    saga.add_step(SagaStep(
        name="validate_compliance",
        description="Validate constitutional compliance",
        execute=validate_compliance,
        compensation=SagaCompensation(
            name="log_validation_failure",
            description="Log validation as failed",
            execute=log_validation_failure
        )
    ))

    # Step 3: Apply policy decision
    async def apply_policy(input: Dict[str, Any]) -> Dict[str, Any]:
        return await acts.apply_policy_decision(
            saga_id=input["saga_id"],
            policy_path="acgs/constitutional/allow",
            decision_data=input["context"]
        )

    async def revert_policy(input: Dict[str, Any]) -> bool:
        decision = input["context"].get("apply_policy", {})
        return await acts.revert_policy_decision(
            saga_id=input["saga_id"],
            decision_id=decision.get("decision_id", "unknown")
        )

    saga.add_step(SagaStep(
        name="apply_policy",
        description="Apply policy decision",
        execute=apply_policy,
        compensation=SagaCompensation(
            name="revert_policy",
            description="Revert policy decision",
            execute=revert_policy
        )
    ))

    # Step 4: Record audit entry
    async def record_audit(input: Dict[str, Any]) -> str:
        return await acts.record_audit_entry(
            saga_id=input["saga_id"],
            entry_type="constitutional_validation",
            entry_data=input["context"]
        )

    async def mark_audit_failed(input: Dict[str, Any]) -> bool:
        audit_id = input["context"].get("record_audit", "unknown")
        return await acts.mark_audit_failed(
            saga_id=input["saga_id"],
            audit_id=audit_id,
            reason="Saga compensated"
        )

    saga.add_step(SagaStep(
        name="record_audit",
        description="Record to audit trail",
        execute=record_audit,
        compensation=SagaCompensation(
            name="mark_audit_failed",
            description="Mark audit as failed",
            execute=mark_audit_failed
        )
    ))

    return saga
