"""
Time-R1 Engine for Constitutional AI Governance
===============================================

Constitutional Hash: cdd01ef066bc6cf2

Implements Time-R1 temporal reasoning engine:
- Immutable event log with causal validation
- Temporal consistency checking across governance decisions
- Event sourcing for constitutional state management

Design Principles:
- Every event is immutable and timestamped
- Causal ordering prevents temporal paradoxes
- Event log serves as constitutional audit trail
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of constitutional events."""
    POLICY_CREATED = "policy_created"
    POLICY_EXECUTED = "policy_executed"
    DECISION_MADE = "decision_made"
    VALIDATION_COMPLETED = "validation_completed"
    CONSTITUTIONAL_REVIEW = "constitutional_review"
    BRANCH_ACTION = "branch_action"
    CONSENSUS_ACHIEVED = "consensus_achieved"


class TemporalConsistency(Enum):
    """Temporal consistency states."""
    CONSISTENT = "consistent"
    CAUSALLY_INCONSISTENT = "causally_inconsistent"
    TEMPORALLY_INCONSISTENT = "temporally_inconsistent"
    MISSING_DEPENDENCIES = "missing_dependencies"


@dataclass
class ConstitutionalEvent:
    """An immutable constitutional event."""
    event_id: str
    event_type: EventType
    timestamp: float
    actor: str  # Which agent/branch caused this event
    payload: Dict[str, Any]

    # Causal metadata
    parent_events: Set[str] = field(default_factory=set)
    causal_hash: str = ""

    # Constitutional validation
    constitutional_hash: str = CONSTITUTIONAL_HASH
    validation_status: str = "pending"

    def __post_init__(self):
        if not self.event_id:
            self.event_id = hashlib.sha256(
                f"{self.event_type.value}_{self.timestamp}_{self.actor}_{str(self.payload)}".encode()
            ).hexdigest()[:16]

        if not self.causal_hash:
            self.causal_hash = self._compute_causal_hash()

    def _compute_causal_hash(self) -> str:
        """Compute causal hash including parent events."""
        content = f"{self.event_id}_{sorted(self.parent_events)}_{self.payload}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class TemporalState:
    """Snapshot of constitutional state at a point in time."""
    timestamp: float
    event_count: int
    active_policies: Set[str]
    pending_decisions: Set[str]
    branch_states: Dict[str, Dict[str, Any]]
    causal_frontier: Set[str]  # Latest events in causal order

    # Consistency validation
    consistency_status: TemporalConsistency = TemporalConsistency.CONSISTENT
    last_validation: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "event_count": self.event_count,
            "active_policies": list(self.active_policies),
            "pending_decisions": list(self.pending_decisions),
            "branch_states": self.branch_states,
            "causal_frontier": list(self.causal_frontier),
            "consistency_status": self.consistency_status.value,
            "last_validation": self.last_validation
        }


