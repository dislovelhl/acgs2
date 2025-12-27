"""
Usage Metering Service
Constitutional Hash: cdd01ef066bc6cf2

Core metering logic for tracking and aggregating constitutional governance usage.
Designed for transparency and usage-based pricing models.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from uuid import UUID

from .models import (
    UsageEvent,
    UsageAggregation,
    MeteringQuota,
    BillingRate,
    MeterableOperation,
    MeteringTier,
    CONSTITUTIONAL_HASH,
)

logger = logging.getLogger(__name__)


class UsageMeteringService:
    """
    Tracks and aggregates usage for constitutional governance operations.

    Features:
    - Real-time event ingestion
    - Periodic aggregation for billing
    - Quota enforcement with graceful degradation
    - Constitutional compliance tracking
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        aggregation_interval_seconds: int = 60,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        self.redis_url = redis_url
        self.aggregation_interval = aggregation_interval_seconds
        self.constitutional_hash = constitutional_hash

        # In-memory buffers (would use Redis in production)
        self._event_buffer: List[UsageEvent] = []
        self._aggregations: Dict[str, UsageAggregation] = {}
        self._quotas: Dict[str, MeteringQuota] = {}
        self._rates: Dict[str, BillingRate] = {}

        # Metrics
        self._total_events_processed = 0
        self._events_by_operation: Dict[str, int] = defaultdict(int)

        self._running = False
        self._aggregation_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the metering service."""
        if self._running:
            return

        self._running = True
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        logger.info(
            f"UsageMeteringService started with constitutional hash: {self.constitutional_hash}"
        )

    async def stop(self) -> None:
        """Stop the metering service and flush buffers."""
        self._running = False
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_buffer()
        logger.info("UsageMeteringService stopped")

    async def record_event(
        self,
        tenant_id: str,
        operation: MeterableOperation,
        tier: MeteringTier = MeteringTier.STANDARD,
        agent_id: Optional[str] = None,
        tokens_processed: int = 0,
        latency_ms: float = 0.0,
        compliance_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        """
        Record a metered usage event.

        Returns the created event for tracking.
        """
        # Validate constitutional hash
        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            logger.error("Constitutional hash mismatch in metering service")
            raise ValueError("Constitutional hash validation failed")

        event = UsageEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            operation=operation,
            tier=tier,
            tokens_processed=tokens_processed,
            latency_ms=latency_ms,
            compliance_score=compliance_score,
            constitutional_hash=self.constitutional_hash,
            metadata=metadata or {},
        )

        self._event_buffer.append(event)
        self._total_events_processed += 1
        self._events_by_operation[operation.value] += 1

        # Check quota
        await self._check_and_update_quota(tenant_id, operation)

        return event

    async def get_usage_summary(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage summary for a tenant within a time range."""
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now

        # Aggregate from buffer and stored aggregations
        summary = {
            "tenant_id": tenant_id,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "operations": defaultdict(int),
            "tiers": defaultdict(int),
            "total_events": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0.0,
            "avg_compliance_score": 0.0,
            "constitutional_hash": self.constitutional_hash,
        }

        # Count from buffer
        latencies = []
        scores = []

        for event in self._event_buffer:
            if event.tenant_id == tenant_id and start <= event.timestamp <= end:
                summary["operations"][event.operation.value] += event.units
                summary["tiers"][event.tier.value] += event.units
                summary["total_events"] += event.units
                summary["total_tokens"] += event.tokens_processed
                latencies.append(event.latency_ms)
                scores.append(event.compliance_score)

        if latencies:
            summary["avg_latency_ms"] = sum(latencies) / len(latencies)
        if scores:
            summary["avg_compliance_score"] = sum(scores) / len(scores)

        return dict(summary)

    async def get_quota_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get current quota status for a tenant."""
        quota = self._quotas.get(tenant_id)

        if not quota:
            # Return default unlimited quota
            return {
                "tenant_id": tenant_id,
                "has_limits": False,
                "usage": {},
                "remaining": {},
                "constitutional_hash": self.constitutional_hash,
            }

        usage = quota.current_usage
        remaining = {}

        if quota.monthly_validation_limit:
            remaining["validation"] = max(
                0,
                quota.monthly_validation_limit
                - usage.get(MeterableOperation.CONSTITUTIONAL_VALIDATION.value, 0),
            )

        if quota.monthly_message_limit:
            remaining["messages"] = max(
                0,
                quota.monthly_message_limit
                - usage.get(MeterableOperation.AGENT_MESSAGE.value, 0),
            )

        if quota.monthly_total_limit:
            total_used = sum(usage.values())
            remaining["total"] = max(0, quota.monthly_total_limit - total_used)

        return {
            "tenant_id": tenant_id,
            "has_limits": True,
            "usage": dict(usage),
            "remaining": remaining,
            "rate_limit_per_second": quota.rate_limit_per_second,
            "period_start": quota.current_period_start.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }

    async def set_quota(self, quota: MeteringQuota) -> None:
        """Set or update quota for a tenant."""
        self._quotas[quota.tenant_id] = quota
        logger.info(f"Quota set for tenant {quota.tenant_id}")

    async def get_billing_estimate(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate estimated billing for a tenant's usage."""
        usage = await self.get_usage_summary(tenant_id, start_date, end_date)

        # Apply rates (simplified - would use stored rates in production)
        base_rates = {
            MeterableOperation.CONSTITUTIONAL_VALIDATION.value: 0.1,  # $0.001 per validation
            MeterableOperation.AGENT_MESSAGE.value: 0.05,
            MeterableOperation.POLICY_EVALUATION.value: 0.2,
            MeterableOperation.COMPLIANCE_CHECK.value: 0.15,
            MeterableOperation.DELIBERATION_REQUEST.value: 1.0,
            MeterableOperation.HITL_APPROVAL.value: 5.0,
            MeterableOperation.BLOCKCHAIN_ANCHOR.value: 0.5,
        }

        tier_multipliers = {
            MeteringTier.STANDARD.value: 1.0,
            MeteringTier.ENHANCED.value: 1.5,
            MeteringTier.DELIBERATION.value: 3.0,
            MeteringTier.ENTERPRISE.value: 2.0,
        }

        line_items = []
        total_cents = 0

        for op, count in usage["operations"].items():
            if count > 0:
                rate = base_rates.get(op, 0.1)
                amount = int(count * rate)
                line_items.append({
                    "operation": op,
                    "count": count,
                    "rate_cents": rate,
                    "amount_cents": amount,
                })
                total_cents += amount

        return {
            "tenant_id": tenant_id,
            "period_start": usage["period_start"],
            "period_end": usage["period_end"],
            "line_items": line_items,
            "subtotal_cents": total_cents,
            "total_events": usage["total_events"],
            "constitutional_hash": self.constitutional_hash,
        }

    async def _check_and_update_quota(
        self, tenant_id: str, operation: MeterableOperation
    ) -> bool:
        """Check if operation is within quota and update usage."""
        quota = self._quotas.get(tenant_id)
        if not quota:
            return True  # No quota = unlimited

        # Update current usage
        if operation.value not in quota.current_usage:
            quota.current_usage[operation.value] = 0
        quota.current_usage[operation.value] += 1

        # Check limits (would enforce in production)
        if quota.monthly_total_limit:
            total = sum(quota.current_usage.values())
            if total > quota.monthly_total_limit:
                logger.warning(f"Tenant {tenant_id} exceeded total quota")
                return False

        return True

    async def _aggregation_loop(self) -> None:
        """Background loop to aggregate and flush events."""
        while self._running:
            try:
                await asyncio.sleep(self.aggregation_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aggregation error: {e}")

    async def _flush_buffer(self) -> None:
        """Flush event buffer to aggregated storage."""
        if not self._event_buffer:
            return

        events_to_flush = self._event_buffer.copy()
        self._event_buffer.clear()

        # Group by tenant
        by_tenant: Dict[str, List[UsageEvent]] = defaultdict(list)
        for event in events_to_flush:
            by_tenant[event.tenant_id].append(event)

        # Create aggregations
        now = datetime.now(timezone.utc)
        for tenant_id, events in by_tenant.items():
            agg_key = f"{tenant_id}:{now.strftime('%Y-%m-%d-%H')}"

            if agg_key not in self._aggregations:
                self._aggregations[agg_key] = UsageAggregation(
                    tenant_id=tenant_id,
                    period_start=now.replace(minute=0, second=0, microsecond=0),
                    period_end=now.replace(minute=0, second=0, microsecond=0)
                    + timedelta(hours=1),
                )

            agg = self._aggregations[agg_key]

            for event in events:
                op_key = event.operation.value
                tier_key = event.tier.value

                agg.operation_counts[op_key] = (
                    agg.operation_counts.get(op_key, 0) + event.units
                )
                agg.tier_counts[tier_key] = (
                    agg.tier_counts.get(tier_key, 0) + event.units
                )
                agg.total_operations += event.units
                agg.total_tokens += event.tokens_processed

        logger.debug(f"Flushed {len(events_to_flush)} events to aggregations")

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics for monitoring."""
        return {
            "total_events_processed": self._total_events_processed,
            "events_by_operation": dict(self._events_by_operation),
            "buffer_size": len(self._event_buffer),
            "aggregations_count": len(self._aggregations),
            "quotas_count": len(self._quotas),
            "constitutional_hash": self.constitutional_hash,
            "running": self._running,
        }
