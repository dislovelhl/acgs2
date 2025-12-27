"""
Tests for Constitutional Profiler
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock

from nemo_agent_toolkit.profiler import (
    ConstitutionalProfiler,
    GovernanceMetrics,
    ProfilerEvent,
    ProfilerContext,
    NeMoProfilerBridge,
    MetricType,
    CONSTITUTIONAL_HASH,
)


class TestGovernanceMetrics:
    """Tests for GovernanceMetrics."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = GovernanceMetrics()
        assert metrics.total_requests == 0
        assert metrics.compliant_requests == 0
        assert metrics.blocked_requests == 0
        assert metrics.constitutional_hash == CONSTITUTIONAL_HASH

    def test_compliance_rate_empty(self):
        """Test compliance rate with no requests."""
        metrics = GovernanceMetrics()
        assert metrics.compliance_rate == 1.0

    def test_compliance_rate_calculated(self):
        """Test compliance rate calculation."""
        metrics = GovernanceMetrics(
            total_requests=100,
            compliant_requests=95,
        )
        assert metrics.compliance_rate == 0.95

    def test_block_rate(self):
        """Test block rate calculation."""
        metrics = GovernanceMetrics(
            total_requests=100,
            blocked_requests=10,
        )
        assert metrics.block_rate == 0.1

    def test_violation_rate(self):
        """Test violation rate calculation."""
        metrics = GovernanceMetrics(
            total_requests=100,
            privacy_violations=5,
            safety_violations=3,
            ethics_violations=2,
            compliance_violations=0,
        )
        assert metrics.violation_rate == 0.1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = GovernanceMetrics(
            total_requests=50,
            compliant_requests=45,
            blocked_requests=5,
            privacy_violations=3,
        )
        data = metrics.to_dict()

        assert data["total_requests"] == 50
        assert data["compliant_requests"] == 45
        assert data["compliance_rate"] == 0.9
        assert data["violations"]["privacy"] == 3
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "collection_start" in data


class TestProfilerEvent:
    """Tests for ProfilerEvent."""

    def test_create_event(self):
        """Test creating a profiler event."""
        event = ProfilerEvent(
            event_type="guardrail_check",
            name="input_validation",
            duration_ms=5.5,
            metadata={"blocked": False},
        )
        assert event.event_type == "guardrail_check"
        assert event.name == "input_validation"
        assert event.duration_ms == 5.5
        assert event.metadata == {"blocked": False}
        assert event.constitutional_hash == CONSTITUTIONAL_HASH


