"""
ACGS-2 Voting Workflow
Constitutional Hash: cdd01ef066bc6cf2

Consensus-based decision making for multi-agent coordination.
Supports multiple voting strategies: majority, unanimous, weighted.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..base.result import WorkflowResult, WorkflowStatus
from ..base.workflow import BaseWorkflow

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


class VotingStrategy(Enum):
    """Voting strategy types."""

    MAJORITY = "majority"  # >50% approval
    SUPERMAJORITY = "supermajority"  # >66% approval
    UNANIMOUS = "unanimous"  # 100% approval
    WEIGHTED = "weighted"  # Weight-based threshold
    QUORUM = "quorum"  # Minimum participation required


class VoteDecision(Enum):
    """Individual vote decisions."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """Individual vote from an agent."""

    agent_id: str
    decision: VoteDecision
    weight: float = 1.0
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "decision": self.decision.value,
            "weight": self.weight,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class VotingResult:
    """Result of voting process."""

    voting_id: str
    decision: VoteDecision
    strategy: VotingStrategy
    votes: List[Vote]
    approval_rate: float
    quorum_met: bool
    constitutional_hash: str = CONSTITUTIONAL_HASH
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "voting_id": self.voting_id,
            "decision": self.decision.value,
            "strategy": self.strategy.value,
            "votes": [v.to_dict() for v in self.votes],
            "approval_rate": self.approval_rate,
            "quorum_met": self.quorum_met,
            "constitutional_hash": self.constitutional_hash,
            "details": self.details,
        }


class VotingWorkflow(BaseWorkflow):
    """
    Voting workflow for multi-agent consensus.

    Implements configurable voting strategies for distributed
    decision making with constitutional compliance.

    Strategies:
    - MAJORITY: More than 50% approval required
    - SUPERMAJORITY: More than 66% approval required
    - UNANIMOUS: 100% approval required
    - WEIGHTED: Uses agent weights for voting power
    - QUORUM: Requires minimum participation

    Example:
        workflow = VotingWorkflow(
            eligible_agents=["agent-1", "agent-2", "agent-3"],
            strategy=VotingStrategy.MAJORITY,
        )
        result = await workflow.run({
            "proposal": "Allow high-impact message",
            "context": {"message_id": "123"}
        })
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        eligible_agents: Optional[List[str]] = None,
        strategy: VotingStrategy = VotingStrategy.MAJORITY,
        voting_timeout_seconds: int = 30,
        quorum_percentage: float = 0.5,
        approval_threshold: float = 0.5,
        agent_weights: Optional[Dict[str, float]] = None,
        vote_collector: Optional[Callable] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        """
        Initialize voting workflow.

        Args:
            workflow_id: Unique workflow identifier
            eligible_agents: List of agent IDs allowed to vote
            strategy: Voting strategy to use
            voting_timeout_seconds: Maximum time to wait for votes
            quorum_percentage: Minimum participation required (0.0-1.0)
            approval_threshold: Approval threshold for weighted voting
            agent_weights: Optional weights per agent for weighted voting
            vote_collector: Optional function to collect votes from agents
            constitutional_hash: Expected constitutional hash
        """
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="voting",
            constitutional_hash=constitutional_hash,
        )
        self.eligible_agents = set(eligible_agents or [])
        self.strategy = strategy
        self.voting_timeout = voting_timeout_seconds
        self.quorum_percentage = quorum_percentage
        self.approval_threshold = approval_threshold
        self.agent_weights = agent_weights or {}
        self.vote_collector = vote_collector

        self._votes: List[Vote] = []
        self._voted_agents: Set[str] = set()

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute voting workflow.

        Args:
            input: Voting input with proposal details

        Returns:
            WorkflowResult with voting outcome
        """
        proposal = input.get("proposal", "")
        context_data = input.get("context", {})
        voting_id = str(uuid.uuid4())

        logger.info(
            f"Voting {voting_id}: Starting {self.strategy.value} vote "
            f"with {len(self.eligible_agents)} eligible agents"
        )

        try:
            # Collect votes
            if self.vote_collector:
                await self._collect_votes_external(proposal, context_data)
            else:
                await self._collect_votes_simulated(proposal, context_data)

            # Calculate result
            voting_result = self._calculate_result(voting_id)

            # Store result in context
            self.context.set_step_result("voting_result", voting_result.to_dict())

            # Create workflow result
            if voting_result.decision == VoteDecision.APPROVE:
                return WorkflowResult.success(
                    workflow_id=self.workflow_id,
                    output=voting_result.to_dict(),
                    execution_time_ms=self.context.get_elapsed_time_ms(),
                    steps_completed=["vote_collection", "vote_calculation"],
                )
            else:
                return WorkflowResult(
                    workflow_id=self.workflow_id,
                    status=WorkflowStatus.COMPLETED,
                    output=voting_result.to_dict(),
                    execution_time_ms=self.context.get_elapsed_time_ms(),
                    steps_completed=["vote_collection", "vote_calculation"],
                    metadata={"decision": "rejected"},
                )

        except asyncio.TimeoutError:
            logger.warning(f"Voting {voting_id}: Timeout after {self.voting_timeout}s")
            return WorkflowResult.timeout(
                workflow_id=self.workflow_id,
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=["vote_collection"],
            )

        except Exception as e:
            logger.exception(f"Voting {voting_id}: Error: {e}")
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                errors=[f"Voting error: {e}"],
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=[],
                steps_failed=["vote_collection"],
            )

    async def _collect_votes_external(self, proposal: str, context: Dict[str, Any]) -> None:
        """Collect votes using external vote collector."""

        async def collect_single_vote(agent_id: str) -> Optional[Vote]:
            try:
                result = await asyncio.wait_for(
                    self.vote_collector(agent_id, proposal, context),
                    timeout=self.voting_timeout / len(self.eligible_agents),
                )
                return Vote(
                    agent_id=agent_id,
                    decision=VoteDecision(result.get("decision", "abstain")),
                    weight=self.agent_weights.get(agent_id, 1.0),
                    reasoning=result.get("reasoning"),
                )
            except Exception as e:
                logger.warning(f"Vote collection failed for {agent_id}: {e}")
                return None

        # Collect votes concurrently
        tasks = [collect_single_vote(agent_id) for agent_id in self.eligible_agents]
        results = await asyncio.gather(*tasks)

        for vote in results:
            if vote:
                self._votes.append(vote)
                self._voted_agents.add(vote.agent_id)

    async def _collect_votes_simulated(self, proposal: str, context: Dict[str, Any]) -> None:
        """Simulate vote collection for testing."""
        # In real implementation, this would call agent endpoints
        for agent_id in self.eligible_agents:
            # Simulated vote - in production, call agent's vote endpoint
            vote = Vote(
                agent_id=agent_id,
                decision=VoteDecision.APPROVE,  # Default approve for simulation
                weight=self.agent_weights.get(agent_id, 1.0),
                reasoning="Simulated vote",
            )
            self._votes.append(vote)
            self._voted_agents.add(agent_id)

    def _calculate_result(self, voting_id: str) -> VotingResult:
        """Calculate voting result based on strategy."""
        total_eligible = len(self.eligible_agents)
        total_voted = len(self._voted_agents)

        # Check quorum
        quorum_met = (
            (total_voted / total_eligible) >= self.quorum_percentage
            if total_eligible > 0
            else False
        )

        # Calculate approval rate
        approvals = sum(1 for v in self._votes if v.decision == VoteDecision.APPROVE)
        rejections = sum(1 for v in self._votes if v.decision == VoteDecision.REJECT)
        abstentions = sum(1 for v in self._votes if v.decision == VoteDecision.ABSTAIN)

        # For weighted voting
        weighted_approvals = sum(
            v.weight for v in self._votes if v.decision == VoteDecision.APPROVE
        )
        total_weight = sum(v.weight for v in self._votes)

        # Calculate approval rate based on strategy
        if self.strategy == VotingStrategy.WEIGHTED:
            approval_rate = weighted_approvals / total_weight if total_weight > 0 else 0.0
        else:
            non_abstaining = approvals + rejections
            approval_rate = approvals / non_abstaining if non_abstaining > 0 else 0.0

        # Determine decision based on strategy
        decision = self._apply_strategy(approval_rate, quorum_met, approvals, rejections)

        return VotingResult(
            voting_id=voting_id,
            decision=decision,
            strategy=self.strategy,
            votes=self._votes.copy(),
            approval_rate=approval_rate,
            quorum_met=quorum_met,
            constitutional_hash=self.constitutional_hash,
            details={
                "total_eligible": total_eligible,
                "total_voted": total_voted,
                "approvals": approvals,
                "rejections": rejections,
                "abstentions": abstentions,
                "weighted_approvals": weighted_approvals,
                "total_weight": total_weight,
            },
        )

    def _apply_strategy(
        self, approval_rate: float, quorum_met: bool, approvals: int, rejections: int
    ) -> VoteDecision:
        """Apply voting strategy to determine outcome."""
        # Quorum check for QUORUM strategy
        if self.strategy == VotingStrategy.QUORUM and not quorum_met:
            return VoteDecision.REJECT

        if self.strategy == VotingStrategy.UNANIMOUS:
            return (
                VoteDecision.APPROVE if rejections == 0 and approvals > 0 else VoteDecision.REJECT
            )

        if self.strategy == VotingStrategy.SUPERMAJORITY:
            return VoteDecision.APPROVE if approval_rate > 0.66 else VoteDecision.REJECT

        if self.strategy == VotingStrategy.WEIGHTED:
            return (
                VoteDecision.APPROVE
                if approval_rate >= self.approval_threshold
                else VoteDecision.REJECT
            )

        # Default: MAJORITY
        return VoteDecision.APPROVE if approval_rate > 0.5 else VoteDecision.REJECT

    def add_vote(self, vote: Vote) -> bool:
        """
        Manually add a vote.

        Args:
            vote: Vote to add

        Returns:
            True if vote was added, False if agent already voted
        """
        if vote.agent_id in self._voted_agents:
            return False

        if vote.agent_id not in self.eligible_agents:
            logger.warning(f"Vote from ineligible agent: {vote.agent_id}")
            return False

        self._votes.append(vote)
        self._voted_agents.add(vote.agent_id)
        return True


__all__ = [
    "VotingStrategy",
    "VoteDecision",
    "Vote",
    "VotingResult",
    "VotingWorkflow",
]
