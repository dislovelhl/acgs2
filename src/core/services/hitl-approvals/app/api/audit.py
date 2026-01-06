"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals Audit Log API Endpoints

FastAPI router for audit trail retrieval and querying.
Implements immutable audit log access with filtering and pagination.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.models import AuditEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])

# =============================================================================
# In-Memory Audit Store (Temporary - will be replaced by AuditLedger in phase-6)
# =============================================================================


class AuditStore:
    """
    In-memory audit event store for audit log retrieval.

    This is a temporary implementation that will be replaced by the
    persistent AuditLedger in phase-6 (subtask-6-2).

    The store is append-only to maintain audit trail immutability.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
        self._events_by_request: Dict[str, List[AuditEvent]] = {}

    def record_event(
        self,
        event_type: str,
        request_id: str,
        actor_id: str,
        actor_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record an immutable audit event.

        Args:
            event_type: Type of event (created, approved, rejected, escalated, etc.)
            request_id: ID of the related approval request
            actor_id: ID of the user/system that triggered the event
            actor_role: Role of the actor (optional)
            details: Additional event details (optional)
            previous_state: State before the event (optional)
            new_state: State after the event (optional)

        Returns:
            The recorded AuditEvent
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            request_id=request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            previous_state=previous_state,
            new_state=new_state,
        )

        # Append-only storage (immutable)
        self._events.append(event)

        # Index by request_id for efficient lookups
        if request_id not in self._events_by_request:
            self._events_by_request[request_id] = []
        self._events_by_request[request_id].append(event)

        logger.info(f"Audit event recorded: {event_type} for request {request_id} by {actor_id}")

        return event

    def get_events(
        self,
        request_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[AuditEvent], int]:
        """
        Query audit events with optional filtering.

        Args:
            request_id: Filter by approval request ID
            event_type: Filter by event type
            actor_id: Filter by actor ID
            start_date: Filter events after this timestamp
            end_date: Filter events before this timestamp
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            Tuple of (filtered events list, total count before pagination)
        """
        # Start with all events or filtered by request_id
        if request_id:
            events = self._events_by_request.get(request_id, [])
        else:
            events = self._events

        # Apply filters
        filtered = []
        for event in events:
            # Filter by event_type
            if event_type and event.event_type != event_type:
                continue

            # Filter by actor_id
            if actor_id and event.actor_id != actor_id:
                continue

            # Filter by date range
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue

            filtered.append(event)

        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        # Get total before pagination
        total = len(filtered)

        # Apply pagination
        paginated = filtered[offset : offset + limit]

        return paginated, total

    def get_event_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Get a specific audit event by ID."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def get_events_for_request(self, request_id: str) -> List[AuditEvent]:
        """Get all audit events for a specific approval request."""
        events = self._events_by_request.get(request_id, [])
        # Return sorted by timestamp ascending (chronological order)
        return sorted(events, key=lambda e: e.timestamp)

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        event_type_counts: Dict[str, int] = {}
        for event in self._events:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1

        return {
            "total_events": len(self._events),
            "unique_requests": len(self._events_by_request),
            "event_type_counts": event_type_counts,
        }

    def clear(self) -> None:
        """Clear all events (for testing only)."""
        self._events.clear()
        self._events_by_request.clear()


# Singleton instance
_audit_store: Optional[AuditStore] = None


def get_audit_store() -> AuditStore:
    """Get the singleton audit store instance."""
    global _audit_store
    if _audit_store is None:
        _audit_store = AuditStore()
    return _audit_store


def reset_audit_store() -> None:
    """Reset the audit store (for testing)."""
    global _audit_store
    _audit_store = None


# =============================================================================
# Request/Response Models
# =============================================================================


class AuditEventResponse(BaseModel):
    """Response model for a single audit event."""

    event_id: str = Field(..., description="Unique identifier for the audit event")
    event_type: str = Field(..., description="Type of event")
    request_id: str = Field(..., description="Related approval request ID")
    actor_id: str = Field(..., description="ID of the actor who triggered the event")
    actor_role: Optional[str] = Field(None, description="Role of the actor")
    timestamp: str = Field(..., description="ISO timestamp of the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    previous_state: Optional[str] = Field(None, description="State before the event")
    new_state: Optional[str] = Field(None, description="State after the event")


class AuditListResponse(BaseModel):
    """Response model for listing audit events."""

    total: int = Field(..., description="Total number of events matching the query")
    limit: int = Field(..., description="Maximum events per page")
    offset: int = Field(..., description="Number of events skipped")
    items: List[AuditEventResponse] = Field(
        default_factory=list, description="List of audit events"
    )


class AuditStatsResponse(BaseModel):
    """Response model for audit statistics."""

    total_events: int = Field(..., description="Total number of audit events")
    unique_requests: int = Field(
        ..., description="Number of unique approval requests with audit events"
    )
    event_type_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count of events by type"
    )
    timestamp: str = Field(..., description="Timestamp of the statistics query")


class AuditTimelineResponse(BaseModel):
    """Response model for request audit timeline."""

    request_id: str = Field(..., description="The approval request ID")
    total_events: int = Field(..., description="Total events for this request")
    timeline: List[AuditEventResponse] = Field(
        default_factory=list, description="Chronological list of events"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _format_audit_event(event: AuditEvent) -> AuditEventResponse:
    """Format an AuditEvent model to API response."""
    return AuditEventResponse(
        event_id=event.event_id,
        event_type=event.event_type,
        request_id=event.request_id,
        actor_id=event.actor_id,
        actor_role=event.actor_role,
        timestamp=event.timestamp.isoformat(),
        details=event.details,
        previous_state=event.previous_state,
        new_state=event.new_state,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=AuditListResponse,
    summary="List audit events",
    description="Query audit events with optional filtering and pagination. "
    "Returns events sorted by timestamp (most recent first).",
)
async def list_audit_events(
    request_id: Annotated[Optional[str], Query(description="Filter by approval request ID")] = None,
    event_type: Annotated[
        Optional[str],
        Query(description="Filter by event type (created, approved, rejected, escalated)"),
    ] = None,
    actor_id: Annotated[Optional[str], Query(description="Filter by actor ID")] = None,
    start_date: Annotated[
        Optional[datetime], Query(description="Filter events after this ISO timestamp")
    ] = None,
    end_date: Annotated[
        Optional[datetime], Query(description="Filter events before this ISO timestamp")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum events to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of events to skip")] = 0,
) -> AuditListResponse:
    """
    List audit events with optional filtering.

    Supports filtering by request_id, event_type, actor_id, and date range.
    Results are paginated and sorted by timestamp (most recent first).

    This endpoint is used by the Audit Log Viewer UI component.
    """
    try:
        store = get_audit_store()

        events, total = store.get_events(
            request_id=request_id,
            event_type=event_type,
            actor_id=actor_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        items = [_format_audit_event(event) for event in events]

        return AuditListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    except Exception as e:
        logger.exception(f"Error listing audit events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit events",
        ) from e


@router.get(
    "/stats",
    response_model=AuditStatsResponse,
    summary="Get audit statistics",
    description="Get aggregate statistics about audit events.",
)
async def get_audit_stats() -> AuditStatsResponse:
    """
    Get audit log statistics.

    Returns aggregate counts and metrics about the audit trail.
    """
    try:
        store = get_audit_store()
        stats = store.get_statistics()

        return AuditStatsResponse(
            total_events=stats["total_events"],
            unique_requests=stats["unique_requests"],
            event_type_counts=stats["event_type_counts"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error getting audit stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit statistics",
        ) from e


@router.get(
    "/request/{request_id}",
    response_model=AuditTimelineResponse,
    summary="Get audit timeline for a request",
    description="Get the complete audit timeline for a specific approval request. "
    "Returns events in chronological order.",
)
async def get_request_audit_timeline(request_id: str) -> AuditTimelineResponse:
    """
    Get the complete audit timeline for an approval request.

    Returns all audit events for the specified request in chronological order,
    showing the complete history of the approval workflow.
    """
    try:
        store = get_audit_store()
        events = store.get_events_for_request(request_id)

        if not events:
            # Return empty timeline (request exists but no audit events yet,
            # or request doesn't exist - we don't differentiate for audit queries)
            return AuditTimelineResponse(
                request_id=request_id,
                total_events=0,
                timeline=[],
            )

        timeline = [_format_audit_event(event) for event in events]

        return AuditTimelineResponse(
            request_id=request_id,
            total_events=len(timeline),
            timeline=timeline,
        )

    except Exception as e:
        logger.exception(f"Error getting audit timeline for {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit timeline",
        ) from e


@router.get(
    "/{event_id}",
    response_model=AuditEventResponse,
    summary="Get a specific audit event",
    description="Retrieve a single audit event by its ID.",
)
async def get_audit_event(event_id: str) -> AuditEventResponse:
    """
    Get a specific audit event by ID.

    Args:
        event_id: The unique identifier of the audit event
    """
    try:
        store = get_audit_store()
        event = store.get_event_by_id(event_id)

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit event not found: {event_id}",
            )

        return _format_audit_event(event)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting audit event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit event",
        ) from e


# =============================================================================
# Utility function for other modules to record audit events
# =============================================================================


def record_audit_event(
    event_type: str,
    request_id: str,
    actor_id: str,
    actor_role: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
) -> AuditEvent:
    """
    Record an audit event. This is a convenience function for other modules.

    Args:
        event_type: Type of event (created, approved, rejected, escalated, etc.)
        request_id: ID of the related approval request
        actor_id: ID of the user/system that triggered the event
        actor_role: Role of the actor (optional)
        details: Additional event details (optional)
        previous_state: State before the event (optional)
        new_state: State after the event (optional)

    Returns:
        The recorded AuditEvent
    """
    store = get_audit_store()
    return store.record_event(
        event_type=event_type,
        request_id=request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        details=details,
        previous_state=previous_state,
        new_state=new_state,
    )