class TestConstitutionalProfiler:
    """Tests for ConstitutionalProfiler."""

    @pytest.fixture
    def profiler(self):
        """Create profiler for testing."""
        return ConstitutionalProfiler(name="test-profiler")

    def test_profiler_initialization(self, profiler):
        """Test profiler initialization."""
        assert profiler.name == "test-profiler"
        assert profiler._running is False

    def test_start_profiler(self, profiler):
        """Test starting profiler."""
        profiler.start()
        assert profiler._running is True
        assert profiler.metrics.total_requests == 0

    def test_stop_profiler(self, profiler):
        """Test stopping profiler."""
        profiler.start()
        metrics = profiler.stop()
        assert profiler._running is False
        assert metrics.collection_end is not None

    def test_record_request_compliant(self, profiler):
        """Test recording compliant request."""
        profiler.start()
        profiler.record_request(compliant=True)
        assert profiler.metrics.total_requests == 1
        assert profiler.metrics.compliant_requests == 1

    def test_record_request_blocked(self, profiler):
        """Test recording blocked request."""
        profiler.start()
        profiler.record_request(compliant=False, blocked=True)
        assert profiler.metrics.total_requests == 1
        assert profiler.metrics.compliant_requests == 0
        assert profiler.metrics.blocked_requests == 1

    def test_record_request_modified(self, profiler):
        """Test recording modified request."""
        profiler.start()
        profiler.record_request(compliant=True, modified=True)
        assert profiler.metrics.modified_requests == 1

    def test_record_violation_privacy(self, profiler):
        """Test recording privacy violation."""
        profiler.start()
        profiler.record_violation("privacy")
        assert profiler.metrics.privacy_violations == 1

    def test_record_violation_safety(self, profiler):
        """Test recording safety violation."""
        profiler.start()
        profiler.record_violation("safety")
        assert profiler.metrics.safety_violations == 1

    def test_record_violation_ethics(self, profiler):
        """Test recording ethics violation."""
        profiler.start()
        profiler.record_violation("ethics")
        assert profiler.metrics.ethics_violations == 1

    def test_record_violation_compliance(self, profiler):
        """Test recording compliance violation."""
        profiler.start()
        profiler.record_violation("compliance")
        assert profiler.metrics.compliance_violations == 1

    def test_record_guardrail_check_input(self, profiler):
        """Test recording input guardrail check."""
        profiler.start()
        profiler.record_guardrail_check(
            direction="input",
            blocked=False,
            latency_ms=2.5,
        )
        assert profiler.metrics.input_checks == 1
        assert profiler.metrics.input_blocks == 0

    def test_record_guardrail_check_input_blocked(self, profiler):
        """Test recording blocked input guardrail check."""
        profiler.start()
        profiler.record_guardrail_check(
            direction="input",
            blocked=True,
            latency_ms=3.0,
        )
        assert profiler.metrics.input_checks == 1
        assert profiler.metrics.input_blocks == 1

    def test_record_guardrail_check_output(self, profiler):
        """Test recording output guardrail check."""
        profiler.start()
        profiler.record_guardrail_check(
            direction="output",
            blocked=False,
            latency_ms=2.0,
        )
        assert profiler.metrics.output_checks == 1
        assert profiler.metrics.output_blocks == 0

    def test_record_guardrail_check_pii_redaction(self, profiler):
        """Test recording PII redaction."""
        profiler.start()
        profiler.record_guardrail_check(
            direction="output",
            blocked=False,
            pii_redacted=True,
            latency_ms=4.0,
        )
        assert profiler.metrics.pii_redactions == 1

    def test_record_latency(self, profiler):
        """Test recording latency."""
        profiler.start()
        profiler.record_latency(5.0)
        profiler.record_latency(10.0)
        profiler.record_latency(15.0)
        assert len(profiler._latencies) == 3

    def test_latency_percentiles(self, profiler):
        """Test latency percentile calculation."""
        profiler.start()
        for i in range(100):
            profiler.record_latency(float(i))
        profiler.stop()

        assert profiler.metrics.p50_check_latency_ms == 50.0
        assert profiler.metrics.p95_check_latency_ms == 95.0
        assert profiler.metrics.p99_check_latency_ms == 99.0

    def test_add_callback(self, profiler):
        """Test adding callback."""
        callback_events = []

        def callback(event):
            callback_events.append(event)

        profiler.add_callback(callback)
        profiler = ConstitutionalProfiler(
            name="callback-test",
            enable_detailed_logging=True,
        )
        profiler.add_callback(callback)
        profiler.start()
        profiler.record_guardrail_check(
            direction="input",
            blocked=False,
            latency_ms=1.0,
        )

        assert len(callback_events) == 1

    def test_remove_callback(self, profiler):
        """Test removing callback."""
        def callback(event):
            pass

        profiler.add_callback(callback)
        assert len(profiler._callbacks) == 1

        profiler.remove_callback(callback)
        assert len(profiler._callbacks) == 0

    def test_get_events(self):
        """Test getting recorded events."""
        profiler = ConstitutionalProfiler(
            name="events-test",
            enable_detailed_logging=True,
        )
        profiler.start()
        profiler.record_guardrail_check(
            direction="input",
            blocked=False,
            latency_ms=1.0,
        )

        events = profiler.get_events()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_export_metrics(self, profiler):
        """Test exporting metrics."""
        profiler.start()
        profiler.record_request(compliant=True)
        profiler.record_latency(5.0)

        metrics = await profiler.export_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_get_summary(self, profiler):
        """Test getting summary."""
        profiler.start()
        profiler.record_request(compliant=True)
        profiler.record_violation("privacy")
        profiler.stop()

        summary = profiler.get_summary()
        assert "test-profiler" in summary
        assert "Total Requests: 1" in summary
        assert "Privacy: 1" in summary
        assert CONSTITUTIONAL_HASH in summary


