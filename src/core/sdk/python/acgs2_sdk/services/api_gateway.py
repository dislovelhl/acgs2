"""
ACGS-2 API Gateway Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import TYPE_CHECKING, Any, Dict, List, Union, Optional

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]  # type: ignore[misc]
    JSONDict = Dict[str, JSONValue]  # type: ignore[misc]

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class APIGatewayService:
    """Service for interacting with the API Gateway endpoints."""

    def __init__(self, client: "ACGS2Client") -> None:
        """Initialize the API gateway service.

        Args:
            client: ACGS2 client instance
        """
        self._client = client

    async def health_check(self) -> JSONDict:
        """Check API gateway health.

        Returns:
            Health check response
        """
        return await self._client.get("/health")

    async def submit_feedback(
        self,
        user_id: str,
        category: str,
        rating: int,
        title: str,
        description: str = "",
        metadata: Optional[JSONDict] = None,
    ) -> JSONDict:
        """Submit user feedback.

        Args:
            user_id: User identifier
            category: Feedback category (bug, feature, general)
            rating: Rating from 1-5
            title: Feedback title
            description: Feedback description
            metadata: Additional metadata

        Returns:
            Feedback submission response
        """
        data = {
            "user_id": user_id,
            "category": category,
            "rating": rating,
            "title": title,
            "description": description,
        }

        if metadata:
            data["metadata"] = metadata

        return await self._client.post("/feedback", json=data)

    async def get_feedback_stats(self) -> JSONDict:
        """Get feedback statistics.

        Returns:
            Feedback statistics
        """
        return await self._client.get("/feedback/stats")

    async def list_services(self) -> JSONDict:
        """List available services.

        Returns:
            Services information
        """
        return await self._client.get("/services")
