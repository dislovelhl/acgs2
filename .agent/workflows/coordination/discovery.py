"""
ACGS-2 Agent Discovery Workflow
Constitutional Hash: cdd01ef066bc6cf2

Workflow for finding suitable agents based on capabilities, availability, and reputation.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from ..base.result import WorkflowResult
from ..base.workflow import BaseWorkflow

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class AgentDiscoveryWorkflow(BaseWorkflow):
    """
    Workflow for discovering agents that meet specific criteria.
    Implements a reliable discovery process with constitutional validation.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        discovery_timeout_seconds: int = 30,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="discovery",
            constitutional_hash=constitutional_hash,
            timeout_seconds=discovery_timeout_seconds,
        )

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute discovery workflow.

        Expected Input:
            required_capabilities: List[str]
            min_reputation: float (optional)
            status: str (optional, defaults to 'active')
            max_results: int (optional, defaults to 10)
        """
        # Always validate constitutional hash first
        await self.validate_constitutional_hash()

        required_capabilities = input.get("required_capabilities", [])
        min_reputation = input.get("min_reputation", 0.0)
        status = input.get("status", "active")
        max_results = input.get("max_results", 10)

        logger.info(
            f"Discovery {self.workflow_id}: Searching for agents with "
            f"capabilities={required_capabilities}, min_reputation={min_reputation}"
        )

        try:
            # Step 1: Query agent directory
            agents = await self.activities.list_agents(
                capabilities=required_capabilities, status=status
            )
            self._completed_steps.append("query_directory")

            # Step 2: Filter and score results
            # In a real implementation, this could be more complex (ML scoring, etc.)
            qualified_agents = [
                a for a in agents if a.get("reputation_score", 1.0) >= min_reputation
            ]
            self._completed_steps.append("filter_results")

            # Step 3: Sort by reputation (desc) and latency (asc)
            qualified_agents.sort(
                key=lambda x: (-x.get("reputation_score", 1.0), x.get("latency_ms", 0))
            )
            self._completed_steps.append("sort_results")

            # Step 4: Limit and format output
            results = qualified_agents[:max_results]

            output = {
                "discovery_id": str(uuid.uuid4()),
                "status": "success",
                "agents": results,
                "count": len(results),
                "total_found": len(agents),
            }

            return await self.complete(output)

        except Exception as e:
            logger.exception(f"Discovery {self.workflow_id} failed: {e}")
            self._failed_steps.append("discovery_execution")
            raise
