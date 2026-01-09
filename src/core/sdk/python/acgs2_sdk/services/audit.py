"""
ACGS-2 Audit Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = str | int | float | bool | None | dict[str, Any] | list[Any]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import AUDIT_ENDPOINT, CONSTITUTIONAL_HASH
from acgs2_sdk.models import (
    AuditEvent,
    EventCategory,
    EventSeverity,
    PaginatedResponse,
    QueryAuditEventsRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class AuditService:
    """Service for audit logging and querying."""

    def __init__(self, client: "ACGS2Client") -> None:
        self._client = client
        self._base_path = AUDIT_ENDPOINT

    async def record(
        self,
        category: EventCategory,
        severity: EventSeverity,
        action: str,
        actor: str,
        resource: str,
        outcome: str,
        resource_id: str | None = None,
        details: JSONDict | None = None,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        """Record an audit event."""
        data = await self._client.post(
            f"{self._base_path}/events",
            json={
                "category": category.value,
                "severity": severity.value,
                "action": action,
                "actor": actor,
                "resource": resource,
                "resourceId": resource_id,
                "outcome": outcome,
                "details": details,
                "correlationId": correlation_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return AuditEvent.model_validate(data.get("data", data))

    async def record_batch(
        self,
        events: list[JSONDict],
    ) -> list[AuditEvent]:
        """Record multiple audit events."""
        prepared = [
            {
                **event,
                "timestamp": datetime.now(UTC).isoformat(),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            }
            for event in events
        ]
        data = await self._client.post(
            f"{self._base_path}/events/batch",
            json={"events": prepared},
        )
        return [AuditEvent.model_validate(e) for e in data.get("data", [])]

    async def get_event(self, event_id: str) -> AuditEvent:
        """Get an audit event by ID."""
        data = await self._client.get(f"{self._base_path}/events/{event_id}")
        return AuditEvent.model_validate(data.get("data", data))

    async def query_events(
        self,
        request: QueryAuditEventsRequest | None = None,
        **kwargs: Any,
    ) -> PaginatedResponse[AuditEvent]:
        """Query audit events."""
        params = request.model_dump(by_alias=True, exclude_none=True) if request else kwargs

        data = await self._client.get(f"{self._base_path}/events", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[AuditEvent](
            data=[AuditEvent.model_validate(e) for e in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", 1),
            page_size=response_data.get("pageSize", 50),
            total_pages=response_data.get("totalPages", 0),
        )

    async def search_events(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[AuditEvent]:
        """Search audit events."""
        data = await self._client.get(
            f"{self._base_path}/events/search",
            params={"query": query, "page": page, "pageSize": page_size},
        )
        response_data = data.get("data", data)
        return PaginatedResponse[AuditEvent](
            data=[AuditEvent.model_validate(e) for e in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def get_trail(
        self,
        resource_type: str,
        resource_id: str,
    ) -> JSONDict:
        """Get audit trail for a resource."""
        data = await self._client.get(f"{self._base_path}/trails/{resource_type}/{resource_id}")
        return data.get("data", data)

    async def create_export(
        self,
        format: str = "json",
        query: QueryAuditEventsRequest | None = None,
    ) -> JSONDict:
        """Create an export job."""
        payload: JSONDict = {
            "format": format,
            "constitutionalHash": CONSTITUTIONAL_HASH,
        }
        if query:
            payload["query"] = query.model_dump(by_alias=True, exclude_none=True)

        data = await self._client.post(f"{self._base_path}/exports", json=payload)
        return data.get("data", data)

    async def get_export(self, export_id: str) -> JSONDict:
        """Get export job status."""
        data = await self._client.get(f"{self._base_path}/exports/{export_id}")
        return data.get("data", data)

    async def get_statistics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        category: EventCategory | None = None,
    ) -> JSONDict:
        """Get audit statistics."""
        params: JSONDict = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if category:
            params["category"] = category.value

        data = await self._client.get(f"{self._base_path}/statistics", params=params)
        return data.get("data", data)

    async def verify_integrity(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        event_ids: list[str] | None = None,
    ) -> JSONDict:
        """Verify audit event integrity."""
        data = await self._client.post(
            f"{self._base_path}/verify",
            json={
                "startDate": start_date,
                "endDate": end_date,
                "eventIds": event_ids,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return data.get("data", data)
