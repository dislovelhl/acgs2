"""
ACGS-2 Handoff Workflow
Constitutional Hash: cdd01ef066bc6cf2

Agent-to-agent task handoff with state transfer.
Ensures constitutional compliance during agent transitions.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..base.result import WorkflowResult, WorkflowStatus
from ..base.workflow import BaseWorkflow

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


class HandoffStage(Enum):
    """Stages of handoff process."""

    VALIDATION = "validation"
    STATE_CAPTURE = "state_capture"
    TARGET_PREPARATION = "target_preparation"
    STATE_TRANSFER = "state_transfer"
    VERIFICATION = "verification"
    COMPLETION = "completion"


class HandoffStatus(Enum):
    """Status of handoff."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class HandoffResult:
    """Result of handoff operation."""

    handoff_id: str
    status: HandoffStatus
    source_agent_id: str
    target_agent_id: str
    state_transferred: bool
    stages_completed: List[str]
    execution_time_ms: float
    constitutional_hash: str = CONSTITUTIONAL_HASH
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "handoff_id": self.handoff_id,
            "status": self.status.value,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "state_transferred": self.state_transferred,
            "stages_completed": self.stages_completed,
            "execution_time_ms": self.execution_time_ms,
            "constitutional_hash": self.constitutional_hash,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class HandoffWorkflow(BaseWorkflow):
    """
    Handoff workflow for agent-to-agent task transfer.

    Implements safe state transfer between agents with:
    - Constitutional validation at boundaries
    - State capture and verification
    - Rollback on failure
    - Audit trail

    Example:
        workflow = HandoffWorkflow(
            source_agent_id="agent-1",
            target_agent_id="agent-2",
        )
        result = await workflow.run({
            "task_id": "task-123",
            "state": {"progress": 50, "data": {...}},
            "reason": "Load balancing"
        })
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        source_agent_id: str = "",
        target_agent_id: str = "",
        state_capturer: Optional[Callable] = None,
        state_transferrer: Optional[Callable] = None,
        verification_callback: Optional[Callable] = None,
        rollback_callback: Optional[Callable] = None,
        handoff_timeout_seconds: int = 60,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        """
        Initialize handoff workflow.

        Args:
            workflow_id: Unique workflow identifier
            source_agent_id: Source agent ID
            target_agent_id: Target agent ID
            state_capturer: Function to capture source state
            state_transferrer: Function to transfer state to target
            verification_callback: Function to verify successful handoff
            rollback_callback: Function to rollback on failure
            handoff_timeout_seconds: Maximum handoff duration
            constitutional_hash: Expected constitutional hash
        """
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="handoff",
            constitutional_hash=constitutional_hash,
        )
        self.source_agent_id = source_agent_id
        self.target_agent_id = target_agent_id
        self.state_capturer = state_capturer
        self.state_transferrer = state_transferrer
        self.verification_callback = verification_callback
        self.rollback_callback = rollback_callback
        self.handoff_timeout = handoff_timeout_seconds

        self._handoff_id = str(uuid.uuid4())
        self._captured_state: Optional[Dict[str, Any]] = None
        self._stages_completed: List[str] = []
        self._errors: List[str] = []

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute handoff workflow.

        Args:
            input: Handoff input with task and state info

        Returns:
            WorkflowResult with handoff outcome
        """
        task_id = input.get("task_id", "")
        provided_state = input.get("state", {})
        _reason = input.get("reason", "")  # noqa: F841

        logger.info(
            f"Handoff {self._handoff_id}: Starting transfer from "
            f"{self.source_agent_id} to {self.target_agent_id}"
        )

        try:
            # Stage 1: Validation
            await self._validate_handoff(input)
            self._stages_completed.append(HandoffStage.VALIDATION.value)

            # Stage 2: State Capture
            await self._capture_state(task_id, provided_state)
            self._stages_completed.append(HandoffStage.STATE_CAPTURE.value)

            # Stage 3: Target Preparation
            await self._prepare_target()
            self._stages_completed.append(HandoffStage.TARGET_PREPARATION.value)

            # Stage 4: State Transfer
            await self._transfer_state()
            self._stages_completed.append(HandoffStage.STATE_TRANSFER.value)

            # Stage 5: Verification
            verified = await self._verify_handoff()
            self._stages_completed.append(HandoffStage.VERIFICATION.value)

            if not verified:
                # Rollback on verification failure
                await self._rollback()
                return self._create_failure_result("Verification failed, rolled back")

            # Stage 6: Completion
            await self._complete_handoff()
            self._stages_completed.append(HandoffStage.COMPLETION.value)

            return self._create_success_result()

        except asyncio.TimeoutError:
            logger.warning(f"Handoff {self._handoff_id}: Timeout")
            await self._rollback()
            return WorkflowResult.timeout(
                workflow_id=self.workflow_id,
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=self._stages_completed,
            )

        except Exception as e:
            logger.exception(f"Handoff {self._handoff_id}: Error: {e}")
            await self._rollback()
            return self._create_failure_result(str(e))

    async def _validate_handoff(self, input: Dict[str, Any]) -> None:
        """Validate handoff preconditions."""
        # Validate constitutional hash
        provided_hash = input.get("constitutional_hash", self.constitutional_hash)
        if provided_hash != self.constitutional_hash:
            raise ValueError(f"Constitutional hash mismatch: {provided_hash}")

        # Validate agents
        if not self.source_agent_id:
            raise ValueError("Source agent ID required")
        if not self.target_agent_id:
            raise ValueError("Target agent ID required")
        if self.source_agent_id == self.target_agent_id:
            raise ValueError("Source and target agents must be different")

        logger.debug(f"Handoff {self._handoff_id}: Validation passed")

    async def _capture_state(self, task_id: str, provided_state: Dict[str, Any]) -> None:
        """Capture current state from source agent."""
        if self.state_capturer:
            self._captured_state = await asyncio.wait_for(
                self.state_capturer(self.source_agent_id, task_id), timeout=self.handoff_timeout / 4
            )
        else:
            # Use provided state if no capturer
            self._captured_state = {
                "task_id": task_id,
                "state": provided_state,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "source_agent_id": self.source_agent_id,
                "constitutional_hash": self.constitutional_hash,
            }

        self.context.set_step_result("captured_state", self._captured_state)
        logger.debug(f"Handoff {self._handoff_id}: State captured")

    async def _prepare_target(self) -> None:
        """Prepare target agent for handoff."""
        # In production, this would call target agent's prepare endpoint
        logger.debug(f"Handoff {self._handoff_id}: Target {self.target_agent_id} prepared")

    async def _transfer_state(self) -> None:
        """Transfer state to target agent."""
        if self.state_transferrer:
            await asyncio.wait_for(
                self.state_transferrer(self.target_agent_id, self._captured_state),
                timeout=self.handoff_timeout / 4,
            )
        else:
            # Simulated transfer
            logger.debug(f"Handoff {self._handoff_id}: State transferred to {self.target_agent_id}")

        self.context.set_step_result("state_transferred", True)

    async def _verify_handoff(self) -> bool:
        """Verify successful state transfer."""
        if self.verification_callback:
            return await asyncio.wait_for(
                self.verification_callback(self.target_agent_id, self._captured_state),
                timeout=self.handoff_timeout / 4,
            )

        # Default verification passes
        return True

    async def _rollback(self) -> None:
        """Rollback handoff on failure."""
        logger.warning(f"Handoff {self._handoff_id}: Rolling back")

        if self.rollback_callback and self._captured_state:
            try:
                await asyncio.wait_for(
                    self.rollback_callback(self.source_agent_id, self._captured_state),
                    timeout=self.handoff_timeout / 4,
                )
                logger.info(f"Handoff {self._handoff_id}: Rollback completed")
            except Exception as e:
                self._errors.append(f"Rollback failed: {e}")
                logger.error(f"Handoff {self._handoff_id}: Rollback failed: {e}")

    async def _complete_handoff(self) -> None:
        """Complete handoff and cleanup."""
        # Notify source agent of completion
        logger.info(
            f"Handoff {self._handoff_id}: Completed transfer from "
            f"{self.source_agent_id} to {self.target_agent_id}"
        )

    def _create_success_result(self) -> WorkflowResult:
        """Create successful handoff result."""
        handoff_result = HandoffResult(
            handoff_id=self._handoff_id,
            status=HandoffStatus.COMPLETED,
            source_agent_id=self.source_agent_id,
            target_agent_id=self.target_agent_id,
            state_transferred=True,
            stages_completed=self._stages_completed,
            execution_time_ms=self.context.get_elapsed_time_ms(),
            constitutional_hash=self.constitutional_hash,
        )

        return WorkflowResult.success(
            workflow_id=self.workflow_id,
            output=handoff_result.to_dict(),
            execution_time_ms=self.context.get_elapsed_time_ms(),
            steps_completed=self._stages_completed,
        )

    def _create_failure_result(self, error: str) -> WorkflowResult:
        """Create failed handoff result."""
        self._errors.append(error)

        handoff_result = HandoffResult(
            handoff_id=self._handoff_id,
            status=HandoffStatus.FAILED,
            source_agent_id=self.source_agent_id,
            target_agent_id=self.target_agent_id,
            state_transferred=False,
            stages_completed=self._stages_completed,
            execution_time_ms=self.context.get_elapsed_time_ms(),
            constitutional_hash=self.constitutional_hash,
            errors=self._errors,
        )

        return WorkflowResult(
            workflow_id=self._handoff_id,
            status=WorkflowStatus.FAILED,
            output=handoff_result.to_dict(),
            execution_time_ms=self.context.get_elapsed_time_ms(),
            steps_completed=self._stages_completed,
        )

        return WorkflowResult.failure(
            workflow_id=self.workflow_id,
            errors=self._errors,
            execution_time_ms=self.context.get_elapsed_time_ms(),
            steps_completed=self._stages_completed,
            steps_failed=[HandoffStage.COMPLETION.value],
        )


__all__ = [
    "HandoffStage",
    "HandoffStatus",
    "HandoffResult",
    "HandoffWorkflow",
]
