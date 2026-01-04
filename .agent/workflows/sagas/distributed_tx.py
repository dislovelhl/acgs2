"""
ACGS-2 Distributed Transaction Saga
Constitutional Hash: cdd01ef066bc6cf2

Saga for atomic operations across multiple services/agents.
"""

import logging
from typing import Any, Dict, List, Optional

from ..base.context import WorkflowContext
from .base_saga import BaseSaga, SagaResult, SagaStep

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class DistributedTransactionSaga(BaseSaga):
    """
    Saga for managing distributed transactions across multiple agents.
    Ensures either all steps complete or all are compensated.
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

    async def execute_transaction(
        self, context: WorkflowContext, steps: List[SagaStep], input_data: Dict[str, Any]
    ) -> SagaResult:
        """
        Execute a set of transaction steps.
        """
        # Add steps to saga
        for step in steps:
            self.add_step(step)

        return await self.execute(context, input_data)

    @classmethod
    async def run_standard_tx(
        cls, context: WorkflowContext, input_data: Dict[str, Any], activities: Any
    ) -> SagaResult:
        """
        Helper to run a standard multi-agent transaction.
        """
        saga = cls(constitutional_hash=context.constitutional_hash)

        # Example: Reserve -> Charge -> Process
        saga.add_step(
            SagaStep(
                name="reserve_resource",
                execute=lambda x: activities.execute_agent_task(x["target_agent"], "reserve", x),
                compensate=lambda x: activities.execute_agent_task(x["target_agent"], "release", x),
            )
        )

        saga.add_step(
            SagaStep(
                name="process_transaction",
                execute=lambda x: activities.execute_agent_task(x["processor_agent"], "process", x),
                compensate=lambda x: activities.execute_agent_task(
                    x["processor_agent"], "undo_process", x
                ),
            )
        )

        return await saga.execute(context, input_data)
