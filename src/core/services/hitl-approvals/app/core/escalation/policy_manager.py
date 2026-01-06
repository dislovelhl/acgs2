"""
Escalation Policy Manager for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from typing import Dict, List, Optional

from app.models import ApprovalPriority, ApprovalRequest, EscalationPolicy

from .models import SLAConfig
from .timer_manager import EscalationTimerManager, get_escalation_manager

logger = logging.getLogger(__name__)

REDIS_POLICY_PREFIX = "hitl:escalation:policy:"
REDIS_POLICY_SET = "hitl:escalation:policies"


class EscalationPolicyManager:
    """Manages escalation policies with Redis-backed storage."""

    def __init__(self, timer_manager: Optional[EscalationTimerManager] = None):
        self._timer_manager = timer_manager
        self._policies: Dict[str, EscalationPolicy] = {}
        self._sla_config = SLAConfig()
        self._lock = asyncio.Lock()
        logger.info("EscalationPolicyManager initialized")

    @property
    def timer_manager(self) -> EscalationTimerManager:
        if self._timer_manager is None:
            self._timer_manager = get_escalation_manager()
        return self._timer_manager

    @property
    def sla_config(self) -> SLAConfig:
        return self._sla_config

    def set_sla_config(self, config: SLAConfig) -> None:
        self._sla_config = config
        logger.info(f"SLA config updated: {config.to_dict()}")

    async def register_policy(self, policy: EscalationPolicy) -> None:
        async with self._lock:
            self._policies[policy.policy_id] = policy
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
        async with self._lock:
            if policy_id not in self._policies:
                return False
            del self._policies[policy_id]
            if self.timer_manager._redis:
                await self.timer_manager._redis.delete(f"{REDIS_POLICY_PREFIX}{policy_id}")
                await self.timer_manager._redis.srem(REDIS_POLICY_SET, policy_id)
        return True

    async def get_policy(self, policy_id: str) -> Optional[EscalationPolicy]:
        if policy_id in self._policies:
            return self._policies[policy_id]
        if self.timer_manager._redis:
            data = await self.timer_manager._redis.hgetall(f"{REDIS_POLICY_PREFIX}{policy_id}")
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
                self._policies[policy_id] = policy
                return policy
        return None

    async def get_all_policies(self) -> List[EscalationPolicy]:
        policies = list(self._policies.values())
        if self.timer_manager._redis:
            policy_ids = await self.timer_manager._redis.smembers(REDIS_POLICY_SET)
            for pid in policy_ids:
                if pid not in self._policies:
                    p = await self.get_policy(pid)
                    if p:
                        policies.append(p)
        return policies

    def get_timeout_for_request(self, request: ApprovalRequest) -> int:
        if request.chain_id in self._policies:
            return self._policies[request.chain_id].timeout_minutes
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.timeout_minutes
        return self._sla_config.get_timeout_for_priority(request.priority)

    def should_trigger_pagerduty(self, request: ApprovalRequest) -> bool:
        if request.chain_id in self._policies:
            return self._policies[request.chain_id].pagerduty_on_critical
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.pagerduty_on_critical
        if request.priority == ApprovalPriority.CRITICAL:
            return self._sla_config.pagerduty_on_critical
        return False

    def get_max_escalations(self, request: ApprovalRequest) -> int:
        if request.chain_id in self._policies:
            return self._policies[request.chain_id].max_escalations
        for p in self._policies.values():
            if p.priority == request.priority:
                return p.max_escalations
        return self._sla_config.max_escalations

    async def setup_default_policies(self) -> None:
        default_configs = [
            (
                "default-critical",
                "Critical Escalation Policy",
                ApprovalPriority.CRITICAL,
                self._sla_config.critical_timeout_minutes,
                2,
                True,
            ),
            (
                "default-high",
                "High Priority Escalation Policy",
                ApprovalPriority.HIGH,
                self._sla_config.high_timeout_minutes,
                3,
                True,
            ),
            (
                "default-medium",
                "Medium Priority Escalation Policy",
                ApprovalPriority.MEDIUM,
                self._sla_config.medium_timeout_minutes,
                3,
                False,
            ),
            (
                "default-low",
                "Low Priority Escalation Policy",
                ApprovalPriority.LOW,
                self._sla_config.low_timeout_minutes,
                4,
                False,
            ),
        ]
        for pid, name, prio, timeout, max_esc, pd in default_configs:
            await self.register_policy(
                EscalationPolicy(
                    policy_id=pid,
                    name=name,
                    priority=prio,
                    timeout_minutes=timeout,
                    max_escalations=max_esc,
                    notify_on_escalation=True,
                    pagerduty_on_critical=pd,
                )
            )


_policy_manager: Optional[EscalationPolicyManager] = None


def get_policy_manager() -> EscalationPolicyManager:
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = EscalationPolicyManager()
    return _policy_manager


def reset_policy_manager() -> None:
    global _policy_manager
    _policy_manager = None
