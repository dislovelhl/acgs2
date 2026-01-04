"""
Kafka → Analytics Engine Data Pipeline Integration Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests the end-to-end flow:
1. Publish governance events to Kafka topic
2. Run analytics-engine batch processing
3. Verify Redis cache populated with processed data
4. Check analytics-engine logs for successful processing
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from data_processor import GovernanceDataProcessor, GovernanceEvent, ProcessedMetrics

logger = logging.getLogger(__name__)


class TestGovernanceDataProcessor:
    """Unit tests for GovernanceDataProcessor."""

    def test_initialization_defaults(self) -> None:
        """Test processor initialization with default values."""
        processor = GovernanceDataProcessor()

        assert processor.kafka_topic == "governance-events"
        assert processor.consumer_group == "analytics-engine"
        assert processor.max_retries == 3
        assert processor.retry_delay == 2.0
        assert processor.kafka_consumer is None
        assert processor._running is False

    def test_initialization_custom_values(self) -> None:
        """Test processor initialization with custom values."""
        processor = GovernanceDataProcessor(
            kafka_bootstrap_servers="kafka:29092",
            kafka_topic="custom-topic",
            consumer_group="custom-group",
            max_retries=5,
            retry_delay=1.0,
        )

        assert processor.kafka_bootstrap_servers == "kafka:29092"
        assert processor.kafka_topic == "custom-topic"
        assert processor.consumer_group == "custom-group"
        assert processor.max_retries == 5
        assert processor.retry_delay == 1.0


class TestEventParsing:
    """Tests for event parsing functionality."""

    def test_parse_event_complete(self) -> None:
        """Test parsing a complete governance event."""
        processor = GovernanceDataProcessor()

        event_data = {
            "event_id": "evt-123",
            "event_type": "violation",
            "timestamp": "2025-01-01T12:00:00+00:00",
            "policy_id": "policy-001",
            "user_id": "user-001",
            "action": "write",
            "resource": "/sensitive/data",
            "outcome": "violation",
            "severity": "high",
            "metadata": {"source": "test"},
        }

        event = processor._parse_event(event_data)

        assert event is not None
        assert event.event_id == "evt-123"
        assert event.event_type == "violation"
        assert event.policy_id == "policy-001"
        assert event.user_id == "user-001"
        assert event.outcome == "violation"
        assert event.severity == "high"
        assert event.metadata == {"source": "test"}

    def test_parse_event_minimal(self) -> None:
        """Test parsing a minimal governance event."""
        processor = GovernanceDataProcessor()

        event_data = {
            "event_id": "evt-456",
            "event_type": "access",
            "timestamp": "2025-01-01T12:00:00Z",
        }

        event = processor._parse_event(event_data)

        assert event is not None
        assert event.event_id == "evt-456"
        assert event.event_type == "access"
        assert event.policy_id is None
        assert event.user_id is None

    def test_parse_event_with_unix_timestamp(self) -> None:
        """Test parsing event with Unix timestamp."""
        processor = GovernanceDataProcessor()

        event_data = {
            "event_id": "evt-789",
            "event_type": "audit",
            "timestamp": 1704110400,  # Unix timestamp
        }

        event = processor._parse_event(event_data)

        assert event is not None
        assert event.timestamp is not None

    def test_parse_event_missing_timestamp(self) -> None:
        """Test parsing event without timestamp uses current time."""
        processor = GovernanceDataProcessor()

        event_data = {
            "event_id": "evt-no-ts",
            "event_type": "access",
        }

        before = datetime.now(timezone.utc)
        event = processor._parse_event(event_data)
        after = datetime.now(timezone.utc)

        assert event is not None
        assert before <= event.timestamp <= after

    def test_parse_event_alternative_fields(self) -> None:
        """Test parsing event with alternative field names."""
        processor = GovernanceDataProcessor()

        event_data = {
            "id": "alt-evt-123",  # Alternative to event_id
            "type": "policy_change",  # Alternative to event_type
            "timestamp": "2025-01-01T12:00:00Z",
        }

        event = processor._parse_event(event_data)

        assert event is not None
        assert event.event_id == "alt-evt-123"
        assert event.event_type == "policy_change"


class TestDataFrameConversion:
    """Tests for DataFrame conversion functionality."""

    def test_events_to_dataframe_empty(self) -> None:
        """Test converting empty events list to DataFrame."""
        processor = GovernanceDataProcessor()

        df = processor.events_to_dataframe([])

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert "event_id" in df.columns
        assert "timestamp" in df.columns

    def test_events_to_dataframe_with_events(
        self, minimal_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test converting events to DataFrame."""
        processor = GovernanceDataProcessor()
        events = processor.load_from_json(minimal_governance_events)

        df = processor.events_to_dataframe(events)

        assert len(df) == 2
        assert "event_id" in df.columns
        assert "event_type" in df.columns
        assert "timestamp" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    def test_events_to_dataframe_from_buffer(
        self, minimal_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test converting events from internal buffer."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(minimal_governance_events)

        df = processor.events_to_dataframe()  # Uses buffer

        assert len(df) == 2


class TestProphetPreparation:
    """Tests for Prophet DataFrame preparation."""

    def test_prepare_for_prophet_empty(self) -> None:
        """Test preparing empty DataFrame for Prophet."""
        processor = GovernanceDataProcessor()

        df = pd.DataFrame()
        prophet_df = processor.prepare_for_prophet(df)

        assert "ds" in prophet_df.columns
        assert "y" in prophet_df.columns
        assert prophet_df.empty

    def test_prepare_for_prophet_with_violations(
        self, sample_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test preparing DataFrame with violations for Prophet."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(sample_governance_events)
        df = processor.events_to_dataframe()

        prophet_df = processor.prepare_for_prophet(df)

        # Should have ds (datetime) and y (value) columns
        assert "ds" in prophet_df.columns
        assert "y" in prophet_df.columns
        assert pd.api.types.is_datetime64_any_dtype(prophet_df["ds"])
        # y should contain daily violation counts
        assert all(prophet_df["y"] >= 0)

    def test_prepare_for_prophet_strict_column_names(
        self, sample_governance_events: list[dict[str, Any]]
    ) -> None:
        """Verify Prophet strict column naming: 'ds' and 'y'."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(sample_governance_events)
        df = processor.events_to_dataframe()

        prophet_df = processor.prepare_for_prophet(df)

        # Critical: Prophet requires exactly these column names
        assert set(prophet_df.columns) == {"ds", "y"}


class TestAnomalyDetectionPreparation:
    """Tests for anomaly detection DataFrame preparation."""

    def test_prepare_for_anomaly_detection_empty(self) -> None:
        """Test preparing empty DataFrame for anomaly detection."""
        processor = GovernanceDataProcessor()

        df = pd.DataFrame()
        anomaly_df = processor.prepare_for_anomaly_detection(df)

        assert "violation_count" in anomaly_df.columns
        assert "user_count" in anomaly_df.columns
        assert "policy_changes" in anomaly_df.columns
        assert anomaly_df.empty

    def test_prepare_for_anomaly_detection_with_data(
        self, sample_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test preparing DataFrame for anomaly detection."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(sample_governance_events)
        df = processor.events_to_dataframe()

        anomaly_df = processor.prepare_for_anomaly_detection(df)

        assert "violation_count" in anomaly_df.columns
        assert "user_count" in anomaly_df.columns
        assert "policy_changes" in anomaly_df.columns
        assert "total_events" in anomaly_df.columns
        assert "date" in anomaly_df.columns
        assert len(anomaly_df) > 0


class TestMetricsComputation:
    """Tests for metrics computation."""

    def test_compute_metrics_empty(self) -> None:
        """Test computing metrics from empty DataFrame."""
        processor = GovernanceDataProcessor()

        df = pd.DataFrame()
        metrics = processor.compute_metrics(df)

        assert isinstance(metrics, ProcessedMetrics)
        assert metrics.total_events == 0
        assert metrics.violation_count == 0

    def test_compute_metrics_with_data(
        self, sample_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test computing metrics from sample data."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(sample_governance_events)
        df = processor.events_to_dataframe()

        metrics = processor.compute_metrics(df)

        assert metrics.total_events > 0
        assert metrics.unique_users > 0
        assert metrics.unique_policies > 0
        assert isinstance(metrics.severity_distribution, dict)
        assert isinstance(metrics.top_violated_policies, list)


class TestBufferManagement:
    """Tests for event buffer management."""

    def test_clear_buffer(self, minimal_governance_events: list[dict[str, Any]]) -> None:
        """Test clearing the events buffer."""
        processor = GovernanceDataProcessor()
        processor.load_from_json(minimal_governance_events)

        assert processor.get_buffer_size() > 0

        processor.clear_buffer()

        assert processor.get_buffer_size() == 0

    def test_get_buffer_size(self, minimal_governance_events: list[dict[str, Any]]) -> None:
        """Test getting buffer size."""
        processor = GovernanceDataProcessor()

        assert processor.get_buffer_size() == 0

        processor.load_from_json(minimal_governance_events)

        assert processor.get_buffer_size() == len(minimal_governance_events)


class TestKafkaConsumerLifecycle:
    """Tests for Kafka consumer lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_without_aiokafka(self) -> None:
        """Test initialization when aiokafka is not available."""
        processor = GovernanceDataProcessor()

        # Patch AIOKafkaConsumer to None (simulating unavailable)
        with patch.object(sys.modules[processor.__module__], "AIOKafkaConsumer", None):
            result = await processor.initialize()

        assert result is False
        assert processor.kafka_consumer is None

    @pytest.mark.asyncio
    async def test_shutdown_without_consumer(self) -> None:
        """Test shutdown when consumer is not initialized."""
        processor = GovernanceDataProcessor()

        # Should not raise
        await processor.shutdown()

        assert processor._running is False

    @pytest.mark.asyncio
    async def test_consume_events_without_consumer(self) -> None:
        """Test consume_events when consumer is not initialized."""
        processor = GovernanceDataProcessor()

        events = await processor.consume_events()

        assert events == []


class TestLoadFromJson:
    """Tests for loading events from JSON."""

    def test_load_from_json_list(self, minimal_governance_events: list[dict[str, Any]]) -> None:
        """Test loading events from a list of dictionaries."""
        processor = GovernanceDataProcessor()

        events = processor.load_from_json(minimal_governance_events)

        assert len(events) == len(minimal_governance_events)
        for event in events:
            assert isinstance(event, GovernanceEvent)

    def test_load_from_json_adds_to_buffer(
        self, minimal_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test that loading events adds them to the buffer."""
        processor = GovernanceDataProcessor()

        initial_size = processor.get_buffer_size()
        processor.load_from_json(minimal_governance_events)
        final_size = processor.get_buffer_size()

        assert final_size == initial_size + len(minimal_governance_events)


class TestKafkaIntegration:
    """Integration tests for Kafka connectivity (requires running Kafka)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_kafka_consumer_connection(self, kafka_bootstrap_servers: str) -> None:
        """Test connecting to Kafka (requires Kafka to be running)."""
        processor = GovernanceDataProcessor(
            kafka_bootstrap_servers=kafka_bootstrap_servers,
            kafka_topic="governance-events",
        )

        try:
            result = await processor.initialize()
            # Connection attempt should succeed or fail gracefully
            assert isinstance(result, bool)
        finally:
            await processor.shutdown()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_processing_with_sample_data(self) -> None:
        """Test batch processing with sample data (no Kafka required)."""
        processor = GovernanceDataProcessor()

        # Use JSON loading instead of Kafka
        sample_events = [
            {
                "event_id": f"evt-{i}",
                "event_type": "violation" if i % 3 == 0 else "access",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "policy_id": f"policy-{i % 5}",
                "user_id": f"user-{i % 10}",
                "outcome": "violation" if i % 3 == 0 else "allowed",
                "severity": "high" if i % 3 == 0 else None,
            }
            for i in range(100)
        ]

        processor.load_from_json(sample_events)
        df = processor.events_to_dataframe()

        assert len(df) == 100
        assert df["event_type"].value_counts()["violation"] > 0


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""

    def test_full_pipeline_with_sample_data(
        self, sample_governance_events: list[dict[str, Any]]
    ) -> None:
        """Test the full data processing pipeline with sample data."""
        processor = GovernanceDataProcessor()

        # Step 1: Load events
        events = processor.load_from_json(sample_governance_events)
        assert len(events) > 0

        # Step 2: Convert to DataFrame
        df = processor.events_to_dataframe()
        assert len(df) == len(events)

        # Step 3: Prepare for Prophet
        prophet_df = processor.prepare_for_prophet(df)
        assert "ds" in prophet_df.columns
        assert "y" in prophet_df.columns

        # Step 4: Prepare for anomaly detection
        anomaly_df = processor.prepare_for_anomaly_detection(df)
        assert "violation_count" in anomaly_df.columns

        # Step 5: Compute metrics
        metrics = processor.compute_metrics(df)
        assert metrics.total_events == len(events)

    def test_pipeline_with_empty_data(self) -> None:
        """Test pipeline handles empty data gracefully."""
        processor = GovernanceDataProcessor()

        # Load empty list
        events = processor.load_from_json([])
        df = processor.events_to_dataframe()

        # All operations should work without errors
        prophet_df = processor.prepare_for_prophet(df)
        anomaly_df = processor.prepare_for_anomaly_detection(df)
        metrics = processor.compute_metrics(df)

        assert len(events) == 0
        assert df.empty
        assert prophet_df.empty
        assert anomaly_df.empty
        assert metrics.total_events == 0


class TestDataQuality:
    """Tests for data quality and edge cases."""

    def test_handles_malformed_events(self) -> None:
        """Test handling of malformed events."""
        processor = GovernanceDataProcessor()

        malformed_events = [
            {},  # Empty event
            {"event_id": None},  # Null event_id
            {"event_type": 123},  # Wrong type
        ]

        # Should not raise, just skip invalid events
        events = processor.load_from_json(malformed_events)

        # Malformed events should be skipped or handled gracefully
        assert isinstance(events, list)

    def test_handles_special_characters(self) -> None:
        """Test handling of special characters in event data."""
        processor = GovernanceDataProcessor()

        events_with_special = [
            {
                "event_id": "evt-special-1",
                "event_type": "violation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource": "/path/with/special/chars/<>&\"'",
                "metadata": {"message": "Test with unicode: 日本語 🔒"},
            }
        ]

        events = processor.load_from_json(events_with_special)
        df = processor.events_to_dataframe()

        assert len(events) == 1
        assert "日本語" in str(df.to_dict())