class TimeR1Engine:
    """
    Time-R1 Temporal Reasoning Engine.

    Provides immutable event sourcing with causal validation:
    - Every governance action creates an immutable event
    - Events are causally ordered to prevent paradoxes
    - Temporal queries enable governance analytics
    - Event log serves as constitutional audit trail
    """

    def __init__(self):
        self.events: Dict[str, ConstitutionalEvent] = {}
        self.event_log: List[ConstitutionalEvent] = []
        self.causal_graph: Dict[str, Set[str]] = {}  # event_id -> children

        # Temporal indexing
        self.events_by_time: List[ConstitutionalEvent] = []
        self.events_by_actor: Dict[str, List[ConstitutionalEvent]] = {}
        self.events_by_type: Dict[EventType, List[ConstitutionalEvent]] = {}

        # State snapshots
        self.state_snapshots: List[TemporalState] = []
        self.current_state: Optional[TemporalState] = None

        # Consistency checking
        self.consistency_cache: Dict[str, TemporalConsistency] = {}
        self.last_consistency_check: float = 0

        logger.info("Initialized Time-R1 Engine")

    async def record_event(
        self,
        event_type: EventType,
        actor: str,
        payload: Dict[str, Any],
        parent_events: Optional[Set[str]] = None
    ) -> ConstitutionalEvent:
        """
        Record a new constitutional event.

        Args:
            event_type: Type of event
            actor: Agent/branch that caused the event
            payload: Event data
            parent_events: Events this event depends on

        Returns:
            The recorded event
        """
        if parent_events is None:
            parent_events = set()

        # Validate parent events exist
        for parent_id in parent_events:
            if parent_id not in self.events:
                raise ValueError(f"Parent event {parent_id} does not exist")

        # Create event
        event = ConstitutionalEvent(
            event_id="",
            event_type=event_type,
            timestamp=time.time(),
            actor=actor,
            payload=payload,
            parent_events=parent_events
        )

        # Store event
        self.events[event.event_id] = event
        self.event_log.append(event)

        # Update causal graph
        for parent_id in parent_events:
            if parent_id not in self.causal_graph:
                self.causal_graph[parent_id] = set()
            self.causal_graph[parent_id].add(event.event_id)

        # Update indexes
        self._update_indexes(event)

        # Update current state
        await self._update_current_state(event)

        logger.debug(f"Recorded event {event.event_id} of type {event_type.value}")
        return event

    def _update_indexes(self, event: ConstitutionalEvent) -> None:
        """Update temporal indexes."""
        # Time index (maintain sorted order)
        self.events_by_time.append(event)
        self.events_by_time.sort(key=lambda e: e.timestamp)

        # Actor index
        if event.actor not in self.events_by_actor:
            self.events_by_actor[event.actor] = []
        self.events_by_actor[event.actor].append(event)

        # Type index
        if event.event_type not in self.events_by_type:
            self.events_by_type[event.event_type] = []
        self.events_by_type[event.event_type].append(event)

    async def _update_current_state(self, event: ConstitutionalEvent) -> None:
        """Update the current constitutional state."""
        if self.current_state is None:
            # Initialize state
            self.current_state = TemporalState(
                timestamp=event.timestamp,
                event_count=1,
                active_policies=set(),
                pending_decisions=set(),
                branch_states={},
                causal_frontier={event.event_id}
            )
        else:
            # Update existing state
            new_state = TemporalState(
                timestamp=event.timestamp,
                event_count=self.current_state.event_count + 1,
                active_policies=self.current_state.active_policies.copy(),
                pending_decisions=self.current_state.pending_decisions.copy(),
                branch_states=self.current_state.branch_states.copy(),
                causal_frontier=self.current_state.causal_frontier.copy()
            )

            # Update causal frontier
            new_state.causal_frontier.discard(*event.parent_events)
            new_state.causal_frontier.add(event.event_id)

            # Update domain-specific state
            await self._apply_event_to_state(new_state, event)

            self.current_state = new_state

        # Create snapshot every 100 events
        if len(self.event_log) % 100 == 0:
            self.state_snapshots.append(self.current_state)

    async def _apply_event_to_state(
        self,
        state: TemporalState,
        event: ConstitutionalEvent
    ) -> None:
        """Apply event effects to constitutional state."""
        if event.event_type == EventType.POLICY_CREATED:
            policy_id = event.payload.get("policy_id")
            if policy_id:
                state.active_policies.add(policy_id)

        elif event.event_type == EventType.POLICY_EXECUTED:
            policy_id = event.payload.get("policy_id")
            if policy_id and policy_id in state.pending_decisions:
                state.pending_decisions.remove(policy_id)

        elif event.event_type == EventType.DECISION_MADE:
            decision_id = event.payload.get("decision_id")
            if decision_id:
                state.pending_decisions.add(decision_id)

        elif event.event_type == EventType.BRANCH_ACTION:
            branch = event.payload.get("branch")
            action = event.payload.get("action")
            if branch:
                if branch not in state.branch_states:
                    state.branch_states[branch] = {}
                state.branch_states[branch][action] = event.timestamp

    async def validate_temporal_consistency(
        self,
        event: ConstitutionalEvent
    ) -> Tuple[TemporalConsistency, str]:
        """
        Validate temporal consistency of an event.

        Checks:
        - Parent events exist and are properly ordered
        - No causal paradoxes
        - Constitutional invariants maintained
        """
        # Check parent events exist
        for parent_id in event.parent_events:
            if parent_id not in self.events:
                return TemporalConsistency.MISSING_DEPENDENCIES, f"Parent event {parent_id} missing"

        # Check causal ordering (no cycles)
        if await self._has_causal_cycle(event):
            return TemporalConsistency.CAUSALLY_INCONSISTENT, "Causal cycle detected"

        # Check temporal ordering
        for parent_id in event.parent_events:
            parent_event = self.events[parent_id]
            if parent_event.timestamp >= event.timestamp:
                return TemporalConsistency.TEMPORALLY_INCONSISTENT, f"Parent event {parent_id} is not before child"

        # Check constitutional invariants
        if not await self._validate_constitutional_invariants(event):
            return TemporalConsistency.CAUSALLY_INCONSISTENT, "Constitutional invariants violated"

        return TemporalConsistency.CONSISTENT, "Event is temporally consistent"

    async def _has_causal_cycle(self, event: ConstitutionalEvent) -> bool:
        """Check if adding this event would create a causal cycle."""
        # Simple cycle detection using DFS
        visited = set()
        stack = set()

        async def dfs(event_id: str) -> bool:
            visited.add(event_id)
            stack.add(event_id)

            for child_id in self.causal_graph.get(event_id, set()):
                if child_id not in visited:
                    if await dfs(child_id):
                        return True
                elif child_id in stack:
                    return True

            stack.remove(event_id)
            return False

        return await dfs(event.event_id)

    async def _validate_constitutional_invariants(
        self,
        event: ConstitutionalEvent
    ) -> bool:
        """Validate constitutional invariants for the event."""
        # Check that constitutional hash is maintained
        if event.constitutional_hash != CONSTITUTIONAL_HASH:
            return False

        # Check separation of powers (simplified)
        if event.event_type == EventType.BRANCH_ACTION:
            branch = event.payload.get("branch")
            # Ensure branches don't overstep (would be more complex in practice)
            if branch and len(event.actor.split("_")) > 2:  # Rough heuristic
                return False

        return True

    async def query_events(
        self,
        event_type: Optional[EventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[ConstitutionalEvent]:
        """
        Query events with temporal filters.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        candidates = self.event_log

        # Apply filters
        if event_type:
            candidates = [e for e in candidates if e.event_type == event_type]

        if actor:
            candidates = [e for e in candidates if e.actor == actor]

        if start_time:
            candidates = [e for e in candidates if e.timestamp >= start_time]

        if end_time:
            candidates = [e for e in candidates if e.timestamp <= end_time]

        # Sort by timestamp (most recent first)
        candidates.sort(key=lambda e: e.timestamp, reverse=True)

        return candidates[:limit]

    async def get_state_at_time(self, timestamp: float) -> Optional[TemporalState]:
        """
        Get constitutional state at a specific timestamp.

        Uses snapshots and event replay for efficiency.
        """
        # Find closest snapshot
        closest_snapshot = None
        for snapshot in reversed(self.state_snapshots):
            if snapshot.timestamp <= timestamp:
                closest_snapshot = snapshot
                break

        if not closest_snapshot:
            return None

        # Replay events from snapshot to target time
        state = closest_snapshot
        for event in self.events_by_time:
            if event.timestamp > timestamp:
                break
            if event.timestamp > closest_snapshot.timestamp:
                # Apply event effects (simplified)
                new_state = TemporalState(
                    timestamp=event.timestamp,
                    event_count=state.event_count + 1,
                    active_policies=state.active_policies.copy(),
                    pending_decisions=state.pending_decisions.copy(),
                    branch_states=state.branch_states.copy(),
                    causal_frontier=state.causal_frontier.copy()
                )
                await self._apply_event_to_state(new_state, event)
                state = new_state

        return state

    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_events": len(self.events),
            "event_types": {et.value: len(events) for et, events in self.events_by_type.items()},
            "actors": list(self.events_by_actor.keys()),
            "snapshots": len(self.state_snapshots),
            "causal_graph_size": len(self.causal_graph),
            "current_timestamp": time.time(),
            "constitutional_hash": CONSTITUTIONAL_HASH
        }

    async def validate_full_consistency(self) -> Tuple[bool, List[str]]:
        """
        Validate consistency of entire event log.

        Returns:
            Tuple of (is_consistent, error_messages)
        """
        errors = []
        is_consistent = True

        for event in self.event_log:
            consistency, message = await self.validate_temporal_consistency(event)
            if consistency != TemporalConsistency.CONSISTENT:
                is_consistent = False
                errors.append(f"Event {event.event_id}: {message}")

        self.last_consistency_check = time.time()
        return is_consistent, errors
