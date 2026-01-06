"""Constitutional Hash: cdd01ef066bc6cf2
Kafka Client for HITL Approvals Event Streaming

Provides async Kafka producer and consumer for approval workflow events.
Topics:
- hitl.approvals.pending: New approval requests awaiting review
- hitl.approvals.escalated: Approvals that have been escalated to next level
- hitl.approvals.completed: Approvals that have been approved/rejected

Design Decisions:
- Uses aiokafka for async operations (consistent with enhanced_agent_bus)
- Singleton pattern for global client access
- Topic auto-creation on startup (development mode)
- JSON serialization for message payloads
- Error sanitization for secure logging
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Coroutine, Dict, List, Optional, Set

from acgs2_core.shared.types import JSONDict, KwargsType

from app.config import settings

logger = logging.getLogger(__name__)

# Check if aiokafka is available
try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning(
        "aiokafka not installed. Kafka event streaming unavailable. "
        "Install with: pip install aiokafka"
    )

# =============================================================================
# Topic Definitions
# =============================================================================


class HITLTopic(str, Enum):
    """HITL approval event topics."""

    PENDING = "hitl.approvals.pending"
    ESCALATED = "hitl.approvals.escalated"
    COMPLETED = "hitl.approvals.completed"

    @classmethod
    def all_topics(cls) -> List[str]:
        """Get all topic names."""
        return [t.value for t in cls]


# =============================================================================
# Event Types
# =============================================================================


class HITLEventType(str, Enum):
    """HITL approval event types."""

    # Approval lifecycle events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_SUBMITTED = "approval_submitted"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_CANCELLED = "approval_cancelled"

    # Escalation events
    ESCALATION_TRIGGERED = "escalation_triggered"
    ESCALATION_TIMEOUT = "escalation_timeout"
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"

    # Notification events
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"


# =============================================================================
# Event Data Structures
# =============================================================================


@dataclass
class HITLEvent:
    """
    Represents an HITL approval event.

    All events contain common metadata plus event-specific payload.
    """

    event_id: str
    event_type: HITLEventType
    topic: HITLTopic
    request_id: str
    timestamp: float  # Unix timestamp
    payload: JSONDict = field(default_factory=dict)

    # Optional context
    user_id: Optional[str] = None
    chain_id: Optional[str] = None
    priority: Optional[str] = None
    escalation_level: int = 1

    def to_dict(self) -> JSONDict:
        """Convert to dictionary for Kafka serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "topic": self.topic.value,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "payload": self.payload,
            "user_id": self.user_id,
            "chain_id": self.chain_id,
            "priority": self.priority,
            "escalation_level": self.escalation_level,
        }

    @classmethod
    def from_dict(cls, data: JSONDict) -> "HITLEvent":
        """Create from dictionary (Kafka deserialization)."""
        return cls(
            event_id=data["event_id"],
            event_type=HITLEventType(data["event_type"]),
            topic=HITLTopic(data["topic"]),
            request_id=data["request_id"],
            timestamp=float(data["timestamp"]),
            payload=data.get("payload", {}),
            user_id=data.get("user_id"),
            chain_id=data.get("chain_id"),
            priority=data.get("priority"),
            escalation_level=int(data.get("escalation_level", 1)),
        )

    @classmethod
    def create(
        cls,
        event_type: HITLEventType,
        request_id: str,
        payload: Optional[JSONDict] = None,
        **kwargs: KwargsType,
    ) -> "HITLEvent":
        """
        Create a new HITL event with auto-generated ID and timestamp.

        The topic is automatically determined based on event type.
        """
        # Determine topic based on event type
        if event_type in (
            HITLEventType.ESCALATION_TRIGGERED,
            HITLEventType.ESCALATION_TIMEOUT,
            HITLEventType.SLA_WARNING,
            HITLEventType.SLA_BREACH,
        ):
            topic = HITLTopic.ESCALATED
        elif event_type in (
            HITLEventType.APPROVAL_APPROVED,
            HITLEventType.APPROVAL_REJECTED,
            HITLEventType.APPROVAL_CANCELLED,
        ):
            topic = HITLTopic.COMPLETED
        else:
            topic = HITLTopic.PENDING

        import time

        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            topic=topic,
            request_id=request_id,
            timestamp=time.time(),
            payload=payload or {},
            **kwargs,
        )


