"""
Escalation Engine for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.models import ApprovalPriority, ApprovalRequest

from .enums import EscalationReason, SLAStatus
from .models import SLABreach, SLAMetrics
from .policy_manager import EscalationPolicyManager, get_policy_manager
from .timer_manager import EscalationTimer, EscalationTimerManager, get_escalation_manager

logger = logging.getLogger(__name__)

REDIS_SLA_METRICS_KEY = "hitl:sla:metrics"
REDIS_SLA_BREACHES_ZSET = "hitl:sla:breaches"
REDIS_SLA_BREACH_DATA_PREFIX = "hitl:sla:breach:data:"


class EscalationEngine:
    """High-level escalation engine that integrates with the ApprovalEngine."""

    def __init__(
        self,
        timer_manager: Optional[EscalationTimerManager] = None,
        policy_manager: Optional[EscalationPolicyManager] = None,
    ):
        self._timer_manager = timer_manager
        self._policy_manager = policy_manager
        self._approval_engine_callback: Optional[
            Callable[[str, str], Coroutine[Any, Any, Any]]
        ] = None
        self._warning_callbacks: List[Callable[[str, float], Coroutine[Any, Any, None]]] = []
        self._breach_callbacks: List[Callable[[SLABreach], Coroutine[Any, Any, None]]] = []
        self._sla_metrics = SLAMetrics()
        self._sla_breaches: List[SLABreach] = []
        self._request_start_times: Dict[str, float] = {}
        logger.info("EscalationEngine initialized with SLA tracking")

    @property
    def timer_manager(self) -> EscalationTimerManager:
        if self._timer_manager is None:
            self._timer_manager = get_escalation_manager()
        return self._timer_manager

    @property
    def policy_manager(self) -> EscalationPolicyManager:
        if self._policy_manager is None:
            self._policy_manager = get_policy_manager()
        return self._policy_manager

    @property
    def sla_metrics(self) -> SLAMetrics:
        return self._sla_metrics

    def set_approval_engine_callback(
        self, callback: Callable[[str, str], Coroutine[Any, Any, Any]]
    ) -> None:
        self._approval_engine_callback = callback

        async def wrapped_callback(request_id: str, reason: EscalationReason) -> None:
            await self._handle_escalation_timeout(request_id, reason)
            if self._approval_engine_callback:
                await self._approval_engine_callback(request_id, reason.value)

        self.timer_manager.register_escalation_callback(wrapped_callback)

    def register_warning_callback(
        self, callback: Callable[[str, float], Coroutine[Any, Any, None]]
    ) -> None:
        self._warning_callbacks.append(callback)

    def register_breach_callback(
        self, callback: Callable[[SLABreach], Coroutine[Any, Any, None]]
    ) -> None:
        self._breach_callbacks.append(callback)

    async def schedule_escalation(
        self, request: ApprovalRequest, timeout_minutes: Optional[int] = None
    ) -> EscalationTimer:
        if timeout_minutes is None:
            timeout_minutes = self.policy_manager.get_timeout_for_request(request)
        if request.request_id not in self._request_start_times:
            self._request_start_times[request.request_id] = time.time()
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
        return await self.timer_manager.cancel_timer(request_id)

    async def reschedule_escalation(
        self, request: ApprovalRequest, timeout_minutes: Optional[int] = None
    ) -> Optional[EscalationTimer]:
        await self.cancel_escalation(request.request_id)
        return await self.schedule_escalation(request, timeout_minutes)

    async def get_escalation_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        timer = await self.timer_manager.get_timer(request_id)
        if not timer:
            return None
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

    async def record_completion(self, request_id: str, priority: ApprovalPriority) -> None:
        start_time = self._request_start_times.pop(request_id, None)
        if start_time is None:
            return
        response_time_seconds = time.time() - start_time
        sla_timeout_seconds = self.policy_manager.sla_config.get_timeout_for_priority(priority) * 60
        within_sla = response_time_seconds <= sla_timeout_seconds
        self._sla_metrics.record_completion(response_time_seconds, within_sla, priority)
        await self.cancel_escalation(request_id)
        await self._persist_sla_metrics()

    async def record_breach(
        self,
        request_id: str,
        priority: ApprovalPriority,
        reason: EscalationReason,
        escalation_level: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SLABreach:
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
        await self._persist_sla_breach(breach)
        for callback in self._breach_callbacks:
            await callback(breach)
        return breach

    async def check_sla_warnings(self) -> List[str]:
        warning_requests: List[str] = []
        expiring_soon = await self.timer_manager.get_expiring_soon(within_minutes=10)
        for timer in expiring_soon:
            if timer.time_remaining_minutes <= self._get_warning_threshold(timer):
                warning_requests.append(timer.request_id)
                for callback in self._warning_callbacks:
                    await callback(timer.request_id, timer.time_remaining_minutes)
                self._sla_metrics.record_warning()
        return warning_requests

    def get_sla_status(self, request_id: str) -> SLAStatus:
        for breach in self._sla_breaches:
            if breach.request_id == request_id:
                return SLAStatus.CRITICAL if breach.escalation_level > 1 else SLAStatus.BREACHED
        return SLAStatus.COMPLIANT

    async def get_sla_status_async(self, request_id: str) -> SLAStatus:
        for breach in self._sla_breaches:
            if breach.request_id == request_id:
                return SLAStatus.CRITICAL if breach.escalation_level > 1 else SLAStatus.BREACHED
        timer = await self.timer_manager.get_timer(request_id)
        return self._get_sla_status_for_timer(timer) if timer else SLAStatus.COMPLIANT

    def _get_sla_status_for_timer(self, timer: EscalationTimer) -> SLAStatus:
        if timer.is_expired:
            return SLAStatus.BREACHED
        if timer.time_remaining_minutes <= self._get_warning_threshold(timer):
            return SLAStatus.WARNING
        return SLAStatus.COMPLIANT

    def _get_warning_threshold(self, timer: EscalationTimer) -> float:
        threshold_percent = self.policy_manager.sla_config.warning_threshold_percent / 100
        return timer.timeout_minutes * (1 - threshold_percent)

    async def _handle_escalation_timeout(self, request_id: str, reason: EscalationReason) -> None:
        timer = await self.timer_manager.get_timer(request_id)
        if timer:
            await self.record_breach(
                request_id, timer.priority, reason, timer.current_level, timer.metadata
            )

    async def _persist_sla_metrics(self) -> None:
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

    async def _persist_sla_breach(self, breach: SLABreach) -> None:
        if not self.timer_manager._redis:
            return
        try:
            breach_key = f"{REDIS_SLA_BREACH_DATA_PREFIX}{breach.breach_id}"
            await self.timer_manager._redis.hset(
                breach_key,
                mapping={
                    k: json.dumps(v) if isinstance(v, dict) else str(v)
                    for k, v in breach.to_dict().items()
                },
            )
            await self.timer_manager._redis.zadd(
                REDIS_SLA_BREACHES_ZSET, {breach.breach_id: breach.breach_time}
            )
            await self.timer_manager._redis.expire(breach_key, 30 * 24 * 3600)
        except Exception as e:
            logger.error(f"Failed to persist SLA breach: {e}")


_escalation_engine: Optional[EscalationEngine] = None


def get_escalation_engine() -> EscalationEngine:
    global _escalation_engine
    if _escalation_engine is None:
        _escalation_engine = EscalationEngine()
    return _escalation_engine


def reset_escalation_engine() -> None:
    global _escalation_engine
    _escalation_engine = None
