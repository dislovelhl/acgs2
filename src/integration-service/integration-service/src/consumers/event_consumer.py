"""
Kafka Event Consumer for Governance Events

Provides async Kafka consumer to ingest governance events from the Agent Bus
and route them to enabled integrations.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from uuid import uuid4

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError, OffsetOutOfRangeError
from aiokafka.structs import ConsumerRecord
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..integration_types import ConfigDict as ConfigDictType
from ..integration_types import EventData, JSONDict
from ..integrations.base import EventSeverity, IntegrationEvent

logger = logging.getLogger(__name__)


class GovernanceEventType(str, Enum):
    """Types of governance events consumed from Agent Bus."""

    # Policy events
    POLICY_VIOLATION = "policy.violation"
    POLICY_CREATED = "policy.created"
    POLICY_UPDATED = "policy.updated"
    POLICY_DELETED = "policy.deleted"
    POLICY_EVALUATION = "policy.evaluation"

    # Compliance events
    COMPLIANCE_CHECK_STARTED = "compliance.check.started"
    COMPLIANCE_CHECK_PASSED = "compliance.check.passed"
    COMPLIANCE_CHECK_FAILED = "compliance.check.failed"

    # Access review events
    ACCESS_REVIEW_STARTED = "access_review.started"
    ACCESS_REVIEW_COMPLETED = "access_review.completed"
    ACCESS_REVIEW_EXPIRED = "access_review.expired"

    # Approval workflow events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    APPROVAL_EXPIRED = "approval.expired"

    # System events
    SYSTEM_ALERT = "system.alert"
    INTEGRATION_ERROR = "integration.error"
    AUDIT_LOG = "audit.log"

    # Custom events
    CUSTOM = "custom"


class EventConsumerState(str, Enum):
    """State of the event consumer."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class GovernanceEvent(BaseModel):
    """
    Governance event model from Agent Bus.

    Represents an event published by the Agent Bus that needs to be
    routed to configured integrations.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier",
    )
    event_type: str = Field(..., description="Type of governance event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    severity: str = Field(default="info", description="Event severity level")
    source: str = Field(default="agent-bus", description="Source system")

    # Event content
    policy_id: Optional[str] = Field(None, description="Related policy ID")
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    action: Optional[str] = Field(None, description="Action that triggered the event")
    outcome: Optional[str] = Field(None, description="Outcome of the action")

    # Event details
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(None, description="Detailed description")
    details: EventData = Field(default_factory=dict, description="Additional event details")

    # Metadata
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    tags: List[str] = Field(default_factory=list, description="Event tags")

    # Kafka metadata
    kafka_topic: Optional[str] = Field(None, description="Source Kafka topic")
    kafka_partition: Optional[int] = Field(None, description="Kafka partition")
    kafka_offset: Optional[int] = Field(None, description="Kafka offset")
    kafka_timestamp: Optional[int] = Field(None, description="Kafka message timestamp (ms)")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        """Normalize severity to lowercase."""
        if isinstance(v, str):
            return v.lower().strip()
        return str(v).lower()

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, v: str) -> str:
        """Normalize event type format."""
        if isinstance(v, str):
            return v.lower().strip()
        return str(v).lower()

    def to_integration_event(self) -> IntegrationEvent:
        """
        Convert to IntegrationEvent for adapter consumption.

        Returns:
            IntegrationEvent suitable for integration adapters
        """
        # Map severity string to EventSeverity enum
        severity_map = {
            "critical": EventSeverity.CRITICAL,
            "high": EventSeverity.HIGH,
            "medium": EventSeverity.MEDIUM,
            "low": EventSeverity.LOW,
            "info": EventSeverity.INFO,
        }
        severity = severity_map.get(self.severity.lower(), EventSeverity.INFO)

        return IntegrationEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            timestamp=self.timestamp,
            severity=severity,
            source=self.source,
            policy_id=self.policy_id,
            resource_id=self.resource_id,
            resource_type=self.resource_type,
            action=self.action,
            outcome=self.outcome,
            title=self.title,
            description=self.description,
            details=self.details,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            correlation_id=self.correlation_id,
            tags=self.tags,
        )


class EventConsumerMetrics(BaseModel):
    """Metrics for event consumer operations."""

    events_received: int = Field(default=0, description="Total events received")
    events_processed: int = Field(default=0, description="Events successfully processed")
    events_failed: int = Field(default=0, description="Events that failed processing")
    events_skipped: int = Field(default=0, description="Events skipped due to filters")
    events_retried: int = Field(default=0, description="Events retried after failure")

    # Timing metrics
    last_event_received_at: Optional[datetime] = Field(
        None, description="Timestamp of last received event"
    )
    last_event_processed_at: Optional[datetime] = Field(
        None, description="Timestamp of last successfully processed event"
    )
    last_error_at: Optional[datetime] = Field(None, description="Timestamp of last error")

    # Lag metrics
    current_lag: int = Field(default=0, description="Current consumer lag")
    max_lag_observed: int = Field(default=0, description="Maximum lag observed")

    # Processing metrics
    avg_processing_time_ms: float = Field(
        default=0.0, description="Average processing time in milliseconds"
    )
    total_processing_time_ms: float = Field(
        default=0.0, description="Total processing time in milliseconds"
    )

    # Connection metrics
    connection_errors: int = Field(default=0, description="Number of connection errors")
    reconnections: int = Field(default=0, description="Number of reconnections")

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
    )

    def record_event_received(self) -> None:
        """Record that an event was received."""
        self.events_received += 1
        self.last_event_received_at = datetime.now(timezone.utc)

    def record_event_processed(self, processing_time_ms: float) -> None:
        """Record that an event was successfully processed."""
        self.events_processed += 1
        self.last_event_processed_at = datetime.now(timezone.utc)
        self.total_processing_time_ms += processing_time_ms

        # Update average
        if self.events_processed > 0:
            self.avg_processing_time_ms = self.total_processing_time_ms / self.events_processed

    def record_event_failed(self) -> None:
        """Record that an event failed processing."""
        self.events_failed += 1
        self.last_error_at = datetime.now(timezone.utc)

    def record_event_skipped(self) -> None:
        """Record that an event was skipped."""
        self.events_skipped += 1

    def record_connection_error(self) -> None:
        """Record a connection error."""
        self.connection_errors += 1
        self.last_error_at = datetime.now(timezone.utc)

    def record_reconnection(self) -> None:
        """Record a successful reconnection."""
        self.reconnections += 1

    def update_lag(self, lag: int) -> None:
        """Update current lag metrics."""
        self.current_lag = lag
        if lag > self.max_lag_observed:
            self.max_lag_observed = lag

    def to_dict(self) -> JSONDict:
        """Convert metrics to dictionary."""
        return self.model_dump()


class EventConsumerConfig(BaseModel):
    """Configuration for the Kafka event consumer."""

    # Kafka connection settings
    bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated list of Kafka bootstrap servers",
    )
    topics: List[str] = Field(
        default_factory=lambda: ["governance-events"],
        description="Kafka topics to subscribe to",
    )
    group_id: str = Field(
        default="integration-service-consumer",
        description="Kafka consumer group ID",
    )
    client_id: str = Field(
        default="integration-service",
        description="Kafka client ID",
    )

    # Consumer behavior settings
    auto_offset_reset: str = Field(
        default="latest",
        description="Offset reset behavior (earliest, latest)",
    )
    enable_auto_commit: bool = Field(
        default=True,
        description="Enable automatic offset commits",
    )
    auto_commit_interval_ms: int = Field(
        default=5000,
        ge=1000,
        description="Auto-commit interval in milliseconds",
    )
    max_poll_records: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to fetch per poll",
    )
    max_poll_interval_ms: int = Field(
        default=300000,
        ge=60000,
        description="Maximum interval between polls in milliseconds",
    )
    session_timeout_ms: int = Field(
        default=30000,
        ge=10000,
        description="Consumer session timeout in milliseconds",
    )
    heartbeat_interval_ms: int = Field(
        default=10000,
        ge=1000,
        description="Heartbeat interval in milliseconds",
    )

    # Security settings
    security_protocol: str = Field(
        default="PLAINTEXT",
        description="Security protocol (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)",
    )
    sasl_mechanism: Optional[str] = Field(
        None,
        description="SASL mechanism (PLAIN, SCRAM-SHA-256, SCRAM-SHA-512)",
    )
    sasl_username: Optional[str] = Field(
        None,
        description="SASL username",
    )
    sasl_password: Optional[str] = Field(
        None,
        description="SASL password",
    )
    ssl_cafile: Optional[str] = Field(
        None,
        description="Path to CA certificate file",
    )
    ssl_certfile: Optional[str] = Field(
        None,
        description="Path to client certificate file",
    )
    ssl_keyfile: Optional[str] = Field(
        None,
        description="Path to client key file",
    )

    # Processing settings
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of events to process in a batch",
    )
    batch_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum time to wait for a batch to fill",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries for failed event processing",
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial delay between retries",
    )
    retry_exponential_base: float = Field(
        default=2.0,
        ge=1.5,
        le=4.0,
        description="Exponential backoff multiplier",
    )

    # Filtering settings
    event_type_filter: Optional[List[str]] = Field(
        None,
        description="Filter to only process specific event types (None = all)",
    )
    severity_filter: Optional[List[str]] = Field(
        None,
        description="Filter to only process specific severities (None = all)",
    )
    tenant_filter: Optional[List[str]] = Field(
        None,
        description="Filter to only process events from specific tenants (None = all)",
    )

    # Health check settings
    health_check_interval_seconds: int = Field(
        default=30,
        ge=5,
        description="Interval for consumer health checks",
    )
    max_consecutive_errors: int = Field(
        default=10,
        ge=1,
        description="Maximum consecutive errors before pausing",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_validator("auto_offset_reset", mode="before")
    @classmethod
    def validate_offset_reset(cls, v: str) -> str:
        """Validate offset reset policy."""
        valid = {"earliest", "latest", "none"}
        if v.lower() not in valid:
            raise ValueError(f"auto_offset_reset must be one of {valid}")
        return v.lower()

    @field_validator("security_protocol", mode="before")
    @classmethod
    def validate_security_protocol(cls, v: str) -> str:
        """Validate security protocol."""
        valid = {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}
        v_upper = v.upper()
        if v_upper not in valid:
            raise ValueError(f"security_protocol must be one of {valid}")
        return v_upper

    @classmethod
    def from_environment(cls) -> "EventConsumerConfig":
        """
        Create configuration from environment variables.

        Environment variable names:
        - KAFKA_BOOTSTRAP_SERVERS
        - KAFKA_TOPICS (comma-separated)
        - KAFKA_GROUP_ID
        - KAFKA_CLIENT_ID
        - KAFKA_SECURITY_PROTOCOL
        - KAFKA_SASL_MECHANISM
        - KAFKA_SASL_USERNAME
        - KAFKA_SASL_PASSWORD
        - KAFKA_SSL_CAFILE
        - KAFKA_SSL_CERTFILE
        - KAFKA_SSL_KEYFILE
        - KAFKA_AUTO_OFFSET_RESET
        - KAFKA_MAX_POLL_RECORDS
        """
        topics_str = os.getenv("KAFKA_TOPICS", "governance-events")
        topics = [t.strip() for t in topics_str.split(",") if t.strip()]

        event_types_str = os.getenv("KAFKA_EVENT_TYPE_FILTER")
        event_type_filter = None
        if event_types_str:
            event_type_filter = [t.strip() for t in event_types_str.split(",")]

        severity_str = os.getenv("KAFKA_SEVERITY_FILTER")
        severity_filter = None
        if severity_str:
            severity_filter = [s.strip() for s in severity_str.split(",")]

        tenant_str = os.getenv("KAFKA_TENANT_FILTER")
        tenant_filter = None
        if tenant_str:
            tenant_filter = [t.strip() for t in tenant_str.split(",")]

        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            topics=topics,
            group_id=os.getenv("KAFKA_GROUP_ID", "integration-service-consumer"),
            client_id=os.getenv("KAFKA_CLIENT_ID", "integration-service"),
            auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest"),
            max_poll_records=int(os.getenv("KAFKA_MAX_POLL_RECORDS", "100")),
            security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
            sasl_username=os.getenv("KAFKA_SASL_USERNAME"),
            sasl_password=os.getenv("KAFKA_SASL_PASSWORD"),
            ssl_cafile=os.getenv("KAFKA_SSL_CAFILE"),
            ssl_certfile=os.getenv("KAFKA_SSL_CERTFILE"),
            ssl_keyfile=os.getenv("KAFKA_SSL_KEYFILE"),
            event_type_filter=event_type_filter,
            severity_filter=severity_filter,
            tenant_filter=tenant_filter,
        )


# Type alias for event handler callback
EventHandler = Callable[[GovernanceEvent], Coroutine[Any, Any, bool]]


class EventConsumer:
    """
    Kafka consumer for governance events from Agent Bus.

    Provides async consumption of governance events with support for:
    - Configurable event filtering
    - Batch processing
    - Retry logic with exponential backoff
    - Metrics and health monitoring
    - Graceful shutdown
    """

    def __init__(self, config: Optional[EventConsumerConfig] = None):
        """
        Initialize the event consumer.

        Args:
            config: Consumer configuration. If None, loads from environment.
        """
        self.config = config or EventConsumerConfig.from_environment()
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._state = EventConsumerState.STOPPED
        self._metrics = EventConsumerMetrics()
        self._handlers: List[EventHandler] = []
        self._stop_event = asyncio.Event()
        self._consecutive_errors = 0
        self._assigned_partitions: Set[str] = set()

    @property
    def state(self) -> EventConsumerState:
        """Get current consumer state."""
        return self._state

    @property
    def metrics(self) -> EventConsumerMetrics:
        """Get current metrics."""
        return self._metrics

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._state == EventConsumerState.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""
        return (
            self._state in (EventConsumerState.RUNNING, EventConsumerState.PAUSED)
            and self._consecutive_errors < self.config.max_consecutive_errors
        )

    def add_handler(self, handler: EventHandler) -> None:
        """
        Add an event handler callback.

        Args:
            handler: Async function that processes events. Should return True on
                    success, False on failure.
        """
        self._handlers.append(handler)
        logger.info(f"Added event handler: {handler.__name__}")

    def remove_handler(self, handler: EventHandler) -> None:
        """
        Remove an event handler callback.

        Args:
            handler: Handler to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            logger.info(f"Removed event handler: {handler.__name__}")

    def clear_handlers(self) -> None:
        """Remove all event handlers."""
        self._handlers.clear()
        logger.info("Cleared all event handlers")

    async def start(self) -> None:
        """
        Start the consumer and begin consuming events.

        Raises:
            KafkaConnectionError: If connection to Kafka fails
        """
        if self._state == EventConsumerState.RUNNING:
            logger.warning("Consumer is already running")
            return

        logger.info(f"Starting Kafka consumer for topics: {self.config.topics}")
        self._state = EventConsumerState.STARTING
        self._stop_event.clear()

        try:
            # Build consumer configuration
            consumer_config = self._build_consumer_config()

            # Create and start consumer
            self._consumer = AIOKafkaConsumer(
                *self.config.topics,
                **consumer_config,
            )

            await self._consumer.start()

            # Get assigned partitions
            assignment = self._consumer.assignment()
            self._assigned_partitions = {f"{tp.topic}:{tp.partition}" for tp in assignment}
            logger.info(f"Assigned partitions: {self._assigned_partitions}")

            self._state = EventConsumerState.RUNNING
            self._consecutive_errors = 0
            logger.info("Kafka consumer started successfully")

        except KafkaConnectionError as e:
            self._state = EventConsumerState.ERROR
            self._metrics.record_connection_error()
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

        except Exception as e:
            self._state = EventConsumerState.ERROR
            logger.error(f"Failed to start consumer: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop the consumer gracefully.

        Waits for current message processing to complete before stopping.
        """
        if self._state == EventConsumerState.STOPPED:
            logger.warning("Consumer is already stopped")
            return

        logger.info("Stopping Kafka consumer...")
        self._state = EventConsumerState.STOPPING
        self._stop_event.set()

        if self._consumer:
            try:
                await self._consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
            finally:
                self._consumer = None

        self._state = EventConsumerState.STOPPED
        self._assigned_partitions.clear()

    async def pause(self) -> None:
        """Pause event consumption."""
        if self._state != EventConsumerState.RUNNING:
            logger.warning(f"Cannot pause consumer in state: {self._state}")
            return

        if self._consumer:
            partitions = self._consumer.assignment()
            self._consumer.pause(*partitions)
            self._state = EventConsumerState.PAUSED
            logger.info("Consumer paused")

    async def resume(self) -> None:
        """Resume event consumption."""
        if self._state != EventConsumerState.PAUSED:
            logger.warning(f"Cannot resume consumer in state: {self._state}")
            return

        if self._consumer:
            partitions = self._consumer.assignment()
            self._consumer.resume(*partitions)
            self._state = EventConsumerState.RUNNING
            logger.info("Consumer resumed")

    async def consume(self) -> None:
        """
        Main consumption loop.

        Continuously polls for messages and processes them through registered handlers.
        Call stop() to terminate the loop gracefully.
        """
        if self._state != EventConsumerState.RUNNING:
            raise RuntimeError(f"Consumer not running (state: {self._state})")

        logger.info("Starting consumption loop")

        while not self._stop_event.is_set():
            try:
                # Poll for messages
                messages = await self._poll_messages()

                if not messages:
                    continue

                # Process messages
                for message in messages:
                    if self._stop_event.is_set():
                        break

                    await self._process_message(message)

            except OffsetOutOfRangeError:
                logger.warning("Offset out of range, seeking to beginning")
                if self._consumer:
                    await self._consumer.seek_to_beginning()
                self._metrics.record_connection_error()

            except KafkaError as e:
                self._consecutive_errors += 1
                self._metrics.record_connection_error()
                logger.error(f"Kafka error: {e}")

                if self._consecutive_errors >= self.config.max_consecutive_errors:
                    logger.error(
                        f"Max consecutive errors ({self.config.max_consecutive_errors}) "
                        "reached, pausing consumer"
                    )
                    await self.pause()
                    # Wait before trying to resume
                    await asyncio.sleep(self.config.retry_delay_seconds * 5)
                    await self.resume()
                else:
                    await asyncio.sleep(self.config.retry_delay_seconds)

            except asyncio.CancelledError:
                logger.info("Consumption loop cancelled")
                break

            except Exception as e:
                self._consecutive_errors += 1
                self._metrics.record_connection_error()
                logger.exception(f"Unexpected error in consumption loop: {e}")
                await asyncio.sleep(self.config.retry_delay_seconds)

        logger.info("Consumption loop terminated")

    async def _poll_messages(self) -> List[ConsumerRecord]:
        """
        Poll Kafka for messages.

        Returns:
            List of Kafka consumer records
        """
        if not self._consumer:
            return []

        try:
            # Use getmany for batch polling
            batch = await asyncio.wait_for(
                self._consumer.getmany(
                    timeout_ms=int(self.config.batch_timeout_seconds * 1000),
                    max_records=self.config.batch_size,
                ),
                timeout=self.config.batch_timeout_seconds + 5.0,
            )

            messages = []
            for _tp, records in batch.items():
                messages.extend(records)

            return messages

        except asyncio.TimeoutError:
            return []

    async def _process_message(self, message: ConsumerRecord) -> None:
        """
        Process a single Kafka message.

        Args:
            message: Kafka consumer record
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Parse message
            event = self._parse_message(message)

            if event is None:
                self._metrics.record_event_skipped()
                return

            self._metrics.record_event_received()

            # Apply filters
            if not self._should_process_event(event):
                self._metrics.record_event_skipped()

                return

            # Process through handlers
            success = await self._dispatch_event(event)

            # Record metrics
            end_time = datetime.now(timezone.utc)
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            if success:
                self._metrics.record_event_processed(processing_time_ms)
                self._consecutive_errors = 0
            else:
                self._metrics.record_event_failed()

        except Exception as e:
            self._metrics.record_event_failed()
            logger.exception(f"Error processing message: {e}")

    def _parse_message(self, message: ConsumerRecord) -> Optional[GovernanceEvent]:
        """
        Parse a Kafka message into a GovernanceEvent.

        Args:
            message: Kafka consumer record

        Returns:
            Parsed GovernanceEvent or None if parsing fails
        """
        try:
            # Decode message value
            if message.value is None:
                logger.warning("Received message with null value")
                return None

            if isinstance(message.value, bytes):
                value_str = message.value.decode("utf-8")
            else:
                value_str = str(message.value)

            # Parse JSON
            data = json.loads(value_str)

            # Ensure required fields
            if "title" not in data:
                data["title"] = data.get("event_type", "Unknown Event")

            # Create event with Kafka metadata
            event = GovernanceEvent(
                kafka_topic=message.topic,
                kafka_partition=message.partition,
                kafka_offset=message.offset,
                kafka_timestamp=message.timestamp,
                **data,
            )

            return event

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            return None

        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None

    def _should_process_event(self, event: GovernanceEvent) -> bool:
        """
        Check if an event should be processed based on filters.

        Args:
            event: The governance event to check

        Returns:
            True if the event passes all filters
        """
        # Check event type filter
        if self.config.event_type_filter:
            if event.event_type not in self.config.event_type_filter:
                return False

        # Check severity filter
        if self.config.severity_filter:
            if event.severity not in self.config.severity_filter:
                return False

        # Check tenant filter
        if self.config.tenant_filter:
            if event.tenant_id not in self.config.tenant_filter:
                return False

        return True

    async def _dispatch_event(self, event: GovernanceEvent) -> bool:
        """
        Dispatch an event to all registered handlers.

        Args:
            event: The governance event to dispatch

        Returns:
            True if all handlers succeeded, False otherwise
        """
        if not self._handlers:
            logger.warning("No event handlers registered")
            return True

        all_success = True

        for handler in self._handlers:
            try:
                success = await self._invoke_handler_with_retry(handler, event)
                if not success:
                    all_success = False
            except Exception as e:
                logger.exception(
                    f"Handler {handler.__name__} failed for event {event.event_id}: {e}"
                )
                all_success = False

        return all_success

    async def _invoke_handler_with_retry(
        self, handler: EventHandler, event: GovernanceEvent
    ) -> bool:
        """
        Invoke a handler with retry logic.

        Args:
            handler: The event handler to invoke
            event: The governance event to process

        Returns:
            True if handler succeeded, False otherwise
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await handler(event)
                return result

            except Exception as e:
                last_error = e
                self._metrics.events_retried += 1

                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay_seconds * (
                        self.config.retry_exponential_base**attempt
                    )
                    logger.warning(
                        f"Handler {handler.__name__} failed (attempt {attempt + 1}/"
                        f"{self.config.max_retries + 1}), retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Handler {handler.__name__} failed after "
                        f"{self.config.max_retries + 1} attempts: {last_error}"
                    )

        return False

    def _build_consumer_config(self) -> ConfigDictType:
        """
        Build Kafka consumer configuration dictionary.

        Returns:
            Configuration dictionary for AIOKafkaConsumer
        """
        config = {
            "bootstrap_servers": self.config.bootstrap_servers,
            "group_id": self.config.group_id,
            "client_id": self.config.client_id,
            "auto_offset_reset": self.config.auto_offset_reset,
            "enable_auto_commit": self.config.enable_auto_commit,
            "auto_commit_interval_ms": self.config.auto_commit_interval_ms,
            "max_poll_records": self.config.max_poll_records,
            "max_poll_interval_ms": self.config.max_poll_interval_ms,
            "session_timeout_ms": self.config.session_timeout_ms,
            "heartbeat_interval_ms": self.config.heartbeat_interval_ms,
            "security_protocol": self.config.security_protocol,
        }

        # Add SASL configuration if using SASL
        if self.config.security_protocol in ("SASL_PLAINTEXT", "SASL_SSL"):
            if self.config.sasl_mechanism:
                config["sasl_mechanism"] = self.config.sasl_mechanism
            if self.config.sasl_username:
                config["sasl_plain_username"] = self.config.sasl_username
            if self.config.sasl_password:
                config["sasl_plain_password"] = self.config.sasl_password

        # Add SSL configuration if using SSL
        if self.config.security_protocol in ("SSL", "SASL_SSL"):
            if self.config.ssl_cafile:
                config["ssl_cafile"] = self.config.ssl_cafile
            if self.config.ssl_certfile:
                config["ssl_certfile"] = self.config.ssl_certfile
            if self.config.ssl_keyfile:
                config["ssl_keyfile"] = self.config.ssl_keyfile

        return config

    async def get_lag(self) -> Dict[str, int]:
        """
        Get current consumer lag per partition.

        Returns:
            Dictionary mapping partition to lag
        """
        if not self._consumer:
            return {}

        lag = {}

        try:
            assignment = self._consumer.assignment()

            for tp in assignment:
                # Get current position
                position = await self._consumer.position(tp)

                # Get end offset
                end_offsets = await self._consumer.end_offsets([tp])
                end_offset = end_offsets.get(tp, 0)

                # Calculate lag
                partition_lag = max(0, end_offset - position)
                lag[f"{tp.topic}:{tp.partition}"] = partition_lag

            # Update metrics
            total_lag = sum(lag.values())
            self._metrics.update_lag(total_lag)

        except Exception as e:
            logger.error(f"Error getting consumer lag: {e}")

        return lag

    def get_health_status(self) -> JSONDict:
        """
        Get consumer health status.

        Returns:
            Dictionary with health information
        """
        return {
            "state": self._state.value,
            "is_healthy": self.is_healthy,
            "is_running": self.is_running,
            "consecutive_errors": self._consecutive_errors,
            "max_consecutive_errors": self.config.max_consecutive_errors,
            "assigned_partitions": list(self._assigned_partitions),
            "handlers_count": len(self._handlers),
            "topics": self.config.topics,
            "group_id": self.config.group_id,
            "metrics": self._metrics.to_dict(),
        }

    def __repr__(self) -> str:
        return (
            f"<EventConsumer(topics={self.config.topics}, "
            f"group_id={self.config.group_id}, state={self._state.value})>"
        )
