"""
ACGS-2 Recovery Orchestrator
Constitutional Hash: cdd01ef066bc6cf2

Automated recovery orchestrator for the Enhanced Agent Bus that manages service
recovery when circuit breakers open. Provides priority-based recovery queues,
configurable recovery strategies, and constitutional compliance validation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import heapq

# Import centralized constitutional hash from shared module
try:
    from shared.constants import CONSTITUTIONAL_HASH
    from shared.circuit_breaker import CircuitBreakerRegistry, get_circuit_breaker
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
    CircuitBreakerRegistry = None  # type: ignore
    get_circuit_breaker = None  # type: ignore

try:
    from .exceptions import (
        AgentBusError,
        ConstitutionalError,
        ConstitutionalHashMismatchError,
    )
    from .validators import validate_constitutional_hash, ValidationResult
except ImportError:
    # Fallback for standalone usage
    AgentBusError = Exception  # type: ignore
    ConstitutionalError = Exception  # type: ignore
    ConstitutionalHashMismatchError = Exception  # type: ignore

    @dataclass
    class ValidationResult:  # type: ignore
        """Fallback ValidationResult - mirrors validators.ValidationResult interface.

        Constitutional Hash: cdd01ef066bc6cf2
        """
        is_valid: bool = True
        errors: List[str] = field(default_factory=list)
        warnings: List[str] = field(default_factory=list)
        metadata: Dict[str, Any] = field(default_factory=dict)
        decision: str = "ALLOW"
        constitutional_hash: str = CONSTITUTIONAL_HASH

        def add_error(self, error: str) -> None:
            """Add an error to the result."""
            self.errors.append(error)
            self.is_valid = False

        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary for serialization."""
            return {
                "is_valid": self.is_valid,
                "errors": self.errors,
                "warnings": self.warnings,
                "metadata": self.metadata,
                "decision": self.decision,
                "constitutional_hash": self.constitutional_hash,
            }

    def validate_constitutional_hash(hash_value: str) -> ValidationResult:  # type: ignore
        """Fallback hash validation."""
        result = ValidationResult()
        if hash_value != CONSTITUTIONAL_HASH:
            result.add_error(f"Invalid hash: {hash_value}")
        return result


logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class RecoveryStrategy(Enum):
    """Recovery strategy types for service recovery.

    Constitutional Hash: cdd01ef066bc6cf2
    """
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Delay doubles each attempt
    LINEAR_BACKOFF = "linear_backoff"  # Delay increases linearly
    IMMEDIATE = "immediate"  # Attempt recovery immediately
    MANUAL = "manual"  # Requires manual intervention


class RecoveryState(Enum):
    """Recovery state for services.

    Constitutional Hash: cdd01ef066bc6cf2
    """
    IDLE = "idle"  # No recovery in progress
    SCHEDULED = "scheduled"  # Recovery scheduled but not started
    IN_PROGRESS = "in_progress"  # Recovery attempt in progress
    SUCCEEDED = "succeeded"  # Recovery successful
    FAILED = "failed"  # Recovery failed (all retries exhausted)
    CANCELLED = "cancelled"  # Recovery cancelled by user
    AWAITING_MANUAL = "awaiting_manual"  # Waiting for manual intervention


@dataclass
class RecoveryPolicy:
    """Policy configuration for service recovery.

    Constitutional Hash: cdd01ef066bc6cf2

    Attributes:
        max_retry_attempts: Maximum number of recovery attempts (default: 5)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        initial_delay_ms: Initial delay before first retry in milliseconds (default: 1000)
        max_delay_ms: Maximum delay between retries in milliseconds (default: 60000)
        health_check_fn: Optional function to check service health
        constitutional_hash: Constitutional hash for validation
    """
    max_retry_attempts: int = 5
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    health_check_fn: Optional[Callable[[], bool]] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def __post_init__(self):
        """Validate recovery policy."""
        if self.max_retry_attempts < 1:
            raise ValueError("max_retry_attempts must be >= 1")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")
        if self.initial_delay_ms < 0:
            raise ValueError("initial_delay_ms must be >= 0")
        if self.max_delay_ms < self.initial_delay_ms:
            raise ValueError("max_delay_ms must be >= initial_delay_ms")


@dataclass
class RecoveryResult:
    """Result of a recovery attempt.

    Constitutional Hash: cdd01ef066bc6cf2
    """
    service_name: str
    success: bool
    attempt_number: int
    total_attempts: int
    elapsed_time_ms: float
    state: RecoveryState
    error_message: Optional[str] = None
    health_check_passed: bool = False
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "service_name": self.service_name,
            "success": self.success,
            "attempt_number": self.attempt_number,
            "total_attempts": self.total_attempts,
            "elapsed_time_ms": self.elapsed_time_ms,
            "state": self.state.value,
            "error_message": self.error_message,
            "health_check_passed": self.health_check_passed,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(order=True)
