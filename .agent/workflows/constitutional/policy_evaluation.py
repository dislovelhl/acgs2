"""
ACGS-2 Policy Evaluation Workflow
Constitutional Hash: cdd01ef066bc6cf2

Workflow for evaluating complex governance policies using the OPA engine.
"""

import logging
from typing import Any, Dict, Optional

from ..base.result import WorkflowResult
from ..base.workflow import BaseWorkflow

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class PolicyEvaluationWorkflow(BaseWorkflow):
    """
    Workflow for evaluating specific input against OPA policies.
    Provides a standardized way to request policy decisions from agents.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        evaluation_timeout_seconds: int = 15,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="policy_evaluation",
            constitutional_hash=constitutional_hash,
            timeout_seconds=evaluation_timeout_seconds,
        )

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute policy evaluation.

        Expected Input:
            policy_path: str (e.g., "acgs/deliberation/impact")
            evaluation_data: Dict[str, Any] (data to evaluate)
            context: Dict[str, Any] (optional evaluation context)
        """
        await self.validate_constitutional_hash()

        policy_path = input.get("policy_path", "acgs/constitutional/main/allow")
        evaluation_data = input.get("evaluation_data", {})
        context = input.get("context", {})

        logger.info(f"PolicyEvaluation {self.workflow_id}: Evaluating '{policy_path}'")

        try:
            # Step 1: OPA Evaluation
            eval_input = {"message": evaluation_data, "context": context}

            result = await self.activities.evaluate_policy(
                workflow_id=self.workflow_id, policy_path=policy_path, input_data=eval_input
            )
            self._completed_steps.append("opa_evaluation")

            # Step 2: Format result
            output = {
                "allowed": result.get("allowed", False),
                "reasons": result.get("reasons", []),
                "metadata": {
                    "policy_path": policy_path,
                    "policy_version": result.get("policy_version", "unknown"),
                    "constitutional_hash": self.constitutional_hash,
                },
            }

            return await self.complete(output)

        except Exception as e:
            logger.exception(f"Policy evaluation {self.workflow_id} failed: {e}")
            self._failed_steps.append("evaluation_execution")
            raise
