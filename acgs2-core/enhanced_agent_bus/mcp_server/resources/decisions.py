"""
Recent Decisions MCP Resource.

Provides read access to recent governance decisions.

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..protocol.types import ResourceDefinition

logger = logging.getLogger(__name__)


class DecisionsResource:
    """
    MCP Resource for recent governance decisions.

    Provides read-only access to recent governance decisions
    for transparency and audit purposes.
    """

    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
    URI = "acgs2://governance/decisions"

    def __init__(
        self,
        submit_governance_tool: Optional[Any] = None,
        max_decisions: int = 100,
    ):
        """
        Initialize the decisions resource.

        Args:
            submit_governance_tool: Optional reference to SubmitGovernanceTool
            max_decisions: Maximum number of decisions to store
        """
        self.submit_governance_tool = submit_governance_tool
        self.max_decisions = max_decisions
        self._access_count = 0
        self._decisions: List[Dict[str, Any]] = []

    @classmethod
    def get_definition(cls) -> ResourceDefinition:
        """Get the MCP resource definition."""
        return ResourceDefinition(
            uri=cls.URI,
            name="Recent Decisions",
            description=(
                "Recent governance decisions for transparency. "
                "Shows decision outcomes, reasoning, and applied principles."
            ),
            mimeType="application/json",
            constitutional_scope="read",
        )

    async def read(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Read recent governance decisions.

        Args:
            params: Optional parameters (limit, outcome_filter, etc.)

        Returns:
            JSON string of recent decisions
        """
        self._access_count += 1
        params = params or {}
        limit = params.get("limit", 10)
        outcome_filter = params.get("outcome")

        logger.info(f"Reading recent decisions (limit={limit})")

        try:
            if self.submit_governance_tool:
                # Get decisions from completed requests
                completed = self.submit_governance_tool._completed_requests
                decisions = [req.to_dict() for req in completed.values()]
            else:
                decisions = self._decisions

            # Apply filters
            if outcome_filter:
                decisions = [d for d in decisions if d.get("status") == outcome_filter]

            # Sort by timestamp (newest first) and limit
            decisions.sort(
                key=lambda d: d.get("timestamp", ""),
                reverse=True,
            )
            decisions = decisions[:limit]

            return json.dumps(
                {
                    "constitutional_hash": self.CONSTITUTIONAL_HASH,
                    "total_count": len(decisions),
                    "decisions": decisions,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error reading decisions resource: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "constitutional_hash": self.CONSTITUTIONAL_HASH,
                }
            )

    def add_decision(self, decision: Dict[str, Any]) -> None:
        """
        Add a decision to the resource.

        Args:
            decision: Decision data to add
        """
        self._decisions.append(decision)

        # Maintain max size
        if len(self._decisions) > self.max_decisions:
            self._decisions = self._decisions[-self.max_decisions :]

    def get_metrics(self) -> Dict[str, Any]:
        """Get resource access metrics."""
        return {
            "access_count": self._access_count,
            "decision_count": len(self._decisions),
            "uri": self.URI,
            "constitutional_hash": self.CONSTITUTIONAL_HASH,
        }
