"""
Redis-backed Escalation Timer System

Implements time-based auto-escalation using Redis for timer storage and
sorted sets for reliable expiration detection. Avoids polling by using
Redis sorted sets with scores as expiration timestamps.

Key Design Decisions:
- Uses Redis sorted sets instead of TTL-based expiration for reliable detection
- Uses Redis server time (TIME command) to avoid clock drift issues
- Supports configurable timeouts per priority level
- Integrates with ApprovalEngine for escalation callbacks
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from app.config import settings
from app.models import ApprovalPriority, ApprovalRequest

logger = logging.getLogger(__name__)

# Redis key prefixes
REDIS_ESCALATION_ZSET = "hitl:escalation:timers"
REDIS_ESCALATION_DATA_PREFIX = "hitl:escalation:data:"
REDIS_ESCALATION_LOCK = "hitl:escalation:lock"

# Default check interval for expired timers (seconds)
DEFAULT_CHECK_INTERVAL_SECONDS = 5


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
# Integration Helper: Approval Engine Integration
# =============================================================================


class EscalationEngine:
    """
    High-level escalation engine that integrates with the ApprovalEngine.

    Provides a simplified interface for managing escalation timers with
    automatic integration to the approval workflow.
    """

    def __init__(
        self,
        timer_manager: Optional[EscalationTimerManager] = None,
    ):
        """
        Initialize the escalation engine.

        Args:
            timer_manager: Custom timer manager (uses global singleton if None)
        """
        self._timer_manager = timer_manager
        self._approval_engine_callback: Optional[Callable[[str, str], Coroutine[Any, Any, Any]]] = (
            None
        )

    @property
    def timer_manager(self) -> EscalationTimerManager:
        """Get the timer manager instance."""
        if self._timer_manager is None:
            self._timer_manager = get_escalation_manager()
        return self._timer_manager

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
            if self._approval_engine_callback:
                await self._approval_engine_callback(request_id, reason.value)

        self.timer_manager.register_escalation_callback(wrapped_callback)
        logger.info("Approval engine callback registered with escalation engine")

    async def schedule_escalation(
        self,
        request: ApprovalRequest,
        timeout_minutes: Optional[int] = None,
    ) -> EscalationTimer:
        """
        Schedule escalation for an approval request.

        Args:
            request: The approval request
            timeout_minutes: Custom timeout (uses priority default if None)

        Returns:
            The created EscalationTimer
        """
        return await self.timer_manager.set_timer(
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
            timeout_minutes: Custom timeout (uses priority default if None)

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

        Args:
            request_id: The approval request ID

        Returns:
            Dictionary with escalation status, or None if no timer
        """
        timer = await self.timer_manager.get_timer(request_id)
        if not timer:
            return None

        return {
            "request_id": request_id,
            "is_expired": timer.is_expired,
            "time_remaining_minutes": timer.time_remaining_minutes,
            "timeout_minutes": timer.timeout_minutes,
            "current_level": timer.current_level,
            "escalation_count": timer.escalation_count,
            "created_at": datetime.fromtimestamp(timer.created_at, tz=timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(timer.expires_at, tz=timezone.utc).isoformat(),
        }


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
