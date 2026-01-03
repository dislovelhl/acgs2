"""
ACGS-2 Policy Registry Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from acgs2_sdk.constants import CONSTITUTIONAL_HASH
from acgs2_sdk.models import (
    CreatePolicyRequest,
    PaginatedResponse,
    Policy,
    PolicyStatus,
    UpdatePolicyRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class PolicyRegistryService:
    """Service for managing policies through the Policy Registry API."""

    def __init__(self, client: "ACGS2Client") -> None:
        """Initialize the policy registry service.

        Args:
            client: ACGS2 client instance
        """
        self._client = client
        self._base_path = "/api/v1"

    async def list_policies(
        self,
        status: Optional[PolicyStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Policy]:
        """List policies with optional filtering.

        Args:
            status: Filter by policy status
            limit: Maximum number of policies to return
            offset: Number of policies to skip

        Returns:
            List of policies
        """
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status.value

        data = await self._client.get(f"{self._base_path}/policies", params=params)
        return [Policy(**policy) for policy in data]

    async def create_policy(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        description: Optional[str] = None,
        format: str = "json",
        tags: Optional[List[str]] = None,
        compliance_tags: Optional[List[str]] = None,
    ) -> Policy:
        """Create a new policy.

        Args:
            name: Policy name
            rules: Policy rules
            description: Policy description
            format: Policy format (default: json)
            tags: Policy tags
            compliance_tags: Compliance tags

        Returns:
            Created policy
        """
        request = CreatePolicyRequest(
            name=name,
            rules=rules,
            description=description,
            tags=tags,
            compliance_tags=compliance_tags,
        )

        data = await self._client.post(
            f"{self._base_path}/policies",
            json={
                "name": request.name,
                "content": {"rules": request.rules},
                "format": format,
                "description": request.description,
            }
        )

        return Policy(**data)

    async def get_policy(self, policy_id: str) -> Policy:
        """Get a policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy details
        """
        data = await self._client.get(f"{self._base_path}/policies/{policy_id}")
        return Policy(**data)

    async def update_policy(
        self,
        policy_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        status: Optional[PolicyStatus] = None,
        tags: Optional[List[str]] = None,
        compliance_tags: Optional[List[str]] = None,
    ) -> Policy:
        """Update a policy.

        Args:
            policy_id: Policy ID
            name: New policy name
            description: New policy description
            rules: New policy rules
            status: New policy status
            tags: New policy tags
            compliance_tags: New compliance tags

        Returns:
            Updated policy
        """
        request = UpdatePolicyRequest(
            name=name,
            description=description,
            rules=rules,
            status=status,
            tags=tags,
            compliance_tags=compliance_tags,
        )

        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.rules is not None:
            update_data["rules"] = request.rules
        if request.status is not None:
            update_data["status"] = request.status.value
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.compliance_tags is not None:
            update_data["compliance_tags"] = request.compliance_tags

        data = await self._client.patch(f"{self._base_path}/policies/{policy_id}", json=update_data)
        return Policy(**data)

    async def activate_policy(self, policy_id: str) -> Policy:
        """Activate a policy.

        Args:
            policy_id: Policy ID

        Returns:
            Activated policy
        """
        data = await self._client.put(f"{self._base_path}/policies/{policy_id}/activate")
        return Policy(**data)

    async def verify_policy(self, policy_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify input against a policy.

        Args:
            policy_id: Policy ID
            input_data: Input data to verify

        Returns:
            Verification result
        """
        data = await self._client.post(
            f"{self._base_path}/policies/{policy_id}/verify",
            json={"input": input_data}
        )
        return data

    async def get_policy_content(self, policy_id: str) -> Dict[str, Any]:
        """Get raw policy content.

        Args:
            policy_id: Policy ID

        Returns:
            Raw policy content
        """
        return await self._client.get(f"{self._base_path}/policies/{policy_id}/content")

    async def get_policy_versions(self, policy_id: str) -> List[Dict[str, Any]]:
        """Get policy version history.

        Args:
            policy_id: Policy ID

        Returns:
            List of policy versions
        """
        return await self._client.get(f"{self._base_path}/policies/{policy_id}/versions")

    async def create_policy_version(
        self,
        policy_id: str,
        rules: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new policy version.

        Args:
            policy_id: Policy ID
            rules: New policy rules
            description: Version description

        Returns:
            Created policy version
        """
        data = await self._client.post(
            f"{self._base_path}/policies/{policy_id}/versions",
            json={
                "content": {"rules": rules},
                "description": description,
            }
        )
        return data

    async def get_policy_version(self, policy_id: str, version: str) -> Dict[str, Any]:
        """Get a specific policy version.

        Args:
            policy_id: Policy ID
            version: Version identifier

        Returns:
            Policy version details
        """
        return await self._client.get(f"{self._base_path}/policies/{policy_id}/versions/{version}")

    # Authentication endpoints
    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate and get access token.

        Args:
            username: Username
            password: Password

        Returns:
            Authentication response with token
        """
        data = await self._client.post(
            f"{self._base_path}/auth/token",
            json={"username": username, "password": password}
        )
        return data

    # Bundle endpoints
    async def list_bundles(self) -> List[Dict[str, Any]]:
        """List all policy bundles.

        Returns:
            List of policy bundles
        """
        return await self._client.get(f"{self._base_path}/bundles")

    async def create_bundle(
        self,
        name: str,
        policies: List[str],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a policy bundle.

        Args:
            name: Bundle name
            policies: List of policy IDs
            description: Bundle description

        Returns:
            Created bundle
        """
        data = await self._client.post(
            f"{self._base_path}/bundles",
            json={
                "name": name,
                "policies": policies,
                "description": description,
            }
        )
        return data

    async def get_bundle(self, bundle_id: str) -> Dict[str, Any]:
        """Get a policy bundle by ID.

        Args:
            bundle_id: Bundle ID

        Returns:
            Bundle details
        """
        return await self._client.get(f"{self._base_path}/bundles/{bundle_id}")

    async def get_active_bundle(self) -> Dict[str, Any]:
        """Get the currently active policy bundle.

        Returns:
            Active bundle details
        """
        return await self._client.get(f"{self._base_path}/bundles/active")

    # Health check endpoints
    async def health_check(self) -> Dict[str, Any]:
        """Check policy registry health.

        Returns:
            Health check response
        """
        return await self._client.get(f"{self._base_path}/health/policies")

    async def cache_health(self) -> Dict[str, Any]:
        """Check cache health.

        Returns:
            Cache health response
        """
        return await self._client.get(f"{self._base_path}/health/cache")

    async def connections_health(self) -> Dict[str, Any]:
        """Check connections health.

        Returns:
            Connections health response
        """
        return await self._client.get(f"{self._base_path}/health/connections")
