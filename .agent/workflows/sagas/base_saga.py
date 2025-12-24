"""
ACGS-2 Base Saga Implementation
Constitutional Hash: cdd01ef066bc6cf2

Core saga orchestration with LIFO compensation order.
Implements the Saga pattern for distributed transactions with
automatic rollback on failure.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional
from enum import Enum
import uuid

from ..base.context import WorkflowContext
from ..base.step import StepCompensation

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    """Status of saga execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    PARTIALLY_COMPENSATED = "partially_compensated"


@dataclass
class SagaStep:
    """
    A step in the saga with its compensation action.

    Attributes:
        name: Human-readable step name
        execute: Async function to execute the step
        compensate: Async function to undo the step
        timeout_seconds: Maximum execution time
        is_critical: If True, failure stops saga (default True)
    """
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[Any]]
    compensate: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    timeout_seconds: int = 30
    is_critical: bool = True
    idempotency_key: Optional[str] = None

    # Runtime state
    result: Optional[Any] = field(default=None, init=False)
    error: Optional[str] = field(default=None, init=False)
    executed_at: Optional[datetime] = field(default=None, init=False)
    compensated_at: Optional[datetime] = field(default=None, init=False)


@dataclass
class SagaResult:
    """Result of saga execution."""
    saga_id: str
    status: SagaStatus
    steps_completed: List[str]
    steps_failed: List[str]
    compensations_executed: List[str]
    compensations_failed: List[str]
    execution_time_ms: float
    constitutional_hash: str = CONSTITUTIONAL_HASH
    output: Optional[Any] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "saga_id": self.saga_id,
            "status": self.status.value,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "compensations_executed": self.compensations_executed,
            "compensations_failed": self.compensations_failed,
            "execution_time_ms": self.execution_time_ms,
            "constitutional_hash": self.constitutional_hash,
            "output": self.output,
            "errors": self.errors,
        }