class RecoveryTask:
    """Recovery task with priority ordering.

    Constitutional Hash: cdd01ef066bc6cf2

    Uses negative priority for min-heap behavior (higher priority = lower number).
    """
    priority: int
    service_name: str = field(compare=False)
    strategy: RecoveryStrategy = field(compare=False)
    policy: RecoveryPolicy = field(compare=False)
    scheduled_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
        compare=False
    )
    attempt_count: int = field(default=0, compare=False)
    last_attempt_at: Optional[datetime] = field(default=None, compare=False)
    next_attempt_at: Optional[datetime] = field(default=None, compare=False)
    state: RecoveryState = field(default=RecoveryState.SCHEDULED, compare=False)
    constitutional_hash: str = field(default=CONSTITUTIONAL_HASH, compare=False)


class RecoveryOrchestratorError(AgentBusError):
    """Base exception for recovery orchestrator errors."""
    def __init__(self, message: str = "", **kwargs):
        self.message = message
        super().__init__(message)


class RecoveryValidationError(RecoveryOrchestratorError):
    """Raised when recovery validation fails."""
    def __init__(self, message: str = "", **kwargs):
        self.message = message
        super().__init__(message)


class RecoveryConstitutionalError(ConstitutionalError):
    """Raised when constitutional validation fails during recovery."""
    def __init__(self, message: str = "", **kwargs):
        self.message = message
        super().__init__(message)


# =============================================================================
# Recovery Orchestrator
# =============================================================================


