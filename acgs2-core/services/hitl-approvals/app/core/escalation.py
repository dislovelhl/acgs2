"""
Redis-backed Escalation Timer System with SLA Tracking

Implements time-based auto-escalation using Redis for timer storage and
sorted sets for reliable expiration detection. Avoids polling by using
Redis sorted sets with scores as expiration timestamps.

Key Design Decisions:
- Uses Redis sorted sets instead of TTL-based expiration for reliable detection
- Uses Redis server time (TIME command) to avoid clock drift issues
- Supports configurable timeouts per priority level
- Integrates with ApprovalEngine for escalation callbacks
- Provides comprehensive SLA tracking and compliance monitoring
- Supports configurable escalation policies with SLA thresholds
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from app.config import settings
from app.models import ApprovalPriority, ApprovalRequest, EscalationPolicy

logger = logging.getLogger(__name__)

# Redis key prefixes
REDIS_ESCALATION_ZSET = "hitl:escalation:timers"
REDIS_ESCALATION_DATA_PREFIX = "hitl:escalation:data:"
REDIS_ESCALATION_LOCK = "hitl:escalation:lock"

# SLA tracking Redis keys
REDIS_SLA_METRICS_KEY = "hitl:sla:metrics"
REDIS_SLA_BREACHES_ZSET = "hitl:sla:breaches"
REDIS_SLA_BREACH_DATA_PREFIX = "hitl:sla:breach:data:"
REDIS_POLICY_PREFIX = "hitl:escalation:policy:"
REDIS_POLICY_SET = "hitl:escalation:policies"

# Default check interval for expired timers (seconds)
DEFAULT_CHECK_INTERVAL_SECONDS = 5

# SLA warning threshold (percentage of timeout before warning)
DEFAULT_SLA_WARNING_THRESHOLD_PERCENT = 75


class EscalationTimerError(Exception):
    """Base exception for escalation timer errors."""

    pass


class RedisConnectionError(EscalationTimerError):
    """Raised when Redis connection fails."""

    pass


class TimerNotFoundError(EscalationTimerError):
    """Raised when a timer is not found."""

    pass


class EscalationReason(str, Enum):
    """Reasons for escalation."""

    TIMEOUT = "timeout"
    MANUAL = "manual"
    SLA_BREACH = "sla_breach"
    NO_RESPONSE = "no_response"


class SLAStatus(str, Enum):
    """SLA compliance status."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    BREACHED = "breached"
    CRITICAL = "critical"


@dataclass
class SLAConfig:
    """Configuration for SLA thresholds and monitoring.

    Defines the timeout thresholds per priority level and warning percentages.
    """

    # Priority-based timeout configuration (in minutes)
    critical_timeout_minutes: int = field(
        default_factory=lambda: settings.critical_escalation_timeout_minutes
    )
    high_timeout_minutes: int = field(
        default_factory=lambda: int(settings.default_escalation_timeout_minutes * 0.75)
    )
    medium_timeout_minutes: int = field(
        default_factory=lambda: settings.default_escalation_timeout_minutes
    )
    low_timeout_minutes: int = field(
        default_factory=lambda: int(settings.default_escalation_timeout_minutes * 1.5)
    )

    # Warning threshold (percentage of timeout before warning)
    warning_threshold_percent: int = DEFAULT_SLA_WARNING_THRESHOLD_PERCENT

    # Maximum allowed escalations before final fallback
    max_escalations: int = 3

    # Enable PagerDuty for critical breaches
    pagerduty_on_critical: bool = True

    def get_timeout_for_priority(self, priority: ApprovalPriority) -> int:
        """Get timeout in minutes for a priority level."""
        if priority == ApprovalPriority.CRITICAL:
            return self.critical_timeout_minutes
        elif priority == ApprovalPriority.HIGH:
            return self.high_timeout_minutes
        elif priority == ApprovalPriority.MEDIUM:
            return self.medium_timeout_minutes
        else:  # LOW
            return self.low_timeout_minutes

    def get_warning_threshold_minutes(self, priority: ApprovalPriority) -> float:
        """Get the warning threshold in minutes for a priority level."""
        timeout = self.get_timeout_for_priority(priority)
        return timeout * (self.warning_threshold_percent / 100)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "critical_timeout_minutes": self.critical_timeout_minutes,
            "high_timeout_minutes": self.high_timeout_minutes,
            "medium_timeout_minutes": self.medium_timeout_minutes,
            "low_timeout_minutes": self.low_timeout_minutes,
            "warning_threshold_percent": self.warning_threshold_percent,
            "max_escalations": self.max_escalations,
            "pagerduty_on_critical": self.pagerduty_on_critical,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLAConfig":
        """Create from dictionary."""
        return cls(
            critical_timeout_minutes=int(data.get("critical_timeout_minutes", 15)),
            high_timeout_minutes=int(data.get("high_timeout_minutes", 22)),
            medium_timeout_minutes=int(data.get("medium_timeout_minutes", 30)),
            low_timeout_minutes=int(data.get("low_timeout_minutes", 45)),
            warning_threshold_percent=int(data.get("warning_threshold_percent", 75)),
            max_escalations=int(data.get("max_escalations", 3)),
            pagerduty_on_critical=bool(data.get("pagerduty_on_critical", True)),
        )