# Type alias for event handlers
from typing import Any

EventHandler = Callable[[HITLEvent], Coroutine[Any, Any, None]]

# =============================================================================
# Kafka Client Exceptions
# =============================================================================


class KafkaClientError(Exception):
    """Base exception for Kafka client errors."""

    pass


class KafkaConnectionError(KafkaClientError):
    """Raised when Kafka connection fails."""

    pass


class KafkaNotAvailableError(KafkaClientError):
    """Raised when aiokafka is not installed."""

    pass


class KafkaPublishError(KafkaClientError):
    """Raised when message publishing fails."""

    pass


# =============================================================================
# Kafka Client
# =============================================================================


class HITLKafkaClient:
    """
    Kafka client for HITL approval event streaming.

    Features:
    - Async producer for publishing events
    - Consumer support with handler registration
    - Topic auto-creation in development mode
    - JSON serialization with proper error handling
    - Error message sanitization for secure logging
    - Singleton pattern support
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "hitl-approvals",
        auto_create_topics: bool = True,
    ):
        """
        Initialize the Kafka client.

        Args:
            bootstrap_servers: Kafka bootstrap servers (uses settings if None)
            client_id: Client identifier for Kafka
            auto_create_topics: Whether to create topics on startup
        """
        if not KAFKA_AVAILABLE:
            raise KafkaNotAvailableError(
                "aiokafka not installed. Install with: pip install aiokafka"
            )

        self._bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self._client_id = client_id
        self._auto_create_topics = auto_create_topics

        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._handlers: Dict[HITLTopic, List[EventHandler]] = {topic: [] for topic in HITLTopic}
        self._running = False
        self._consumer_tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()

        logger.info(
            f"HITLKafkaClient initialized (bootstrap={self._sanitize_url(self._bootstrap_servers)})"
        )

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def start(self) -> None:
        """
        Start the Kafka client.

        Creates topics if needed and starts the producer.
        """
        if self._running:
            logger.warning("HITLKafkaClient already running")
            return

        try:
            # Create topics if enabled
            if self._auto_create_topics:
                await self._ensure_topics_exist()

            # Start producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                value_serializer=self._serialize_event,
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Ensure durability
                retry_backoff_ms=500,
                request_timeout_ms=30000,
                max_batch_size=16384,
            )
            await self._producer.start()

            self._running = True
            logger.info(f"HITLKafkaClient started on {self._sanitize_url(self._bootstrap_servers)}")

        except Exception as e:
            raise KafkaConnectionError(
                f"Failed to start Kafka client: {self._sanitize_error(e)}"
            ) from e

    async def stop(self) -> None:
        """Stop the Kafka client and cleanup resources."""
        self._running = False

        # Cancel consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._consumer_tasks = []

        # Stop consumers
        for consumer in self._consumers.values():
            try:
                await consumer.stop()
            except Exception as e:
                logger.error(f"Error stopping consumer: {self._sanitize_error(e)}")

        self._consumers = {}

        # Stop producer
        if self._producer:
            try:
                await self._producer.flush()
                await self._producer.stop()
            except Exception as e:
                logger.error(f"Error stopping producer: {self._sanitize_error(e)}")
            self._producer = None

        logger.info("HITLKafkaClient stopped")

    async def health_check(self) -> bool:
        """
        Check Kafka connectivity.

        Returns:
            True if Kafka is reachable
        """
        if not self._running or not self._producer:
            return False

        try:
            # Try to get metadata from broker
            metadata = await self._producer.partitions_for(HITLTopic.PENDING.value)
            return metadata is not None
        except Exception as e:
            logger.error(f"Kafka health check failed: {self._sanitize_error(e)}")
            return False

    async def _ensure_topics_exist(self) -> None:
        """Create HITL topics if they don't exist."""
        try:
            admin = AIOKafkaAdminClient(
                bootstrap_servers=self._bootstrap_servers,
                client_id=f"{self._client_id}-admin",
            )
            await admin.start()

            try:
                # Get existing topics
                existing_topics: Set[str] = set()
                try:
                    # describe_cluster doesn't return topics directly
                    # We'll just try to create and handle the error
                    await admin.describe_cluster()
                except Exception:  # nosec B110 - intentionally ignoring errors from describe_cluster
                    pass

                # Create new topics
                new_topics = [
                    NewTopic(
                        name=topic,
                        num_partitions=3,  # Support parallelism
                        replication_factor=1,  # Adjust for production
                    )
                    for topic in HITLTopic.all_topics()
                    if topic not in existing_topics
                ]

                if new_topics:
                    try:
                        await admin.create_topics(new_topics)
                        logger.info(f"Created Kafka topics: {[t.name for t in new_topics]}")
                    except Exception as e:
                        # Topic may already exist
                        if "TopicAlreadyExistsError" not in str(e):
                            logger.warning(f"Topic creation warning: {self._sanitize_error(e)}")

            finally:
                await admin.close()

        except Exception as e:
            logger.warning(
                f"Could not ensure topics exist (will be created on first use): "
                f"{self._sanitize_error(e)}"
            )

    # =========================================================================
    # Publishing
    # =========================================================================

    async def publish_event(self, event: HITLEvent) -> bool:
        """
        Publish an HITL event to Kafka.

        Args:
            event: The event to publish

        Returns:
            True if published successfully

        Raises:
            KafkaPublishError: If publishing fails
        """
        if not self._running or not self._producer:
            raise KafkaPublishError("Kafka producer not started")

        try:
            # Use request_id as partition key for ordering within a request
            key = event.request_id

            await self._producer.send_and_wait(
                topic=event.topic.value,
                value=event.to_dict(),
                key=key,
            )

            logger.debug(
                f"Published event {event.event_id} to {event.topic.value} "
                f"(type={event.event_type.value}, request={event.request_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {self._sanitize_error(e)}")
            raise KafkaPublishError(f"Failed to publish event: {self._sanitize_error(e)}") from e

    async def publish_approval_requested(
        self,
        request_id: str,
        chain_id: str,
        priority: str,
        decision_type: str,
        impact_level: str,
        requester_id: Optional[str] = None,
        metadata: Optional[JSONDict] = None,
    ) -> HITLEvent:
        """
        Publish an approval requested event.

        Args:
            request_id: Unique approval request ID
            chain_id: Approval chain ID
            priority: Request priority (critical/high/medium/low)
            decision_type: Type of decision requiring approval
            impact_level: Impact level of the decision
            requester_id: ID of the user/system requesting approval
            metadata: Additional metadata

        Returns:
            The published event
        """
        event = HITLEvent.create(
            event_type=HITLEventType.APPROVAL_REQUESTED,
            request_id=request_id,
            chain_id=chain_id,
            priority=priority,
            payload={
                "decision_type": decision_type,
                "impact_level": impact_level,
                "requester_id": requester_id,
                **(metadata or {}),
            },
        )
        await self.publish_event(event)
        return event

    async def publish_escalation(
        self,
        request_id: str,
        reason: str,
        from_level: int,
        to_level: int,
        timeout_minutes: Optional[int] = None,
        metadata: Optional[JSONDict] = None,
    ) -> HITLEvent:
        """
        Publish an escalation event.

        Args:
            request_id: Approval request ID
            reason: Reason for escalation (timeout/manual/sla_breach)
            from_level: Previous escalation level
            to_level: New escalation level
            timeout_minutes: Timeout that triggered escalation (if applicable)
            metadata: Additional metadata

        Returns:
            The published event
        """
        event = HITLEvent.create(
            event_type=HITLEventType.ESCALATION_TRIGGERED,
            request_id=request_id,
            escalation_level=to_level,
            payload={
                "reason": reason,
                "from_level": from_level,
                "to_level": to_level,
                "timeout_minutes": timeout_minutes,
                **(metadata or {}),
            },
        )
        await self.publish_event(event)
        return event

    async def publish_approval_completed(
        self,
        request_id: str,
        decision: str,  # approved/rejected
        approver_id: str,
        reasoning: Optional[str] = None,
        chain_id: Optional[str] = None,
        metadata: Optional[JSONDict] = None,
    ) -> HITLEvent:
        """
        Publish an approval completed event.

        Args:
            request_id: Approval request ID
            decision: Decision made (approved/rejected)
            approver_id: ID of the approver
            reasoning: Reasoning for the decision
            chain_id: Approval chain ID
            metadata: Additional metadata

        Returns:
            The published event
        """
        event_type = (
            HITLEventType.APPROVAL_APPROVED
            if decision == "approved"
            else HITLEventType.APPROVAL_REJECTED
        )

        event = HITLEvent.create(
            event_type=event_type,
            request_id=request_id,
            user_id=approver_id,
            chain_id=chain_id,
            payload={
                "decision": decision,
                "approver_id": approver_id,
                "reasoning": reasoning,
                **(metadata or {}),
            },
        )
        await self.publish_event(event)
        return event

    async def publish_sla_breach(
        self,
        request_id: str,
        priority: str,
        sla_timeout_minutes: int,
        actual_time_minutes: float,
        escalation_level: int,
        metadata: Optional[JSONDict] = None,
    ) -> HITLEvent:
        """
        Publish an SLA breach event.

        Args:
            request_id: Approval request ID
            priority: Request priority
            sla_timeout_minutes: Configured SLA timeout
            actual_time_minutes: Actual time elapsed
            escalation_level: Current escalation level
            metadata: Additional metadata

        Returns:
            The published event
        """
        event = HITLEvent.create(
            event_type=HITLEventType.SLA_BREACH,
            request_id=request_id,
            priority=priority,
            escalation_level=escalation_level,
            payload={
                "sla_timeout_minutes": sla_timeout_minutes,
                "actual_time_minutes": actual_time_minutes,
                "overage_minutes": actual_time_minutes - sla_timeout_minutes,
                "overage_percent": (
                    ((actual_time_minutes - sla_timeout_minutes) / sla_timeout_minutes) * 100
                    if sla_timeout_minutes > 0
                    else 0
                ),
                **(metadata or {}),
            },
        )
        await self.publish_event(event)
        return event

    # =========================================================================
    # Subscribing
    # =========================================================================

    def register_handler(
        self,
        topic: HITLTopic,
        handler: EventHandler,
    ) -> None:
        """
        Register an event handler for a topic.

        Args:
            topic: Topic to handle events from
            handler: Async function to call for each event
        """
        self._handlers[topic].append(handler)
        logger.info(f"Registered handler for {topic.value}: {handler.__name__}")

    def unregister_handler(
        self,
        topic: HITLTopic,
        handler: EventHandler,
    ) -> bool:
        """
        Unregister an event handler.

        Args:
            topic: Topic the handler was registered for
            handler: Handler to unregister

        Returns:
            True if handler was found and removed
        """
        try:
            self._handlers[topic].remove(handler)
            logger.info(f"Unregistered handler for {topic.value}: {handler.__name__}")
            return True
        except ValueError:
            return False

    async def start_consuming(
        self,
        topics: Optional[List[HITLTopic]] = None,
        group_id: Optional[str] = None,
    ) -> None:
        """
        Start consuming events from topics.

        Args:
            topics: Topics to consume (all if None)
            group_id: Consumer group ID (auto-generated if None)
        """
        if not self._running:
            raise KafkaClientError("Kafka client not started")

        topics = topics or list(HITLTopic)
        topic_names = [t.value for t in topics]
        group_id = group_id or f"{self._client_id}-consumer-group"

        consumer = AIOKafkaConsumer(
            *topic_names,
            bootstrap_servers=self._bootstrap_servers,
            group_id=group_id,
            value_deserializer=self._deserialize_event,
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )

        consumer_id = f"consumer-{uuid.uuid4().hex[:8]}"
        self._consumers[consumer_id] = consumer

        await consumer.start()

        async def consume_loop():
            """Process messages from consumer."""
            try:
                async for msg in consumer:
                    if not self._running:
                        break

                    try:
                        event = msg.value
                        if event:
                            topic = HITLTopic(msg.topic)
                            for handler in self._handlers[topic]:
                                try:
                                    await handler(event)
                                except Exception as e:
                                    logger.error(
                                        f"Handler error for {event.event_id}: "
                                        f"{self._sanitize_error(e)}"
                                    )

                    except Exception as e:
                        logger.error(f"Error processing Kafka message: {self._sanitize_error(e)}")

            except asyncio.CancelledError:
                pass
            finally:
                await consumer.stop()
                self._consumers.pop(consumer_id, None)

        task = asyncio.create_task(consume_loop())
        self._consumer_tasks.append(task)

        logger.info(f"Started consuming from topics: {topic_names}")

    # =========================================================================
    # Serialization
    # =========================================================================

    def _serialize_event(self, event_dict: JSONDict) -> bytes:
        """Serialize event to JSON bytes."""
        return json.dumps(event_dict, default=str).encode("utf-8")

    def _deserialize_event(self, data: bytes) -> Optional[HITLEvent]:
        """Deserialize event from JSON bytes."""
        try:
            event_dict = json.loads(data.decode("utf-8"))
            return HITLEvent.from_dict(event_dict)
        except Exception as e:
            logger.error(f"Failed to deserialize event: {self._sanitize_error(e)}")
            return None

    # =========================================================================
    # Utilities
    # =========================================================================

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for logging (remove passwords)."""
        if "@" in url:
            parts = url.split("@")
            return f"***@{parts[-1]}"
        return url

    def _sanitize_error(self, error: Exception) -> str:
        """Sanitize error message for logging (remove sensitive data)."""
        error_msg = str(error)
        error_msg = re.sub(r"bootstrap_servers='[^']+'", "bootstrap_servers='REDACTED'", error_msg)
        error_msg = re.sub(r"password='[^']+'", "password='REDACTED'", error_msg)
        error_msg = re.sub(r"sasl_plain_password='[^']+'", "password='REDACTED'", error_msg)
        return error_msg

    @property
    def is_running(self) -> bool:
        """Check if client is running."""
        return self._running

    @property
    def topics(self) -> List[str]:
        """Get list of HITL topic names."""
        return HITLTopic.all_topics()


# =============================================================================
# Singleton Instance Management
# =============================================================================

_kafka_client: Optional[HITLKafkaClient] = None


def get_kafka_client() -> HITLKafkaClient:
    """
    Get the global HITLKafkaClient instance.

    Returns:
        The singleton HITLKafkaClient instance

    Raises:
        KafkaNotAvailableError: If aiokafka is not installed
    """
    global _kafka_client
    if _kafka_client is None:
        _kafka_client = HITLKafkaClient()
    return _kafka_client


async def initialize_kafka_client(
    bootstrap_servers: Optional[str] = None,
    client_id: str = "hitl-approvals",
    auto_create_topics: bool = True,
    start: bool = True,
) -> HITLKafkaClient:
    """
    Initialize and optionally start the global Kafka client.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        client_id: Client identifier
        auto_create_topics: Whether to create topics on startup
        start: Whether to start the client

    Returns:
        The initialized HITLKafkaClient
    """
    global _kafka_client

    _kafka_client = HITLKafkaClient(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
        auto_create_topics=auto_create_topics,
    )

    if start:
        await _kafka_client.start()

    return _kafka_client


async def close_kafka_client() -> None:
    """Close and cleanup the global Kafka client."""
    global _kafka_client

    if _kafka_client:
        await _kafka_client.stop()
        _kafka_client = None


def reset_kafka_client() -> None:
    """
    Reset the global HITLKafkaClient instance.

    Used primarily for test isolation.
    """
    global _kafka_client
    _kafka_client = None