class RecoveryOrchestrator:
    """
    Automated recovery orchestrator for ACGS-2 Enhanced Agent Bus.

    Constitutional Hash: cdd01ef066bc6cf2

    Manages service recovery when circuit breakers open, providing priority-based
    recovery queues, configurable recovery strategies, and constitutional compliance
    validation before any recovery action.

    Features:
        - Priority-based recovery queue for multiple failing services
        - Multiple recovery strategies (exponential, linear, immediate, manual)
        - Integration with circuit breaker half-open state for testing recovery
        - Constitutional compliance check before any recovery action
        - Configurable recovery policies per service
        - Health check integration for validation

    Usage:
        orchestrator = RecoveryOrchestrator()
        await orchestrator.start()

        # Schedule recovery
        orchestrator.schedule_recovery(
            service_name="policy_service",
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            priority=1
        )

        # Check status
        status = orchestrator.get_recovery_status()

        # Cancel recovery
        orchestrator.cancel_recovery("policy_service")
    """

    def __init__(
        self,
        default_policy: Optional[RecoveryPolicy] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        """
        Initialize recovery orchestrator.

        Args:
            default_policy: Default recovery policy for services
            constitutional_hash: Constitutional hash for validation
        """
        self.constitutional_hash = constitutional_hash
        self.default_policy = default_policy or RecoveryPolicy()

        # Priority queue for recovery tasks (min-heap)
        self._recovery_queue: List[RecoveryTask] = []

        # Service-specific recovery policies
        self._policies: Dict[str, RecoveryPolicy] = {}

        # Active recovery tasks by service name
        self._active_tasks: Dict[str, RecoveryTask] = {}

        # Recovery history
        self._history: List[RecoveryResult] = []

        # Circuit breaker registry
        self._circuit_registry = CircuitBreakerRegistry() if CircuitBreakerRegistry else None

        # Orchestrator state
        self._running = False
        self._recovery_task: Optional[asyncio.Task] = None

        logger.info(
            f"[{self.constitutional_hash}] Recovery Orchestrator initialized"
        )

    def _validate_constitutional(self) -> None:
        """
        Validate constitutional hash before any operation.

        Raises:
            RecoveryConstitutionalError: If validation fails
        """
        result = validate_constitutional_hash(self.constitutional_hash)
        if not result.is_valid:
            raise RecoveryConstitutionalError(
                validation_errors=result.errors,
                agent_id="recovery_orchestrator",
                action_type="constitutional_validation",
            )

    async def start(self) -> None:
        """
        Start the recovery orchestrator.

        Raises:
            RecoveryOrchestratorError: If orchestrator is already running
        """
        self._validate_constitutional()

        if self._running:
            raise RecoveryOrchestratorError(
                message="Recovery orchestrator is already running",
                constitutional_hash=self.constitutional_hash,
            )

        self._running = True
        self._recovery_task = asyncio.create_task(self._recovery_loop())

        logger.info(
            f"[{self.constitutional_hash}] Recovery Orchestrator started"
        )

    async def stop(self) -> None:
        """Stop the recovery orchestrator."""
        if not self._running:
            return

        self._running = False

        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"[{self.constitutional_hash}] Recovery Orchestrator stopped"
        )

    def schedule_recovery(
        self,
        service_name: str,
        strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF,
        priority: int = 1,
        policy: Optional[RecoveryPolicy] = None,
    ) -> None:
        """
        Schedule a service for recovery.

        Args:
            service_name: Name of the service to recover
            strategy: Recovery strategy to use
            priority: Recovery priority (lower = higher priority)
            policy: Optional service-specific recovery policy

        Raises:
            RecoveryConstitutionalError: If constitutional validation fails
        """
        self._validate_constitutional()

        # Use service-specific policy, provided policy, or default
        recovery_policy = (
            policy or
            self._policies.get(service_name) or
            self.default_policy
        )

        # Create recovery task
        task = RecoveryTask(
            priority=priority,
            service_name=service_name,
            strategy=strategy,
            policy=recovery_policy,
            state=RecoveryState.SCHEDULED,
        )

        # Add to priority queue
        heapq.heappush(self._recovery_queue, task)
        self._active_tasks[service_name] = task

        logger.info(
            f"[{self.constitutional_hash}] Scheduled recovery for '{service_name}' "
            f"with strategy {strategy.value} and priority {priority}"
        )

    async def execute_recovery(self, service_name: str) -> RecoveryResult:
        """
        Execute recovery for a specific service.

        Args:
            service_name: Name of the service to recover

        Returns:
            RecoveryResult with recovery outcome

        Raises:
            RecoveryConstitutionalError: If constitutional validation fails
            RecoveryValidationError: If service not found in active tasks
        """
        self._validate_constitutional()

        if service_name not in self._active_tasks:
            raise RecoveryValidationError(
                message=f"No active recovery task for service '{service_name}'",
                constitutional_hash=self.constitutional_hash,
            )

        task = self._active_tasks[service_name]
        task.state = RecoveryState.IN_PROGRESS
        task.attempt_count += 1
        task.last_attempt_at = datetime.now(timezone.utc)

        start_time = datetime.now(timezone.utc)

        try:
            # Execute recovery based on strategy
            success = await self._execute_recovery_attempt(task)

            # Calculate elapsed time
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Check health if configured
            health_passed = False
            if task.policy.health_check_fn:
                try:
                    health_passed = task.policy.health_check_fn()
                    if not health_passed:
                        success = False
                except Exception as e:
                    logger.error(
                        f"[{self.constitutional_hash}] Health check failed for "
                        f"'{service_name}': {e}"
                    )
                    success = False

            # Update task state
            if success:
                task.state = RecoveryState.SUCCEEDED
                del self._active_tasks[service_name]
            elif task.attempt_count >= task.policy.max_retry_attempts:
                if task.strategy == RecoveryStrategy.MANUAL:
                    task.state = RecoveryState.AWAITING_MANUAL
                else:
                    task.state = RecoveryState.FAILED
                    del self._active_tasks[service_name]
            else:
                task.state = RecoveryState.SCHEDULED
                # Calculate next attempt time
                task.next_attempt_at = self._calculate_next_attempt(task)

            # Create result
            result = RecoveryResult(
                service_name=service_name,
                success=success,
                attempt_number=task.attempt_count,
                total_attempts=task.policy.max_retry_attempts,
                elapsed_time_ms=elapsed,
                state=task.state,
                health_check_passed=health_passed,
            )

            # Store in history
            self._history.append(result)

            logger.info(
                f"[{self.constitutional_hash}] Recovery attempt {task.attempt_count}/"
                f"{task.policy.max_retry_attempts} for '{service_name}': "
                f"{'SUCCESS' if success else 'FAILED'}"
            )

            return result

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            task.state = RecoveryState.FAILED

            result = RecoveryResult(
                service_name=service_name,
                success=False,
                attempt_number=task.attempt_count,
                total_attempts=task.policy.max_retry_attempts,
                elapsed_time_ms=elapsed,
                state=RecoveryState.FAILED,
                error_message=str(e),
            )

            self._history.append(result)

            logger.error(
                f"[{self.constitutional_hash}] Recovery failed for '{service_name}': {e}"
            )

            return result

    def get_recovery_status(self) -> Dict[str, Any]:
        """
        Get recovery status for all services.

        Returns:
            Dictionary containing recovery status information
        """
        return {
            "constitutional_hash": self.constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orchestrator_running": self._running,
            "active_recoveries": len(self._active_tasks),
            "queued_recoveries": len(self._recovery_queue),
            "services": {
                service_name: {
                    "state": task.state.value,
                    "strategy": task.strategy.value,
                    "priority": task.priority,
                    "attempt_count": task.attempt_count,
                    "max_attempts": task.policy.max_retry_attempts,
                    "scheduled_at": task.scheduled_at.isoformat(),
                    "last_attempt_at": (
                        task.last_attempt_at.isoformat()
                        if task.last_attempt_at
                        else None
                    ),
                    "next_attempt_at": (
                        task.next_attempt_at.isoformat()
                        if task.next_attempt_at
                        else None
                    ),
                }
                for service_name, task in self._active_tasks.items()
            },
            "recent_history": [
                result.to_dict()
                for result in self._history[-10:]  # Last 10 results
            ],
        }

    def cancel_recovery(self, service_name: str) -> bool:
        """
        Cancel recovery for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            True if recovery was cancelled, False if not found
        """
        if service_name not in self._active_tasks:
            return False

        task = self._active_tasks[service_name]
        task.state = RecoveryState.CANCELLED
        del self._active_tasks[service_name]

        logger.info(
            f"[{self.constitutional_hash}] Cancelled recovery for '{service_name}'"
        )

        return True

    def set_recovery_policy(
        self,
        service_name: str,
        policy: RecoveryPolicy,
    ) -> None:
        """
        Set recovery policy for a specific service.

        Args:
            service_name: Name of the service
            policy: Recovery policy to set

        Raises:
            RecoveryConstitutionalError: If constitutional validation fails
        """
        self._validate_constitutional()

        self._policies[service_name] = policy

        logger.info(
            f"[{self.constitutional_hash}] Set recovery policy for '{service_name}'"
        )

    def get_recovery_policy(self, service_name: str) -> RecoveryPolicy:
        """
        Get recovery policy for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Recovery policy for the service (or default if not set)
        """
        return self._policies.get(service_name, self.default_policy)

    async def _recovery_loop(self) -> None:
        """Main recovery loop that processes recovery queue."""
        while self._running:
            try:
                # Check for tasks ready to execute
                now = datetime.now(timezone.utc)

                # Process tasks that are ready
                ready_tasks = []
                for task in list(self._active_tasks.values()):
                    if task.state == RecoveryState.SCHEDULED:
                        # Check if it's time to retry
                        if task.next_attempt_at is None or task.next_attempt_at <= now:
                            ready_tasks.append(task)

                # Execute ready tasks in priority order
                ready_tasks.sort(key=lambda t: t.priority)
                for task in ready_tasks:
                    try:
                        await self.execute_recovery(task.service_name)
                    except Exception as e:
                        logger.error(
                            f"[{self.constitutional_hash}] Error executing recovery "
                            f"for '{task.service_name}': {e}"
                        )

                # Sleep before next iteration
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"[{self.constitutional_hash}] Error in recovery loop: {e}"
                )
                await asyncio.sleep(5.0)  # Back off on errors

    async def _execute_recovery_attempt(self, task: RecoveryTask) -> bool:
        """
        Execute a single recovery attempt.

        Args:
            task: Recovery task to execute

        Returns:
            True if recovery succeeded, False otherwise
        """
        # Reset circuit breaker for half-open testing
        if self._circuit_registry:
            self._circuit_registry.reset(task.service_name)

            # Wait a moment for circuit breaker to settle
            await asyncio.sleep(0.1)

            # Check circuit breaker state
            states = self._circuit_registry.get_all_states()
            if task.service_name in states:
                state = states[task.service_name]['state']
                # Success if circuit is closed or half-open
                try:
                    import pybreaker
                    return state in [pybreaker.STATE_CLOSED, pybreaker.STATE_HALF_OPEN]
                except ImportError:
                    # Fallback if pybreaker not available
                    return True

        # If no circuit breaker registry, assume success
        return True

    def _calculate_next_attempt(self, task: RecoveryTask) -> datetime:
        """
        Calculate next attempt time based on strategy and policy.

        Args:
            task: Recovery task

        Returns:
            Datetime for next attempt
        """
        policy = task.policy

        if task.strategy == RecoveryStrategy.IMMEDIATE:
            # Immediate retry
            delay_ms = 0
        elif task.strategy == RecoveryStrategy.LINEAR_BACKOFF:
            # Linear backoff
            delay_ms = min(
                policy.initial_delay_ms * task.attempt_count,
                policy.max_delay_ms
            )
        elif task.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            # Exponential backoff
            delay_ms = min(
                policy.initial_delay_ms * (policy.backoff_multiplier ** (task.attempt_count - 1)),
                policy.max_delay_ms
            )
        else:  # MANUAL
            # No automatic retry for manual strategy
            delay_ms = policy.max_delay_ms * 1000  # Very long delay

        # Calculate next attempt time
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        return now + timedelta(milliseconds=delay_ms)


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Enums
    "RecoveryStrategy",
    "RecoveryState",
    # Data Classes
    "RecoveryPolicy",
    "RecoveryResult",
    "RecoveryTask",
    # Exceptions
    "RecoveryOrchestratorError",
    "RecoveryValidationError",
    "RecoveryConstitutionalError",
    # Main Class
    "RecoveryOrchestrator",
]
