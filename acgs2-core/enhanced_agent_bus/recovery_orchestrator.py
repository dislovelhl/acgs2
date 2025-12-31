import asyncio, logging, heapq, time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from .utils import get_iso_timestamp
from .models import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)

class RecoveryState(Enum):
    IDLE = "idle"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_MANUAL = "awaiting_manual"

class RecoveryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"
    MANUAL = "manual"

class RecoveryOrchestratorError(Exception): pass
class RecoveryConstitutionalError(Exception): pass
class RecoveryValidationError(Exception): pass

@dataclass
class RecoveryPolicy:
    max_retry_attempts: int = 5
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    health_check_fn: Optional[Callable] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def __post_init__(self):
        if self.max_retry_attempts < 1: raise ValueError("max_retry_attempts must be >= 1")
        if self.backoff_multiplier < 1.0: raise ValueError("backoff_multiplier must be >= 1.0")
        if self.initial_delay_ms < 0: raise ValueError("initial_delay_ms must be >= 0")
        if self.max_delay_ms < self.initial_delay_ms: raise ValueError("max_delay_ms must be >= initial_delay_ms")

@dataclass
class RecoveryResult:
    service_name: str
    success: bool
    attempt_number: int
    total_attempts: int
    elapsed_time_ms: float
    state: RecoveryState
    error_message: Optional[str] = None
    health_check_passed: Optional[bool] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: str = field(default_factory=get_iso_timestamp)

    def to_dict(self) -> Dict[str, Any]:
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
            "timestamp": self.timestamp
        }

@dataclass(order=True)
class RecoveryTask:
    priority: int
    service_name: str = field(compare=False)
    strategy: RecoveryStrategy = field(compare=False)
    policy: RecoveryPolicy = field(compare=False)
    attempt_count: int = field(default=0, compare=False)
    state: RecoveryState = field(default=RecoveryState.SCHEDULED, compare=False)
    last_attempt_at: Optional[datetime] = field(default=None, compare=False)
    next_attempt_at: Optional[datetime] = field(default=None, compare=False)
    constitutional_hash: str = CONSTITUTIONAL_HASH

class RecoveryOrchestrator:
    def __init__(self, default_policy: Optional[RecoveryPolicy] = None):
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self.default_policy = default_policy or RecoveryPolicy()
        self._tasks: Dict[str, RecoveryTask] = {}
        self._policies: Dict[str, RecoveryPolicy] = {}
        self._queue: List[RecoveryTask] = []
        self._history: List[RecoveryResult] = []
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def constitutional_hash(self) -> str: return self._constitutional_hash

    async def start(self):
        async with self._lock:
            if self._running: raise RecoveryOrchestratorError("already running")
            self._running = True
            self._loop_task = asyncio.create_task(self._loop())

    async def stop(self):
        async with self._lock:
            self._running = False
            if self._loop_task:
                self._loop_task.cancel()
                self._loop_task = None

    def schedule_recovery(self, service_name: str, strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF, priority: int = 1, policy: Optional[RecoveryPolicy] = None):
        if service_name in self._tasks: return
        task = RecoveryTask(priority, service_name, strategy, policy or self.default_policy)
        task.next_attempt_at = self._calculate_next_attempt(task)
        self._tasks[service_name] = task
        heapq.heappush(self._queue, task)

    def cancel_recovery(self, service_name: str) -> bool:
        if service_name not in self._tasks: return False
        task = self._tasks.pop(service_name)
        task.state = RecoveryState.CANCELLED
        # Note: Task remains in heap but will be skipped
        return True

    def set_recovery_policy(self, service_name: str, policy: RecoveryPolicy):
        self._policies[service_name] = policy
        if service_name in self._tasks:
            self._tasks[service_name].policy = policy

    def get_recovery_policy(self, service_name: str) -> RecoveryPolicy:
        if service_name in self._tasks: return self._tasks[service_name].policy
        return self._policies.get(service_name, self.default_policy)

    def get_recovery_status(self) -> Dict[str, Any]:
        return {
            "constitutional_hash": self._constitutional_hash,
            "timestamp": get_iso_timestamp(),
            "orchestrator_running": self._running,
            "active_recoveries": sum(1 for t in self._tasks.values() if t.state == RecoveryState.IN_PROGRESS),
            "queued_recoveries": len(self._queue),
            "services": {name: {"state": t.state.value, "max_attempts": t.policy.max_retry_attempts} for name, t in self._tasks.items()},
            "recent_history": [r.to_dict() for r in self._history[-10:]]
        }

    async def execute_recovery(self, service_name: str) -> RecoveryResult:
        if service_name not in self._tasks: raise RecoveryValidationError("No active recovery task")
        task = self._tasks[service_name]
        start_time = time.time()
        task.state = RecoveryState.IN_PROGRESS
        task.attempt_count += 1
        task.last_attempt_at = datetime.now(timezone.utc)

        success = True
        health_passed = None
        error = None

        if task.policy.health_check_fn:
            try:
                health_passed = task.policy.health_check_fn()
                success = health_passed
            except Exception as e:
                success = False
                error = str(e)

        elapsed = (time.time() - start_time) * 1000

        if success:
            task.state = RecoveryState.SUCCEEDED
            del self._tasks[service_name]
        elif task.attempt_count >= task.policy.max_retry_attempts:
            task.state = RecoveryState.FAILED
            del self._tasks[service_name]
        else:
            task.state = RecoveryState.SCHEDULED
            task.next_attempt_at = self._calculate_next_attempt(task)
            heapq.heappush(self._queue, task)

        result = RecoveryResult(
            service_name=service_name,
            success=success,
            attempt_number=task.attempt_count,
            total_attempts=task.policy.max_retry_attempts,
            elapsed_time_ms=elapsed,
            state=task.state,
            error_message=error,
            health_check_passed=health_passed
        )
        self._history.append(result)
        return result

    def _calculate_next_attempt(self, task: RecoveryTask) -> datetime:
        now = datetime.now(timezone.utc)
        if task.strategy == RecoveryStrategy.IMMEDIATE:
            return now
        elif task.strategy == RecoveryStrategy.LINEAR_BACKOFF:
            delay = task.policy.initial_delay_ms * task.attempt_count
        elif task.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            delay = task.policy.initial_delay_ms * (task.policy.backoff_multiplier ** (task.attempt_count - 1 if task.attempt_count > 0 else 0))
        else:
            return now # Manual or other

        delay = min(delay, task.policy.max_delay_ms)
        return now + timedelta(milliseconds=delay)

    async def _loop(self):
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                while self._queue and (self._queue[0].state == RecoveryState.CANCELLED or self._queue[0].next_attempt_at <= now):
                    task = heapq.heappop(self._queue)
                    if task.state == RecoveryState.CANCELLED: continue
                    if task.service_name in self._tasks:
                        await self.execute_recovery(task.service_name)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError: break
            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(1)

_orchestrator = None
def get_recovery_orchestrator():
    global _orchestrator
    if not _orchestrator: _orchestrator = RecoveryOrchestrator()
    return _orchestrator