@dataclass
class SLAMetrics:
    """Tracks SLA compliance metrics over time.

    Provides real-time and historical SLA performance data.
    """

    total_requests: int = 0
    completed_within_sla: int = 0
    sla_breaches: int = 0
    warnings_triggered: int = 0
    escalations_performed: int = 0

    # Timing metrics (in seconds)
    total_response_time_seconds: float = 0.0
    min_response_time_seconds: float = float("inf")
    max_response_time_seconds: float = 0.0

    # Priority-specific metrics
    breaches_by_priority: Dict[str, int] = field(default_factory=dict)
    escalations_by_priority: Dict[str, int] = field(default_factory=dict)

    # Time window (for windowed metrics)
    window_start: Optional[float] = None
    window_end: Optional[float] = None

    @property
    def compliance_rate(self) -> float:
        """Calculate SLA compliance rate as a percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.completed_within_sla / self.total_requests) * 100

    @property
    def breach_rate(self) -> float:
        """Calculate SLA breach rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.sla_breaches / self.total_requests) * 100

    @property
    def average_response_time_seconds(self) -> float:
        """Calculate average response time in seconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_seconds / self.total_requests

    @property
    def average_response_time_minutes(self) -> float:
        """Calculate average response time in minutes."""
        return self.average_response_time_seconds / 60

    def record_completion(
        self,
        response_time_seconds: float,
        within_sla: bool,
        priority: ApprovalPriority,
    ) -> None:
        """Record a completed request."""
        self.total_requests += 1
        self.total_response_time_seconds += response_time_seconds

        # Update min/max response times
        self.min_response_time_seconds = min(self.min_response_time_seconds, response_time_seconds)
        self.max_response_time_seconds = max(self.max_response_time_seconds, response_time_seconds)

        if within_sla:
            self.completed_within_sla += 1

    def record_breach(self, priority: ApprovalPriority) -> None:
        """Record an SLA breach."""
        self.sla_breaches += 1
        priority_key = priority.value
        self.breaches_by_priority[priority_key] = self.breaches_by_priority.get(priority_key, 0) + 1

    def record_escalation(self, priority: ApprovalPriority) -> None:
        """Record an escalation event."""
        self.escalations_performed += 1
        priority_key = priority.value
        self.escalations_by_priority[priority_key] = (
            self.escalations_by_priority.get(priority_key, 0) + 1
        )

    def record_warning(self) -> None:
        """Record a warning event."""
        self.warnings_triggered += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "total_requests": self.total_requests,
            "completed_within_sla": self.completed_within_sla,
            "sla_breaches": self.sla_breaches,
            "warnings_triggered": self.warnings_triggered,
            "escalations_performed": self.escalations_performed,
            "total_response_time_seconds": self.total_response_time_seconds,
            "min_response_time_seconds": self.min_response_time_seconds,
            "max_response_time_seconds": self.max_response_time_seconds,
            "breaches_by_priority": self.breaches_by_priority,
            "escalations_by_priority": self.escalations_by_priority,
            "compliance_rate": self.compliance_rate,
            "breach_rate": self.breach_rate,
            "average_response_time_seconds": self.average_response_time_seconds,
            "window_start": self.window_start,
            "window_end": self.window_end,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLAMetrics":
        """Create from dictionary."""
        metrics = cls(
            total_requests=int(data.get("total_requests", 0)),
            completed_within_sla=int(data.get("completed_within_sla", 0)),
            sla_breaches=int(data.get("sla_breaches", 0)),
            warnings_triggered=int(data.get("warnings_triggered", 0)),
            escalations_performed=int(data.get("escalations_performed", 0)),
            total_response_time_seconds=float(data.get("total_response_time_seconds", 0.0)),
            min_response_time_seconds=float(data.get("min_response_time_seconds", float("inf"))),
            max_response_time_seconds=float(data.get("max_response_time_seconds", 0.0)),
            breaches_by_priority=data.get("breaches_by_priority", {}),
            escalations_by_priority=data.get("escalations_by_priority", {}),
            window_start=data.get("window_start"),
            window_end=data.get("window_end"),
        )
        return metrics


@dataclass
class SLABreach:
    """Represents an SLA breach event.

    Captures details about when and why an SLA was breached.
    """

    breach_id: str
    request_id: str
    priority: ApprovalPriority
    breach_time: float  # Unix timestamp
    sla_timeout_minutes: int
    actual_time_minutes: float
    breach_reason: EscalationReason
    escalation_level: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overage_minutes(self) -> float:
        """Calculate how much the SLA was exceeded by."""
        return self.actual_time_minutes - self.sla_timeout_minutes

    @property
    def overage_percent(self) -> float:
        """Calculate the percentage by which SLA was exceeded."""
        if self.sla_timeout_minutes == 0:
            return 0.0
        return (self.overage_minutes / self.sla_timeout_minutes) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "breach_id": self.breach_id,
            "request_id": self.request_id,
            "priority": self.priority.value,
            "breach_time": self.breach_time,
            "sla_timeout_minutes": self.sla_timeout_minutes,
            "actual_time_minutes": self.actual_time_minutes,
            "breach_reason": self.breach_reason.value,
            "escalation_level": self.escalation_level,
            "overage_minutes": self.overage_minutes,
            "overage_percent": self.overage_percent,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLABreach":
        """Create from dictionary."""
        return cls(
            breach_id=data["breach_id"],
            request_id=data["request_id"],
            priority=ApprovalPriority(data["priority"]),
            breach_time=float(data["breach_time"]),
            sla_timeout_minutes=int(data["sla_timeout_minutes"]),
            actual_time_minutes=float(data["actual_time_minutes"]),
            breach_reason=EscalationReason(data["breach_reason"]),
            escalation_level=int(data.get("escalation_level", 1)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EscalationTimer:
    """Represents an escalation timer for an approval request."""

    request_id: str
    priority: ApprovalPriority
    timeout_minutes: int
    created_at: float  # Unix timestamp from Redis server
    expires_at: float  # Unix timestamp from Redis server
    current_level: int = 1
    escalation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the timer has expired using current time."""
        return time.time() >= self.expires_at

    @property
    def time_remaining_seconds(self) -> float:
        """Get remaining time in seconds."""
        return max(0, self.expires_at - time.time())

    @property
    def time_remaining_minutes(self) -> float:
        """Get remaining time in minutes."""
        return self.time_remaining_seconds / 60

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "request_id": self.request_id,
            "priority": self.priority.value,
            "timeout_minutes": self.timeout_minutes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "current_level": self.current_level,
            "escalation_count": self.escalation_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationTimer":
        """Create from dictionary (Redis storage)."""
        return cls(
            request_id=data["request_id"],
            priority=ApprovalPriority(data["priority"]),
            timeout_minutes=int(data["timeout_minutes"]),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
            current_level=int(data.get("current_level", 1)),
            escalation_count=int(data.get("escalation_count", 0)),
            metadata=data.get("metadata", {}),
        )


# Type alias for escalation callback
EscalationCallback = Callable[[str, EscalationReason], Coroutine[Any, Any, None]]


