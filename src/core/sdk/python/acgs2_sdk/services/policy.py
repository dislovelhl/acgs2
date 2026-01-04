"""
ACGS-2 Policy Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import TYPE_CHECKING, Any, Dict, List, Union
try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]  # type: ignore[misc]
    JSONDict = Dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, POLICIES_ENDPOINT
from acgs2_sdk.models import (
    CreatePolicyRequest,
    PaginatedResponse,
    Policy,
    PolicyStatus,
    UpdatePolicyRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class PolicyService:
    """Service for managing policies."""

    def __init__(self, client: "ACGS2Client") -> None:
        """Initialize the policy service.

        Args:
            client: ACGS2 client instance
        """
        self._client = client
        self._base_path = POLICIES_ENDPOINT

    async def create(self, request: CreatePolicyRequest) -> Policy:
        """Create a new policy.

        Args:
            request: Policy creation request

        Returns:
            Created policy
        """
        data = await self._client.post(
            self._base_path,
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return Policy.model_validate(data.get("data", data))

    async def get(self, policy_id: str) -> Policy:
        """Get a policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy details
        """
        data = await self._client.get(f"{self._base_path}/{policy_id}")
        return Policy.model_validate(data.get("data", data))

    async def update(self, policy_id: str, request: UpdatePolicyRequest) -> Policy:
        """Update a policy.

        Args:
            policy_id: Policy ID
            request: Policy update request

        Returns:
            Updated policy
        """
        data = await self._client.patch(
            f"{self._base_path}/{policy_id}",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Policy.model_validate(data.get("data", data))

    async def delete(self, policy_id: str) -> None:
        """Delete a policy.

        Args:
            policy_id: Policy ID
        """
        await self._client.delete(f"{self._base_path}/{policy_id}")

    async def list_policies(
        self,
        page: int = 1,
        page_size: int = 50,
        status: PolicyStatus | None = None,
        tags: list[str] | None = None,
    ) -> PaginatedResponse[Policy]:
        """List policies.

        Args:
            page: Page number
            page_size: Items per page
            status: Filter by status
            tags: Filter by tags

        Returns:
            Paginated list of policies
        """
        params: JSONDict = {"page": page, "pageSize": page_size}
        if status:
            params["status"] = status.value
        if tags:
            params["tags"] = ",".join(tags)

        data = await self._client.get(self._base_path, params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[Policy](
            data=[Policy.model_validate(p) for p in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def activate(self, policy_id: str) -> Policy:
        """Activate a policy.

        Args:
            policy_id: Policy ID

        Returns:
            Activated policy
        """
        data = await self._client.post(
            f"{self._base_path}/{policy_id}/status",
            json={"status": PolicyStatus.ACTIVE.value},
        )
        return Policy.model_validate(data.get("data", data))

    async def deprecate(self, policy_id: str) -> Policy:
        """Deprecate a policy.

        Args:
            policy_id: Policy ID

        Returns:
            Deprecated policy
        """
        data = await self._client.post(
            f"{self._base_path}/{policy_id}/status",
            json={"status": PolicyStatus.DEPRECATED.value},
        )
        return Policy.model_validate(data.get("data", data))

    async def validate_rules(self, rules: list[JSONDict]) -> JSONDict:
        """Validate policy rules syntax.

        Args:
            rules: Policy rules to validate

        Returns:
            Validation result with errors if any
        """
        data = await self._client.post(
            f"{self._base_path}/validate",
            json={"rules": rules, "constitutionalHash": CONSTITUTIONAL_HASH},
        )
        return data.get("data", data)

    async def analyze_impact(self, policy_id: str) -> JSONDict:
        """Analyze policy impact.

        Args:
            policy_id: Policy ID

        Returns:
            Impact analysis result
        """
        data = await self._client.get(f"{self._base_path}/{policy_id}/impact")
        return data.get("data", data)

    async def get_versions(self, policy_id: str) -> list[Policy]:
        """Get all versions of a policy.

        Args:
            policy_id: Policy ID

        Returns:
            List of policy versions
        """
        data = await self._client.get(f"{self._base_path}/{policy_id}/versions")
        return [Policy.model_validate(p) for p in data.get("data", [])]
