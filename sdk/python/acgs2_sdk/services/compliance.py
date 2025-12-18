"""
ACGS-2 Compliance Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import TYPE_CHECKING, Any

from acgs2_sdk.constants import COMPLIANCE_ENDPOINT, CONSTITUTIONAL_HASH
from acgs2_sdk.models import (
    ComplianceResult,
    ComplianceStatus,
    PaginatedResponse,
    ValidateComplianceRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class ComplianceService:
    """Service for compliance validation."""

    def __init__(self, client: "ACGS2Client") -> None:
        self._client = client
        self._base_path = COMPLIANCE_ENDPOINT

    async def validate(self, request: ValidateComplianceRequest) -> ComplianceResult:
        """Validate compliance against a policy."""
        data = await self._client.post(
            f"{self._base_path}/validate",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return ComplianceResult.model_validate(data.get("data", data))

    async def validate_batch(
        self,
        context: dict[str, Any],
        policy_ids: list[str],
    ) -> list[ComplianceResult]:
        """Validate compliance against multiple policies."""
        data = await self._client.post(
            f"{self._base_path}/validate/batch",
            json={
                "context": context,
                "policyIds": policy_ids,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return [ComplianceResult.model_validate(r) for r in data.get("data", [])]

    async def validate_action(
        self,
        agent_id: str,
        action: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate an agent action against policies."""
        data = await self._client.post(
            f"{self._base_path}/validate/action",
            json={
                "agentId": agent_id,
                "action": action,
                "context": context,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return data.get("data", data)

    async def get_result(self, result_id: str) -> ComplianceResult:
        """Get a compliance result by ID."""
        data = await self._client.get(f"{self._base_path}/results/{result_id}")
        return ComplianceResult.model_validate(data.get("data", data))

    async def list_results(
        self,
        page: int = 1,
        page_size: int = 50,
        policy_id: str | None = None,
        status: ComplianceStatus | None = None,
    ) -> PaginatedResponse[ComplianceResult]:
        """List compliance results."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if policy_id:
            params["policyId"] = policy_id
        if status:
            params["status"] = status.value

        data = await self._client.get(f"{self._base_path}/results", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[ComplianceResult](
            data=[ComplianceResult.model_validate(r) for r in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def generate_report(
        self,
        name: str,
        start_date: str,
        end_date: str,
        policy_ids: list[str] | None = None,
        format: str = "json",
    ) -> dict[str, Any]:
        """Generate a compliance report."""
        data = await self._client.post(
            f"{self._base_path}/reports",
            json={
                "name": name,
                "startDate": start_date,
                "endDate": end_date,
                "policyIds": policy_ids,
                "format": format,
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return data.get("data", data)

    async def get_dashboard(self) -> dict[str, Any]:
        """Get compliance dashboard data."""
        data = await self._client.get(f"{self._base_path}/dashboard")
        return data.get("data", data)
