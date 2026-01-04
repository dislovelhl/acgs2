"""
ACGS-2 Feedback Handler Module
Constitutional Hash: cdd01ef066bc6cf2

Implements user feedback collection and storage for governance decision quality.
Supports feedback persistence to PostgreSQL and event publishing to Kafka.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# Optional Kafka support
try:
    from aiokafka import AIOKafkaProducer

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configuration from environment
POSTGRES_ML_HOST = os.getenv("POSTGRES_ML_HOST", "localhost")
POSTGRES_ML_PORT = int(os.getenv("POSTGRES_ML_PORT", "5432"))
POSTGRES_ML_DB = os.getenv("POSTGRES_ML_DB", "mlflow_db")
POSTGRES_ML_USER = os.getenv("POSTGRES_ML_USER", "mlflow")
POSTGRES_ML_PASSWORD = os.getenv("POSTGRES_ML_PASSWORD", "mlflow_password")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC_FEEDBACK = os.getenv("KAFKA_TOPIC_FEEDBACK", "governance.feedback.v1")


class FeedbackType(str, Enum):
    """Type of feedback provided by user."""

    POSITIVE = "positive"  # Thumbs up - decision was correct
    NEGATIVE = "negative"  # Thumbs down - decision was incorrect
    NEUTRAL = "neutral"  # No opinion
    CORRECTION = "correction"  # User provides explicit correction


class OutcomeStatus(str, Enum):
    """Status of the governance decision outcome."""

    SUCCESS = "success"  # Decision led to successful outcome
    FAILURE = "failure"  # Decision led to failed outcome
    PARTIAL = "partial"  # Decision led to partial success
    UNKNOWN = "unknown"  # Outcome not yet determined


# Pydantic Models for API Validation


class FeedbackEvent(BaseModel):
    """
    User feedback event for a governance decision.

    Captures user feedback (thumbs up/down, outcome confirmation) on governance
    decisions made by the model. Used for continuous learning and model improvement.
    """

    decision_id: str = Field(
        ...,
        description="Unique identifier of the governance decision being rated",
        min_length=1,
        max_length=255,
    )

    feedback_type: FeedbackType = Field(
        ...,
        description="Type of feedback: positive, negative, neutral, or correction",
    )

    outcome: OutcomeStatus = Field(
        default=OutcomeStatus.UNKNOWN,
        description="Outcome status of the decision: success, failure, partial, or unknown",
    )

    user_id: Optional[str] = Field(
        default=None,
        description="Identifier of the user providing feedback",
        max_length=255,
    )

    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant deployments",
        max_length=255,
    )

    comment: Optional[str] = Field(
        default=None,
        description="Optional user comment explaining the feedback",
        max_length=2000,
    )

    correction_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explicit correction data if feedback_type is 'correction'",
    )

    features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Feature values at the time of the decision for training",
    )

    actual_impact: Optional[float] = Field(
        default=None,
        description="Actual impact score observed (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the feedback event",
    )

    @field_validator("decision_id")
    @classmethod
    def validate_decision_id(cls, v: str) -> str:
        """Validate decision_id is not empty and has no leading/trailing whitespace."""
        if not v or not v.strip():
            raise ValueError("decision_id cannot be empty or whitespace only")
        return v.strip()

    @model_validator(mode="after")
    def validate_correction_data(self) -> "FeedbackEvent":
        """Validate correction_data is provided when feedback_type is correction."""
        if self.feedback_type == FeedbackType.CORRECTION and not self.correction_data:
            logger.warning(
                f"feedback_type is 'correction' but no correction_data provided "
                f"for decision_id={self.decision_id}"
            )
        return self


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""

    feedback_id: str = Field(..., description="Unique identifier for the feedback event")
    decision_id: str = Field(..., description="The decision ID the feedback was for")
    status: str = Field(..., description="Status of the feedback submission")
    timestamp: str = Field(..., description="ISO timestamp of when feedback was received")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional response details"
    )


class FeedbackBatchRequest(BaseModel):
    """Request model for batch feedback submission."""

    events: List[FeedbackEvent] = Field(
        ...,
        description="List of feedback events to submit",
        min_length=1,
        max_length=100,
    )


class FeedbackBatchResponse(BaseModel):
    """Response model for batch feedback submission."""

    total: int = Field(..., description="Total number of events submitted")
    accepted: int = Field(..., description="Number of events successfully processed")
    rejected: int = Field(..., description="Number of events that failed processing")
    feedback_ids: List[str] = Field(..., description="IDs of accepted feedback events")
    errors: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Details of rejected events"
    )


class FeedbackQueryParams(BaseModel):
    """Query parameters for feedback retrieval."""

    decision_id: Optional[str] = Field(default=None, description="Filter by decision ID")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    tenant_id: Optional[str] = Field(default=None, description="Filter by tenant ID")
    feedback_type: Optional[FeedbackType] = Field(
        default=None, description="Filter by feedback type"
    )
    outcome: Optional[OutcomeStatus] = Field(default=None, description="Filter by outcome status")
    start_date: Optional[datetime] = Field(default=None, description="Filter by start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter by end date")
    limit: int = Field(default=100, description="Maximum number of results", ge=1, le=1000)
    offset: int = Field(default=0, description="Number of results to skip", ge=0)


# Internal Data Classes


@dataclass
class StoredFeedbackEvent:
    """Internal representation of a stored feedback event."""

    id: str
    decision_id: str
    feedback_type: FeedbackType
    outcome: OutcomeStatus
    user_id: Optional[str]
    tenant_id: Optional[str]
    comment: Optional[str]
    correction_data: Optional[Dict[str, Any]]
    features: Optional[Dict[str, Any]]
    actual_impact: Optional[float]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    processed: bool = False
    published_to_kafka: bool = False


@dataclass
class FeedbackStats:
    """Statistics for feedback events."""

    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    correction_count: int = 0
    success_rate: float = 0.0
    average_impact: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# Database Schema


FEEDBACK_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(50) NOT NULL,
    outcome VARCHAR(50) NOT NULL DEFAULT 'unknown',
    user_id VARCHAR(255),
    tenant_id VARCHAR(255),
    comment TEXT,
    correction_data JSONB,
    features JSONB,
    actual_impact FLOAT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    published_to_kafka BOOLEAN DEFAULT FALSE,

    -- Indexes for common queries
    CONSTRAINT valid_feedback_type CHECK (feedback_type IN ('positive', 'negative', 'neutral', 'correction')),
    CONSTRAINT valid_outcome CHECK (outcome IN ('success', 'failure', 'partial', 'unknown')),
    CONSTRAINT valid_actual_impact CHECK (actual_impact IS NULL OR (actual_impact >= 0.0 AND actual_impact <= 1.0))
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_feedback_decision_id ON feedback_events(decision_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback_events(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_tenant_id ON feedback_events(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback_events(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback_events(processed) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_events(feedback_type);
"""


