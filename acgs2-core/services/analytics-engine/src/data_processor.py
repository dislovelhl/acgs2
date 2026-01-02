"""
Governance Data Processor - Kafka consumer for governance events

Consumes governance events from Kafka topics and processes them into
pandas DataFrames for analytics, anomaly detection, and forecasting.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

try:
    from aiokafka import AIOKafkaConsumer
except ImportError:
    AIOKafkaConsumer = None

logger = logging.getLogger(__name__)


class GovernanceEvent(BaseModel):
    """Model for governance events consumed from Kafka"""

    event_id: str
    event_type: str  # e.g., "violation", "policy_change", "access_denied"
    timestamp: datetime
    policy_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    outcome: Optional[str] = None  # "allowed", "denied", "violation"
    severity: Optional[str] = None  # "low", "medium", "high", "critical"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedMetrics(BaseModel):
    """Aggregated metrics from processed governance events"""

    period_start: datetime
    period_end: datetime
    total_events: int
    violation_count: int
    policy_changes: int
    unique_users: int
    unique_policies: int
    severity_distribution: Dict[str, int]
    top_violated_policies: List[Dict[str, Any]]


class GovernanceDataProcessor:
    """
    Kafka consumer and data processor for governance events.

    Consumes governance events from Kafka, processes them into pandas
    DataFrames, and provides aggregated metrics for analytics.
    """

    def __init__(
        self,
        kafka_bootstrap_servers: Optional[str] = None,
        kafka_topic: str = "governance-events",
        consumer_group: str = "analytics-engine",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize the governance data processor.

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers (default from env)
            kafka_topic: Topic to consume governance events from
            consumer_group: Consumer group ID for Kafka
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.kafka_bootstrap_servers = kafka_bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP", "localhost:9092"
        )
        self.kafka_topic = kafka_topic
        self.consumer_group = consumer_group
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.kafka_consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._events_buffer: List[GovernanceEvent] = []
        self._last_processed: Optional[datetime] = None

    async def initialize(self) -> bool:
        """
        Initialize the Kafka consumer with retry logic.

        Returns:
            True if initialization successful, False otherwise
        """
        if not AIOKafkaConsumer:
            logger.warning("aiokafka not available, Kafka consumption disabled")
            return False

        for attempt in range(1, self.max_retries + 1):
            try:
                self.kafka_consumer = AIOKafkaConsumer(
                    self.kafka_topic,
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    group_id=self.consumer_group,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                )
                await self.kafka_consumer.start()
                logger.info(f"Kafka consumer initialized for topic '{self.kafka_topic}'")
                return True
            except Exception as e:
                logger.warning(
                    f"Kafka consumer initialization attempt {attempt}/{self.max_retries} "
                    f"failed: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    logger.error(
                        f"Kafka consumer initialization failed after {self.max_retries} "
                        "attempts. Continuing without Kafka connection."
                    )
                    self.kafka_consumer = None
                    return False
        return False

    async def shutdown(self) -> None:
        """Shutdown the Kafka consumer gracefully"""
        self._running = False

        if self.kafka_consumer:
            try:
                await self.kafka_consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")
            finally:
                self.kafka_consumer = None

    async def consume_events(
        self,
        timeout_ms: int = 5000,
        max_records: int = 1000,
    ) -> List[GovernanceEvent]:
        """
        Consume governance events from Kafka.

        Args:
            timeout_ms: Timeout for polling in milliseconds
            max_records: Maximum number of records to consume per batch

        Returns:
            List of parsed governance events
        """
        if not self.kafka_consumer:
            logger.warning("Kafka consumer not initialized, returning empty list")
            return []

        events: List[GovernanceEvent] = []

        try:
            records = await self.kafka_consumer.getmany(
                timeout_ms=timeout_ms,
                max_records=max_records,
            )

            for _topic_partition, messages in records.items():
                for message in messages:
                    try:
                        event = self._parse_event(message.value)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")
                        continue

            if events:
                self._events_buffer.extend(events)
                logger.debug(f"Consumed {len(events)} governance events")

        except Exception as e:
            logger.error(f"Error consuming Kafka events: {e}")

        return events

    def _parse_event(self, data: Dict[str, Any]) -> Optional[GovernanceEvent]:
        """
        Parse raw Kafka message data into a GovernanceEvent.

        Args:
            data: Raw event data from Kafka

        Returns:
            Parsed GovernanceEvent or None if parsing fails
        """
        try:
            # Handle various timestamp formats
            timestamp = data.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif timestamp is None:
                timestamp = datetime.now(timezone.utc)

            return GovernanceEvent(
                event_id=data.get("event_id", data.get("id", "")),
                event_type=data.get("event_type", data.get("type", "unknown")),
                timestamp=timestamp,
                policy_id=data.get("policy_id"),
                user_id=data.get("user_id"),
                action=data.get("action"),
                resource=data.get("resource"),
                outcome=data.get("outcome"),
                severity=data.get("severity"),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to parse governance event: {e}")
            return None

    def events_to_dataframe(
        self,
        events: Optional[List[GovernanceEvent]] = None,
    ) -> pd.DataFrame:
        """
        Convert governance events to a pandas DataFrame.

        Args:
            events: List of events to convert (uses buffer if None)

        Returns:
            pandas DataFrame with governance event data
        """
        if events is None:
            events = self._events_buffer

        if not events:
            return pd.DataFrame(
                columns=[
                    "event_id",
                    "event_type",
                    "timestamp",
                    "policy_id",
                    "user_id",
                    "action",
                    "resource",
                    "outcome",
                    "severity",
                ]
            )

        data = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "policy_id": e.policy_id,
                "user_id": e.user_id,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
                "severity": e.severity,
                **e.metadata,
            }
            for e in events
        ]

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def prepare_for_prophet(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for Prophet forecasting.

        Prophet requires columns named 'ds' (datetime) and 'y' (value).
        This aggregates violation counts by day.

        Args:
            df: DataFrame with governance events

        Returns:
            DataFrame with 'ds' and 'y' columns for Prophet
        """
        if df.empty:
            return pd.DataFrame(columns=["ds", "y"])

        # Filter to violations and aggregate by day
        violations = df[df["outcome"] == "violation"].copy()

        if violations.empty:
            # If no violations, use all events as activity count
            violations = df.copy()

        violations["date"] = pd.to_datetime(violations["timestamp"]).dt.date
        daily_counts = violations.groupby("date").size().reset_index(name="count")

        # Rename columns for Prophet
        prophet_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(daily_counts["date"]),
                "y": daily_counts["count"],
            }
        )

        return prophet_df

    def prepare_for_anomaly_detection(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for anomaly detection.

        Aggregates metrics by time period for IsolationForest analysis.

        Args:
            df: DataFrame with governance events

        Returns:
            DataFrame with features for anomaly detection
        """
        if df.empty:
            return pd.DataFrame(columns=["violation_count", "user_count", "policy_changes"])

        df = df.copy()
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date

        # Calculate daily metrics
        daily_metrics = (
            df.groupby("date")
            .agg(
                violation_count=("outcome", lambda x: (x == "violation").sum()),
                user_count=("user_id", "nunique"),
                policy_changes=("event_type", lambda x: (x == "policy_change").sum()),
                total_events=("event_id", "count"),
            )
            .reset_index()
        )

        return daily_metrics

    def compute_metrics(
        self,
        df: pd.DataFrame,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> ProcessedMetrics:
        """
        Compute aggregated metrics from governance events.

        Args:
            df: DataFrame with governance events
            period_start: Start of analysis period
            period_end: End of analysis period

        Returns:
            ProcessedMetrics with aggregated statistics
        """
        if df.empty:
            now = datetime.now(timezone.utc)
            return ProcessedMetrics(
                period_start=period_start or now,
                period_end=period_end or now,
                total_events=0,
                violation_count=0,
                policy_changes=0,
                unique_users=0,
                unique_policies=0,
                severity_distribution={},
                top_violated_policies=[],
            )

        if period_start is None:
            period_start = pd.to_datetime(df["timestamp"]).min()
        if period_end is None:
            period_end = pd.to_datetime(df["timestamp"]).max()

        # Filter to period
        mask = (pd.to_datetime(df["timestamp"]) >= period_start) & (
            pd.to_datetime(df["timestamp"]) <= period_end
        )
        period_df = df[mask]

        # Calculate metrics
        violations = period_df[period_df["outcome"] == "violation"]

        severity_dist = {}
        if "severity" in period_df.columns:
            severity_counts = period_df["severity"].value_counts()
            severity_dist = severity_counts.to_dict()

        # Top violated policies
        top_policies = []
        if not violations.empty and "policy_id" in violations.columns:
            policy_counts = violations["policy_id"].value_counts().head(5)
            top_policies = [
                {"policy_id": pid, "count": int(count)}
                for pid, count in policy_counts.items()
                if pd.notna(pid)
            ]

        return ProcessedMetrics(
            period_start=period_start,
            period_end=period_end,
            total_events=len(period_df),
            violation_count=len(violations),
            policy_changes=len(period_df[period_df["event_type"] == "policy_change"]),
            unique_users=period_df["user_id"].nunique(),
            unique_policies=period_df["policy_id"].nunique(),
            severity_distribution=severity_dist,
            top_violated_policies=top_policies,
        )

    def clear_buffer(self) -> None:
        """Clear the events buffer"""
        self._events_buffer = []
        logger.debug("Events buffer cleared")

    def get_buffer_size(self) -> int:
        """Get the current size of the events buffer"""
        return len(self._events_buffer)

    async def run_batch_processing(
        self,
        batch_timeout_ms: int = 10000,
        max_batches: int = 10,
    ) -> pd.DataFrame:
        """
        Run batch processing to consume and aggregate events.

        Args:
            batch_timeout_ms: Timeout for each batch poll
            max_batches: Maximum number of batches to process

        Returns:
            DataFrame with all processed events
        """
        if not await self.initialize():
            logger.warning("Could not initialize Kafka, returning empty DataFrame")
            return pd.DataFrame()

        try:
            all_events: List[GovernanceEvent] = []

            for batch_num in range(max_batches):
                events = await self.consume_events(timeout_ms=batch_timeout_ms)
                if not events:
                    logger.info(f"No more events after {batch_num + 1} batches")
                    break
                all_events.extend(events)
                logger.info(
                    f"Batch {batch_num + 1}: consumed {len(events)} events, "
                    f"total: {len(all_events)}"
                )

            self._last_processed = datetime.now(timezone.utc)
            return self.events_to_dataframe(all_events)

        finally:
            await self.shutdown()

    def load_from_json(self, json_data: List[Dict[str, Any]]) -> List[GovernanceEvent]:
        """
        Load governance events from JSON data (for testing or file-based input).

        Args:
            json_data: List of event dictionaries

        Returns:
            List of parsed GovernanceEvent objects
        """
        events = []
        for data in json_data:
            event = self._parse_event(data)
            if event:
                events.append(event)
        self._events_buffer.extend(events)
        return events
