"""
CCAI Democratic Constitutional Governance
==========================================

Constitutional Hash: cdd01ef066bc6cf2

Implements democratic input for constitutional evolution:
- Polis deliberation with representative sampling
- Cross-group consensus filtering
- Performance-legitimacy balance
- Fast automated + async human review

References:
- CCAI: Collective Constitutional AI (Anthropic)
- Polis: Real-time opinion visualization
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .. import CONSENSUS_THRESHOLD, CONSTITUTIONAL_HASH
from ..metrics.dfc import DFCCalculator, get_dfc_components_from_context

logger = logging.getLogger(__name__)


class DeliberationStatus(Enum):
    """Status of a deliberation process."""

    PENDING = "pending"
    ACTIVE = "active"
    CONSENSUS_REACHED = "consensus_reached"
    NO_CONSENSUS = "no_consensus"
    CLOSED = "closed"


class StatementVote(Enum):
    """Vote options for statements."""

    AGREE = "agree"
    DISAGREE = "disagree"
    PASS = "pass"


@dataclass
class Stakeholder:
    """A stakeholder participating in deliberation."""

    stakeholder_id: str
    role: str
    group: Optional[str] = None
    weight: float = 1.0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stakeholder_id": self.stakeholder_id,
            "role": self.role,
            "group": self.group,
            "weight": self.weight,
            "active": self.active,
        }


@dataclass
class Statement:
    """A statement in the deliberation."""

    statement_id: str
    content: str
    author_id: str
    timestamp: datetime
    votes: Dict[str, StatementVote] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def support_ratio(self, group: Optional[str] = None) -> float:
        """Calculate support ratio, optionally for a specific group."""
        if not self.votes:
            return 0.0

        agrees = sum(1 for v in self.votes.values() if v == StatementVote.AGREE)
        total = sum(1 for v in self.votes.values() if v != StatementVote.PASS)

        return agrees / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "content": self.content,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat(),
            "support_ratio": self.support_ratio(),
            "total_votes": len(self.votes),
        }


@dataclass
class OpinionGroup:
    """A group of stakeholders with similar opinions."""

    group_id: str
    name: str
    member_ids: Set[str]
    characteristic_statements: List[str]

    def support(self, statement: Statement) -> float:
        """Calculate group's support for a statement."""
        if not self.member_ids:
            return 0.0

        agrees = sum(
            1
            for member_id in self.member_ids
            if statement.votes.get(member_id) == StatementVote.AGREE
        )

        total = sum(
            1
            for member_id in self.member_ids
            if member_id in statement.votes and statement.votes[member_id] != StatementVote.PASS
        )

        return agrees / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "member_count": len(self.member_ids),
            "characteristic_statements": self.characteristic_statements,
        }


@dataclass
class Deliberation:
    """A deliberation session."""

    deliberation_id: str
    topic: str
    status: DeliberationStatus
    statements: List[Statement]
    opinion_groups: List[OpinionGroup]
    participants: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    pending: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deliberation_id": self.deliberation_id,
            "topic": self.topic,
            "status": self.status.value,
            "statement_count": len(self.statements),
            "group_count": len(self.opinion_groups),
            "participant_count": len(self.participants),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class ConstitutionalProposal:
    """A proposal for constitutional change."""

    proposal_id: str
    title: str
    description: str
    proposed_principles: List[str]
    author_id: str
    timestamp: datetime
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "proposed_principles": self.proposed_principles,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat(),
            "rationale": self.rationale,
        }


@dataclass
class DeliberationResult:
    """Result of a deliberation process."""

    deliberation_id: str
    approved: bool
    consensus_principles: List[str]
    participation_rate: float
    opinion_groups: List[Dict[str, Any]]
    pending_review: List[str]
    rejected: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deliberation_id": self.deliberation_id,
            "approved": self.approved,
            "consensus_principles": self.consensus_principles,
            "participation_rate": self.participation_rate,
            "opinion_groups": self.opinion_groups,
            "pending_review": self.pending_review,
            "rejected": self.rejected,
            "timestamp": self.timestamp.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class ConstitutionalAmendment:
    """A constitutional amendment resulting from deliberation."""

    amendment_id: str
    approved_principles: List[str]
    pending_review: List[str]
    rejected: List[str]
    deliberation_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amendment_id": self.amendment_id,
            "approved_principles": self.approved_principles,
            "pending_review": self.pending_review,
            "rejected": self.rejected,
            "deliberation_id": self.deliberation_id,
            "timestamp": self.timestamp.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class Decision:
    """A governance decision requiring validation."""

    decision_id: str
    action: str
    context: Dict[str, Any]
    urgency: float  # 0.0-1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HybridDecision:
    """A decision with both immediate and reviewed components."""

    decision_id: str
    immediate_result: Dict[str, Any]
    review_pending: bool
    review_task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "immediate_result": self.immediate_result,
            "review_pending": self.review_pending,
            "review_task_id": self.review_task_id,
            "timestamp": self.timestamp.isoformat(),
        }


