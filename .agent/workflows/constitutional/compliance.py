"""
ACGS-2 Compliance Check Workflow
Constitutional Hash: cdd01ef066bc6cf2

Workflow for auditing and verifying agent actions against constitutional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..base.result import WorkflowResult
from ..base.workflow import BaseWorkflow

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class ComplianceCheckWorkflow(BaseWorkflow):
    """
    Workflow for verifying that agent actions comply with constitutional rules.
    Typically used for post-action auditing or high-stakes validation.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        compliance_timeout_seconds: int = 60,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="compliance",
            constitutional_hash=constitutional_hash,
            timeout_seconds=compliance_timeout_seconds,
        )

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute compliance check.

        Expected Input:
            target_agent_id: str
            actions: List[Dict[str, Any]] (actions to verify)
            ruleset: str (optional, defaults to 'standard')
        """
        await self.validate_constitutional_hash()

        agent_id = input.get("target_agent_id", "unknown")
        actions = input.get("actions", [])
        ruleset = input.get("ruleset", "standard")

        logger.info(
            f"Compliance {self.workflow_id}: Auditing {len(actions)} actions "
            f"for agent {agent_id} using ruleset '{ruleset}'"
        )

        try:
            # Step 1: Structural validation of actions
            # Ensure all actions have required fields for audit
            valid_actions = []
            malformed_actions = []
            for action in actions:
                if "action_id" in action and "timestamp" in action:
                    valid_actions.append(action)
                else:
                    malformed_actions.append(action)

            self._completed_steps.append("structure_validation")

            # Step 2: Constitutional Policy Evaluation
            # Evaluate each action against the OPA policy
            compliance_results = []
            violations = []

            for action in valid_actions:
                policy_result = await self.activities.evaluate_policy(
                    workflow_id=self.workflow_id,
                    policy_path="acgs/constitutional/allow",
                    input_data={"message": action, "context": {"agent_id": agent_id}},
                )

                result = {
                    "action_id": action.get("action_id"),
                    "allowed": policy_result.get("allowed", False),
                    "reasons": policy_result.get("reasons", []),
                }

                compliance_results.append(result)
                if not result["allowed"]:
                    violations.append(result)

            self._completed_steps.append("policy_evaluation")

            # Step 3: Result Summary
            is_compliant = len(violations) == 0 and len(malformed_actions) == 0

            output = {
                "audit_id": self.workflow_id,
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_compliant": is_compliant,
                "summary": {
                    "total_actions": len(actions),
                    "valid_actions": len(valid_actions),
                    "malformed_actions": len(malformed_actions),
                    "violations_detected": len(violations),
                },
                "details": {
                    "compliance_results": compliance_results,
                    "violations": violations,
                    "malformed": malformed_actions,
                },
                "constitutional_hash": self.constitutional_hash,
            }

            # Step 4: Record audit if violations found
            if not is_compliant:
                await self.activities.record_audit(
                    workflow_id=self.workflow_id,
                    event_type="compliance_violation",
                    event_data=output,
                )
                self._completed_steps.append("record_violation_audit")

            return await self.complete(output)

        except Exception as e:
            logger.exception(f"Compliance check {self.workflow_id} failed: {e}")
            self._failed_steps.append("compliance_execution")
            raise
