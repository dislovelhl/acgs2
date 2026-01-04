"""
ACGS-2 Governance Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Union

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]  # type: ignore[misc]
    JSONDict = Dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, GOVERNANCE_ENDPOINT
from acgs2_sdk.models import (
    ApprovalRequest,
    ApprovalStatus,
    CreateApprovalRequest,
    GovernanceDecision,
    PaginatedResponse,
    SubmitApprovalDecision,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class GovernanceService:
    """Service for governance and approval workflows."""

    def __init__(self, client: "ACGS2Client") -> None:
        self._client = client
        self._base_path = GOVERNANCE_ENDPOINT

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

    async def get_decision(self, decision_id: str) -> GovernanceDecision:
        """Get a governance decision by ID."""
        data = await self._client.get(f"{self._base_path}/decisions/{decision_id}")
        return GovernanceDecision.model_validate(data.get("data", data))

    async def list_decisions(
        self,
        page: int = 1,
        page_size: int = 50,
        decision: str | None = None,
        request_id: str | None = None,
        reviewer_id: str | None = None,
    ) -> PaginatedResponse[GovernanceDecision]:
        """List governance decisions."""
        params: JSONDict = {"page": page, "pageSize": page_size}
        if decision:
            params["decision"] = decision
        if request_id:
            params["requestId"] = request_id
        if reviewer_id:
            params["reviewerId"] = reviewer_id

        data = await self._client.get(f"{self._base_path}/decisions", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[GovernanceDecision](
            data=[GovernanceDecision.model_validate(d) for d in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def verify_decision_anchor(self, decision_id: str) -> JSONDict:
        """Verify a decision's blockchain anchor."""
        data = await self._client.get(f"{self._base_path}/decisions/{decision_id}/verify")
        return data.get("data", data)

    async def validate_constitutional(
        self,
        agent_id: str,
        action: str,
        context: JSONDict,
        metadata: JSONDict | None = None,
    ) -> JSONDict:
        """Validate an action against constitutional principles."""
        data = await self._client.post(
            f"{self._base_path}/constitutional/validate",
            json={
                "agentId": agent_id,
                "action": action,
                "context": context,
                "metadata": metadata,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return data.get("data", data)

    async def get_constitutional_principles(self) -> list[JSONDict]:
        """Get constitutional principles."""
        data = await self._client.get(f"{self._base_path}/constitutional/principles")
        return data.get("data", [])

    async def get_metrics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        policy_id: str | None = None,
    ) -> JSONDict:
        """Get governance metrics."""
        params: JSONDict = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if policy_id:
            params["policyId"] = policy_id

        data = await self._client.get(f"{self._base_path}/metrics", params=params)
        return data.get("data", data)

    async def get_dashboard(self) -> JSONDict:
        """Get governance dashboard data."""
        data = await self._client.get(f"{self._base_path}/dashboard")
        return data.get("data", data)
