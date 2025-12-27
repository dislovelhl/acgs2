"""
Usage Metering Service Tests
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import (
    UsageEvent,
    MeterableOperation,
    MeteringTier,
    MeteringQuota,
    CONSTITUTIONAL_HASH,
)
from app.service import UsageMeteringService


@pytest.fixture
def metering_service():
    """Create a fresh metering service for each test."""
    return UsageMeteringService(
        aggregation_interval_seconds=1,
        constitutional_hash=CONSTITUTIONAL_HASH,
    )


@pytest.mark.asyncio
async def test_record_event(metering_service):
    """Test recording a usage event."""
    await metering_service.start()

    event = await metering_service.record_event(
        tenant_id="test-tenant",
        operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
        tier=MeteringTier.STANDARD,
        tokens_processed=100,
        latency_ms=2.5,
    )

    assert event.tenant_id == "test-tenant"
    assert event.operation == MeterableOperation.CONSTITUTIONAL_VALIDATION
    assert event.constitutional_hash == CONSTITUTIONAL_HASH
    assert event.tokens_processed == 100

    await metering_service.stop()


@pytest.mark.asyncio
async def test_usage_summary(metering_service):
    """Test getting usage summary."""
    await metering_service.start()

    # Record multiple events
    for _ in range(5):
        await metering_service.record_event(
            tenant_id="test-tenant",
            operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
        )

    for _ in range(3):
        await metering_service.record_event(
            tenant_id="test-tenant",
            operation=MeterableOperation.AGENT_MESSAGE,
        )

    summary = await metering_service.get_usage_summary("test-tenant")

    assert summary["tenant_id"] == "test-tenant"
    assert summary["total_events"] == 8
    assert summary["operations"]["constitutional_validation"] == 5
    assert summary["operations"]["agent_message"] == 3
    assert summary["constitutional_hash"] == CONSTITUTIONAL_HASH

    await metering_service.stop()


@pytest.mark.asyncio
async def test_quota_enforcement(metering_service):
    """Test quota tracking."""
    await metering_service.start()

    # Set quota
    quota = MeteringQuota(
        tenant_id="limited-tenant",
        monthly_total_limit=10,
        rate_limit_per_second=5,
    )
    await metering_service.set_quota(quota)

    # Record events up to limit
    for _ in range(10):
        await metering_service.record_event(
            tenant_id="limited-tenant",
            operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
        )

    status = await metering_service.get_quota_status("limited-tenant")

    assert status["has_limits"] is True
    assert status["remaining"]["total"] == 0
    assert status["constitutional_hash"] == CONSTITUTIONAL_HASH

    await metering_service.stop()


@pytest.mark.asyncio
async def test_billing_estimate(metering_service):
    """Test billing calculation."""
    await metering_service.start()

    # Record varied events
    await metering_service.record_event(
        tenant_id="billing-tenant",
        operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
    )
    await metering_service.record_event(
        tenant_id="billing-tenant",
        operation=MeterableOperation.DELIBERATION_REQUEST,
    )

    estimate = await metering_service.get_billing_estimate("billing-tenant")

    assert estimate["tenant_id"] == "billing-tenant"
    assert estimate["total_events"] == 2
    assert len(estimate["line_items"]) == 2
    assert estimate["subtotal_cents"] > 0
    assert estimate["constitutional_hash"] == CONSTITUTIONAL_HASH

    await metering_service.stop()


@pytest.mark.asyncio
async def test_metrics(metering_service):
    """Test service metrics."""
    await metering_service.start()

    await metering_service.record_event(
        tenant_id="metrics-tenant",
        operation=MeterableOperation.AGENT_MESSAGE,
    )

    metrics = metering_service.get_metrics()

    assert metrics["total_events_processed"] == 1
    assert metrics["events_by_operation"]["agent_message"] == 1
    assert metrics["running"] is True
    assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    await metering_service.stop()


@pytest.mark.asyncio
async def test_constitutional_hash_validation(metering_service):
    """Test constitutional hash is always included."""
    await metering_service.start()

    event = await metering_service.record_event(
        tenant_id="hash-test",
        operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
    )

    assert event.constitutional_hash == CONSTITUTIONAL_HASH
    assert metering_service.constitutional_hash == CONSTITUTIONAL_HASH

    await metering_service.stop()


@pytest.mark.asyncio
async def test_aggregation_flush(metering_service):
    """Test event buffer flush and aggregation."""
    service = UsageMeteringService(
        aggregation_interval_seconds=0.1,  # Fast aggregation for test
    )
    await service.start()

    # Record events
    for _ in range(10):
        await service.record_event(
            tenant_id="flush-tenant",
            operation=MeterableOperation.POLICY_EVALUATION,
        )

    # Wait for aggregation
    await asyncio.sleep(0.2)

    metrics = service.get_metrics()
    assert metrics["total_events_processed"] == 10

    await service.stop()


@pytest.mark.asyncio
async def test_multiple_tenants(metering_service):
    """Test isolation between tenants."""
    await metering_service.start()

    # Record for tenant A
    for _ in range(5):
        await metering_service.record_event(
            tenant_id="tenant-a",
            operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
        )

    # Record for tenant B
    for _ in range(3):
        await metering_service.record_event(
            tenant_id="tenant-b",
            operation=MeterableOperation.AGENT_MESSAGE,
        )

    summary_a = await metering_service.get_usage_summary("tenant-a")
    summary_b = await metering_service.get_usage_summary("tenant-b")

    assert summary_a["total_events"] == 5
    assert summary_b["total_events"] == 3
    assert "agent_message" not in summary_a["operations"]
    assert "constitutional_validation" not in summary_b["operations"]

    await metering_service.stop()


@pytest.mark.asyncio
async def test_tier_tracking(metering_service):
    """Test tier-based usage tracking."""
    await metering_service.start()

    await metering_service.record_event(
        tenant_id="tier-tenant",
        operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
        tier=MeteringTier.STANDARD,
    )
    await metering_service.record_event(
        tenant_id="tier-tenant",
        operation=MeterableOperation.DELIBERATION_REQUEST,
        tier=MeteringTier.DELIBERATION,
    )

    summary = await metering_service.get_usage_summary("tier-tenant")

    assert summary["tiers"]["standard"] == 1
    assert summary["tiers"]["deliberation"] == 1

    await metering_service.stop()
