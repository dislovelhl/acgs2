"""
SagaLLM Constitutional Transactions
===================================

Constitutional Hash: cdd01ef066bc6cf2

Implements transaction guarantees with compensation for
constitutional governance operations:
- Checkpoint-based state management
- LIFO compensation for rollback
- Automatic recovery on failure

References:
- SagaLLM: Transaction Guarantees (arXiv:2503.11951)
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """States for saga transaction lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMMITTED = "committed"
    COMPENSATING = "compensating"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class SagaCheckpoint:
    """A checkpoint in the saga transaction."""

    checkpoint_id: str
    name: str
    state: Dict[str, Any]
    timestamp: datetime
    compensation: Optional[Callable[[], Awaitable[None]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "has_compensation": self.compensation is not None,
            "metadata": self.metadata,
        }


@dataclass
class SagaStep:
    """A step in the saga transaction."""

    step_id: str
    name: str
    action: Callable[[], Awaitable[Any]]
    compensation: Callable[[], Awaitable[None]]
    timeout_seconds: float = 30.0
    retries: int = 3
    result: Optional[Any] = None
    executed: bool = False
    compensated: bool = False
    error: Optional[str] = None


@dataclass
class TransactionResult:
    """Result of a saga transaction."""

    transaction_id: str
    state: TransactionState
    checkpoints: List[SagaCheckpoint]
    steps_completed: int
    steps_compensated: int
    final_state: Dict[str, Any]
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    constitutional_hash: str = CONSTITUTIONAL_HASH


class SagaConstitutionalTransaction:
    """
    Constitutional Saga Transaction Manager.

    Provides transaction guarantees for governance operations:
    - Atomic execution with checkpoint-based recovery
    - LIFO compensation stack for rollback
    - Automatic retry with exponential backoff

    Usage:
        async with SagaConstitutionalTransaction() as saga:
            saga.checkpoint("initial", state)
            result = await saga.step("operation", action, compensation)
            saga.checkpoint("after_operation", new_state)
    """

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
    ):
        """
        Initialize a Saga transaction.

        Args:
            transaction_id: Optional transaction ID
            max_retries: Maximum retries per step
            timeout_seconds: Overall transaction timeout
        """
        self.transaction_id = transaction_id or f"saga-{uuid.uuid4().hex[:8]}"
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        self._state = TransactionState.PENDING
        self._checkpoints: List[SagaCheckpoint] = []
        self._steps: List[SagaStep] = []
        self._current_state: Dict[str, Any] = {}
        self._start_time: Optional[datetime] = None
        self._compensation_stack: List[Callable[[], Awaitable[None]]] = []

        logger.info(f"Created SagaTransaction: {self.transaction_id}")

    async def __aenter__(self) -> "SagaConstitutionalTransaction":
        """Enter transaction context."""
        self._state = TransactionState.RUNNING
        self._start_time = datetime.utcnow()

        return self

    async def __aexit__(
        self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]
    ) -> bool:
        """Exit transaction context with automatic compensation on error."""
        if exc_type is not None:
            # Error occurred - compensate
            logger.warning(
                f"Transaction {self.transaction_id} failed: {exc_val}. Initiating compensation."
            )
            await self.compensate()
            return False  # Re-raise exception

        # Success - commit
        self._state = TransactionState.COMMITTED
        logger.info(f"Transaction {self.transaction_id} committed successfully")
        return False

    def checkpoint(
        self,
        name: str,
        state: Dict[str, Any],
        compensation: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> SagaCheckpoint:
        """
        Create a checkpoint in the transaction.

        Args:
            name: Checkpoint name for identification
            state: State snapshot at this point
            compensation: Optional compensation function

        Returns:
            SagaCheckpoint instance
        """
        checkpoint = SagaCheckpoint(
            checkpoint_id=f"cp-{uuid.uuid4().hex[:8]}",
            name=name,
            state=state.copy(),
            timestamp=datetime.utcnow(),
            compensation=compensation,
        )

        self._checkpoints.append(checkpoint)
        self._current_state = state.copy()

        if compensation:
            self._compensation_stack.append(compensation)

        return checkpoint

    async def step(
        self,
        name: str,
        action: Callable[[], Awaitable[Any]],
        compensation: Callable[[], Awaitable[None]],
        timeout_seconds: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> Any:
        """
        Execute a saga step with compensation.

        Args:
            name: Step name
            action: Async function to execute
            compensation: Async function for rollback
            timeout_seconds: Optional step timeout
            retries: Optional retry count

        Returns:
            Result of the action
        """
        step = SagaStep(
            step_id=f"step-{uuid.uuid4().hex[:8]}",
            name=name,
            action=action,
            compensation=compensation,
            timeout_seconds=timeout_seconds or 30.0,
            retries=retries or self.max_retries,
        )

        self._steps.append(step)

        # Execute with retry
        last_error = None
        for attempt in range(step.retries):
            try:
                # Execute action with timeout
                result = await asyncio.wait_for(action(), timeout=step.timeout_seconds)

                step.result = result
                step.executed = True
                self._compensation_stack.append(compensation)

                return result

            except asyncio.TimeoutError:
                last_error = f"Step '{name}' timed out after {step.timeout_seconds}s"
                logger.warning(f"{last_error}, attempt {attempt + 1}/{step.retries}")

            except Exception as e:
                last_error = f"Step '{name}' failed: {str(e)}"
                logger.warning(f"{last_error}, attempt {attempt + 1}/{step.retries}")

            # Exponential backoff
            if attempt < step.retries - 1:
                await asyncio.sleep(2**attempt)

        # All retries exhausted
        step.error = last_error
        raise RuntimeError(last_error)

    async def compensate(self) -> None:
        """
        Execute compensation in LIFO order.

        This rolls back all executed steps in reverse order,
        ensuring consistent state recovery.
        """
        if self._state == TransactionState.ROLLED_BACK:
            return

        self._state = TransactionState.COMPENSATING
        logger.info(f"Compensating transaction {self.transaction_id}")

        compensated_count = 0

        # LIFO order - reverse the compensation stack
        while self._compensation_stack:
            compensation = self._compensation_stack.pop()
            try:
                await compensation()
                compensated_count += 1

            except Exception as e:
                logger.error(f"Compensation failed: {e}")
                # Continue with remaining compensations

        # Mark steps as compensated
        for step in reversed(self._steps):
            if step.executed and not step.compensated:
                step.compensated = True

        self._state = TransactionState.ROLLED_BACK
        logger.info(
            f"Transaction {self.transaction_id} rolled back. "
            f"Compensated {compensated_count} operations."
        )

    async def get_checkpoint(self, name: str) -> Optional[SagaCheckpoint]:
        """Get a checkpoint by name."""
        for cp in self._checkpoints:
            if cp.name == name:
                return cp
        return None

    async def restore_to_checkpoint(self, name: str) -> bool:
        """
        Restore state to a specific checkpoint.

        Compensates all operations after the checkpoint.
        """
        target_idx = None
        for i, cp in enumerate(self._checkpoints):
            if cp.name == name:
                target_idx = i
                break

        if target_idx is None:
            return False

        # Compensate operations after this checkpoint
        checkpoints_to_compensate = len(self._checkpoints) - target_idx - 1

        for _ in range(checkpoints_to_compensate):
            if self._compensation_stack:
                compensation = self._compensation_stack.pop()
                try:
                    await compensation()
                except Exception as e:
                    logger.error(f"Compensation during restore failed: {e}")

        # Restore state
        target_cp = self._checkpoints[target_idx]
        self._current_state = target_cp.state.copy()
        self._checkpoints = self._checkpoints[: target_idx + 1]

        logger.info(f"Restored to checkpoint '{name}'")
        return True

    def get_result(self) -> TransactionResult:
        """Get the transaction result."""

        processing_time = 0.0
        if self._start_time:
            processing_time = (datetime.utcnow() - self._start_time).total_seconds() * 1000

        return TransactionResult(
            transaction_id=self.transaction_id,
            state=self._state,
            checkpoints=self._checkpoints,
            steps_completed=sum(1 for s in self._steps if s.executed),
            steps_compensated=sum(1 for s in self._steps if s.compensated),
            final_state=self._current_state,
            error=self._steps[-1].error if self._steps and self._steps[-1].error else None,
            processing_time_ms=processing_time,
        )


class SagaOrchestrator:
    """
    Orchestrates multiple saga transactions.

    Provides:
    - Transaction coordination
    - Deadlock detection
    - Resource locking
    - Audit logging
    """

    def __init__(self):
        self._active_transactions: Dict[str, SagaConstitutionalTransaction] = {}
        self._completed_transactions: List[TransactionResult] = []
        self._locks: Dict[str, str] = {}  # resource -> transaction_id

        logger.info("Initialized SagaOrchestrator")

    @asynccontextmanager
    async def transaction(
        self, transaction_id: Optional[str] = None, resources: Optional[List[str]] = None
    ):
        """
        Create and manage a saga transaction with optional resource locking.

        Args:
            transaction_id: Optional transaction ID
            resources: Optional list of resources to lock

        Yields:
            SagaConstitutionalTransaction instance
        """
        saga = SagaConstitutionalTransaction(transaction_id=transaction_id)

        # Acquire locks
        if resources:
            await self._acquire_locks(saga.transaction_id, resources)

        self._active_transactions[saga.transaction_id] = saga

        try:
            async with saga as s:
                yield s

            # Success - record result
            result = saga.get_result()
            self._completed_transactions.append(result)

        finally:
            # Release locks and cleanup
            if resources:
                await self._release_locks(saga.transaction_id, resources)

            if saga.transaction_id in self._active_transactions:
                del self._active_transactions[saga.transaction_id]

    async def _acquire_locks(self, transaction_id: str, resources: List[str]) -> None:
        """Acquire locks on resources."""
        for resource in resources:
            if resource in self._locks:
                # Check for deadlock potential
                holding_tx = self._locks[resource]
                if holding_tx != transaction_id:
                    raise RuntimeError(f"Resource '{resource}' locked by transaction {holding_tx}")
            self._locks[resource] = transaction_id

    async def _release_locks(self, transaction_id: str, resources: List[str]) -> None:
        """Release locks on resources."""
        for resource in resources:
            if self._locks.get(resource) == transaction_id:
                del self._locks[resource]

    def get_active_transactions(self) -> List[str]:
        """Get list of active transaction IDs."""
        return list(self._active_transactions.keys())

    def get_transaction_history(self, limit: int = 100) -> List[TransactionResult]:
        """Get recent transaction history."""
        return self._completed_transactions[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        completed = len(self._completed_transactions)
        committed = sum(
            1 for t in self._completed_transactions if t.state == TransactionState.COMMITTED
        )
        rolled_back = sum(
            1 for t in self._completed_transactions if t.state == TransactionState.ROLLED_BACK
        )

        return {
            "active_transactions": len(self._active_transactions),
            "completed_transactions": completed,
            "committed": committed,
            "rolled_back": rolled_back,
            "success_rate": committed / max(completed, 1),
            "active_locks": len(self._locks),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Global orchestrator instance
_orchestrator: Optional[SagaOrchestrator] = None


def get_saga_orchestrator() -> SagaOrchestrator:
    """Get the global saga orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SagaOrchestrator()
    return _orchestrator
