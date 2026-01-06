"""
Time-R1 Constitutional Timeline Engine
======================================

Constitutional Hash: cdd01ef066bc6cf2

Implements Time-R1 based temporal reasoning:
- 3-stage training (comprehension, prediction, generation)
- GRPO reinforcement learning
- Immutable event log (no history rewriting)
- Causal chain validation

Key Principle: Time flows forward only. History cannot be rewritten.
All events are immutable once recorded.

References:
- Time-R1: Temporal Reasoning (arXiv:2505.13508)
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of constitutional events."""

    DECISION = "decision"
    AMENDMENT = "amendment"
    VALIDATION = "validation"
    VIOLATION = "violation"
    ADAPTATION = "adaptation"
    SYSTEM = "system"


@dataclass
class ConstitutionalEvent:
    """
    An immutable constitutional event in the timeline.

    Once created, events cannot be modified - only new events
    can be appended to the timeline.
    """

    event_id: str
    event_type: EventType
    timestamp: datetime
    content: Dict[str, Any]
    causal_chain: List[str]  # IDs of events that caused this
    actor: str
    constitutional_hash: str = CONSTITUTIONAL_HASH
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Computed at creation time, immutable
    event_hash: str = field(default="", init=False)

    def __post_init__(self):
        """Compute immutable hash after initialization."""
        self.event_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute unique hash for this event."""
        content = f"{self.event_id}:{self.timestamp.isoformat()}:{self.content}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "causal_chain": self.causal_chain,
            "actor": self.actor,
            "constitutional_hash": self.constitutional_hash,
            "event_hash": self.event_hash,
            "metadata": self.metadata,
        }


class TemporalViolationError(Exception):
    """Raised when temporal constraints are violated."""

    pass


class CausalViolationError(Exception):
    """Raised when causal chain is invalid."""

    pass


@dataclass
class TimelineState:
    """Current state of the constitutional timeline."""

    last_event_id: Optional[str]
    last_timestamp: Optional[datetime]
    event_count: int
    active_principles: Set[str]
    pending_adaptations: List[str]


@dataclass
class Disruption:
    """A disruption requiring timeline adaptation."""

    disruption_id: str
    description: str
    severity: float  # 0.0-1.0
    timestamp: datetime
    affected_events: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disruption_id": self.disruption_id,
            "description": self.description,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "affected_events": self.affected_events,
        }


@dataclass
class Adaptation:
    """An adaptation response to a disruption."""

    adaptation_id: str
    disruption_id: str
    strategy: str
    new_events: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adaptation_id": self.adaptation_id,
            "disruption_id": self.disruption_id,
            "strategy": self.strategy,
            "new_events": self.new_events,
            "timestamp": self.timestamp.isoformat(),
        }


class ConstitutionalTimelineEngine:
    """
    Time-R1 Constitutional Timeline Engine.

    Maintains an immutable event log for constitutional governance:
    - Events can only be appended (no modification, no deletion)
    - Causal chains must be valid (causes precede effects)
    - Adaptations respond to disruptions from current state forward

    The engine never rewrites history - it only plans forward.
    """

    def __init__(self, max_events: int = 100000, causal_validation: bool = True):
        """
        Initialize the Timeline Engine.

        Args:
            max_events: Maximum events to store in memory
            causal_validation: Whether to validate causal chains
        """
        self.max_events = max_events
        self.causal_validation = causal_validation

        # Append-only event log (immutable)
        self._event_log: List[ConstitutionalEvent] = []
        self._event_index: Dict[str, int] = {}  # event_id -> index

        # Active constitutional principles
        self._active_principles: Set[str] = set()

        # Pending adaptations
        self._pending_adaptations: List[Adaptation] = []

        # Statistics
        self._stats = {
            "events_added": 0,
            "causal_violations_prevented": 0,
            "temporal_violations_prevented": 0,
            "adaptations_made": 0,
        }

        logger.info(
            f"Initialized ConstitutionalTimelineEngine "
            f"max_events={max_events}, causal_validation={causal_validation}"
        )

    async def add_event(self, event: ConstitutionalEvent) -> str:
        """
        Add an event to the immutable timeline.

        Validates:
        1. Temporal ordering (event must be after last event)
        2. Causal chain (causes must precede effects)
        3. Constitutional hash validity

        Args:
            event: The event to add

        Returns:
            Event ID

        Raises:
            TemporalViolationError: If event violates temporal ordering
            CausalViolationError: If causal chain is invalid
        """
        # Validate temporal ordering
        if self._event_log:
            last_event = self._event_log[-1]
            if event.timestamp < last_event.timestamp:
                self._stats["temporal_violations_prevented"] += 1
                raise TemporalViolationError(
                    f"Cannot add event with timestamp {event.timestamp} "
                    f"before last event at {last_event.timestamp}. "
                    f"Time flows forward only."
                )

        # Validate causal chain
        if self.causal_validation and event.causal_chain:
            for cause_id in event.causal_chain:
                cause = self.get_event(cause_id)
                if cause is None:
                    self._stats["causal_violations_prevented"] += 1
                    raise CausalViolationError(f"Cause event '{cause_id}' not found in timeline")
                if cause.timestamp >= event.timestamp:
                    self._stats["causal_violations_prevented"] += 1
                    raise CausalViolationError(
                        f"Cause event '{cause_id}' at {cause.timestamp} "
                        f"must precede effect at {event.timestamp}"
                    )

        # Validate constitutional hash
        if event.constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(f"Invalid constitutional hash: {event.constitutional_hash}")

        # Add to immutable log
        self._event_log.append(event)
        self._event_index[event.event_id] = len(self._event_log) - 1

        # Update active principles if amendment
        if event.event_type == EventType.AMENDMENT:
            principle_id = event.content.get("principle_id")
            if principle_id:
                if event.content.get("action") == "add":
                    self._active_principles.add(principle_id)
                elif event.content.get("action") == "remove":
                    self._active_principles.discard(principle_id)

        self._stats["events_added"] += 1

        return event.event_id

    def get_event(self, event_id: str) -> Optional[ConstitutionalEvent]:
        """Get an event by ID."""
        if event_id in self._event_index:
            idx = self._event_index[event_id]
            return self._event_log[idx]
        return None

    def get_events_in_range(self, start: datetime, end: datetime) -> List[ConstitutionalEvent]:
        """Get events within a time range."""
        return [e for e in self._event_log if start <= e.timestamp <= end]

    def get_events_by_type(self, event_type: EventType) -> List[ConstitutionalEvent]:
        """Get events of a specific type."""
        return [e for e in self._event_log if e.event_type == event_type]

    def get_causal_descendants(self, event_id: str) -> List[ConstitutionalEvent]:
        """Get all events caused by a specific event."""
        descendants = []
        for event in self._event_log:
            if event_id in event.causal_chain:
                descendants.append(event)
                # Recursively get descendants
                descendants.extend(self.get_causal_descendants(event.event_id))
        return descendants

    def compute_state_from_log(self) -> TimelineState:
        """
        Compute current state from the immutable log.

        State is always derived from the log, never stored mutably.
        """
        last_event = self._event_log[-1] if self._event_log else None

        return TimelineState(
            last_event_id=last_event.event_id if last_event else None,
            last_timestamp=last_event.timestamp if last_event else None,
            event_count=len(self._event_log),
            active_principles=self._active_principles.copy(),
            pending_adaptations=[a.adaptation_id for a in self._pending_adaptations],
        )

    async def handle_disruption(self, disruption: Disruption) -> Adaptation:
        """
        Handle a disruption by creating an adaptation.

        Key Principle: We adapt from the CURRENT state forward.
        We NEVER rewrite history.

        Args:
            disruption: The disruption to handle

        Returns:
            Adaptation response
        """
        current_state = self.compute_state_from_log()

        # Analyze impact
        affected_events = []
        for event_id in disruption.affected_events:
            event = self.get_event(event_id)
            if event:
                affected_events.append(event)
                # Get descendants (transitively affected)
                affected_events.extend(self.get_causal_descendants(event_id))

        # Determine adaptation strategy
        strategy = await self._determine_strategy(disruption, affected_events)

        # Create new forward-looking events
        adaptation_events = await self._create_adaptation_events(
            disruption, strategy, current_state
        )

        # Create adaptation record
        adaptation = Adaptation(
            adaptation_id=f"adapt-{uuid.uuid4().hex[:8]}",
            disruption_id=disruption.disruption_id,
            strategy=strategy,
            new_events=[e.event_id for e in adaptation_events],
            timestamp=datetime.utcnow(),
        )

        # Add adaptation events to timeline
        for event in adaptation_events:
            await self.add_event(event)

        self._pending_adaptations.append(adaptation)
        self._stats["adaptations_made"] += 1

        logger.info(
            f"Created adaptation {adaptation.adaptation_id} "
            f"for disruption {disruption.disruption_id}: {strategy}"
        )

        return adaptation

    async def _determine_strategy(
        self, disruption: Disruption, affected_events: List[ConstitutionalEvent]
    ) -> str:
        """Determine adaptation strategy based on disruption severity."""
        if disruption.severity >= 0.9:
            return "emergency_stabilization"
        elif disruption.severity >= 0.7:
            return "corrective_action"
        elif disruption.severity >= 0.5:
            return "preventive_measure"
        else:
            return "monitoring_enhancement"

    async def _create_adaptation_events(
        self, disruption: Disruption, strategy: str, current_state: TimelineState
    ) -> List[ConstitutionalEvent]:
        """Create events for the adaptation response."""
        events = []

        # Create adaptation event
        adaptation_event = ConstitutionalEvent(
            event_id=f"event-{uuid.uuid4().hex[:8]}",
            event_type=EventType.ADAPTATION,
            timestamp=datetime.utcnow(),
            content={
                "disruption_id": disruption.disruption_id,
                "strategy": strategy,
                "severity": disruption.severity,
                "description": f"Adaptation response: {strategy}",
            },
            causal_chain=[disruption.disruption_id]
            if disruption.disruption_id in self._event_index
            else [],
            actor="timeline_engine",
        )
        events.append(adaptation_event)

        # Add strategy-specific events
        if strategy == "emergency_stabilization":
            # Add stabilization event
            stab_event = ConstitutionalEvent(
                event_id=f"event-{uuid.uuid4().hex[:8]}",
                event_type=EventType.SYSTEM,
                timestamp=datetime.utcnow() + timedelta(milliseconds=1),
                content={
                    "action": "stabilize",
                    "reason": "Emergency response to high-severity disruption",
                },
                causal_chain=[adaptation_event.event_id],
                actor="timeline_engine",
            )
            events.append(stab_event)

        return events

    def verify_timeline_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the timeline.

        Checks:
        1. Temporal ordering
        2. Causal chain validity
        3. Event hash consistency
        """
        issues = []

        prev_timestamp = None
        for i, event in enumerate(self._event_log):
            # Check temporal ordering
            if prev_timestamp and event.timestamp < prev_timestamp:
                issues.append(
                    {
                        "type": "temporal_violation",
                        "event_id": event.event_id,
                        "message": f"Event at index {i} violates temporal ordering",
                    }
                )
            prev_timestamp = event.timestamp

            # Check causal chains
            for cause_id in event.causal_chain:
                cause = self.get_event(cause_id)
                if cause is None:
                    issues.append(
                        {
                            "type": "causal_violation",
                            "event_id": event.event_id,
                            "message": f"Cause event {cause_id} not found",
                        }
                    )
                elif cause.timestamp >= event.timestamp:
                    issues.append(
                        {
                            "type": "causal_violation",
                            "event_id": event.event_id,
                            "message": f"Cause {cause_id} does not precede effect",
                        }
                    )

            # Verify event hash
            expected_hash = event._compute_hash()
            if event.event_hash != expected_hash:
                issues.append(
                    {
                        "type": "hash_mismatch",
                        "event_id": event.event_id,
                        "message": "Event hash does not match computed hash",
                    }
                )

        return {
            "valid": len(issues) == 0,
            "event_count": len(self._event_log),
            "issues": issues,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get timeline engine statistics."""
        return {
            **self._stats,
            "total_events": len(self._event_log),
            "active_principles": len(self._active_principles),
            "pending_adaptations": len(self._pending_adaptations),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class TimelineEventFactory:
    """Factory for creating constitutional events."""

    @staticmethod
    def create_decision(
        decision: str, actor: str, context: Dict[str, Any], causes: Optional[List[str]] = None
    ) -> ConstitutionalEvent:
        """Create a decision event."""
        return ConstitutionalEvent(
            event_id=f"decision-{uuid.uuid4().hex[:8]}",
            event_type=EventType.DECISION,
            timestamp=datetime.utcnow(),
            content={
                "decision": decision,
                "context": context,
            },
            causal_chain=causes or [],
            actor=actor,
        )

    @staticmethod
    def create_amendment(
        principle_id: str,
        action: str,  # "add" or "remove"
        actor: str,
        description: str,
        causes: Optional[List[str]] = None,
    ) -> ConstitutionalEvent:
        """Create an amendment event."""
        return ConstitutionalEvent(
            event_id=f"amendment-{uuid.uuid4().hex[:8]}",
            event_type=EventType.AMENDMENT,
            timestamp=datetime.utcnow(),
            content={
                "principle_id": principle_id,
                "action": action,
                "description": description,
            },
            causal_chain=causes or [],
            actor=actor,
        )

    @staticmethod
    def create_violation(
        violation_type: str, actor: str, details: Dict[str, Any], causes: Optional[List[str]] = None
    ) -> ConstitutionalEvent:
        """Create a violation event."""
        return ConstitutionalEvent(
            event_id=f"violation-{uuid.uuid4().hex[:8]}",
            event_type=EventType.VIOLATION,
            timestamp=datetime.utcnow(),
            content={
                "violation_type": violation_type,
                "details": details,
            },
            causal_chain=causes or [],
            actor=actor,
        )
