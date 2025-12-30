"""
ACGS-2 Governance Decision Workflow
Constitutional Hash: cdd01ef066bc6cf2

Workflow for high-impact governance changes requiring consensus and validation.
"""

import logging
from typing import Any, Dict, Optional

from ..base.result import WorkflowResult, WorkflowStatus
from ..base.workflow import BaseWorkflow
from ..coordination.voting import VotingStrategy, VotingWorkflow

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class GovernanceDecisionWorkflow(BaseWorkflow):
    """
    Workflow for handling major system changes (e.g., constitutional updates).
    Requires multi-stage validation and agent consensus via voting.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        governance_timeout_seconds: int = 600,  # Governance takes time
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="governance_decision",
            constitutional_hash=constitutional_hash,
            timeout_seconds=governance_timeout_seconds,
        )

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute governance decision workflow.

        Expected Input:
            proposal_type: str (e.g., 'constitutional_update')
            proposal_data: Dict[str, Any]
            eligible_voters: List[str]
            voting_strategy: str (optional, defaults to 'supermajority')
        """
        await self.validate_constitutional_hash()

        proposal_type = input.get("proposal_type", "unspecified")
        proposal_data = input.get("proposal_data", {})
        eligible_voters = input.get("eligible_voters", [])
        voting_strategy_name = input.get("voting_strategy", "supermajority")

        logger.info(f"Governance {self.workflow_id}: Processing '{proposal_type}' proposal")

        try:
            # Stage 1: Impact Assessment (using OPA)
            impact_result = await self.activities.evaluate_policy(
                workflow_id=self.workflow_id,
                policy_path="acgs/deliberation/impact",
                input_data={"message": {"content": proposal_data, "message_type": proposal_type}},
            )

            if not impact_result.get("allowed", False):
                return await self.complete(
                    {
                        "decision": "rejected",
                        "reason": "Policy evaluation blocked the proposal",
                        "details": impact_result.get("reasons", []),
                    }
                )

            self._completed_steps.append("impact_assessment")

            # Stage 2: Multi-Agent Consensus (Voting)
            voting_strategy = VotingStrategy(voting_strategy_name)
            voting_wf = VotingWorkflow(
                workflow_id=f"vote:{self.workflow_id}",
                eligible_agents=eligible_voters,
                strategy=voting_strategy,
                constitutional_hash=self.constitutional_hash,
            )

            vote_input = {
                "proposal": f"Governance Proposal: {proposal_type}",
                "context": proposal_data,
            }

            # Execute voting as a sub-workflow or direct call
            voting_result_wf = await voting_wf.run(vote_input)

            if voting_result_wf.status != WorkflowStatus.COMPLETED:
                return await self.complete(
                    {
                        "decision": "aborted",
                        "reason": "Voting process failed or timed out",
                        "voting_status": voting_result_wf.status.value,
                    }
                )

            voting_result_data = voting_result_wf.output
            self._completed_steps.append("voting_consensus")

            # Stage 3: Final Approval based on voting result
            approved = voting_result_data.get("decision") == "approve"

            output = {
                "proposal_id": self.workflow_id,
                "proposal_type": proposal_type,
                "decision": "approved" if approved else "rejected",
                "voting_summary": {
                    "approval_rate": voting_result_data.get("approval_rate"),
                    "quorum_met": voting_result_data.get("quorum_met"),
                },
                "constitutional_hash": self.constitutional_hash,
            }

            # Step 4: Record final governance decision to audit
            await self.activities.record_audit(
                workflow_id=self.workflow_id,
                event_type="governance_decision_finalized",
                event_data=output,
            )
            self._completed_steps.append("final_audit")

            return await self.complete(output)

        except Exception as e:
            logger.exception(f"Governance decision {self.workflow_id} failed: {e}")
            self._failed_steps.append("governance_execution")
            raise
