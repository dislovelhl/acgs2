"""
ACGS-2 Base Workflow
Constitutional Hash: cdd01ef066bc6cf2

Abstract base class for all workflow implementations.
Provides common infrastructure for constitutional validation,
step execution, compensation handling, and audit recording.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .activities import BaseActivities, get_default_activities
from .context import WorkflowContext
from .result import WorkflowResult, WorkflowStatus
from .step import StepCompensation, WorkflowStep

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Metrics integration
try:
    from shared import metrics

    HAS_METRICS = True
except ImportError:
    HAS_METRICS = False

try:
    from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError
except ImportError:

    class ConstitutionalHashMismatchError(Exception):
        def __init__(self, expected_hash: str, actual_hash: str, context: Optional[str] = None):
            self.expected_hash = expected_hash
            self.actual_hash = actual_hash
            self.context = context
            super().__init__(
                f"Constitutional hash mismatch: expected {expected_hash}, got {actual_hash}"
            )


logger = logging.getLogger(__name__)


class BaseWorkflow(ABC):
    """
    Abstract base class for all ACGS-2 workflows.

    Provides common infrastructure:
    - Constitutional hash validation at boundaries
    - Step execution with retries and timeouts
    - Compensation handling (LIFO order)
    - Audit trail recording
    - Metrics and tracing support

    Subclasses must implement:
    - execute(input: Dict) -> WorkflowResult

    Example:
        class MyWorkflow(BaseWorkflow):
            async def execute(self, input: Dict) -> WorkflowResult:
                # Validate constitutional hash (always first)
                await self.validate_constitutional_hash()

                # Execute steps
                result1 = await self.run_step(self.step1, input)
                result2 = await self.run_step(self.step2, {"prev": result1})

                # Record audit (always last)
                return await self.complete(result2)
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        workflow_name: str = "base",
        activities: Optional[BaseActivities] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        timeout_seconds: int = 300,
        fail_closed: bool = True,
    ):
        """
        Initialize workflow.

        Args:
            workflow_id: Unique workflow instance ID (generated if not provided)
            activities: Activity implementations for external operations
            constitutional_hash: Expected constitutional hash
            timeout_seconds: Maximum workflow execution time
            fail_closed: If True, reject on validation/policy failures
        """
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.workflow_name = workflow_name
        self.activities = activities or get_default_activities()
        self.constitutional_hash = constitutional_hash
        self.timeout_seconds = timeout_seconds
        self.fail_closed = fail_closed

        # Workflow state
        self._status = WorkflowStatus.PENDING
        self._context: Optional[WorkflowContext] = None
        self._steps: List[WorkflowStep] = []
        self._compensations: List[StepCompensation] = []
        self._completed_steps: List[str] = []
        self._failed_steps: List[str] = []
        self._errors: List[str] = []
        self._start_time: Optional[datetime] = None
        self._output: Optional[Any] = None

    @property
    def status(self) -> WorkflowStatus:
        """Get current workflow status."""
        return self._status

    @property
    def context(self) -> Optional[WorkflowContext]:
        """Get workflow context."""
        return self._context

    @abstractmethod
    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the workflow.

        This is the main entry point for workflow execution.
        Subclasses must implement this method.

        Args:
            input: Workflow input data

        Returns:
            WorkflowResult with execution outcome
        """
        pass

    async def run(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Run the workflow with error handling and timeout.

        This is the public interface for workflow execution.
        Wraps execute() with timeout and error handling.

        Args:
            input: Workflow input data

        Returns:
            WorkflowResult with execution outcome
        """
        self._start_time = datetime.now(timezone.utc)
        self._status = WorkflowStatus.EXECUTING

        # Initialize context
        self._context = WorkflowContext(
            workflow_id=self.workflow_id,
            constitutional_hash=self.constitutional_hash,
            metadata={"input": input},
        )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(self.execute(input), timeout=self.timeout_seconds)
            return result

        except asyncio.TimeoutError:
            self._status = WorkflowStatus.TIMED_OUT
            self._errors.append(f"Workflow timed out after {self.timeout_seconds}s")

            # Run compensations on timeout
            await self._run_compensations()

            return WorkflowResult.timeout(
                workflow_id=self.workflow_id,
                execution_time_ms=self._get_elapsed_time_ms(),
                steps_completed=self._completed_steps,
            )

        except Exception as e:
            self._status = WorkflowStatus.FAILED
            self._errors.append(str(e))
            logger.exception(f"Workflow {self.workflow_id} failed: {e}")

            # Run compensations on failure
            await self._run_compensations()

            result = WorkflowResult.failure(
                workflow_id=self.workflow_id,
                errors=self._errors,
                execution_time_ms=self._get_elapsed_time_ms(),
                steps_completed=self._completed_steps,
                steps_failed=self._failed_steps,
                compensations_executed=[c.name for c in self._compensations if c],
            )
            return result
        finally:
            # Emit workflow metrics
            if HAS_METRICS:
                try:
                    duration_s = self._get_elapsed_time_ms() / 1000.0
                    metrics.WORKFLOW_EXECUTION_DURATION.labels(
                        workflow_name=self.workflow_name, status=self._status.value
                    ).observe(duration_s)

                    metrics.WORKFLOW_EXECUTIONS_TOTAL.labels(
                        workflow_name=self.workflow_name, status=self._status.value
                    ).inc()
                except Exception as me:
                    logger.debug(f"Failed to emit workflow metrics: {me}")

    async def validate_constitutional_hash(self, provided_hash: Optional[str] = None) -> bool:
        """
        Validate constitutional hash.

        This should be called at the beginning of every workflow.
        Raises ConstitutionalHashMismatchError if validation fails
        and fail_closed is True.

        Args:
            provided_hash: Hash to validate (uses workflow hash if not provided)

        Returns:
            True if validation passes

        Raises:
            ConstitutionalHashMismatchError: If validation fails and fail_closed
        """
        hash_to_check = provided_hash or self.constitutional_hash

        result = await self.activities.validate_constitutional_hash(
            workflow_id=self.workflow_id,
            provided_hash=hash_to_check,
            expected_hash=CONSTITUTIONAL_HASH,
        )

        if not result["is_valid"]:
            error_msg = "; ".join(result["errors"])
            self._errors.append(error_msg)

            if self.fail_closed:
                raise ConstitutionalHashMismatchError(
                    expected_hash=CONSTITUTIONAL_HASH,
                    actual_hash=hash_to_check,
                )

            logger.warning(
                f"Workflow {self.workflow_id}: Constitutional validation failed "
                f"but fail_closed=False, continuing"
            )
            return False

        logger.info(f"Workflow {self.workflow_id}: Constitutional validation passed")
        return True

    async def run_step(
        self,
        step: WorkflowStep,
        input: Dict[str, Any],
    ) -> Any:
        """
        Execute a single workflow step.

        Handles:
        - Constitutional validation (if required by step)
        - Compensation registration (BEFORE execution)
        - Retry logic with exponential backoff
        - Timeout handling
        - Result storage in context

        Args:
            step: WorkflowStep to execute
            input: Step input data

        Returns:
            Step result

        Raises:
            Exception: If step fails after all retries
        """
        # Constitutional check if required
        if step.requires_constitutional_check:
            await self.validate_constitutional_hash()

        # CRITICAL: Register compensation BEFORE executing
        if step.compensation:
            self._compensations.append(step.compensation)

        # Mark step as executing
        step.mark_executing()

        # Retry loop
        last_error: Optional[Exception] = None

        while step.can_retry():
            try:
                # Build step input
                step_input = {
                    "workflow_id": self.workflow_id,
                    "step_name": step.name,
                    "attempt": step.attempt_count,
                    "input": input,
                    "context": self._context.step_results if self._context else {},
                    "constitutional_hash": self.constitutional_hash,
                }

                # Execute with timeout
                result = await asyncio.wait_for(
                    step.execute(step_input), timeout=step.timeout_seconds
                )

                # Success
                step.mark_completed(result)
                self._completed_steps.append(step.name)

                if self._context:
                    self._context.set_step_result(step.name, result)

                logger.info(
                    f"Workflow {self.workflow_id}: Step '{step.name}' completed "
                    f"(attempt {step.attempt_count}, {step.execution_time_ms:.2f}ms)"
                )

                # Emit step metrics
                if HAS_METRICS:
                    try:
                        metrics.WORKFLOW_STEP_DURATION.labels(
                            workflow_name=self.workflow_name, step_name=step.name, status="success"
                        ).observe(step.execution_time_ms / 1000.0)
                    except Exception as me:
                        logger.debug(f"Failed to emit step metrics: {me}")

                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(
                    f"Step '{step.name}' timed out after {step.timeout_seconds}s"
                )
                step.mark_executing()  # Allow retry
                logger.warning(
                    f"Workflow {self.workflow_id}: Step '{step.name}' timed out "
                    f"(attempt {step.attempt_count})"
                )

            except Exception as e:
                last_error = e
                step.mark_executing()  # Allow retry
                logger.warning(
                    f"Workflow {self.workflow_id}: Step '{step.name}' failed "
                    f"(attempt {step.attempt_count}): {e}"
                )

            # Wait before retry
            if step.can_retry():
                if HAS_METRICS:
                    try:
                        metrics.WORKFLOW_STEP_RETRIES_TOTAL.labels(
                            workflow_name=self.workflow_name, step_name=step.name
                        ).inc()
                    except Exception as me:
                        logger.debug(f"Failed to emit retry metrics: {me}")
                await asyncio.sleep(step.retry_delay_seconds)

        # All retries exhausted
        step.mark_failed(str(last_error))
        self._failed_steps.append(step.name)
        self._errors.append(f"Step '{step.name}' failed: {last_error}")

        if not step.is_optional:
            raise last_error or Exception(f"Step '{step.name}' failed")

        logger.warning(
            f"Workflow {self.workflow_id}: Optional step '{step.name}' failed, continuing"
        )

        # Emit step metrics for failure
        if HAS_METRICS:
            try:
                metrics.WORKFLOW_STEP_DURATION.labels(
                    workflow_name=self.workflow_name, step_name=step.name, status="failed"
                ).observe(step.execution_time_ms / 1000.0)
            except Exception as me:
                logger.debug(f"Failed to emit step metrics: {me}")

        return None

    def register_compensation(self, compensation: StepCompensation) -> None:
        """
        Register a compensation action.

        MUST be called BEFORE the operation that needs compensation.
        Compensations are executed in LIFO order on failure.

        Args:
            compensation: Compensation to register
        """
        self._compensations.append(compensation)

    async def _run_compensations(self) -> List[str]:
        """
        Execute compensations in reverse order (LIFO).

        Returns:
            List of successfully executed compensation names
        """
        if not self._compensations:
            return []

        self._status = WorkflowStatus.COMPENSATING
        executed = []
        failed = []

        logger.info(
            f"Workflow {self.workflow_id}: Running {len(self._compensations)} compensations"
        )

        # Reverse order - LIFO
        for compensation in reversed(self._compensations):
            try:
                compensation_input = {
                    "workflow_id": self.workflow_id,
                    "compensation_name": compensation.name,
                    "context": self._context.step_results if self._context else {},
                    "idempotency_key": compensation.idempotency_key
                    or f"{self.workflow_id}:{compensation.name}",
                }

                success = False
                for attempt in range(compensation.max_retries):
                    try:
                        result = await compensation.execute(compensation_input)
                        if result:
                            success = True
                            break
                    except Exception as e:
                        logger.warning(
                            f"Workflow {self.workflow_id}: Compensation '{compensation.name}' "
                            f"failed (attempt {attempt + 1}): {e}"
                        )
                        await asyncio.sleep(compensation.retry_delay_seconds)

                if success:
                    executed.append(compensation.name)
                    logger.info(
                        f"Workflow {self.workflow_id}: Compensation '{compensation.name}' completed"
                    )
                else:
                    failed.append(compensation.name)
                    self._errors.append(f"Compensation '{compensation.name}' failed")

            except Exception as e:
                failed.append(compensation.name)
                self._errors.append(f"Compensation '{compensation.name}' error: {e}")
                logger.error(
                    f"Workflow {self.workflow_id}: Compensation '{compensation.name}' error: {e}"
                )

        # Update status
        if failed:
            self._status = WorkflowStatus.PARTIALLY_COMPENSATED
        else:
            self._status = WorkflowStatus.COMPENSATED

        return executed

    async def complete(self, output: Any, record_audit: bool = True) -> WorkflowResult:
        """
        Complete the workflow successfully.

        Args:
            output: Workflow output data
            record_audit: Whether to record to audit trail

        Returns:
            WorkflowResult with success status
        """
        self._status = WorkflowStatus.COMPLETED
        self._output = output

        audit_hash = None
        if record_audit:
            try:
                audit_hash = await self.activities.record_audit(
                    workflow_id=self.workflow_id,
                    event_type="workflow_completed",
                    event_data={
                        "output": output,
                        "steps_completed": self._completed_steps,
                        "execution_time_ms": self._get_elapsed_time_ms(),
                    },
                )
            except Exception as e:
                logger.warning(f"Audit recording failed: {e}")

        return WorkflowResult.success(
            workflow_id=self.workflow_id,
            output=output,
            execution_time_ms=self._get_elapsed_time_ms(),
            steps_completed=self._completed_steps,
            audit_hash=audit_hash,
        )

    def _get_elapsed_time_ms(self) -> float:
        """Get elapsed time since workflow start in milliseconds."""
        if self._start_time is None:
            return 0.0
        elapsed = datetime.now(timezone.utc) - self._start_time
        return elapsed.total_seconds() * 1000


__all__ = [
    "BaseWorkflow",
    "WorkflowStatus",
]
