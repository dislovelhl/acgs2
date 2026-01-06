"""
Tests for BaseIntegration batch event processing.

Tests cover:
- send_events_batch() success scenarios (all events succeed)
- send_events_batch() failure scenarios (authentication, all events fail)
- send_events_batch() partial success scenarios (some events succeed, some fail)
- Metrics tracking for batch operations
- Error handling and retry logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

import httpx
import pytest
from pydantic import SecretStr

from src.integrations.base import (
    AuthenticationError,
    BaseIntegration,
    EventSeverity,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationStatus,
    IntegrationType,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Test Implementation of BaseIntegration
# ============================================================================


class TestIntegrationCredentials(IntegrationCredentials):
    """Test credentials for BaseIntegration testing."""

    integration_type: IntegrationType = IntegrationType.SIEM
    api_key: SecretStr = SecretStr("test-api-key")


class TestIntegration(BaseIntegration):
    """
    Concrete implementation of BaseIntegration for testing.

    Provides mock implementations of abstract methods to test the base class
    batch processing functionality.
    """

    def __init__(self, credentials: TestIntegrationCredentials, fail_send: bool = False):
        super().__init__(credentials)
        self.fail_send = fail_send
        self._send_event_calls = []
        self._send_batch_calls = []

    async def _do_authenticate(self) -> IntegrationResult:
        """Mock authentication."""
        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="authenticate",
            external_id="test-auth-id",
        )

    async def _do_validate(self) -> IntegrationResult:
        """Mock validation."""
        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """Mock single event sending."""
        self._send_event_calls.append(event.event_id)

        if self.fail_send:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="send_event",
                error_code="SEND_FAILED",
                error_message="Mock send failure",
            )

        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="send_event",
            external_id=f"ext-{event.event_id}",
        )


class TestIntegrationWithCustomBatch(TestIntegration):
    """
    Test integration that overrides _do_send_events_batch() for custom batch handling.
    """

    def __init__(
        self,
        credentials: TestIntegrationCredentials,
        batch_behavior: str = "success",  # "success", "failure", "partial"
    ):
        super().__init__(credentials)
        self.batch_behavior = batch_behavior

    async def _do_send_events_batch(
        self, events: List[IntegrationEvent]
    ) -> List[IntegrationResult]:
        """Custom batch implementation with configurable behavior."""
        self._send_batch_calls.append([e.event_id for e in events])

        if self.batch_behavior == "success":
            # All events succeed
            return [
                IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=f"batch-ext-{event.event_id}",
                )
                for event in events
            ]
        elif self.batch_behavior == "failure":
            # All events fail
            return [
                IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="send_event",
                    error_code="BATCH_FAILED",
                    error_message="Mock batch failure",
                )
                for _ in events
            ]
        elif self.batch_behavior == "partial":
            # Partial success: even indices succeed, odd indices fail
            return [
                IntegrationResult(
                    success=(i % 2 == 0),
                    integration_name=self.name,
                    operation="send_event",
                    external_id=f"batch-ext-{event.event_id}" if i % 2 == 0 else None,
                    error_code=None if i % 2 == 0 else "SEND_FAILED",
                    error_message=None if i % 2 == 0 else f"Event {i} failed",
                )
                for i, event in enumerate(events)
            ]
        else:
            raise ValueError(f"Unknown batch_behavior: {self.batch_behavior}")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_credentials() -> TestIntegrationCredentials:
    """Create test credentials for BaseIntegration testing."""
    return TestIntegrationCredentials(
        integration_name="Test Integration",
        api_key=SecretStr("test-api-key-12345"),
    )


@pytest.fixture
def test_integration(test_credentials: TestIntegrationCredentials) -> TestIntegration:
    """Create a test integration adapter."""
    return TestIntegration(test_credentials)


@pytest.fixture
def sample_event() -> IntegrationEvent:
    """Create a sample governance event for testing."""
    return IntegrationEvent(
        event_id="evt-test-001",
        event_type="policy_violation",
        severity=EventSeverity.HIGH,
        source="acgs2",
        policy_id="POL-001",
        resource_id="res-123",
        resource_type="compute",
        action="create",
        outcome="blocked",
        title="Policy Violation Detected",
        description="Resource creation blocked due to policy violation",
        details={"region": "us-east-1", "cost_estimate": 150.00},
        user_id="user-456",
        tenant_id="tenant-789",
        correlation_id="corr-123",
        tags=["security", "compliance"],
    )


@pytest.fixture
def sample_events() -> List[IntegrationEvent]:
    """Create a list of sample events for batch testing."""
    return [
        IntegrationEvent(
            event_id=f"evt-test-{i:03d}",
            event_type="policy_violation",
            severity=EventSeverity.HIGH,
            source="acgs2",
            title=f"Test Event {i}",
            description=f"Test event description {i}",
        )
        for i in range(1, 6)  # 5 events
    ]


# ============================================================================
# Batch Processing Success Tests
# ============================================================================


class TestBatchProcessingSuccess:
    """Tests for successful batch event processing scenarios."""

    @pytest.mark.asyncio
    async def test_successful_batch_all_events_succeed(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test batch processing when all events succeed."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="success")
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        results = await adapter.send_events_batch(sample_events)

        # Verify all results are successful
        assert len(results) == 5
        assert all(r.success for r in results)
        assert all(r.external_id.startswith("batch-ext-") for r in results)

        # Verify metrics
        assert adapter._batches_sent == 1
        assert adapter._batches_failed == 0
        assert adapter._events_sent == 5
        assert adapter._events_failed == 0
        assert adapter._batch_events_total == 5
        assert adapter._last_success is not None
        assert adapter._last_failure is None

    @pytest.mark.asyncio
    async def test_successful_batch_with_default_implementation(
        self,
        test_integration: TestIntegration,
        sample_events: List[IntegrationEvent],
    ):
        """Test batch processing using default one-by-one implementation."""
        test_integration._authenticated = True
        test_integration._status = IntegrationStatus.ACTIVE

        results = await test_integration.send_events_batch(sample_events)

        # Verify all results are successful
        assert len(results) == 5
        assert all(r.success for r in results)

        # Verify _do_send_event was called for each event (default fallback)
        assert len(test_integration._send_event_calls) == 5
        assert test_integration._send_event_calls == [
            "evt-test-001",
            "evt-test-002",
            "evt-test-003",
            "evt-test-004",
            "evt-test-005",
        ]

        # Verify metrics
        assert test_integration._batches_sent == 1
        assert test_integration._batches_failed == 0
        assert test_integration._events_sent == 5
        assert test_integration._events_failed == 0
        assert test_integration._batch_events_total == 5

    @pytest.mark.asyncio
    async def test_batch_with_empty_list(
        self,
        test_integration: TestIntegration,
    ):
        """Test batch processing with empty event list."""
        test_integration._authenticated = True
        test_integration._status = IntegrationStatus.ACTIVE

        results = await test_integration.send_events_batch([])

        # Verify empty result
        assert len(results) == 0

        # Verify no metrics updated
        assert test_integration._batches_sent == 0
        assert test_integration._batches_failed == 0
        assert test_integration._events_sent == 0
        assert test_integration._events_failed == 0

    @pytest.mark.asyncio
    async def test_batch_with_single_event(
        self,
        test_integration: TestIntegration,
        sample_event: IntegrationEvent,
    ):
        """Test batch processing with single event."""
        test_integration._authenticated = True
        test_integration._status = IntegrationStatus.ACTIVE

        results = await test_integration.send_events_batch([sample_event])

        # Verify result
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].external_id == f"ext-{sample_event.event_id}"

        # Verify metrics
        assert test_integration._batches_sent == 1
        assert test_integration._events_sent == 1
        assert test_integration._batch_events_total == 1


# ============================================================================
# Batch Processing Failure Tests
# ============================================================================


class TestBatchProcessingFailure:
    """Tests for batch event processing failure scenarios."""

    @pytest.mark.asyncio
    async def test_batch_requires_authentication(
        self,
        test_integration: TestIntegration,
        sample_events: List[IntegrationEvent],
    ):
        """Test that batch processing requires authentication."""
        # Don't authenticate
        test_integration._authenticated = False

        with pytest.raises(AuthenticationError, match="not authenticated"):
            await test_integration.send_events_batch(sample_events)

        # Verify no metrics updated
        assert test_integration._batches_sent == 0
        assert test_integration._events_sent == 0

    @pytest.mark.asyncio
    async def test_batch_all_events_fail(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test batch processing when all events fail."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="failure")
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        results = await adapter.send_events_batch(sample_events)

        # Verify all results are failures
        assert len(results) == 5
        assert all(not r.success for r in results)
        assert all(r.error_code == "BATCH_FAILED" for r in results)
        assert all(r.error_message == "Mock batch failure" for r in results)

        # Verify metrics - all events failed
        assert adapter._batches_sent == 0
        assert adapter._batches_failed == 1
        assert adapter._events_sent == 0
        assert adapter._events_failed == 5
        assert adapter._batch_events_total == 0
        assert adapter._last_failure is not None
        assert adapter._last_error == "Mock batch failure"

    @pytest.mark.asyncio
    async def test_batch_with_default_implementation_all_fail(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test batch processing with default implementation when all events fail."""
        adapter = TestIntegration(test_credentials, fail_send=True)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        results = await adapter.send_events_batch(sample_events)

        # Verify all results are failures
        assert len(results) == 5
        assert all(not r.success for r in results)

        # Verify metrics
        assert adapter._batches_sent == 0
        assert adapter._batches_failed == 1
        assert adapter._events_sent == 0
        assert adapter._events_failed == 5

    @pytest.mark.asyncio
    async def test_batch_retry_on_network_error(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test that batch processing retries on network errors."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="success")
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        # Mock _do_send_events_batch to raise network error then succeed
        call_count = 0
        original_method = adapter._do_send_events_batch

        async def mock_send_batch_with_retry(events):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.NetworkError("Connection failed")
            return await original_method(events)

        adapter._do_send_events_batch = mock_send_batch_with_retry

        results = await adapter.send_events_batch(sample_events)

        # Verify retry succeeded
        assert call_count == 2  # First call failed, second succeeded
        assert len(results) == 5
        assert all(r.success for r in results)


# ============================================================================
# Batch Processing Partial Success Tests
# ============================================================================


class TestBatchProcessingPartialSuccess:
    """Tests for partial success scenarios in batch processing."""

    @pytest.mark.asyncio
    async def test_batch_partial_success(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test batch processing with partial success (some events succeed, some fail)."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="partial")
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        results = await adapter.send_events_batch(sample_events)

        # Verify results: even indices succeed, odd indices fail
        assert len(results) == 5
        assert results[0].success is True  # Index 0: success
        assert results[1].success is False  # Index 1: failure
        assert results[2].success is True  # Index 2: success
        assert results[3].success is False  # Index 3: failure
        assert results[4].success is True  # Index 4: success

        # Verify metrics - 3 succeeded, 2 failed
        assert adapter._batches_sent == 1  # Batch counted as sent (partial success)
        assert adapter._batches_failed == 0
        assert adapter._events_sent == 3  # 3 events succeeded
        assert adapter._events_failed == 2  # 2 events failed
        assert adapter._batch_events_total == 3  # Only successful events counted
        assert adapter._last_success is not None

    @pytest.mark.asyncio
    async def test_batch_partial_success_with_default_implementation(
        self,
        test_credentials: TestIntegrationCredentials,
    ):
        """Test partial success with default one-by-one implementation."""

        # Create custom adapter that fails on odd event IDs
        class PartialFailAdapter(TestIntegration):
            async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
                # Fail on odd event numbers
                event_num = int(event.event_id.split("-")[-1])
                if event_num % 2 == 1:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="send_event",
                        error_code="SEND_FAILED",
                        error_message=f"Event {event.event_id} failed",
                    )
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=f"ext-{event.event_id}",
                )

        adapter = PartialFailAdapter(test_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        events = [
            IntegrationEvent(
                event_id=f"evt-test-{i:03d}",
                event_type="test",
                title=f"Event {i}",
            )
            for i in range(1, 6)
        ]

        results = await adapter.send_events_batch(events)

        # Verify partial success: events 1, 3, 5 fail; events 2, 4 succeed
        assert len(results) == 5
        assert results[0].success is False  # evt-test-001 (odd)
        assert results[1].success is True  # evt-test-002 (even)
        assert results[2].success is False  # evt-test-003 (odd)
        assert results[3].success is True  # evt-test-004 (even)
        assert results[4].success is False  # evt-test-005 (odd)

        # Verify metrics
        assert adapter._batches_sent == 1
        assert adapter._batches_failed == 0
        assert adapter._events_sent == 2
        assert adapter._events_failed == 3
        assert adapter._batch_events_total == 2


# ============================================================================
# Metrics Tracking Tests
# ============================================================================


class TestBatchMetricsTracking:
    """Tests for batch operation metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking_all_success(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test metrics tracking when all events succeed."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="success")
        adapter._authenticated = True

        # Initial metrics
        assert adapter.metrics["batches_sent"] == 0
        assert adapter.metrics["batches_failed"] == 0
        assert adapter.metrics["events_sent"] == 0
        assert adapter.metrics["events_failed"] == 0
        assert adapter.metrics["batch_events_total"] == 0

        await adapter.send_events_batch(sample_events)

        # Verify metrics after successful batch
        metrics = adapter.metrics
        assert metrics["batches_sent"] == 1
        assert metrics["batches_failed"] == 0
        assert metrics["events_sent"] == 5
        assert metrics["events_failed"] == 0
        assert metrics["batch_events_total"] == 5
        assert metrics["last_success"] is not None
        assert metrics["last_failure"] is None

    @pytest.mark.asyncio
    async def test_metrics_tracking_all_failure(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test metrics tracking when all events fail."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="failure")
        adapter._authenticated = True

        await adapter.send_events_batch(sample_events)

        # Verify metrics after failed batch
        metrics = adapter.metrics
        assert metrics["batches_sent"] == 0
        assert metrics["batches_failed"] == 1
        assert metrics["events_sent"] == 0
        assert metrics["events_failed"] == 5
        assert metrics["batch_events_total"] == 0
        assert metrics["last_failure"] is not None

    @pytest.mark.asyncio
    async def test_metrics_tracking_partial_success(
        self,
        test_credentials: TestIntegrationCredentials,
        sample_events: List[IntegrationEvent],
    ):
        """Test metrics tracking for partial success."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="partial")
        adapter._authenticated = True

        await adapter.send_events_batch(sample_events)

        # Verify metrics after partial success (3 succeeded, 2 failed)
        metrics = adapter.metrics
        assert metrics["batches_sent"] == 1  # Counted as sent (partial success)
        assert metrics["batches_failed"] == 0
        assert metrics["events_sent"] == 3
        assert metrics["events_failed"] == 2
        assert metrics["batch_events_total"] == 3

    @pytest.mark.asyncio
    async def test_metrics_accumulation_across_multiple_batches(
        self,
        test_credentials: TestIntegrationCredentials,
    ):
        """Test that metrics accumulate correctly across multiple batch operations."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="success")
        adapter._authenticated = True

        # Send first batch (5 events)
        events1 = [
            IntegrationEvent(event_id=f"evt-1-{i}", event_type="test", title=f"Event 1-{i}")
            for i in range(5)
        ]
        await adapter.send_events_batch(events1)

        assert adapter.metrics["batches_sent"] == 1
        assert adapter.metrics["events_sent"] == 5
        assert adapter.metrics["batch_events_total"] == 5

        # Send second batch (3 events)
        events2 = [
            IntegrationEvent(event_id=f"evt-2-{i}", event_type="test", title=f"Event 2-{i}")
            for i in range(3)
        ]
        await adapter.send_events_batch(events2)

        # Verify accumulated metrics
        assert adapter.metrics["batches_sent"] == 2
        assert adapter.metrics["events_sent"] == 8
        assert adapter.metrics["batch_events_total"] == 8

    @pytest.mark.asyncio
    async def test_metrics_mixed_batch_results(
        self,
        test_credentials: TestIntegrationCredentials,
    ):
        """Test metrics tracking with mixed batch results (success, failure, partial)."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="success")
        adapter._authenticated = True

        events = [
            IntegrationEvent(event_id=f"evt-{i}", event_type="test", title=f"Event {i}")
            for i in range(3)
        ]

        # Batch 1: All succeed
        adapter.batch_behavior = "success"
        await adapter.send_events_batch(events)

        assert adapter.metrics["batches_sent"] == 1
        assert adapter.metrics["batches_failed"] == 0
        assert adapter.metrics["events_sent"] == 3
        assert adapter.metrics["events_failed"] == 0

        # Batch 2: All fail
        adapter.batch_behavior = "failure"
        await adapter.send_events_batch(events)

        assert adapter.metrics["batches_sent"] == 1
        assert adapter.metrics["batches_failed"] == 1
        assert adapter.metrics["events_sent"] == 3
        assert adapter.metrics["events_failed"] == 3

        # Batch 3: Partial success (2 succeed, 1 fails for 3 events)
        adapter.batch_behavior = "partial"
        await adapter.send_events_batch(events)

        assert adapter.metrics["batches_sent"] == 2  # Partial counted as sent
        assert adapter.metrics["batches_failed"] == 1
        assert adapter.metrics["events_sent"] == 5  # 3 + 2 (from partial)
        assert adapter.metrics["events_failed"] == 4  # 3 + 1 (from partial)


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestBatchErrorHandling:
    """Tests for error handling in batch processing."""

    @pytest.mark.asyncio
    async def test_batch_handles_exception_in_default_implementation(
        self,
        test_credentials: TestIntegrationCredentials,
    ):
        """Test that exceptions in default implementation are handled gracefully."""

        class ExceptionAdapter(TestIntegration):
            async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
                # Raise exception on second event
                if event.event_id == "evt-test-002":
                    raise ValueError("Simulated error for testing")
                return await super()._do_send_event(event)

        adapter = ExceptionAdapter(test_credentials)
        adapter._authenticated = True

        events = [
            IntegrationEvent(event_id=f"evt-test-{i:03d}", event_type="test", title=f"Event {i}")
            for i in range(1, 4)
        ]

        results = await adapter.send_events_batch(events)

        # Verify results
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False  # Exception caught
        assert results[1].error_code == "SEND_FAILED"
        assert "Simulated error" in results[1].error_message
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_batch_preserves_event_order(
        self,
        test_credentials: TestIntegrationCredentials,
    ):
        """Test that batch results preserve event order."""
        adapter = TestIntegrationWithCustomBatch(test_credentials, batch_behavior="partial")
        adapter._authenticated = True

        events = [
            IntegrationEvent(
                event_id=f"evt-test-{i:03d}",
                event_type="test",
                title=f"Event {i}",
            )
            for i in range(1, 11)  # 10 events
        ]

        results = await adapter.send_events_batch(events)

        # Verify order is preserved
        assert len(results) == 10
        for i, (_event, result) in enumerate(zip(events, results, strict=True)):
            assert result.integration_name == adapter.name
            # Even indices succeed, odd indices fail (based on partial behavior)
            if i % 2 == 0:
                assert result.success is True
                assert f"evt-test-{i + 1:03d}" in result.external_id
            else:
                assert result.success is False

    @pytest.mark.asyncio
    async def test_batch_empty_list_no_error(
        self,
        test_integration: TestIntegration,
    ):
        """Test that empty list doesn't cause errors."""
        test_integration._authenticated = True

        results = await test_integration.send_events_batch([])

        assert results == []
        assert test_integration._batches_sent == 0
        assert test_integration._events_sent == 0