class EscalationTimerManager:
    """
    Manages escalation timers using Redis sorted sets.

    Architecture:
    - Sorted set (ZSET) stores request_ids with expiration timestamps as scores
    - Hash keys store timer metadata for each request
    - Background task checks for expired timers and triggers escalations

    Clock Drift Handling:
    - Uses Redis TIME command for all timestamp operations
    - Server-side time ensures consistency across distributed instances

    Rate Limiting:
    - Processes expired timers in batches
    - Uses distributed lock to prevent duplicate processing
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    ):
        """
        Initialize the escalation timer manager.

        Args:
            redis_url: Redis connection URL. Uses settings if not provided.
            check_interval: Interval in seconds between expiration checks.
        """
        self._redis_url = redis_url or settings.redis_url
        self._check_interval = check_interval
        self._redis: Optional[Any] = None
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        self._escalation_callbacks: List[EscalationCallback] = []
        self._lock = asyncio.Lock()
        self._processed_timers: Set[str] = set()

        logger.info(f"EscalationTimerManager initialized " f"(check_interval={check_interval}s)")

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        """
        Establish connection to Redis.

        Raises:
            RedisConnectionError: If connection fails
        """
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()

            logger.info(f"Connected to Redis: {self._sanitize_url(self._redis_url)}")

        except ImportError as err:
            raise RedisConnectionError(
                "redis package not installed. Install with: pip install redis"
            ) from err
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Close Redis connection and stop background tasks."""
        await self.stop()

        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def health_check(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if Redis is reachable
        """
        if not self._redis:
            return False

        try:
            await self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for logging (remove password)."""
        if "@" in url:
            # Format: redis://:password@host:port/db
            parts = url.split("@")
            return f"redis://***@{parts[-1]}"
        return url

    # =========================================================================
    # Server Time Operations (Clock Drift Prevention)
    # =========================================================================

    async def _get_server_time(self) -> float:
        """
        Get current time from Redis server.

        Uses Redis TIME command to avoid clock drift issues in distributed systems.

        Returns:
            Unix timestamp from Redis server
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        # TIME returns [seconds, microseconds]
        time_result = await self._redis.time()
        return float(time_result[0]) + float(time_result[1]) / 1_000_000

    # =========================================================================
    # Timer Operations
    # =========================================================================

    async def set_timer(
        self,
        request_id: str,
        priority: ApprovalPriority,
        timeout_minutes: Optional[int] = None,
        current_level: int = 1,
        escalation_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EscalationTimer:
        """
        Set an escalation timer for an approval request.

        Args:
            request_id: Unique identifier for the approval request
            priority: Priority level (affects default timeout if not specified)
            timeout_minutes: Custom timeout in minutes (uses priority default if None)
            current_level: Current approval level
            escalation_count: Number of previous escalations
            metadata: Additional timer metadata

        Returns:
            The created EscalationTimer

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        # Determine timeout based on priority if not specified
        if timeout_minutes is None:
            timeout_minutes = self._get_timeout_for_priority(priority)

        # Get server time to avoid clock drift
        server_time = await self._get_server_time()
        expires_at = server_time + (timeout_minutes * 60)

        timer = EscalationTimer(
            request_id=request_id,
            priority=priority,
            timeout_minutes=timeout_minutes,
            created_at=server_time,
            expires_at=expires_at,
            current_level=current_level,
            escalation_count=escalation_count,
            metadata=metadata or {},
        )

        # Store in Redis using sorted set for efficient expiration queries
        # Score = expiration timestamp (allows range queries for expired timers)
        async with self._lock:
            # Add to sorted set with expiration time as score
            await self._redis.zadd(REDIS_ESCALATION_ZSET, {request_id: expires_at})

            # Store timer data as hash
            data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
            await self._redis.hset(data_key, mapping=self._flatten_dict(timer.to_dict()))

            # Set TTL on data key for cleanup (extra buffer time)
            await self._redis.expire(data_key, timeout_minutes * 60 + 3600)

        logger.info(
            f"Escalation timer set for {request_id}: "
            f"timeout={timeout_minutes}min, priority={priority.value}, "
            f"expires_at={datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()}"
        )

        return timer

    async def cancel_timer(self, request_id: str) -> bool:
        """
        Cancel an escalation timer.

        Args:
            request_id: The approval request ID

        Returns:
            True if timer was found and cancelled

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        async with self._lock:
            # Remove from sorted set
            removed = await self._redis.zrem(REDIS_ESCALATION_ZSET, request_id)

            # Remove timer data
            data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
            await self._redis.delete(data_key)

            # Remove from processed set if present
            self._processed_timers.discard(request_id)

        if removed:
            logger.info(f"Escalation timer cancelled for {request_id}")
            return True
        else:
            logger.debug(f"No escalation timer found for {request_id}")
            return False

    async def get_timer(self, request_id: str) -> Optional[EscalationTimer]:
        """
        Get an escalation timer by request ID.

        Args:
            request_id: The approval request ID

        Returns:
            The EscalationTimer if found, None otherwise

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
        data = await self._redis.hgetall(data_key)

        if not data:
            return None

        return EscalationTimer.from_dict(self._unflatten_dict(data))

    async def extend_timer(
        self,
        request_id: str,
        additional_minutes: int,
    ) -> Optional[EscalationTimer]:
        """
        Extend an existing escalation timer.

        Args:
            request_id: The approval request ID
            additional_minutes: Minutes to add to the current expiration

        Returns:
            The updated EscalationTimer, or None if not found

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        timer = await self.get_timer(request_id)
        if not timer:
            return None

        # Calculate new expiration
        new_expires_at = timer.expires_at + (additional_minutes * 60)

        async with self._lock:
            # Update sorted set score
            await self._redis.zadd(REDIS_ESCALATION_ZSET, {request_id: new_expires_at})

            # Update stored data
            data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
            await self._redis.hset(data_key, "expires_at", str(new_expires_at))

            # Extend TTL on data key
            remaining = int(new_expires_at - time.time()) + 3600
            await self._redis.expire(data_key, max(remaining, 3600))

        timer.expires_at = new_expires_at
        logger.info(f"Escalation timer extended for {request_id}: +{additional_minutes}min")

        return timer

    async def reset_timer(
        self,
        request_id: str,
        new_timeout_minutes: Optional[int] = None,
    ) -> Optional[EscalationTimer]:
        """
        Reset an escalation timer with a new timeout starting from now.

        Args:
            request_id: The approval request ID
            new_timeout_minutes: New timeout (uses priority default if None)

        Returns:
            The updated EscalationTimer, or None if not found

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        timer = await self.get_timer(request_id)
        if not timer:
            return None

        # Cancel existing timer
        await self.cancel_timer(request_id)

        # Create new timer with same metadata
        return await self.set_timer(
            request_id=request_id,
            priority=timer.priority,
            timeout_minutes=new_timeout_minutes or timer.timeout_minutes,
            current_level=timer.current_level,
            escalation_count=timer.escalation_count,
            metadata=timer.metadata,
        )

    # =========================================================================
    # Timer Queries
    # =========================================================================

    async def get_expired_timers(self, limit: int = 100) -> List[EscalationTimer]:
        """
        Get all expired escalation timers.

        Uses Redis ZRANGEBYSCORE to efficiently query timers by expiration time.

        Args:
            limit: Maximum number of timers to return

        Returns:
            List of expired EscalationTimer objects

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        # Get server time for consistent expiration check
        server_time = await self._get_server_time()

        # Query sorted set for all timers with score <= current time
        expired_ids = await self._redis.zrangebyscore(
            REDIS_ESCALATION_ZSET,
            "-inf",
            server_time,
            start=0,
            num=limit,
        )

        timers = []
        for request_id in expired_ids:
            timer = await self.get_timer(request_id)
            if timer:
                timers.append(timer)

        return timers

    async def get_pending_timers(self, limit: int = 100) -> List[EscalationTimer]:
        """
        Get all pending (non-expired) escalation timers.

        Args:
            limit: Maximum number of timers to return

        Returns:
            List of pending EscalationTimer objects

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        server_time = await self._get_server_time()

        # Query sorted set for all timers with score > current time
        pending_ids = await self._redis.zrangebyscore(
            REDIS_ESCALATION_ZSET,
            f"({server_time}",  # Exclusive lower bound
            "+inf",
            start=0,
            num=limit,
        )

        timers = []
        for request_id in pending_ids:
            timer = await self.get_timer(request_id)
            if timer:
                timers.append(timer)

        return timers

    async def get_timer_count(self) -> int:
        """
        Get the total number of active escalation timers.

        Returns:
            Number of active timers

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        return await self._redis.zcard(REDIS_ESCALATION_ZSET)

    async def get_expiring_soon(
        self,
        within_minutes: int = 5,
        limit: int = 100,
    ) -> List[EscalationTimer]:
        """
        Get timers expiring within the specified time window.

        Args:
            within_minutes: Time window in minutes
            limit: Maximum number of timers to return

        Returns:
            List of EscalationTimer objects expiring soon

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        server_time = await self._get_server_time()
        cutoff_time = server_time + (within_minutes * 60)

        expiring_ids = await self._redis.zrangebyscore(
            REDIS_ESCALATION_ZSET,
            f"({server_time}",  # Exclusive: not already expired
            cutoff_time,
            start=0,
            num=limit,
        )

        timers = []
        for request_id in expiring_ids:
            timer = await self.get_timer(request_id)
            if timer:
                timers.append(timer)

        return timers

    # =========================================================================
    # Callback Registration
    # =========================================================================

    def register_escalation_callback(self, callback: EscalationCallback) -> None:
        """
        Register a callback to be called when a timer expires.

        Args:
            callback: Async function that takes (request_id, reason) parameters
        """
        self._escalation_callbacks.append(callback)
        logger.info(f"Registered escalation callback: {callback.__name__}")

    def unregister_escalation_callback(self, callback: EscalationCallback) -> bool:
        """
        Unregister an escalation callback.

        Args:
            callback: The callback to remove

        Returns:
            True if callback was found and removed
        """
        try:
            self._escalation_callbacks.remove(callback)
            logger.info(f"Unregistered escalation callback: {callback.__name__}")
            return True
        except ValueError:
            return False

    # =========================================================================
    # Background Processing
    # =========================================================================

    async def start(self) -> None:
        """Start the background task for processing expired timers."""
        if self._running:
            logger.warning("Escalation timer manager already running")
            return

        if not self._redis:
            await self.connect()

        self._running = True
        self._background_task = asyncio.create_task(self._process_expired_timers_loop())
        logger.info("Escalation timer manager started")

    async def stop(self) -> None:
        """Stop the background task."""
        self._running = False

        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None

        logger.info("Escalation timer manager stopped")

    async def _process_expired_timers_loop(self) -> None:
        """Background loop that processes expired timers."""
        logger.info(f"Started expired timer processing loop " f"(interval={self._check_interval}s)")

        while self._running:
            try:
                await self._process_expired_timers()
            except Exception as e:
                logger.error(f"Error processing expired timers: {e}")

            await asyncio.sleep(self._check_interval)

    async def _process_expired_timers(self) -> None:
        """Process all expired timers and trigger escalation callbacks."""
        expired_timers = await self.get_expired_timers()

        if not expired_timers:
            return

        logger.info(f"Processing {len(expired_timers)} expired escalation timers")

        for timer in expired_timers:
            # Skip if already processed (idempotency)
            if timer.request_id in self._processed_timers:
                continue

            try:
                # Mark as processed before callbacks (prevent duplicates)
                self._processed_timers.add(timer.request_id)

                # Trigger all registered callbacks
                for callback in self._escalation_callbacks:
                    try:
                        await callback(timer.request_id, EscalationReason.TIMEOUT)
                    except Exception as e:
                        logger.error(f"Escalation callback error for {timer.request_id}: {e}")

                # Remove the expired timer
                await self.cancel_timer(timer.request_id)

                logger.info(
                    f"Processed escalation for {timer.request_id} "
                    f"(level={timer.current_level}, count={timer.escalation_count})"
                )

            except Exception as e:
                # Remove from processed set on error to allow retry
                self._processed_timers.discard(timer.request_id)
                logger.error(f"Failed to process escalation for {timer.request_id}: {e}")

        # Clean up processed set (keep only recent entries)
        if len(self._processed_timers) > 1000:
            self._processed_timers = set(list(self._processed_timers)[-500:])

    # =========================================================================
    # Priority-Based Timeout Configuration
    # =========================================================================

    def _get_timeout_for_priority(self, priority: ApprovalPriority) -> int:
        """
        Get default timeout in minutes for a priority level.

        Args:
            priority: The approval priority

        Returns:
            Timeout in minutes
        """
        if priority == ApprovalPriority.CRITICAL:
            return settings.critical_escalation_timeout_minutes
        elif priority == ApprovalPriority.HIGH:
            # High priority: 75% of default
            return int(settings.default_escalation_timeout_minutes * 0.75)
        elif priority == ApprovalPriority.MEDIUM:
            return settings.default_escalation_timeout_minutes
        else:  # LOW
            # Low priority: 150% of default
            return int(settings.default_escalation_timeout_minutes * 1.5)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten a nested dictionary for Redis hash storage."""
        items: Dict[str, str] = {}
        for key, value in d.items():
            new_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            if isinstance(value, dict):
                items.update(self._flatten_dict(value, new_key))
            else:
                items[new_key] = str(value)
        return items

    def _unflatten_dict(self, d: Dict[str, str]) -> Dict[str, Any]:
        """Unflatten a Redis hash back to nested dictionary."""
        result: Dict[str, Any] = {}
        for key, value in d.items():
            if "." in key:
                parts = key.split(".", 1)
                if parts[0] not in result:
                    result[parts[0]] = {}
                if isinstance(result[parts[0]], dict):
                    result[parts[0]][parts[1]] = value
            else:
                # Try to convert numeric values
                try:
                    if "." in value:
                        result[key] = float(value)
                    else:
                        result[key] = int(value)
                except (ValueError, TypeError):
                    result[key] = value
        return result

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the escalation timer system.

        Returns:
            Dictionary of statistics

        Raises:
            RedisConnectionError: If Redis is not connected
        """
        if not self._redis:
            raise RedisConnectionError("Redis not connected")

        server_time = await self._get_server_time()
        total_timers = await self.get_timer_count()

        # Count expired timers
        expired_count = await self._redis.zcount(
            REDIS_ESCALATION_ZSET,
            "-inf",
            server_time,
        )

        # Count timers expiring in next 5 minutes
        expiring_soon_count = await self._redis.zcount(
            REDIS_ESCALATION_ZSET,
            f"({server_time}",
            server_time + 300,
        )

        return {
            "total_timers": total_timers,
            "expired_timers": expired_count,
            "expiring_soon_5min": expiring_soon_count,
            "pending_timers": total_timers - expired_count,
            "registered_callbacks": len(self._escalation_callbacks),
            "processed_count": len(self._processed_timers),
            "is_running": self._running,
            "check_interval_seconds": self._check_interval,
        }


# =============================================================================
# Singleton Instance Management
# =============================================================================

_escalation_manager: Optional[EscalationTimerManager] = None


def get_escalation_manager() -> EscalationTimerManager:
    """
    Get the global EscalationTimerManager instance.

    Returns:
        The singleton EscalationTimerManager instance
    """
    global _escalation_manager
    if _escalation_manager is None:
        _escalation_manager = EscalationTimerManager()
    return _escalation_manager


async def initialize_escalation_manager(
    redis_url: Optional[str] = None,
    check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    start_background_task: bool = True,
) -> EscalationTimerManager:
    """
    Initialize and start the global escalation manager.

    Args:
        redis_url: Redis connection URL (uses settings if None)
        check_interval: Interval between expiration checks
        start_background_task: Whether to start the background processing task

    Returns:
        The initialized EscalationTimerManager
    """
    global _escalation_manager

    _escalation_manager = EscalationTimerManager(
        redis_url=redis_url,
        check_interval=check_interval,
    )

    await _escalation_manager.connect()

    if start_background_task:
        await _escalation_manager.start()

    return _escalation_manager


async def close_escalation_manager() -> None:
    """Close and cleanup the global escalation manager."""
    global _escalation_manager

    if _escalation_manager:
        await _escalation_manager.disconnect()
        _escalation_manager = None


def reset_escalation_manager() -> None:
    """
    Reset the global EscalationTimerManager instance.

    Used primarily for test isolation.
    """
    global _escalation_manager
    _escalation_manager = None


# =============================================================================
# Escalation Policy Manager
# =============================================================================


class EscalationPolicyManager:
    """
    Manages escalation policies with Redis-backed storage.

    Provides CRUD operations for escalation policies and policy evaluation
    based on priority and decision type.
    """

    def __init__(
        self,
        timer_manager: Optional[EscalationTimerManager] = None,
    ):
        """
        Initialize the policy manager.

        Args:
            timer_manager: Timer manager for Redis access (uses global if None)
        """
        self._timer_manager = timer_manager
        self._policies: Dict[str, EscalationPolicy] = {}
        self._sla_config = SLAConfig()
        self._lock = asyncio.Lock()

        logger.info("EscalationPolicyManager initialized")

    @property
    def timer_manager(self) -> EscalationTimerManager:
        """Get the timer manager instance."""
        if self._timer_manager is None:
            self._timer_manager = get_escalation_manager()
        return self._timer_manager

    @property
    def sla_config(self) -> SLAConfig:
        """Get the current SLA configuration."""
        return self._sla_config

    def set_sla_config(self, config: SLAConfig) -> None:
        """Set the SLA configuration."""
        self._sla_config = config
        logger.info(f"SLA config updated: {config.to_dict()}")

    # =========================================================================
    # Policy CRUD Operations
    # =========================================================================

    async def register_policy(self, policy: EscalationPolicy) -> None:
        """
        Register an escalation policy.

        Args:
            policy: The escalation policy to register
        """
        async with self._lock:
            self._policies[policy.policy_id] = policy

            # Persist to Redis if connected
            if self.timer_manager._redis:
                policy_key = f"{REDIS_POLICY_PREFIX}{policy.policy_id}"
                await self.timer_manager._redis.hset(
                    policy_key,
                    mapping={
                        "policy_id": policy.policy_id,
                        "name": policy.name,
                        "description": policy.description or "",
                        "priority": policy.priority.value,
                        "timeout_minutes": str(policy.timeout_minutes),
                        "max_escalations": str(policy.max_escalations),
                        "notify_on_escalation": str(policy.notify_on_escalation),
                        "pagerduty_on_critical": str(policy.pagerduty_on_critical),
                    },
                )
                await self.timer_manager._redis.sadd(REDIS_POLICY_SET, policy.policy_id)

        logger.info(f"Registered escalation policy: {policy.policy_id}")

    async def unregister_policy(self, policy_id: str) -> bool:
        """
        Unregister an escalation policy.

        Args:
            policy_id: The policy ID to unregister

        Returns:
            True if policy was found and removed
        """
        async with self._lock:
            if policy_id not in self._policies:
                return False

            del self._policies[policy_id]

            # Remove from Redis if connected
            if self.timer_manager._redis:
                policy_key = f"{REDIS_POLICY_PREFIX}{policy_id}"
                await self.timer_manager._redis.delete(policy_key)
                await self.timer_manager._redis.srem(REDIS_POLICY_SET, policy_id)

        logger.info(f"Unregistered escalation policy: {policy_id}")
        return True

    async def get_policy(self, policy_id: str) -> Optional[EscalationPolicy]:
        """
        Get an escalation policy by ID.

        Args:
            policy_id: The policy ID

        Returns:
            The EscalationPolicy if found, None otherwise
        """
        # Check memory cache first
        if policy_id in self._policies:
            return self._policies[policy_id]

        # Try Redis if connected
        if self.timer_manager._redis:
            policy_key = f"{REDIS_POLICY_PREFIX}{policy_id}"
            data = await self.timer_manager._redis.hgetall(policy_key)
            if data:
                policy = EscalationPolicy(
                    policy_id=data["policy_id"],
                    name=data["name"],
                    description=data.get("description") or None,
                    priority=ApprovalPriority(data["priority"]),
                    timeout_minutes=int(data["timeout_minutes"]),
                    max_escalations=int(data["max_escalations"]),
                    notify_on_escalation=data["notify_on_escalation"].lower() == "true",
                    pagerduty_on_critical=data["pagerduty_on_critical"].lower() == "true",
                )
                # Cache in memory
                self._policies[policy_id] = policy
                return policy

        return None

    async def get_all_policies(self) -> List[EscalationPolicy]:
        """
        Get all registered escalation policies.

        Returns:
            List of all escalation policies
        """
        policies = list(self._policies.values())

        # Also load from Redis if connected
        if self.timer_manager._redis:
            policy_ids = await self.timer_manager._redis.smembers(REDIS_POLICY_SET)
            for policy_id in policy_ids:
                if policy_id not in self._policies:
                    policy = await self.get_policy(policy_id)
                    if policy:
                        policies.append(policy)

        return policies

    async def get_policy_for_priority(
        self,
        priority: ApprovalPriority,
    ) -> Optional[EscalationPolicy]:
        """
        Get the escalation policy for a specific priority.

        Args:
            priority: The approval priority

        Returns:
            The matching EscalationPolicy, or None if not found
        """
        for policy in self._policies.values():
            if policy.priority == priority:
                return policy

        # Check Redis
        if self.timer_manager._redis:
            policies = await self.get_all_policies()
            for policy in policies:
                if policy.priority == priority:
                    return policy

        return None

    # =========================================================================
    # Policy Evaluation
    # =========================================================================

    def get_timeout_for_request(self, request: ApprovalRequest) -> int:
        """
        Get the timeout for an approval request based on policies.

        Args:
            request: The approval request

        Returns:
            Timeout in minutes
        """
        # Check for specific policy
        policy = self._policies.get(request.chain_id)
        if policy:
            return policy.timeout_minutes

        # Check for priority-based policy
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.timeout_minutes

        # Fall back to SLA config
        return self._sla_config.get_timeout_for_priority(request.priority)

    def should_trigger_pagerduty(self, request: ApprovalRequest) -> bool:
        """
        Determine if PagerDuty should be triggered for an escalation.

        Args:
            request: The approval request

        Returns:
            True if PagerDuty should be triggered
        """
        # Check for specific policy
        policy = self._policies.get(request.chain_id)
        if policy:
            return policy.pagerduty_on_critical

        # Check for priority-based policy
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.pagerduty_on_critical

        # Fall back to SLA config for critical requests
        if request.priority == ApprovalPriority.CRITICAL:
            return self._sla_config.pagerduty_on_critical

        return False

    def get_max_escalations(self, request: ApprovalRequest) -> int:
        """
        Get maximum allowed escalations for a request.

        Args:
            request: The approval request

        Returns:
            Maximum escalation count
        """
        # Check for specific policy
        policy = self._policies.get(request.chain_id)
        if policy:
            return policy.max_escalations

        # Check for priority-based policy
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.max_escalations

        return self._sla_config.max_escalations

    # =========================================================================
    # Default Policy Setup
    # =========================================================================

    async def setup_default_policies(self) -> None:
        """Setup default escalation policies for all priority levels."""
        default_policies = [
            EscalationPolicy(
                policy_id="default-critical",
                name="Critical Escalation Policy",
                description="Rapid escalation for critical approvals",
                priority=ApprovalPriority.CRITICAL,
                timeout_minutes=self._sla_config.critical_timeout_minutes,
                max_escalations=2,
                notify_on_escalation=True,
                pagerduty_on_critical=True,
            ),
            EscalationPolicy(
                policy_id="default-high",
                name="High Priority Escalation Policy",
                description="Fast escalation for high priority approvals",
                priority=ApprovalPriority.HIGH,
                timeout_minutes=self._sla_config.high_timeout_minutes,
                max_escalations=3,
                notify_on_escalation=True,
                pagerduty_on_critical=True,
            ),
            EscalationPolicy(
                policy_id="default-medium",
                name="Medium Priority Escalation Policy",
                description="Standard escalation for medium priority approvals",
                priority=ApprovalPriority.MEDIUM,
                timeout_minutes=self._sla_config.medium_timeout_minutes,
                max_escalations=3,
                notify_on_escalation=True,
                pagerduty_on_critical=False,
            ),
            EscalationPolicy(
                policy_id="default-low",
                name="Low Priority Escalation Policy",
                description="Relaxed escalation for low priority approvals",
                priority=ApprovalPriority.LOW,
                timeout_minutes=self._sla_config.low_timeout_minutes,
                max_escalations=4,
                notify_on_escalation=True,
                pagerduty_on_critical=False,
            ),
        ]

        for policy in default_policies:
            await self.register_policy(policy)

        logger.info(f"Setup {len(default_policies)} default escalation policies")


# Global policy manager instance
_policy_manager: Optional[EscalationPolicyManager] = None


def get_policy_manager() -> EscalationPolicyManager:
    """
    Get the global EscalationPolicyManager instance.

    Returns:
        The singleton EscalationPolicyManager instance
    """
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = EscalationPolicyManager()
    return _policy_manager


def reset_policy_manager() -> None:
    """
    Reset the global EscalationPolicyManager instance.

    Used primarily for test isolation.
    """
    global _policy_manager
    _policy_manager = None


# =============================================================================
# Integration Helper: Approval Engine Integration with SLA Tracking
# =============================================================================


class EscalationEngine:
    """
    High-level escalation engine that integrates with the ApprovalEngine.

    Provides a simplified interface for managing escalation timers with
    automatic integration to the approval workflow and comprehensive
    SLA tracking and compliance monitoring.

    Features:
    - Escalation timer scheduling and management
    - SLA compliance tracking with metrics
    - SLA breach detection and recording
    - Warning notifications before SLA breach
    - Policy-based timeout configuration
    """

    def __init__(
        self,
        timer_manager: Optional[EscalationTimerManager] = None,
        policy_manager: Optional[EscalationPolicyManager] = None,
    ):
        """
        Initialize the escalation engine.

        Args:
            timer_manager: Custom timer manager (uses global singleton if None)
            policy_manager: Custom policy manager (uses global singleton if None)
        """
        self._timer_manager = timer_manager
        self._policy_manager = policy_manager
        self._approval_engine_callback: Optional[Callable[[str, str], Coroutine[Any, Any, Any]]] = (
            None
        )
        self._warning_callbacks: List[Callable[[str, float], Coroutine[Any, Any, None]]] = []
        self._breach_callbacks: List[Callable[[SLABreach], Coroutine[Any, Any, None]]] = []

        # In-memory SLA metrics (also persisted to Redis when connected)
        self._sla_metrics = SLAMetrics()
        self._sla_breaches: List[SLABreach] = []
        self._request_start_times: Dict[str, float] = {}

        logger.info("EscalationEngine initialized with SLA tracking")

    @property
    def timer_manager(self) -> EscalationTimerManager:
        """Get the timer manager instance."""
        if self._timer_manager is None:
            self._timer_manager = get_escalation_manager()
        return self._timer_manager

    @property
    def policy_manager(self) -> EscalationPolicyManager:
        """Get the policy manager instance."""
        if self._policy_manager is None:
            self._policy_manager = get_policy_manager()
        return self._policy_manager

    @property
    def sla_metrics(self) -> SLAMetrics:
        """Get current SLA metrics."""
        return self._sla_metrics

    # =========================================================================
    # Callback Registration
    # =========================================================================

    def set_approval_engine_callback(
        self,
        callback: Callable[[str, str], Coroutine[Any, Any, Any]],
    ) -> None:
        """
        Set the callback for approval engine integration.

        The callback should be ApprovalEngine.escalate_request or similar.

        Args:
            callback: Async function that takes (request_id, reason) parameters
        """
        self._approval_engine_callback = callback

        # Register with timer manager
        async def wrapped_callback(request_id: str, reason: EscalationReason) -> None:
            # Record SLA breach
            await self._handle_escalation_timeout(request_id, reason)
            # Call approval engine callback
            if self._approval_engine_callback:
                await self._approval_engine_callback(request_id, reason.value)

        self.timer_manager.register_escalation_callback(wrapped_callback)
        logger.info("Approval engine callback registered with escalation engine")

    def register_warning_callback(
        self,
        callback: Callable[[str, float], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Register a callback for SLA warning notifications.

        Called when a request is approaching its SLA timeout threshold.

        Args:
            callback: Async function that takes (request_id, minutes_remaining)
        """
        self._warning_callbacks.append(callback)
        logger.info(f"Registered SLA warning callback: {callback.__name__}")

    def register_breach_callback(
        self,
        callback: Callable[[SLABreach], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Register a callback for SLA breach notifications.

        Called when an SLA breach occurs.

        Args:
            callback: Async function that takes an SLABreach object
        """
        self._breach_callbacks.append(callback)
        logger.info(f"Registered SLA breach callback: {callback.__name__}")

    # =========================================================================
    # Escalation Timer Operations
    # =========================================================================

    async def schedule_escalation(
        self,
        request: ApprovalRequest,
        timeout_minutes: Optional[int] = None,
    ) -> EscalationTimer:
        """
        Schedule escalation for an approval request.

        Args:
            request: The approval request
            timeout_minutes: Custom timeout (uses policy default if None)

        Returns:
            The created EscalationTimer
        """
        # Use policy-based timeout if not specified
        if timeout_minutes is None:
            timeout_minutes = self.policy_manager.get_timeout_for_request(request)

        # Track request start time for SLA metrics
        if request.request_id not in self._request_start_times:
            self._request_start_times[request.request_id] = time.time()

        timer = await self.timer_manager.set_timer(
            request_id=request.request_id,
            priority=request.priority,
            timeout_minutes=timeout_minutes,
            current_level=request.current_level,
            escalation_count=request.escalation_count,
            metadata={
                "chain_id": request.chain_id,
                "decision_type": request.decision_type,
                "impact_level": request.impact_level,
            },
        )

        logger.info(
            f"Scheduled escalation for {request.request_id}: "
            f"timeout={timeout_minutes}min, priority={request.priority.value}"
        )

        return timer

    async def cancel_escalation(self, request_id: str) -> bool:
        """
        Cancel escalation for an approval request.

        Args:
            request_id: The approval request ID

        Returns:
            True if timer was cancelled
        """
        return await self.timer_manager.cancel_timer(request_id)

    async def reschedule_escalation(
        self,
        request: ApprovalRequest,
        timeout_minutes: Optional[int] = None,
    ) -> Optional[EscalationTimer]:
        """
        Reschedule escalation (cancel existing and create new).

        Used when an approval advances to the next level.

        Args:
            request: The updated approval request
            timeout_minutes: Custom timeout (uses policy default if None)

        Returns:
            The new EscalationTimer, or None if failed
        """
        await self.cancel_escalation(request.request_id)
        return await self.schedule_escalation(request, timeout_minutes)

    async def get_escalation_status(
        self,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get escalation status for an approval request.

        Includes SLA status information.

        Args:
            request_id: The approval request ID

        Returns:
            Dictionary with escalation and SLA status, or None if no timer
        """
        timer = await self.timer_manager.get_timer(request_id)
        if not timer:
            return None

        # Calculate SLA status
        sla_status = self._get_sla_status_for_timer(timer)

        return {
            "request_id": request_id,
            "is_expired": timer.is_expired,
            "time_remaining_minutes": timer.time_remaining_minutes,
            "timeout_minutes": timer.timeout_minutes,
            "current_level": timer.current_level,
            "escalation_count": timer.escalation_count,
            "created_at": datetime.fromtimestamp(timer.created_at, tz=timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(timer.expires_at, tz=timezone.utc).isoformat(),
            "sla_status": sla_status.value,
            "sla_warning_threshold_minutes": self._get_warning_threshold(timer),
        }

    # =========================================================================
    # SLA Tracking and Compliance
    # =========================================================================

    async def record_completion(
        self,
        request_id: str,
        priority: ApprovalPriority,
    ) -> None:
        """
        Record completion of an approval request for SLA metrics.

        Args:
            request_id: The approval request ID
            priority: Priority of the completed request
        """
        start_time = self._request_start_times.pop(request_id, None)
        if start_time is None:
            logger.warning(f"No start time recorded for {request_id}")
            return

        response_time_seconds = time.time() - start_time
        sla_timeout_seconds = self.policy_manager.sla_config.get_timeout_for_priority(priority) * 60
        within_sla = response_time_seconds <= sla_timeout_seconds

        self._sla_metrics.record_completion(
            response_time_seconds=response_time_seconds,
            within_sla=within_sla,
            priority=priority,
        )

        # Cancel any pending escalation timer
        await self.cancel_escalation(request_id)

        # Persist metrics to Redis
        await self._persist_sla_metrics()

        logger.info(
            f"Recorded completion for {request_id}: "
            f"response_time={response_time_seconds:.1f}s, within_sla={within_sla}"
        )

    async def record_breach(
        self,
        request_id: str,
        priority: ApprovalPriority,
        reason: EscalationReason,
        escalation_level: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SLABreach:
        """
        Record an SLA breach.

        Args:
            request_id: The approval request ID
            priority: Priority of the request
            reason: Reason for the breach
            escalation_level: Current escalation level
            metadata: Additional breach metadata

        Returns:
            The recorded SLABreach object
        """
        start_time = self._request_start_times.get(request_id, time.time())
        actual_time_minutes = (time.time() - start_time) / 60
        sla_timeout_minutes = self.policy_manager.sla_config.get_timeout_for_priority(priority)

        breach = SLABreach(
            breach_id=str(uuid.uuid4()),
            request_id=request_id,
            priority=priority,
            breach_time=time.time(),
            sla_timeout_minutes=sla_timeout_minutes,
            actual_time_minutes=actual_time_minutes,
            breach_reason=reason,
            escalation_level=escalation_level,
            metadata=metadata or {},
        )

        self._sla_breaches.append(breach)
        self._sla_metrics.record_breach(priority)
        self._sla_metrics.record_escalation(priority)

        # Persist breach to Redis
        await self._persist_sla_breach(breach)

        # Trigger breach callbacks
        for callback in self._breach_callbacks:
            try:
                await callback(breach)
            except Exception as e:
                logger.error(f"Breach callback error: {e}")

        logger.warning(
            f"SLA breach recorded for {request_id}: "
            f"overage={breach.overage_minutes:.1f}min ({breach.overage_percent:.1f}%)"
        )

        return breach

    async def check_sla_warnings(self) -> List[str]:
        """
        Check for requests approaching SLA warning threshold.

        Returns:
            List of request IDs that are approaching SLA breach
        """
        warning_requests: List[str] = []
        expiring_soon = await self.timer_manager.get_expiring_soon(within_minutes=10)

        for timer in expiring_soon:
            warning_threshold = self._get_warning_threshold(timer)
            if timer.time_remaining_minutes <= warning_threshold:
                warning_requests.append(timer.request_id)

                # Trigger warning callbacks
                for callback in self._warning_callbacks:
                    try:
                        await callback(timer.request_id, timer.time_remaining_minutes)
                    except Exception as e:
                        logger.error(f"Warning callback error: {e}")

                self._sla_metrics.record_warning()

        if warning_requests:
            logger.info(f"SLA warning threshold reached for {len(warning_requests)} requests")

        return warning_requests

    def get_sla_status(self, request_id: str) -> SLAStatus:
        """
        Get the current SLA status for a request.

        Args:
            request_id: The approval request ID

        Returns:
            The current SLAStatus
        """
        # Check if already breached
        for breach in self._sla_breaches:
            if breach.request_id == request_id:
                return SLAStatus.CRITICAL if breach.escalation_level > 1 else SLAStatus.BREACHED

        # Check active timer
        # Note: This is synchronous, so we can't check timer_manager here
        # The async version should be used for accurate status
        return SLAStatus.COMPLIANT

    async def get_sla_status_async(self, request_id: str) -> SLAStatus:
        """
        Get the current SLA status for a request (async version).

        Args:
            request_id: The approval request ID

        Returns:
            The current SLAStatus
        """
        # Check if already breached
        for breach in self._sla_breaches:
            if breach.request_id == request_id:
                return SLAStatus.CRITICAL if breach.escalation_level > 1 else SLAStatus.BREACHED

        # Check active timer
        timer = await self.timer_manager.get_timer(request_id)
        if timer:
            return self._get_sla_status_for_timer(timer)

        return SLAStatus.COMPLIANT

    def _get_sla_status_for_timer(self, timer: EscalationTimer) -> SLAStatus:
        """Determine SLA status based on timer state."""
        if timer.is_expired:
            return SLAStatus.BREACHED

        warning_threshold = self._get_warning_threshold(timer)
        if timer.time_remaining_minutes <= warning_threshold:
            return SLAStatus.WARNING

        return SLAStatus.COMPLIANT

    def _get_warning_threshold(self, timer: EscalationTimer) -> float:
        """Get the warning threshold in minutes for a timer."""
        threshold_percent = self.policy_manager.sla_config.warning_threshold_percent / 100
        return timer.timeout_minutes * (1 - threshold_percent)

    async def _handle_escalation_timeout(
        self,
        request_id: str,
        reason: EscalationReason,
    ) -> None:
        """Handle an escalation timeout event."""
        timer = await self.timer_manager.get_timer(request_id)
        if not timer:
            return

        await self.record_breach(
            request_id=request_id,
            priority=timer.priority,
            reason=reason,
            escalation_level=timer.current_level,
            metadata=timer.metadata,
        )

    # =========================================================================
    # SLA Metrics and Reporting
    # =========================================================================

    async def get_sla_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive SLA metrics.

        Returns:
            Dictionary with SLA metrics
        """
        # Load from Redis if available
        await self._load_sla_metrics()

        return {
            "metrics": self._sla_metrics.to_dict(),
            "recent_breaches": [b.to_dict() for b in self._sla_breaches[-10:]],
            "active_timers": await self.timer_manager.get_timer_count(),
            "expiring_soon_5min": len(await self.timer_manager.get_expiring_soon(within_minutes=5)),
        }

    async def get_breach_history(
        self,
        limit: int = 50,
        priority: Optional[ApprovalPriority] = None,
    ) -> List[SLABreach]:
        """
        Get SLA breach history.

        Args:
            limit: Maximum number of breaches to return
            priority: Filter by priority (None for all)

        Returns:
            List of SLABreach objects
        """
        breaches = self._sla_breaches.copy()

        if priority:
            breaches = [b for b in breaches if b.priority == priority]

        # Sort by breach time (most recent first)
        breaches.sort(key=lambda b: b.breach_time, reverse=True)

        return breaches[:limit]

    async def reset_sla_metrics(self) -> None:
        """Reset all SLA metrics. Used for testing or metric rotation."""
        self._sla_metrics = SLAMetrics()
        self._sla_breaches = []
        self._request_start_times = {}

        # Clear Redis metrics
        if self.timer_manager._redis:
            await self.timer_manager._redis.delete(REDIS_SLA_METRICS_KEY)

        logger.info("SLA metrics reset")

    # =========================================================================
    # Redis Persistence
    # =========================================================================

    async def _persist_sla_metrics(self) -> None:
        """Persist SLA metrics to Redis."""
        if not self.timer_manager._redis:
            return

        try:
            await self.timer_manager._redis.hset(
                REDIS_SLA_METRICS_KEY,
                mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in self._sla_metrics.to_dict().items()
                },
            )
        except Exception as e:
            logger.error(f"Failed to persist SLA metrics: {e}")

    async def _load_sla_metrics(self) -> None:
        """Load SLA metrics from Redis."""
        if not self.timer_manager._redis:
            return

        try:
            data = await self.timer_manager._redis.hgetall(REDIS_SLA_METRICS_KEY)
            if data:
                # Parse JSON values
                parsed_data = {}
                for k, v in data.items():
                    try:
                        parsed_data[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        try:
                            parsed_data[k] = float(v)
                        except ValueError:
                            parsed_data[k] = v

                self._sla_metrics = SLAMetrics.from_dict(parsed_data)
        except Exception as e:
            logger.error(f"Failed to load SLA metrics: {e}")

    async def _persist_sla_breach(self, breach: SLABreach) -> None:
        """Persist an SLA breach to Redis."""
        if not self.timer_manager._redis:
            return

        try:
            # Store breach data
            breach_key = f"{REDIS_SLA_BREACH_DATA_PREFIX}{breach.breach_id}"
            await self.timer_manager._redis.hset(
                breach_key,
                mapping={
                    k: json.dumps(v) if isinstance(v, dict) else str(v)
                    for k, v in breach.to_dict().items()
                },
            )

            # Add to sorted set (score = breach time for ordering)
            await self.timer_manager._redis.zadd(
                REDIS_SLA_BREACHES_ZSET,
                {breach.breach_id: breach.breach_time},
            )

            # Set TTL on breach data (30 days)
            await self.timer_manager._redis.expire(breach_key, 30 * 24 * 3600)

        except Exception as e:
            logger.error(f"Failed to persist SLA breach: {e}")


# Global escalation engine instance
_escalation_engine: Optional[EscalationEngine] = None


def get_escalation_engine() -> EscalationEngine:
    """
    Get the global EscalationEngine instance.

    Returns:
        The singleton EscalationEngine instance
    """
    global _escalation_engine
    if _escalation_engine is None:
        _escalation_engine = EscalationEngine()
    return _escalation_engine


def reset_escalation_engine() -> None:
    """
    Reset the global EscalationEngine instance.

    Used primarily for test isolation.
    """
    global _escalation_engine
    _escalation_engine = None
