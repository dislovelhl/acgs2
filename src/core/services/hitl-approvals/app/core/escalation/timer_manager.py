"""
Escalation Timer Manager for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from app.config import settings
from app.models import ApprovalPriority

from .enums import EscalationReason
from .exceptions import RedisConnectionError
from .models import EscalationTimer

logger = logging.getLogger(__name__)

# Redis key prefixes
REDIS_ESCALATION_ZSET = "hitl:escalation:timers"
REDIS_ESCALATION_DATA_PREFIX = "hitl:escalation:data:"
DEFAULT_CHECK_INTERVAL_SECONDS = 5

# Type alias for escalation callback
EscalationCallback = Callable[[str, EscalationReason], Coroutine[Any, Any, None]]


class EscalationTimerManager:
    """Manages escalation timers using Redis sorted sets."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    ):
        self._redis_url = redis_url or settings.redis_url
        self._check_interval = check_interval
        self._redis: Optional[Any] = None
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        self._escalation_callbacks: List[EscalationCallback] = []
        self._lock = asyncio.Lock()
        self._processed_timers: Set[str] = set()

        logger.info(f"EscalationTimerManager initialized (check_interval={check_interval}s)")

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info(f"Connected to Redis: {self._sanitize_url(self._redis_url)}")
        except ImportError as err:
            raise RedisConnectionError("redis package not installed") from err
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        await self.stop()
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def health_check(self) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def _sanitize_url(self, url: str) -> str:
        if "@" in url:
            parts = url.split("@")
            return f"redis://***@{parts[-1]}"
        return url

    async def _get_server_time(self) -> float:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        time_result = await self._redis.time()
        return float(time_result[0]) + float(time_result[1]) / 1_000_000

    async def set_timer(
        self,
        request_id: str,
        priority: ApprovalPriority,
        timeout_minutes: Optional[int] = None,
        current_level: int = 1,
        escalation_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EscalationTimer:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        if timeout_minutes is None:
            timeout_minutes = self._get_timeout_for_priority(priority)

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

        async with self._lock:
            await self._redis.zadd(REDIS_ESCALATION_ZSET, {request_id: expires_at})
            data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
            await self._redis.hset(data_key, mapping=self._flatten_dict(timer.to_dict()))
            await self._redis.expire(data_key, timeout_minutes * 60 + 3600)

        logger.info(f"Escalation timer set for {request_id}: {timeout_minutes}min")
        return timer

    async def cancel_timer(self, request_id: str) -> bool:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        async with self._lock:
            removed = await self._redis.zrem(REDIS_ESCALATION_ZSET, request_id)
            await self._redis.delete(f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}")
            self._processed_timers.discard(request_id)
        return bool(removed)

    async def get_timer(self, request_id: str) -> Optional[EscalationTimer]:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        data = await self._redis.hgetall(f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}")
        return EscalationTimer.from_dict(self._unflatten_dict(data)) if data else None

    async def extend_timer(
        self, request_id: str, additional_minutes: int
    ) -> Optional[EscalationTimer]:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        timer = await self.get_timer(request_id)
        if not timer:
            return None
        new_expires_at = timer.expires_at + (additional_minutes * 60)
        async with self._lock:
            await self._redis.zadd(REDIS_ESCALATION_ZSET, {request_id: new_expires_at})
            data_key = f"{REDIS_ESCALATION_DATA_PREFIX}{request_id}"
            await self._redis.hset(data_key, "expires_at", str(new_expires_at))
            remaining = int(new_expires_at - time.time()) + 3600
            await self._redis.expire(data_key, max(remaining, 3600))
        timer.expires_at = new_expires_at
        return timer

    async def reset_timer(
        self, request_id: str, new_timeout_minutes: Optional[int] = None
    ) -> Optional[EscalationTimer]:
        timer = await self.get_timer(request_id)
        if not timer:
            return None
        await self.cancel_timer(request_id)
        return await self.set_timer(
            request_id=request_id,
            priority=timer.priority,
            timeout_minutes=new_timeout_minutes or timer.timeout_minutes,
            current_level=timer.current_level,
            escalation_count=timer.escalation_count,
            metadata=timer.metadata,
        )

    async def get_expired_timers(self, limit: int = 100) -> List[EscalationTimer]:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        server_time = await self._get_server_time()
        expired_ids = await self._redis.zrangebyscore(
            REDIS_ESCALATION_ZSET, "-inf", server_time, start=0, num=limit
        )
        timers = []
        for rid in expired_ids:
            t = await self.get_timer(rid)
            if t:
                timers.append(t)
        return timers

    async def get_timer_count(self) -> int:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        return await self._redis.zcard(REDIS_ESCALATION_ZSET)

    def register_escalation_callback(self, callback: EscalationCallback) -> None:
        self._escalation_callbacks.append(callback)

    def unregister_escalation_callback(self, callback: EscalationCallback) -> bool:
        try:
            self._escalation_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    async def start(self) -> None:
        if self._running:
            return
        if not self._redis:
            await self.connect()
        self._running = True
        self._background_task = asyncio.create_task(self._process_expired_timers_loop())

    async def stop(self) -> None:
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None

    async def _process_expired_timers_loop(self) -> None:
        while self._running:
            try:
                await self._process_expired_timers()
            except Exception as e:
                logger.error(f"Error processing expired timers: {e}")
            await asyncio.sleep(self._check_interval)

    async def _process_expired_timers(self) -> None:
        expired_timers = await self.get_expired_timers()
        for timer in expired_timers:
            if timer.request_id in self._processed_timers:
                continue
            try:
                self._processed_timers.add(timer.request_id)
                for callback in self._escalation_callbacks:
                    await callback(timer.request_id, EscalationReason.TIMEOUT)
                await self.cancel_timer(timer.request_id)
            except Exception as e:
                self._processed_timers.discard(timer.request_id)
                logger.error(f"Failed to process escalation for {timer.request_id}: {e}")
        if len(self._processed_timers) > 1000:
            self._processed_timers = set(list(self._processed_timers)[-500:])

    def _get_timeout_for_priority(self, priority: ApprovalPriority) -> int:
        if priority == ApprovalPriority.CRITICAL:
            return settings.critical_escalation_timeout_minutes
        elif priority == ApprovalPriority.HIGH:
            return int(settings.default_escalation_timeout_minutes * 0.75)
        elif priority == ApprovalPriority.MEDIUM:
            return settings.default_escalation_timeout_minutes
        else:
            return int(settings.default_escalation_timeout_minutes * 1.5)

    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        items: Dict[str, str] = {}
        for key, value in d.items():
            new_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            if isinstance(value, dict):
                items.update(self._flatten_dict(value, new_key))
            else:
                items[new_key] = str(value)
        return items

    def _unflatten_dict(self, d: Dict[str, str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in d.items():
            if "." in key:
                parts = key.split(".", 1)
                if parts[0] not in result:
                    result[parts[0]] = {}
                result[parts[0]][parts[1]] = value
            else:
                try:
                    if "." in value:
                        result[key] = float(value)
                    else:
                        result[key] = int(value)
                except (ValueError, TypeError):
                    result[key] = value
        return result

    async def get_statistics(self) -> Dict[str, Any]:
        if not self._redis:
            raise RedisConnectionError("Redis not connected")
        server_time = await self._get_server_time()
        total_timers = await self.get_timer_count()
        expired_count = await self._redis.zcount(REDIS_ESCALATION_ZSET, "-inf", server_time)
        return {
            "total_timers": total_timers,
            "expired_timers": expired_count,
            "pending_timers": total_timers - expired_count,
            "registered_callbacks": len(self._escalation_callbacks),
            "is_running": self._running,
        }


_escalation_manager: Optional[EscalationTimerManager] = None


def get_escalation_manager() -> EscalationTimerManager:
    global _escalation_manager
    if _escalation_manager is None:
        _escalation_manager = EscalationTimerManager()
    return _escalation_manager


async def initialize_escalation_manager(
    redis_url: Optional[str] = None,
    check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    start_background_task: bool = True,
) -> EscalationTimerManager:
    global _escalation_manager
    _escalation_manager = EscalationTimerManager(redis_url=redis_url, check_interval=check_interval)
    await _escalation_manager.connect()
    if start_background_task:
        await _escalation_manager.start()
    return _escalation_manager


async def close_escalation_manager() -> None:
    global _escalation_manager
    if _escalation_manager:
        await _escalation_manager.disconnect()
        _escalation_manager = None