class FeedbackHandler:
    """
    Handles user feedback collection and storage for governance decisions.

    Provides functionality to:
    - Store feedback events in PostgreSQL
    - Retrieve and query feedback history
    - Calculate feedback statistics
    - Publish events to Kafka (via integration with FeedbackKafkaPublisher)
    """

    def __init__(
        self,
        db_connection: Optional[Any] = None,
        auto_publish_kafka: bool = False,
    ):
        """
        Initialize the feedback handler.

        Args:
            db_connection: Optional database connection (creates new if None)
            auto_publish_kafka: Whether to automatically publish to Kafka on store
        """
        self._db_connection = db_connection
        self._auto_publish_kafka = auto_publish_kafka
        self._kafka_publisher: Optional[Any] = None
        self._initialized = False
        self._memory_store: List[StoredFeedbackEvent] = []  # Fallback for testing

    def _get_db_connection(self) -> Any:
        """Get or create a database connection."""
        if self._db_connection is not None:
            return self._db_connection

        try:
            import psycopg2

            self._db_connection = psycopg2.connect(
                host=POSTGRES_ML_HOST,
                port=POSTGRES_ML_PORT,
                database=POSTGRES_ML_DB,
                user=POSTGRES_ML_USER,
                password=POSTGRES_ML_PASSWORD,
            )
            return self._db_connection

        except ImportError:
            logger.warning("psycopg2 not available, using in-memory storage")
            return None
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}, using in-memory storage")
            return None

    def initialize_schema(self) -> bool:
        """
        Initialize the database schema.

        Returns:
            True if schema was created successfully, False otherwise
        """
        conn = self._get_db_connection()
        if conn is None:
            logger.warning("No database connection, schema initialization skipped")
            self._initialized = True
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute(FEEDBACK_TABLE_SCHEMA)
            conn.commit()
            self._initialized = True
            logger.info("Feedback database schema initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize feedback schema: {e}")
            conn.rollback()
            return False

    def store_feedback(self, event: FeedbackEvent) -> FeedbackResponse:
        """
        Store a feedback event.

        Args:
            event: FeedbackEvent to store

        Returns:
            FeedbackResponse with submission status
        """
        feedback_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Create stored event
        stored_event = StoredFeedbackEvent(
            id=feedback_id,
            decision_id=event.decision_id,
            feedback_type=event.feedback_type,
            outcome=event.outcome,
            user_id=event.user_id,
            tenant_id=event.tenant_id,
            comment=event.comment,
            correction_data=event.correction_data,
            features=event.features,
            actual_impact=event.actual_impact,
            metadata=event.metadata,
            created_at=timestamp,
        )

        # Try to store in database
        conn = self._get_db_connection()
        if conn is not None:
            try:
                self._store_to_database(conn, stored_event)
                logger.info(f"Stored feedback {feedback_id} for decision {event.decision_id}")
            except Exception as e:
                logger.error(f"Failed to store feedback to database: {e}")
                # Fall back to memory store
                self._memory_store.append(stored_event)
        else:
            # Use memory store
            self._memory_store.append(stored_event)
            logger.debug(f"Stored feedback {feedback_id} in memory")

        # Auto-publish to Kafka if enabled
        if self._auto_publish_kafka and self._kafka_publisher:
            try:
                self._kafka_publisher.publish(stored_event)
                stored_event.published_to_kafka = True
            except Exception as e:
                logger.error(f"Failed to publish feedback to Kafka: {e}")

        return FeedbackResponse(
            feedback_id=feedback_id,
            decision_id=event.decision_id,
            status="accepted",
            timestamp=timestamp.isoformat(),
            details={
                "feedback_type": event.feedback_type.value,
                "outcome": event.outcome.value,
            },
        )

    def _store_to_database(self, conn: Any, event: StoredFeedbackEvent) -> None:
        """Store event to PostgreSQL database."""
        import json

        query = """
            INSERT INTO feedback_events (
                id, decision_id, feedback_type, outcome, user_id, tenant_id,
                comment, correction_data, features, actual_impact, metadata,
                created_at, processed, published_to_kafka
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    event.id,
                    event.decision_id,
                    event.feedback_type.value,
                    event.outcome.value,
                    event.user_id,
                    event.tenant_id,
                    event.comment,
                    json.dumps(event.correction_data) if event.correction_data else None,
                    json.dumps(event.features) if event.features else None,
                    event.actual_impact,
                    json.dumps(event.metadata) if event.metadata else None,
                    event.created_at,
                    event.processed,
                    event.published_to_kafka,
                ),
            )
        conn.commit()

    def store_batch(self, batch: FeedbackBatchRequest) -> FeedbackBatchResponse:
        """
        Store a batch of feedback events.

        Args:
            batch: FeedbackBatchRequest containing events

        Returns:
            FeedbackBatchResponse with results
        """
        accepted: List[str] = []
        errors: List[Dict[str, str]] = []

        for event in batch.events:
            try:
                response = self.store_feedback(event)
                accepted.append(response.feedback_id)
            except Exception as e:
                errors.append(
                    {
                        "decision_id": event.decision_id,
                        "error": str(e),
                    }
                )

        return FeedbackBatchResponse(
            total=len(batch.events),
            accepted=len(accepted),
            rejected=len(errors),
            feedback_ids=accepted,
            errors=errors if errors else None,
        )

    def get_feedback(
        self,
        decision_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StoredFeedbackEvent]:
        """
        Retrieve feedback events.

        Args:
            decision_id: Optional filter by decision ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of StoredFeedbackEvent
        """
        conn = self._get_db_connection()
        if conn is None:
            # Return from memory store
            events = self._memory_store
            if decision_id:
                events = [e for e in events if e.decision_id == decision_id]
            return events[offset : offset + limit]

        try:
            return self._query_database(conn, decision_id, limit, offset)
        except Exception as e:
            logger.error(f"Failed to query feedback: {e}")
            return []

    def _query_database(
        self,
        conn: Any,
        decision_id: Optional[str],
        limit: int,
        offset: int,
    ) -> List[StoredFeedbackEvent]:
        """Query feedback events from database."""
        query = """
            SELECT id, decision_id, feedback_type, outcome, user_id, tenant_id,
                   comment, correction_data, features, actual_impact, metadata,
                   created_at, processed, published_to_kafka
            FROM feedback_events
        """

        params: List[Any] = []
        if decision_id:
            query += " WHERE decision_id = %s"
            params.append(decision_id)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row: tuple) -> StoredFeedbackEvent:
        """Convert database row to StoredFeedbackEvent."""
        return StoredFeedbackEvent(
            id=str(row[0]),
            decision_id=row[1],
            feedback_type=FeedbackType(row[2]),
            outcome=OutcomeStatus(row[3]),
            user_id=row[4],
            tenant_id=row[5],
            comment=row[6],
            correction_data=row[7],
            features=row[8],
            actual_impact=row[9],
            metadata=row[10],
            created_at=row[11],
            processed=row[12],
            published_to_kafka=row[13],
        )

    def get_feedback_stats(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> FeedbackStats:
        """
        Get feedback statistics.

        Args:
            tenant_id: Optional filter by tenant
            start_date: Optional start of period
            end_date: Optional end of period

        Returns:
            FeedbackStats with aggregated statistics
        """
        conn = self._get_db_connection()

        if conn is None:
            # Calculate from memory store
            return self._calculate_memory_stats(tenant_id, start_date, end_date)

        try:
            return self._calculate_db_stats(conn, tenant_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to calculate stats: {e}")
            return FeedbackStats()

    def _calculate_memory_stats(
        self,
        tenant_id: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> FeedbackStats:
        """Calculate stats from memory store."""
        events = self._memory_store

        # Apply filters
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if start_date:
            events = [e for e in events if e.created_at >= start_date]
        if end_date:
            events = [e for e in events if e.created_at <= end_date]

        if not events:
            return FeedbackStats(period_start=start_date, period_end=end_date)

        positive = sum(1 for e in events if e.feedback_type == FeedbackType.POSITIVE)
        negative = sum(1 for e in events if e.feedback_type == FeedbackType.NEGATIVE)
        neutral = sum(1 for e in events if e.feedback_type == FeedbackType.NEUTRAL)
        correction = sum(1 for e in events if e.feedback_type == FeedbackType.CORRECTION)
        success = sum(1 for e in events if e.outcome == OutcomeStatus.SUCCESS)

        impacts = [e.actual_impact for e in events if e.actual_impact is not None]
        avg_impact = sum(impacts) / len(impacts) if impacts else None

        return FeedbackStats(
            total_count=len(events),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            correction_count=correction,
            success_rate=success / len(events) if events else 0.0,
            average_impact=avg_impact,
            period_start=start_date,
            period_end=end_date,
        )

    def _calculate_db_stats(
        self,
        conn: Any,
        tenant_id: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> FeedbackStats:
        """Calculate stats from database."""
        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN feedback_type = 'neutral' THEN 1 ELSE 0 END) as neutral,
                SUM(CASE WHEN feedback_type = 'correction' THEN 1 ELSE 0 END) as correction,
                SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as success_count,
                AVG(actual_impact) as avg_impact
            FROM feedback_events
            WHERE 1=1
        """

        params: List[Any] = []
        if tenant_id:
            query += " AND tenant_id = %s"
            params.append(tenant_id)
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)

        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()

        if not row or row[0] == 0:
            return FeedbackStats(period_start=start_date, period_end=end_date)

        return FeedbackStats(
            total_count=row[0],
            positive_count=row[1],
            negative_count=row[2],
            neutral_count=row[3],
            correction_count=row[4],
            success_rate=row[5] / row[0] if row[0] > 0 else 0.0,
            average_impact=float(row[6]) if row[6] is not None else None,
            period_start=start_date,
            period_end=end_date,
        )

    def mark_as_processed(self, feedback_ids: List[str]) -> int:
        """
        Mark feedback events as processed.

        Args:
            feedback_ids: List of feedback IDs to mark

        Returns:
            Number of events marked
        """
        if not feedback_ids:
            return 0

        conn = self._get_db_connection()
        if conn is None:
            # Update memory store
            count = 0
            for event in self._memory_store:
                if event.id in feedback_ids:
                    event.processed = True
                    count += 1
            return count

        try:
            query = """
                UPDATE feedback_events
                SET processed = TRUE
                WHERE id = ANY(%s)
            """
            with conn.cursor() as cursor:
                cursor.execute(query, (feedback_ids,))
                count = cursor.rowcount
            conn.commit()
            return count

        except Exception as e:
            logger.error(f"Failed to mark feedback as processed: {e}")
            conn.rollback()
            return 0

    def get_unprocessed_feedback(self, limit: int = 100) -> List[StoredFeedbackEvent]:
        """
        Get unprocessed feedback events for training.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of unprocessed StoredFeedbackEvent
        """
        conn = self._get_db_connection()
        if conn is None:
            return [e for e in self._memory_store if not e.processed][:limit]

        try:
            query = """
                SELECT id, decision_id, feedback_type, outcome, user_id, tenant_id,
                       comment, correction_data, features, actual_impact, metadata,
                       created_at, processed, published_to_kafka
                FROM feedback_events
                WHERE processed = FALSE
                ORDER BY created_at ASC
                LIMIT %s
            """
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

            return [self._row_to_event(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get unprocessed feedback: {e}")
            return []

    def set_kafka_publisher(self, publisher: Any) -> None:
        """
        Set the Kafka publisher for feedback events.

        Args:
            publisher: Kafka publisher instance with publish(event) method
        """
        self._kafka_publisher = publisher
        logger.info("Kafka publisher configured for feedback handler")

    def close(self) -> None:
        """Close database connection and clean up resources."""
        if self._db_connection is not None:
            try:
                self._db_connection.close()
                logger.info("Feedback handler database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
            finally:
                self._db_connection = None


class FeedbackKafkaPublisher:
    """
    Kafka publisher for feedback events.

    Publishes feedback events to the governance.feedback.v1 topic for
    downstream processing by ML training pipelines and analytics systems.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        client_id: str = "acgs2-feedback-publisher",
    ):
        """
        Initialize the Kafka publisher for feedback events.

        Args:
            bootstrap_servers: Kafka bootstrap servers (defaults to KAFKA_BOOTSTRAP env var)
            topic: Kafka topic to publish to (defaults to KAFKA_TOPIC_FEEDBACK env var)
            client_id: Client identifier for Kafka connection
        """
        self.bootstrap_servers = bootstrap_servers or KAFKA_BOOTSTRAP
        self.topic = topic or KAFKA_TOPIC_FEEDBACK
        self.client_id = client_id
        self._producer: Optional[Any] = None
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> bool:
        """
        Start the Kafka producer.

        Returns:
            True if producer started successfully, False otherwise
        """
        if not KAFKA_AVAILABLE:
            logger.error(
                "aiokafka not installed. FeedbackKafkaPublisher unavailable. "
                "Install with: pip install aiokafka"
            )
            return False

        async with self._lock:
            if self._running:
                logger.debug("FeedbackKafkaPublisher already running")
                return True

            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=self.client_id,
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks="all",  # Ensure durability
                    retry_backoff_ms=500,
                )
                await self._producer.start()
                self._running = True
                logger.info(
                    f"FeedbackKafkaPublisher started: servers={self._sanitize_bootstrap(self.bootstrap_servers)}, "
                    f"topic={self.topic}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to start FeedbackKafkaPublisher: {self._sanitize_error(e)}")
                self._producer = None
                return False

    async def stop(self) -> None:
        """Stop the Kafka producer and clean up resources."""
        async with self._lock:
            if not self._running:
                return

            self._running = False
            if self._producer:
                try:
                    await self._producer.flush()
                    await self._producer.stop()
                    logger.info("FeedbackKafkaPublisher stopped")
                except Exception as e:
                    logger.warning(
                        f"Error stopping FeedbackKafkaPublisher: {self._sanitize_error(e)}"
                    )
                finally:
                    self._producer = None

    async def publish(self, event: StoredFeedbackEvent) -> bool:
        """
        Publish a feedback event to Kafka.

        Args:
            event: The StoredFeedbackEvent to publish

        Returns:
            True if published successfully, False otherwise
        """
        if not self._running or not self._producer:
            logger.warning("FeedbackKafkaPublisher not running, cannot publish event")
            return False

        try:
            # Convert event to dict for serialization
            event_dict = self._serialize_event(event)

            # Use decision_id as partition key to ensure ordering per decision
            key = event.decision_id

            await self._producer.send_and_wait(
                self.topic,
                value=event_dict,
                key=key,
            )

            logger.debug(
                f"Published feedback event {event.id} for decision {event.decision_id} "
                f"to topic {self.topic}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish feedback event {event.id}: {self._sanitize_error(e)}")
            return False

    async def publish_batch(self, events: List[StoredFeedbackEvent]) -> Dict[str, bool]:
        """
        Publish multiple feedback events to Kafka.

        Args:
            events: List of StoredFeedbackEvent to publish

        Returns:
            Dict mapping event IDs to publish success status
        """
        results: Dict[str, bool] = {}

        for event in events:
            success = await self.publish(event)
            results[event.id] = success

        return results

    def _serialize_event(self, event: StoredFeedbackEvent) -> Dict[str, Any]:
        """
        Serialize a StoredFeedbackEvent to a dictionary for Kafka.

        Args:
            event: The event to serialize

        Returns:
            Dict representation of the event
        """
        # Convert dataclass to dict
        event_dict = {
            "id": event.id,
            "decision_id": event.decision_id,
            "feedback_type": (
                event.feedback_type.value
                if isinstance(event.feedback_type, Enum)
                else event.feedback_type
            ),
            "outcome": event.outcome.value if isinstance(event.outcome, Enum) else event.outcome,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id,
            "comment": event.comment,
            "correction_data": event.correction_data,
            "features": event.features,
            "actual_impact": event.actual_impact,
            "metadata": event.metadata,
            "created_at": (
                event.created_at.isoformat()
                if isinstance(event.created_at, datetime)
                else event.created_at
            ),
            "processed": event.processed,
            "published_to_kafka": True,  # Mark as published
            "schema_version": "v1",  # Add schema version for future compatibility
        }

        return event_dict

    def _sanitize_error(self, error: Exception) -> str:
        """Strip sensitive metadata from error messages."""
        error_msg = str(error)
        # Remove potential bootstrap server details if they contain secrets
        error_msg = re.sub(r"bootstrap_servers='[^']+'", "bootstrap_servers='REDACTED'", error_msg)
        error_msg = re.sub(r"password='[^']+'", "password='REDACTED'", error_msg)
        return error_msg

    def _sanitize_bootstrap(self, servers: str) -> str:
        """Sanitize bootstrap servers for logging (show host, hide port details)."""
        # Only show host names, not detailed connection info
        parts = servers.split(",")
        sanitized = []
        for part in parts:
            host = part.split(":")[0] if ":" in part else part
            sanitized.append(f"{host}:****")
        return ",".join(sanitized)

    @property
    def is_running(self) -> bool:
        """Check if the publisher is running."""
        return self._running

    def publish_sync(self, event: StoredFeedbackEvent) -> bool:
        """
        Synchronous wrapper to publish a feedback event.

        This method is intended for use in synchronous code paths.
        It creates an event loop if necessary.

        Args:
            event: The StoredFeedbackEvent to publish

        Returns:
            True if published successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, schedule the coroutine
                asyncio.ensure_future(self.publish(event))
                return False  # Can't wait for result in running loop
            else:
                return loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.publish(event))


# Module-level Kafka publisher instance
_feedback_kafka_publisher: Optional[FeedbackKafkaPublisher] = None


async def get_feedback_kafka_publisher() -> FeedbackKafkaPublisher:
    """
    Get or create the global FeedbackKafkaPublisher instance.

    Returns:
        Initialized FeedbackKafkaPublisher
    """
    global _feedback_kafka_publisher

    if _feedback_kafka_publisher is None:
        _feedback_kafka_publisher = FeedbackKafkaPublisher()
        await _feedback_kafka_publisher.start()

    return _feedback_kafka_publisher


async def publish_feedback_event(event: StoredFeedbackEvent) -> bool:
    """
    Publish a feedback event using the global publisher.

    Args:
        event: StoredFeedbackEvent to publish

    Returns:
        True if published successfully, False otherwise
    """
    publisher = await get_feedback_kafka_publisher()
    return await publisher.publish(event)


# Module-level convenience functions

_feedback_handler: Optional[FeedbackHandler] = None


def get_feedback_handler() -> FeedbackHandler:
    """
    Get the global feedback handler instance.

    Returns:
        Initialized FeedbackHandler
    """
    global _feedback_handler

    if _feedback_handler is None:
        _feedback_handler = FeedbackHandler()

    return _feedback_handler


def submit_feedback(event: Union[FeedbackEvent, Dict[str, Any]]) -> FeedbackResponse:
    """
    Submit a feedback event using the global handler.

    Args:
        event: FeedbackEvent or dict with event data

    Returns:
        FeedbackResponse with submission status
    """
    handler = get_feedback_handler()

    if isinstance(event, dict):
        event = FeedbackEvent(**event)

    return handler.store_feedback(event)


def get_feedback_for_decision(decision_id: str) -> List[StoredFeedbackEvent]:
    """
    Get all feedback for a specific decision.

    Args:
        decision_id: The decision ID to query

    Returns:
        List of StoredFeedbackEvent for the decision
    """
    handler = get_feedback_handler()
    return handler.get_feedback(decision_id=decision_id)


# Export key classes and functions
__all__ = [
    # Enums
    "FeedbackType",
    "OutcomeStatus",
    # Pydantic Models
    "FeedbackEvent",
    "FeedbackResponse",
    "FeedbackBatchRequest",
    "FeedbackBatchResponse",
    "FeedbackQueryParams",
    # Data Classes
    "StoredFeedbackEvent",
    "FeedbackStats",
    # Handler Class
    "FeedbackHandler",
    # Kafka Publisher
    "FeedbackKafkaPublisher",
    "KAFKA_AVAILABLE",
    # Schema
    "FEEDBACK_TABLE_SCHEMA",
    # Convenience Functions
    "get_feedback_handler",
    "submit_feedback",
    "get_feedback_for_decision",
    "get_feedback_kafka_publisher",
    "publish_feedback_event",
]