class TestProfilerContext:
    """Tests for ProfilerContext."""

    def test_sync_context_manager(self):
        """Test synchronous context manager."""
        profiler = ConstitutionalProfiler(name="context-test")
        profiler.start()

        with profiler.create_context_manager("test_operation"):
            time.sleep(0.01)

        assert len(profiler._latencies) == 1
        assert profiler._latencies[0] >= 10.0  # At least 10ms

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager."""
        profiler = ConstitutionalProfiler(name="async-context-test")
        profiler.start()

        async with profiler.create_context_manager("async_operation"):
            await asyncio.sleep(0.01)

        assert len(profiler._latencies) == 1

    def test_context_manager_with_error(self):
        """Test context manager handles errors."""
        profiler = ConstitutionalProfiler(
            name="error-context-test",
            enable_detailed_logging=True,
        )
        profiler.start()

        try:
            with profiler.create_context_manager("error_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert len(profiler._latencies) == 1
        events = profiler.get_events()
        assert len(events) == 1


class TestTimeOperationDecorator:
    """Tests for time_operation decorator."""

    def test_sync_decorator(self):
        """Test synchronous decorator."""
        profiler = ConstitutionalProfiler(name="decorator-test")
        profiler.start()

        @profiler.time_operation("sync_func")
        def sync_function():
            time.sleep(0.01)
            return "result"

        result = sync_function()
        assert result == "result"
        assert len(profiler._latencies) == 1

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """Test asynchronous decorator."""
        profiler = ConstitutionalProfiler(name="async-decorator-test")
        profiler.start()

        @profiler.time_operation("async_func")
        async def async_function():
            await asyncio.sleep(0.01)
            return "async result"

        result = await async_function()
        assert result == "async result"
        assert len(profiler._latencies) == 1


class TestNeMoProfilerBridge:
    """Tests for NeMoProfilerBridge."""

    @pytest.fixture
    def bridge(self):
        """Create bridge for testing."""
        profiler = ConstitutionalProfiler(name="bridge-test")
        return NeMoProfilerBridge(profiler)

    def test_bridge_initialization(self, bridge):
        """Test bridge initialization."""
        assert bridge._profiler is not None
        assert bridge._nemo_profiler is None

    def test_connect_nemo_profiler(self, bridge):
        """Test connecting NeMo profiler."""
        mock_nemo = MagicMock()
        mock_nemo.add_callback = MagicMock()

        bridge.connect_nemo_profiler(mock_nemo)
        assert bridge._nemo_profiler is mock_nemo
        mock_nemo.add_callback.assert_called_once()

    def test_get_combined_metrics(self, bridge):
        """Test getting combined metrics."""
        bridge._profiler.start()
        bridge._profiler.record_request(compliant=True)

        metrics = bridge.get_combined_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_get_combined_metrics_with_nemo(self, bridge):
        """Test combined metrics with NeMo profiler."""
        mock_nemo = MagicMock()
        mock_nemo.add_callback = MagicMock()
        mock_nemo.get_metrics = MagicMock(return_value={"nemo_metric": 123})

        bridge.connect_nemo_profiler(mock_nemo)
        metrics = bridge.get_combined_metrics()

        assert "nemo_metrics" in metrics
        assert metrics["nemo_metrics"]["nemo_metric"] == 123

    def test_export_for_nemo(self, bridge):
        """Test exporting metrics in NeMo format."""
        bridge._profiler.start()
        bridge._profiler.record_request(compliant=True)
        bridge._profiler.record_latency(5.0)
        bridge._profiler.stop()

        export = bridge.export_for_nemo()
        assert "governance" in export
        assert "performance" in export
        assert "guardrails" in export
        assert export["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestMetricType:
    """Tests for MetricType enum."""

    def test_metric_type_values(self):
        """Test metric type enum values."""
        assert MetricType.LATENCY.value == "latency"
        assert MetricType.THROUGHPUT.value == "throughput"
        assert MetricType.COMPLIANCE.value == "compliance"
        assert MetricType.VIOLATION.value == "violation"
        assert MetricType.TOKEN_USAGE.value == "token_usage"
        assert MetricType.COST.value == "cost"
        assert MetricType.GUARDRAIL_CHECK.value == "guardrail_check"


class TestConstitutionalHashEnforcement:
    """Tests for constitutional hash enforcement."""

    def test_module_hash(self):
        """Test module-level constitutional hash."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_metrics_default_hash(self):
        """Test metrics default hash."""
        metrics = GovernanceMetrics()
        assert metrics.constitutional_hash == "cdd01ef066bc6cf2"

    def test_event_default_hash(self):
        """Test event default hash."""
        event = ProfilerEvent(
            event_type="test",
            name="test",
            duration_ms=0,
        )
        assert event.constitutional_hash == "cdd01ef066bc6cf2"


# Need this import for async tests
import asyncio