class BaseSaga:
    """
    Base saga implementation with LIFO compensation.

    Implements the Saga pattern for distributed transactions.
    Steps are executed sequentially, and on failure, compensations
    are executed in reverse order (LIFO).

    Key Principles:
    - Register compensation BEFORE executing action
    - Compensations execute in LIFO order
    - Constitutional validation at saga boundaries
    - Idempotent compensations for safety

    Example:
        saga = BaseSaga("order-saga")
        saga.add_step(SagaStep("reserve_inventory", reserve, release))
        saga.add_step(SagaStep("charge_payment", charge, refund))
        saga.add_step(SagaStep("ship_order", ship, cancel_shipment))

        result = await saga.execute(context, {"order_id": "123"})
    """

    def __init__(
        self,
        saga_id: Optional[str] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        max_compensation_retries: int = 3,
    ):
        """
        Initialize saga.

        Args:
            saga_id: Unique saga identifier
            constitutional_hash: Expected constitutional hash
            max_compensation_retries: Max retries for failed compensations
        """
        self.saga_id = saga_id or str(uuid.uuid4())
        self.constitutional_hash = constitutional_hash
        self.max_compensation_retries = max_compensation_retries

        self._steps: List[SagaStep] = []
        self._executed_steps: List[SagaStep] = []
        self._compensation_stack: List[SagaStep] = []

    def add_step(self, step: SagaStep) -> "BaseSaga":
        """
        Add a step to the saga.

        Args:
            step: SagaStep to add

        Returns:
            Self for chaining
        """
        self._steps.append(step)
        return self

    async def execute(
        self,
        context: WorkflowContext,
        input: Dict[str, Any]
    ) -> SagaResult:
        """
        Execute the saga with all steps.

        Executes steps sequentially. On failure, compensates
        in reverse order (LIFO).

        Args:
            context: Workflow context
            input: Input data for saga

        Returns:
            SagaResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        context.set_step_result("_saga_id", self.saga_id)

        steps_completed = []
        steps_failed = []
        compensations_executed = []
        compensations_failed = []
        errors = []
        output = None

        logger.info(f"Saga {self.saga_id}: Starting execution with {len(self._steps)} steps")

        try:
            # Execute steps sequentially
            for step in self._steps:
                success = await self._execute_step(step, context, input)

                if success:
                    steps_completed.append(step.name)
                    self._executed_steps.append(step)

                    # Register compensation AFTER successful execution
                    if step.compensate:
                        self._compensation_stack.append(step)
                else:
                    steps_failed.append(step.name)
                    errors.append(f"Step '{step.name}' failed: {step.error}")

                    if step.is_critical:
                        logger.warning(
                            f"Saga {self.saga_id}: Critical step '{step.name}' failed, "
                            "initiating compensation"
                        )
                        break

            # Determine if compensation is needed
            if steps_failed:
                comp_executed, comp_failed = await self._run_compensations(context, input)
                compensations_executed = comp_executed
                compensations_failed = comp_failed

                if comp_failed:
                    errors.extend([f"Compensation '{c}' failed" for c in comp_failed])

        except Exception as e:
            errors.append(f"Saga execution error: {e}")
            logger.exception(f"Saga {self.saga_id}: Execution error: {e}")

            # Run compensations on unexpected error
            comp_executed, comp_failed = await self._run_compensations(context, input)
            compensations_executed = comp_executed
            compensations_failed = comp_failed

        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Determine final status
        status = self._determine_status(
            steps_completed, steps_failed,
            compensations_executed, compensations_failed
        )

        # Collect output from last successful step if completed
        if status == SagaStatus.COMPLETED and self._executed_steps:
            output = self._executed_steps[-1].result

        logger.info(
            f"Saga {self.saga_id}: Execution {status.value} "
            f"({len(steps_completed)} completed, {len(steps_failed)} failed, "
            f"{execution_time:.2f}ms)"
        )

        return SagaResult(
            saga_id=self.saga_id,
            status=status,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            compensations_executed=compensations_executed,
            compensations_failed=compensations_failed,
            execution_time_ms=execution_time,
            constitutional_hash=self.constitutional_hash,
            output=output,
            errors=errors,
        )

    async def _execute_step(
        self,
        step: SagaStep,
        context: WorkflowContext,
        input: Dict[str, Any]
    ) -> bool:
        """
        Execute a single saga step.

        Returns:
            True if step succeeded, False otherwise
        """
        logger.debug(f"Saga {self.saga_id}: Executing step '{step.name}'")

        step_input = {
            **input,
            "saga_id": self.saga_id,
            "step_name": step.name,
            "context": context.step_results,
            "constitutional_hash": self.constitutional_hash,
        }

        try:
            result = await asyncio.wait_for(
                step.execute(step_input),
                timeout=step.timeout_seconds
            )
            step.result = result
            step.executed_at = datetime.now(timezone.utc)
            context.set_step_result(step.name, result)

            logger.debug(f"Saga {self.saga_id}: Step '{step.name}' completed")
            return True

        except asyncio.TimeoutError:
            step.error = f"Timeout after {step.timeout_seconds}s"
            logger.warning(f"Saga {self.saga_id}: Step '{step.name}' timed out")
            return False

        except Exception as e:
            step.error = str(e)
            logger.warning(f"Saga {self.saga_id}: Step '{step.name}' failed: {e}")
            return False

    async def _run_compensations(
        self,
        context: WorkflowContext,
        input: Dict[str, Any]
    ) -> tuple:
        """
        Run compensations in LIFO order.

        Returns:
            Tuple of (executed, failed) compensation names
        """
        executed = []
        failed = []

        if not self._compensation_stack:
            return executed, failed

        logger.info(
            f"Saga {self.saga_id}: Running {len(self._compensation_stack)} compensations"
        )

        # LIFO order - reverse the stack
        for step in reversed(self._compensation_stack):
            if not step.compensate:
                continue

            success = await self._execute_compensation(step, context, input)

            if success:
                executed.append(step.name)
            else:
                failed.append(step.name)

        return executed, failed

    async def _execute_compensation(
        self,
        step: SagaStep,
        context: WorkflowContext,
        input: Dict[str, Any]
    ) -> bool:
        """
        Execute compensation for a step with retries.

        Returns:
            True if compensation succeeded, False otherwise
        """
        comp_input = {
            **input,
            "saga_id": self.saga_id,
            "step_name": step.name,
            "step_result": step.result,
            "context": context.step_results,
            "idempotency_key": step.idempotency_key or f"{self.saga_id}:{step.name}",
            "constitutional_hash": self.constitutional_hash,
        }

        for attempt in range(self.max_compensation_retries):
            try:
                await asyncio.wait_for(
                    step.compensate(comp_input),
                    timeout=step.timeout_seconds
                )
                step.compensated_at = datetime.now(timezone.utc)

                logger.info(f"Saga {self.saga_id}: Compensation '{step.name}' completed")
                return True

            except asyncio.TimeoutError:
                logger.warning(
                    f"Saga {self.saga_id}: Compensation '{step.name}' timed out "
                    f"(attempt {attempt + 1}/{self.max_compensation_retries})"
                )

            except Exception as e:
                logger.warning(
                    f"Saga {self.saga_id}: Compensation '{step.name}' failed: {e} "
                    f"(attempt {attempt + 1}/{self.max_compensation_retries})"
                )

        logger.error(
            f"Saga {self.saga_id}: Compensation '{step.name}' failed after "
            f"{self.max_compensation_retries} attempts"
        )
        return False

    def _determine_status(
        self,
        completed: List[str],
        failed: List[str],
        comp_executed: List[str],
        comp_failed: List[str]
    ) -> SagaStatus:
        """Determine final saga status."""
        # Check if any critical steps failed
        critical_failed = any(
            step.name in failed and step.is_critical
            for step in self._steps
        )

        if not critical_failed:
            return SagaStatus.COMPLETED

        if not comp_executed and not comp_failed:
            return SagaStatus.FAILED

        if comp_failed:
            return SagaStatus.PARTIALLY_COMPENSATED

        return SagaStatus.COMPENSATED


__all__ = [
    "SagaStatus",
    "SagaStep",
    "SagaResult",
    "BaseSaga",
]
