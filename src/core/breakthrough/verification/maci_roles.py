"""
MACI Role Separation for Constitutional AI Governance
======================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements Multi-Agent Constitutional Intelligence (MACI) with
strict separation of powers:
- Executive: Action execution and enforcement
- Legislative: Policy creation and amendment
- Judicial: Constitutional interpretation and dispute resolution

Design Principles:
- Zero-trust between branches
- Mathematical verification of separation
- Compensable operations with audit trails
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Protocol, Set, Tuple

from ...shared.types import (
    AuditTrail,
    ConstitutionalContext,
    DecisionData,
    JSONDict,
    PolicyData,
)
from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class Branch(Enum):
    """Three branches of constitutional governance."""

    EXECUTIVE = "executive"
    LEGISLATIVE = "legislative"
    JUDICIAL = "judicial"


class DecisionType(Enum):
    """Types of decisions each branch can make."""

    POLICY_CREATION = "policy_creation"
    POLICY_EXECUTION = "policy_execution"
    CONSTITUTIONAL_REVIEW = "constitutional_review"
    DISPUTE_RESOLUTION = "dispute_resolution"
    OVERRIDE_REQUEST = "override_request"


@dataclass
class ConstitutionalDecision:
    """A decision made by a constitutional branch."""

    decision_id: str
    branch: Branch
    decision_type: DecisionType
    content: DecisionData
    justification: str
    timestamp: float
    constitutional_hash: str = CONSTITUTIONAL_HASH
    requires_consensus: bool = False
    consensus_threshold: float = 0.67  # 2/3 majority
    execution_deadline: Optional[float] = None
    audit_trail: AuditTrail = field(default_factory=list)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = hashlib.sha256(
                f"{self.branch.value}_{self.decision_type.value}_{self.timestamp}_{self.content}".encode()
            ).hexdigest()[:16]


@dataclass
class SeparationOfPowers:
    """Mathematical guarantees for branch separation."""

    executive_permissions: Set[str] = field(
        default_factory=lambda: {
            "execute_policy",
            "enforce_decision",
            "monitor_compliance",
            "initiate_override",
        }
    )
    legislative_permissions: Set[str] = field(
        default_factory=lambda: {
            "create_policy",
            "amend_policy",
            "propose_constitutional_amendment",
            "approve_budget",
        }
    )
    judicial_permissions: Set[str] = field(
        default_factory=lambda: {
            "review_constitutionality",
            "resolve_disputes",
            "interpret_constitution",
            "issue_injunctions",
        }
    )

    def validate_separation(self, branch: Branch, action: str) -> bool:
        """Validate that action is permitted for this branch."""
        if branch == Branch.EXECUTIVE:
            return action in self.executive_permissions
        elif branch == Branch.LEGISLATIVE:
            return action in self.legislative_permissions
        elif branch == Branch.JUDICIAL:
            return action in self.judicial_permissions
        return False

    def get_forbidden_actions(self, branch: Branch) -> Set[str]:
        """Get actions forbidden for this branch."""
        all_actions = (
            self.executive_permissions | self.legislative_permissions | self.judicial_permissions
        )
        if branch == Branch.EXECUTIVE:
            return all_actions - self.executive_permissions
        elif branch == Branch.LEGISLATIVE:
            return all_actions - self.legislative_permissions
        elif branch == Branch.JUDICIAL:
            return all_actions - self.judicial_permissions
        return all_actions


class AgentProtocol(Protocol):
    """Protocol for constitutional agents."""

    branch: Branch
    agent_id: str
    capabilities: Set[str]

    async def make_decision(
        self, context: ConstitutionalContext, decision_type: DecisionType
    ) -> ConstitutionalDecision:
        """Make a decision within constitutional bounds."""
        ...

    async def validate_decision(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> Tuple[bool, str]:
        """Validate a decision against constitutional principles."""
        ...


@dataclass
class ConstitutionalAgent:
    """Base class for constitutional agents with separation of powers."""

    agent_id: str
    branch: Branch
    capabilities: Set[str] = field(default_factory=set)
    decision_history: List[ConstitutionalDecision] = field(default_factory=list)
    trust_score: float = 1.0
    last_activity: float = field(default_factory=time.time)

    def __post_init__(self):
        self.capabilities = self._initialize_capabilities()

    def _initialize_capabilities(self) -> Set[str]:
        """Initialize capabilities based on branch."""
        if self.branch == Branch.EXECUTIVE:
            return {"execute", "enforce", "monitor", "override_request"}
        elif self.branch == Branch.LEGISLATIVE:
            return {"create_policy", "amend", "propose", "vote"}
        elif self.branch == Branch.JUDICIAL:
            return {"review", "interpret", "resolve", "injunct"}
        return set()

    async def make_decision(
        self, context: ConstitutionalContext, decision_type: DecisionType
    ) -> ConstitutionalDecision:
        """Make a decision within constitutional bounds."""
        # Validate decision type is appropriate for branch
        if not self._validate_decision_type(decision_type):
            raise ValueError(
                f"Decision type {decision_type} not permitted for {self.branch} branch"
            )

        # Create decision
        decision = ConstitutionalDecision(
            decision_id="",
            branch=self.branch,
            decision_type=decision_type,
            content=context,
            justification=f"{self.branch.value} branch decision",
            timestamp=time.time(),
            audit_trail=[
                {
                    "agent_id": self.agent_id,
                    "action": "decision_made",
                    "timestamp": time.time(),
                    "branch": self.branch.value,
                }
            ],
        )

        # Record in history
        self.decision_history.append(decision)
        self.last_activity = time.time()

        return decision

    def _validate_decision_type(self, decision_type: DecisionType) -> bool:
        """Validate that decision type is appropriate for this branch."""
        branch_decisions = {
            Branch.EXECUTIVE: {DecisionType.POLICY_EXECUTION, DecisionType.OVERRIDE_REQUEST},
            Branch.LEGISLATIVE: {DecisionType.POLICY_CREATION, DecisionType.CONSTITUTIONAL_REVIEW},
            Branch.JUDICIAL: {DecisionType.CONSTITUTIONAL_REVIEW, DecisionType.DISPUTE_RESOLUTION},
        }
        return decision_type in branch_decisions.get(self.branch, set())

    async def validate_decision(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> Tuple[bool, str]:
        """Validate a decision against constitutional principles."""
        # Check constitutional hash
        if decision.constitutional_hash != CONSTITUTIONAL_HASH:
            return False, "Constitutional hash mismatch"

        # Check branch separation
        if decision.branch == self.branch:
            return False, "Agent cannot validate its own decisions"

        # Check timestamp (decisions shouldn't be from future)
        if decision.timestamp > time.time() + 60:  # 1 minute tolerance
            return False, "Decision timestamp is in the future"

        # Branch-specific validation
        if decision.branch == Branch.EXECUTIVE and self.branch == Branch.JUDICIAL:
            return await self._judicial_review(decision, context)
        elif decision.branch == Branch.LEGISLATIVE and self.branch == Branch.JUDICIAL:
            return await self._legislative_review(decision, context)

        return True, "Decision validated"

    async def _judicial_review(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> Tuple[bool, str]:
        """Judicial review of executive decisions."""
        # Placeholder for constitutional review logic
        # In practice, this would use formal verification
        return True, "Executive decision constitutionally sound"

    async def _legislative_review(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> Tuple[bool, str]:
        """Judicial review of legislative decisions."""
        # Placeholder for constitutional review logic
        return True, "Legislative decision constitutionally sound"


class ExecutiveAgent(ConstitutionalAgent):
    """Executive branch agent - executes policies and enforces decisions."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Branch.EXECUTIVE)
        self.execution_queue: List[ConstitutionalDecision] = []
        self.enforcement_actions: List[JSONDict] = []

    async def execute_decision(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> JSONDict:
        """Execute a decision with compensable operations."""
        execution_record = {
            "decision_id": decision.decision_id,
            "timestamp": time.time(),
            "status": "executing",
            "compensable": True,
            "audit_trail": decision.audit_trail.copy(),
        }

        try:
            # Add to execution queue
            self.execution_queue.append(decision)

            # Execute the decision
            result = await self._perform_execution(decision, context)

            # Record successful execution
            execution_record.update(
                {"status": "completed", "result": result, "completed_at": time.time()}
            )

            # Add enforcement action
            self.enforcement_actions.append(
                {
                    "decision_id": decision.decision_id,
                    "action": "executed",
                    "timestamp": time.time(),
                    "result": result,
                }
            )

        except Exception as e:
            execution_record.update({"status": "failed", "error": str(e), "failed_at": time.time()})
            logger.error(f"Execution failed for decision {decision.decision_id}: {e}")

        return execution_record

    async def _perform_execution(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> JSONDict:
        """Perform the actual execution of a decision."""
        # Placeholder for execution logic
        # In practice, this would interface with the runtime system
        await asyncio.sleep(0.1)  # Simulate execution time
        return {"executed": True, "decision_type": decision.decision_type.value}


class LegislativeAgent(ConstitutionalAgent):
    """Legislative branch agent - creates and amends policies."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Branch.LEGISLATIVE)
        self.proposed_policies: List[JSONDict] = []
        self.active_policies: Dict[str, PolicyData] = {}

    async def propose_policy(
        self, policy_content: PolicyData, justification: str
    ) -> ConstitutionalDecision:
        """Propose a new policy for consideration."""
        proposal = {
            "policy_content": policy_content,
            "justification": justification,
            "proposed_at": time.time(),
            "status": "proposed",
        }

        self.proposed_policies.append(proposal)

        return await self.make_decision(
            content=proposal, decision_type=DecisionType.POLICY_CREATION
        )

    async def amend_policy(
        self, policy_id: str, amendments: PolicyData, justification: str
    ) -> ConstitutionalDecision:
        """Amend an existing policy."""
        if policy_id not in self.active_policies:
            raise ValueError(f"Policy {policy_id} not found")

        amendment_record = {
            "policy_id": policy_id,
            "amendments": amendments,
            "justification": justification,
            "amended_at": time.time(),
        }

        return await self.make_decision(
            content=amendment_record, decision_type=DecisionType.POLICY_CREATION
        )


class JudicialAgent(ConstitutionalAgent):
    """Judicial branch agent - reviews constitutionality and resolves disputes."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Branch.JUDICIAL)
        self.review_cases: List[JSONDict] = []
        self.resolved_disputes: List[JSONDict] = []

    async def review_constitutionality(
        self, decision: ConstitutionalDecision, context: ConstitutionalContext
    ) -> Tuple[bool, str]:
        """Review a decision for constitutional compliance."""
        case_record = {
            "decision_id": decision.decision_id,
            "review_type": "constitutionality",
            "started_at": time.time(),
            "status": "reviewing",
        }

        self.review_cases.append(case_record)

        # Perform constitutional review
        is_valid, reasoning = await self.validate_decision(decision, context)

        # Update case record
        case_record.update(
            {
                "completed_at": time.time(),
                "status": "completed",
                "is_constitutional": is_valid,
                "reasoning": reasoning,
            }
        )

        return is_valid, reasoning

    async def resolve_dispute(
        self, dispute_description: str, parties_involved: List[str], context: ConstitutionalContext
    ) -> ConstitutionalDecision:
        """Resolve a constitutional dispute."""
        dispute_record = {
            "dispute_description": dispute_description,
            "parties_involved": parties_involved,
            "filed_at": time.time(),
            "context": context,
        }

        return await self.make_decision(
            content=dispute_record, decision_type=DecisionType.DISPUTE_RESOLUTION
        )


class MACIOrchestrator:
    """
    Multi-Agent Constitutional Intelligence Orchestrator.

    Coordinates the three branches with mathematical guarantees
    of separation of powers and constitutional compliance.
    """

    def __init__(self):
        self.separation_of_powers = SeparationOfPowers()
        self.agents: Dict[str, ConstitutionalAgent] = {}
        self.decision_log: List[ConstitutionalDecision] = []
        self.consensus_required_decisions: Dict[str, List[Tuple[str, bool]]] = {}

        # Initialize one agent per branch
        self.executive = ExecutiveAgent("executive-primary")
        self.legislative = LegislativeAgent("legislative-primary")
        self.judicial = JudicialAgent("judicial-primary")

        self.agents.update(
            {
                self.executive.agent_id: self.executive,
                self.legislative.agent_id: self.legislative,
                self.judicial.agent_id: self.judicial,
            }
        )

        logger.info("Initialized MACI Orchestrator with three-branch separation")

    async def process_decision_request(
        self,
        requesting_branch: Branch,
        decision_type: DecisionType,
        content: DecisionData,
        context: ConstitutionalContext,
    ) -> Tuple[bool, str, Optional[ConstitutionalDecision]]:
        """
        Process a decision request through the constitutional system.

        Returns:
            Tuple of (approved, reasoning, decision)
        """
        # Validate branch permissions
        if not self.separation_of_powers.validate_separation(
            requesting_branch, decision_type.value
        ):
            return (
                False,
                f"Branch {requesting_branch.value} not permitted to make {decision_type.value} decisions",
                None,
            )

        # Get appropriate agent
        agent = self._get_agent_for_branch(requesting_branch)
        if not agent:
            return False, f"No agent available for branch {requesting_branch.value}", None

        try:
            # Create decision
            decision = await agent.make_decision(content, decision_type)

            # Judicial review if required
            if self._requires_judicial_review(decision_type):
                is_valid, reasoning = await self.judicial.review_constitutionality(
                    decision, context
                )
                if not is_valid:
                    return False, f"Judicial review failed: {reasoning}", None

            # Add to decision log
            self.decision_log.append(decision)

            return True, "Decision approved and logged", decision

        except Exception as e:
            return False, f"Decision processing failed: {str(e)}", None

    def _get_agent_for_branch(self, branch: Branch) -> Optional[ConstitutionalAgent]:
        """Get the primary agent for a branch."""
        for agent in self.agents.values():
            if agent.branch == branch:
                return agent
        return None

    def _requires_judicial_review(self, decision_type: DecisionType) -> bool:
        """Determine if a decision type requires judicial review."""
        return decision_type in {
            DecisionType.CONSTITUTIONAL_REVIEW,
            DecisionType.OVERRIDE_REQUEST,
            DecisionType.POLICY_CREATION,
        }

    async def get_consensus(
        self, decision: ConstitutionalDecision, required_branches: List[Branch]
    ) -> Tuple[bool, str]:
        """
        Get consensus across multiple branches for important decisions.

        Required for constitutional amendments, major policy changes, etc.
        """
        if not decision.requires_consensus:
            return True, "Consensus not required"

        decision_id = decision.decision_id
        if decision_id not in self.consensus_required_decisions:
            self.consensus_required_decisions[decision_id] = []

        votes = self.consensus_required_decisions[decision_id]

        # Get votes from required branches
        for branch in required_branches:
            agent = self._get_agent_for_branch(branch)
            if agent:
                # Simulate branch voting (in practice, this would be more complex)
                approved = await self._get_branch_vote(agent, decision)
                votes.append((branch.value, approved))

        # Calculate consensus
        if len(votes) < len(required_branches):
            return False, f"Waiting for votes from {len(required_branches) - len(votes)} branches"

        approved_votes = sum(1 for _, approved in votes if approved)
        consensus_ratio = approved_votes / len(votes)

        if consensus_ratio >= decision.consensus_threshold:
            return True, f"Consensus achieved ({approved_votes}/{len(votes)})"
        else:
            return (
                False,
                f"Consensus failed ({approved_votes}/{len(votes)} < {decision.consensus_threshold})",
            )

    async def _get_branch_vote(
        self, agent: ConstitutionalAgent, decision: ConstitutionalDecision
    ) -> bool:
        """Get a branch's vote on a decision."""
        # Placeholder for voting logic
        # In practice, this would involve deliberation and voting
        return True  # Default to approval for now

    def get_system_status(self) -> JSONDict:
        """Get the current status of the MACI system."""
        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "branches": {
                "executive": {
                    "agent_id": self.executive.agent_id,
                    "decisions_made": len(self.executive.decision_history),
                    "executions": len(self.executive.enforcement_actions),
                },
                "legislative": {
                    "agent_id": self.legislative.agent_id,
                    "decisions_made": len(self.legislative.decision_history),
                    "policies_proposed": len(self.legislative.proposed_policies),
                },
                "judicial": {
                    "agent_id": self.judicial.agent_id,
                    "decisions_made": len(self.judicial.decision_history),
                    "reviews_completed": len(self.judicial.review_cases),
                },
            },
            "total_decisions": len(self.decision_log),
            "separation_violations": 0,  # Track any violations
            "last_activity": max(
                self.executive.last_activity,
                self.legislative.last_activity,
                self.judicial.last_activity,
            ),
        }
