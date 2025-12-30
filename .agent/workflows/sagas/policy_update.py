"""
ACGS-2 Policy Update Saga
Constitutional Hash: cdd01ef066bc6cf2

Saga for rolling out policy changes across the system with safe rollback.
"""

import logging
from typing import Any, Dict, Optional

from ..base.context import WorkflowContext
from .base_saga import BaseSaga, SagaResult, SagaStep

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class PolicyUpdateSaga(BaseSaga):
    """
    Saga for updating system policies (OPA, constitutional, etc.)
    Ensures that policy updates are staged, validated, and committed atomically.
    """

    def __init__(
        self,
        saga_id: Optional[str] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        super().__init__(
            saga_id=saga_id,
            constitutional_hash=constitutional_hash,
        )

    async def run_update(
        self, context: WorkflowContext, policy_data: Dict[str, Any], activities: Any
    ) -> SagaResult:
        """
        Execute the policy update saga.
        """
        # Step 1: Stage Policy
        self.add_step(
            SagaStep(
                name="stage_policy",
                execute=lambda x: activities.evaluate_policy(
                    x["workflow_id"], "acgs/constitutional/validate_policy", x["policy_data"]
                ),
                compensate=lambda x: logger.info(
                    f"Staging failed, no cleanup needed for {x['saga_id']}"
                ),
            )
        )

        # Step 2: Push to Canary
        self.add_step(
            SagaStep(
                name="canary_deployment",
                execute=lambda x: activities.execute_agent_task(
                    "governance", "deploy_canary_policy", x
                ),
                compensate=lambda x: activities.execute_agent_task(
                    "governance", "rollback_canary_policy", x
                ),
            )
        )

        # Step 3: Global Commit
        self.add_step(
            SagaStep(
                name="global_commit",
                execute=lambda x: activities.record_audit(x["workflow_id"], "policy_committed", x),
                compensate=lambda x: logger.warning(
                    f"Global commit failed for {x['saga_id']}, manual intervention required"
                ),
            )
        )

        return await self.execute(context, {"policy_data": policy_data})