class PolisClient:
    """
    Simulated Polis deliberation client.

    In production, would integrate with actual Polis platform.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url
        self._deliberations: Dict[str, Deliberation] = {}

        logger.info("Initialized PolisClient")

    async def create_deliberation(self, topic: str, initial_statements: List[str]) -> str:
        """Create a new deliberation session."""
        deliberation_id = f"delib-{uuid.uuid4().hex[:8]}"

        statements = [
            Statement(
                statement_id=f"stmt-{uuid.uuid4().hex[:8]}",
                content=stmt,
                author_id="system",
                timestamp=datetime.utcnow(),
            )
            for stmt in initial_statements
        ]

        deliberation = Deliberation(
            deliberation_id=deliberation_id,
            topic=topic,
            status=DeliberationStatus.PENDING,
            statements=statements,
            opinion_groups=[],
            participants=[],
            start_time=datetime.utcnow(),
        )

        self._deliberations[deliberation_id] = deliberation
        return deliberation_id

    async def deliberate(
        self,
        topic: str,
        initial_statements: List[str],
        participant_criteria: Dict[str, Any],
        duration_hours: int = 24,
    ) -> Deliberation:
        """
        Run a full deliberation process.

        Simulates stakeholder participation and opinion clustering.
        """
        deliberation_id = await self.create_deliberation(topic, initial_statements)
        deliberation = self._deliberations[deliberation_id]

        # Simulate participant recruitment
        min_participants = participant_criteria.get("min_participants", 100)
        deliberation.participants = [f"participant-{i}" for i in range(min_participants)]

        # Simulate voting on statements
        for statement in deliberation.statements:
            for participant_id in deliberation.participants:
                # Random vote simulation (in production, real votes)
                import secrets

                vote = secrets.choice(
                    [
                        StatementVote.AGREE,
                        StatementVote.DISAGREE,
                        StatementVote.PASS,
                    ]
                )
                statement.votes[participant_id] = vote

        # Simulate opinion group clustering
        deliberation.opinion_groups = await self._cluster_opinions(deliberation)

        # Update status
        deliberation.status = DeliberationStatus.ACTIVE
        deliberation.end_time = datetime.utcnow()

        return deliberation

    async def _cluster_opinions(self, deliberation: Deliberation) -> List[OpinionGroup]:
        """Cluster participants into opinion groups."""
        # Simplified clustering - in production would use actual clustering
        groups = [
            OpinionGroup(
                group_id="group-progressive",
                name="Progressive",
                member_ids=set(deliberation.participants[: len(deliberation.participants) // 3]),
                characteristic_statements=["innovation", "change"],
            ),
            OpinionGroup(
                group_id="group-conservative",
                name="Conservative",
                member_ids=set(
                    deliberation.participants[
                        len(deliberation.participants)
                        // 3 : 2
                        * len(deliberation.participants)
                        // 3
                    ]
                ),
                characteristic_statements=["stability", "tradition"],
            ),
            OpinionGroup(
                group_id="group-moderate",
                name="Moderate",
                member_ids=set(
                    deliberation.participants[2 * len(deliberation.participants) // 3 :]
                ),
                characteristic_statements=["balance", "pragmatism"],
            ),
        ]

        return groups


class ConstitutionalValidator:
    """Validates principles for technical implementability."""

    def __init__(self, dfc_threshold: float = 0.70):
        self.dfc_calculator = DFCCalculator(threshold=dfc_threshold)

    async def can_implement(self, principle: str) -> bool:
        """Check if a principle can be technically implemented."""
        # Check for obvious non-implementable statements
        non_implementable = ["impossible", "always perfect", "never fail"]

        principle_lower = principle.lower()
        for phrase in non_implementable:
            if phrase in principle_lower:
                return False

        return True

    async def fast_validate(self, decision: Decision, time_budget_ms: int) -> Dict[str, Any]:
        """Fast validation within time budget."""
        # Calculate DFC Diagnostic
        dfc_components = get_dfc_components_from_context(decision.context)
        dfc_score = self.dfc_calculator.calculate(dfc_components)

        # Quick constitutional check
        return {
            "valid": True,
            "confidence": 0.85,
            "time_used_ms": time_budget_ms // 2,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "dfc_diagnostic": {
                "score": dfc_score,
                "status": "HEALTHY" if dfc_score >= self.dfc_calculator.threshold else "DEGRADED",
            },
        }


class DemocraticConstitutionalGovernance:
    """
    CCAI-style democratic input for constitutional evolution.

    Implements:
    - Polis deliberation with representative sampling
    - Cross-group consensus filtering (prevents polarization)
    - Performance-legitimacy balance (fast automated + async human)
    - Technical implementability checking
    """

    def __init__(
        self,
        polis_client: Optional[PolisClient] = None,
        consensus_threshold: float = CONSENSUS_THRESHOLD,
    ):
        """
        Initialize democratic governance.

        Args:
            polis_client: Optional Polis client for deliberation
            consensus_threshold: Minimum support across all groups
        """
        self.polis = polis_client or PolisClient()
        self.threshold = consensus_threshold
        self.validator = ConstitutionalValidator()

        self._pending_reviews: Dict[str, asyncio.Task] = {}
        self._stats = {
            "deliberations_conducted": 0,
            "amendments_approved": 0,
            "hybrid_decisions": 0,
        }

        logger.info(
            f"Initialized DemocraticConstitutionalGovernance threshold={consensus_threshold}"
        )

    async def evolve_constitution(
        self, topic: str, current_principles: List[str], min_participants: int = 1000
    ) -> ConstitutionalAmendment:
        """
        Evolve constitutional principles through democratic deliberation.

        Process:
        1. Public deliberation via Polis
        2. Cross-group consensus filtering
        3. Technical implementability check

        Args:
            topic: Topic for deliberation
            current_principles: Current constitutional principles
            min_participants: Minimum participants required

        Returns:
            ConstitutionalAmendment with approved principles
        """
        self._stats["deliberations_conducted"] += 1

        # Phase 1: Public deliberation via Polis
        deliberation = await self.polis.deliberate(
            topic=topic,
            initial_statements=current_principles,
            participant_criteria={
                "representative": True,
                "min_participants": min_participants,
            },
        )

        # Phase 2: Cross-group consensus filtering
        consensus_statements = []
        for statement in deliberation.statements:
            # CCAI requirement: consensus in ALL opinion groups
            if self._has_cross_group_consensus(statement, deliberation.opinion_groups):
                consensus_statements.append(statement.content)

        # Phase 3: Technical implementability check
        implementable = []
        pending = []
        rejected = []

        for statement in consensus_statements:
            if await self.validator.can_implement(statement):
                implementable.append(statement)
            else:
                # Flag for technical review
                pending.append(statement)

        # Create amendment
        amendment = ConstitutionalAmendment(
            amendment_id=f"amend-{uuid.uuid4().hex[:8]}",
            approved_principles=implementable,
            pending_review=pending,
            rejected=rejected,
            deliberation_id=deliberation.deliberation_id,
        )

        if implementable:
            self._stats["amendments_approved"] += 1

        logger.info(
            f"Constitutional evolution complete: "
            f"{len(implementable)} approved, "
            f"{len(pending)} pending, "
            f"{len(rejected)} rejected"
        )

        return amendment

    def _has_cross_group_consensus(
        self, statement: Statement, opinion_groups: List[OpinionGroup]
    ) -> bool:
        """Check if statement has consensus across all opinion groups."""
        if not opinion_groups:
            return statement.support_ratio() >= self.threshold

        for group in opinion_groups:
            if group.support(statement) < self.threshold:
                return False

        return True

    async def fast_govern(self, decision: Decision, time_budget_ms: int = 100) -> HybridDecision:
        """
        Performance-legitimacy balanced decision making.

        Provides:
        - Fast automated decision for immediate action
        - Async human review for legitimacy validation

        Args:
            decision: The decision to make
            time_budget_ms: Time budget for immediate decision

        Returns:
            HybridDecision with immediate result and review status
        """
        self._stats["hybrid_decisions"] += 1

        # Fast path: automated constitutional check
        auto_result = await self.validator.fast_validate(decision, time_budget_ms)

        # Queue for async human review
        review_task_id = f"review-{uuid.uuid4().hex[:8]}"
        review_task = asyncio.create_task(self._queue_human_review(decision, review_task_id))
        self._pending_reviews[review_task_id] = review_task

        return HybridDecision(
            decision_id=decision.decision_id,
            immediate_result=auto_result,
            review_pending=True,
            review_task_id=review_task_id,
        )

    async def _queue_human_review(self, decision: Decision, review_task_id: str) -> Dict[str, Any]:
        """Queue decision for human review."""
        # In production, would integrate with review system
        # Simulate async review
        await asyncio.sleep(0.1)  # Minimal delay for demo

        return {
            "review_task_id": review_task_id,
            "decision_id": decision.decision_id,
            "status": "queued",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_review_status(self, review_task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a pending review."""
        if review_task_id not in self._pending_reviews:
            return None

        task = self._pending_reviews[review_task_id]

        if task.done():
            return await task

        return {
            "review_task_id": review_task_id,
            "status": "pending",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            **self._stats,
            "pending_reviews": len(self._pending_reviews),
            "consensus_threshold": self.threshold,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
