"""
ACGS-2 HITL Approvals Service
Human-in-the-Loop approval workflows
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Union

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, dict[str, Any], list[Any]]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, HITL_APPROVALS_ENDPOINT
from acgs2_sdk.models import (
    ApprovalRequest,
    ApprovalStatus,
    CreateApprovalRequest,
    PaginatedResponse,
    SubmitApprovalDecision,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class HITLApprovalsService:
    """Service for Human-in-the-Loop approval workflows."""

    def __init__(self, client: "ACGS2Client") -> None:
        self._client = client
        self._base_path = HITL_APPROVALS_ENDPOINT

    async def create_approval_request(
        self,
        request: CreateApprovalRequest,
    ) -> ApprovalRequest:
        """Create an approval request."""
        data = await self._client.post(
            f"{self._base_path}/approvals",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return ApprovalRequest.model_validate(data.get("data", data))

    async def get_approval_request(self, request_id: str) -> ApprovalRequest:
        """Get an approval request by ID."""
        data = await self._client.get(f"{self._base_path}/approvals/{request_id}")
        return ApprovalRequest.model_validate(data.get("data", data))

    async def list_approval_requests(
        self,
        page: int = 1,
        page_size: int = 50,
        status: ApprovalStatus | None = None,
        requester_id: str | None = None,
        pending_for: str | None = None,
    ) -> PaginatedResponse[ApprovalRequest]:
        """List approval requests."""
        params: JSONDict = {"page": page, "pageSize": page_size}
        if status:
            params["status"] = status.value
        if requester_id:
            params["requesterId"] = requester_id
        if pending_for:
            params["pendingFor"] = pending_for

        data = await self._client.get(f"{self._base_path}/approvals", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[ApprovalRequest](
            data=[ApprovalRequest.model_validate(r) for r in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def submit_decision(
        self,
        request_id: str,
        decision: SubmitApprovalDecision,
    ) -> ApprovalRequest:
        """Submit an approval decision."""
        data = await self._client.post(
            f"{self._base_path}/approvals/{request_id}/decisions",
            json={
                **decision.model_dump(by_alias=True),
                "timestamp": datetime.now(UTC).isoformat(),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return ApprovalRequest.model_validate(data.get("data", data))

    async def escalate(
        self,
        request_id: str,
        reason: str,
    ) -> ApprovalRequest:
        """Escalate an approval request."""
        data = await self._client.post(
            f"{self._base_path}/approvals/{request_id}/escalate",
            json={"reason": reason},
        )
        return ApprovalRequest.model_validate(data.get("data", data))

    async def cancel_approval_request(
        self,
        request_id: str,
        reason: str | None = None,
    ) -> None:
        """Cancel an approval request."""
        await self._client.post(
            f"{self._base_path}/approvals/{request_id}/cancel",
            json={"reason": reason},
        )

    async def get_pending_approvals(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[ApprovalRequest]:
        """Get pending approvals for a user."""
        params = {"page": page, "pageSize": page_size}
        data = await self._client.get(
            f"{self._base_path}/approvals/pending/{user_id}", params=params
        )
        response_data = data.get("data", data)
        return PaginatedResponse[ApprovalRequest](
            data=[ApprovalRequest.model_validate(r) for r in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def get_approval_workflow_config(self) -> JSONDict:
        """Get approval workflow configuration."""
        data = await self._client.get(f"{self._base_path}/config")
        return data.get("data", data)

    async def update_approval_workflow_config(
        self,
        config: JSONDict,
    ) -> JSONDict:
        """Update approval workflow configuration."""
        data = await self._client.put(
            f"{self._base_path}/config",
            json={
                "config": config,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return data.get("data", data)

    async def get_approval_metrics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> JSONDict:
        """Get approval workflow metrics."""
        params: JSONDict = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        data = await self._client.get(f"{self._base_path}/metrics", params=params)
        return data.get("data", data)
