"""
ACGS-2 Agent Registration Saga
Constitutional Hash: cdd01ef066bc6cf2

Saga for onboarding new agents into the system with multi-stage verification.
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


class AgentRegistrationSaga(BaseSaga):
    """
    Saga for registering a new agent with identity verification and capability audit.
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

    async def run_registration(
        self, context: WorkflowContext, agent_data: Dict[str, Any], activities: Any
    ) -> SagaResult:
        """
        Execute agent registration saga.
        """
        # Step 1: Identity Verification
        self.add_step(
            SagaStep(
                name="verify_identity",
                execute=lambda x: activities.evaluate_policy(
                    x["saga_id"], "acgs/security/verify_identity", x["agent_data"]
                ),
                compensate=None,  # Read-only, no compensation
            )
        )

        # Step 2: Capability Audit
        self.add_step(
            SagaStep(
                name="audit_capabilities",
                execute=lambda x: activities.execute_agent_task("compliance", "audit_agent", x),
                compensate=None,  # Read-only
            )
        )

        # Step 3: Directory Entry
        self.add_step(
            SagaStep(
                name="create_directory_entry",
                execute=lambda x: activities.record_audit(x["saga_id"], "agent_registered", x),
                compensate=lambda x: activities.record_audit(x["saga_id"], "agent_unregistered", x),
            )
        )

        return await self.execute(context, {"agent_data": agent_data})
