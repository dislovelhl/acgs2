"""
CCAI Framework - Constitutional Consensus AI
==============================================

Constitutional Hash: cdd01ef066bc6cf2

Implements democratic governance through Polis-style deliberation:
- Cross-group consensus building
- Liquid democracy with constitutional constraints
- Stakeholder participation with mathematical guarantees
- Democratic legitimacy through verified consensus

Design Principles:
- All decisions grounded in constitutional principles
- Cross-cutting cleavages prevent polarization
- Mathematical consensus thresholds
- Transparent deliberation process
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class ConsensusLevel(Enum):
    """Levels of consensus achievement."""

    UNANIMOUS = 1.0  # All participants agree
    SUPERMAJORITY = 0.75  # 3/4 agreement
    MAJORITY = 0.5  # Simple majority
    PLURALITY = 0.33  # Largest group agrees
    MINIMUM = 0.25  # Minimum viable consensus
    NO_CONSENSUS = 0.0  # No agreement reached


class StakeholderGroup(Enum):
    """Stakeholder groups in constitutional governance."""

    EXECUTIVE_AGENTS = "executive_agents"
    LEGISLATIVE_AGENTS = "legislative_agents"
    JUDICIAL_AGENTS = "judicial_agents"
    END_USERS = "end_users"
    SYSTEM_OPERATORS = "system_operators"
    SECURITY_AUDITORS = "security_auditors"
    COMPLIANCE_OFFICERS = "compliance_officers"
    EXTERNAL_STAKEHOLDERS = "external_stakeholders"


class DeliberationPhase(Enum):
    """Phases of Polis-style deliberation."""

    PROPOSAL_SUBMISSION = "proposal_submission"
    INITIAL_VOTING = "initial_voting"
    CLUSTER_ANALYSIS = "cluster_analysis"
    CROSS_GROUP_DIALOGUE = "cross_group_dialogue"
    CONSENSUS_BUILDING = "consensus_building"
    FINAL_VOTE = "final_vote"
    DECISION_MADE = "decision_made"


@dataclass
class Stakeholder:
    """A participant in constitutional governance."""

    stakeholder_id: str
    group: StakeholderGroup
    name: str
    trust_score: float = 1.0
    participation_count: int = 0
    consensus_contribution: float = 0.0
    constitutional_alignment: float = 1.0

    def __post_init__(self):
        if not self.stakeholder_id:
            self.stakeholder_id = hashlib.sha256(
                f"{self.group.value}_{self.name}_{time.time()}".encode()
            ).hexdigest()[:16]


@dataclass
class Proposal:
    """A governance proposal for deliberation."""

    proposal_id: str
    title: str
    description: str
    proposer: Stakeholder
    content: Dict[str, Any]
    constitutional_grounding: List[str]  # Constitutional principles this addresses

    # Deliberation metadata
    submitted_at: float = field(default_factory=time.time)
    phase: DeliberationPhase = DeliberationPhase.PROPOSAL_SUBMISSION

    # Voting data
    votes_for: Set[str] = field(default_factory=set)
    votes_against: Set[str] = field(default_factory=set)
    abstentions: Set[str] = field(default_factory=set)

    # Consensus analysis
    consensus_level: ConsensusLevel = ConsensusLevel.NO_CONSENSUS
    consensus_score: float = 0.0

    # Cross-group dialogue
    dialogue_threads: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = hashlib.sha256(
                f"{self.title}_{self.proposer.stakeholder_id}_{self.submitted_at}".encode()
            ).hexdigest()[:16]


@dataclass
class VotingCluster:
    """A cluster of stakeholders with similar voting patterns."""

    cluster_id: str
    stakeholders: Set[str]
    centroid_position: Dict[str, float]  # Position in policy space
    cluster_size: int = 0
    polarization_score: float = 0.0
    consensus_potential: float = 0.0

    def __post_init__(self):
        self.cluster_size = len(self.stakeholders)


@dataclass
class DeliberationSession:
    """A complete deliberation session."""

    session_id: str
    proposals: List[Proposal] = field(default_factory=list)
    stakeholders: Dict[str, Stakeholder] = field(default_factory=dict)
    clusters: List[VotingCluster] = field(default_factory=list)

    # Session state
    current_phase: DeliberationPhase = DeliberationPhase.PROPOSAL_SUBMISSION
    started_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None

    # Consensus tracking
    consensus_threshold: float = 0.67  # 2/3 majority default
    decisions_made: List[Proposal] = field(default_factory=list)

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    constitutional_violations: List[str] = field(default_factory=list)


class CCAIFramework:
    """
    Constitutional Consensus AI Framework.

    Implements democratic governance through Polis-style deliberation:
    - Cross-group consensus building prevents polarization
    - Liquid democracy with constitutional constraints
    - Mathematical consensus analysis
    - Transparent, verifiable deliberation process

    This enables legitimate democratic governance with mathematical guarantees.
    """

    def __init__(
        self,
        consensus_threshold: float = 0.67,
        min_participants: int = 5,
        deliberation_timeout_hours: int = 24,
    ):
        """
        Initialize CCAI Framework.

        Args:
            consensus_threshold: Minimum consensus score required (0.0-1.0)
            min_participants: Minimum stakeholders for valid deliberation
            deliberation_timeout_hours: Maximum time for deliberation
        """
        self.consensus_threshold = consensus_threshold
        self.min_participants = min_participants
        self.deliberation_timeout_hours = deliberation_timeout_hours

        # Active sessions
        self.active_sessions: Dict[str, DeliberationSession] = {}

        # Stakeholder registry
        self.registered_stakeholders: Dict[str, Stakeholder] = {}

        # Historical data for learning
        self.deliberation_history: List[DeliberationSession] = []
        self.consensus_patterns: Dict[str, Dict[str, Any]] = {}

        # Performance metrics
        self._metrics = {
            "sessions_completed": 0,
            "consensus_achieved": 0,
            "avg_deliberation_time": 0.0,
            "participation_rate": 0.0,
            "constitutional_compliance": 0.0,
        }

        logger.info(
            f"Initialized CCAI Framework with threshold={consensus_threshold}, "
            f"min_participants={min_participants}"
        )

    async def create_deliberation_session(
        self,
        session_title: str,
        stakeholders: List[Stakeholder],
        deadline_hours: Optional[int] = None,
    ) -> DeliberationSession:
        """
        Create a new deliberation session.

        Args:
            session_title: Title for the deliberation session
            stakeholders: Participating stakeholders
            deadline_hours: Optional custom deadline

        Returns:
            New deliberation session
        """
        session_id = hashlib.sha256(f"session_{session_title}_{time.time()}".encode()).hexdigest()[
            :16
        ]

        deadline = None
        if deadline_hours:
            deadline = time.time() + (deadline_hours * 3600)
        elif self.deliberation_timeout_hours:
            deadline = time.time() + (self.deliberation_timeout_hours * 3600)

        session = DeliberationSession(
            session_id=session_id,
            stakeholders={s.stakeholder_id: s for s in stakeholders},
            deadline=deadline,
        )

        self.active_sessions[session_id] = session

        # Register stakeholders if not already registered
        for stakeholder in stakeholders:
            if stakeholder.stakeholder_id not in self.registered_stakeholders:
                self.registered_stakeholders[stakeholder.stakeholder_id] = stakeholder

        logger.info(
            f"Created deliberation session {session_id} with {len(stakeholders)} stakeholders"
        )
        return session

    async def submit_proposal(
        self,
        session_id: str,
        proposer: Stakeholder,
        title: str,
        description: str,
        content: Dict[str, Any],
        constitutional_grounding: List[str],
    ) -> Proposal:
        """
        Submit a proposal for deliberation.

        Args:
            session_id: Session to submit to
            proposer: Stakeholder making the proposal
            title: Proposal title
            description: Detailed description
            content: Proposal content
            constitutional_grounding: Constitutional principles addressed

        Returns:
            Submitted proposal
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.current_phase != DeliberationPhase.PROPOSAL_SUBMISSION:
            raise ValueError(
                f"Session {session_id} not accepting proposals "
                f"(phase: {session.current_phase.value})"
            )

        proposal = Proposal(
            proposal_id="",
            title=title,
            description=description,
            proposer=proposer,
            content=content,
            constitutional_grounding=constitutional_grounding,
        )

        session.proposals.append(proposal)

        # Validate constitutional grounding
        await self._validate_constitutional_grounding(proposal)

        logger.info(f"Submitted proposal {proposal.proposal_id} to session {session_id}")
        return proposal

    async def _validate_constitutional_grounding(self, proposal: Proposal) -> bool:
        """Validate that proposal is properly grounded in constitutional principles."""
        # Check that constitutional grounding is provided
        if not proposal.constitutional_grounding:
            logger.warning(f"Proposal {proposal.proposal_id} has no constitutional grounding")
            return False

        # In practice, this would validate against the constitutional knowledge base
        # For now, accept any grounding as valid
        return True

    async def cast_vote(
        self,
        session_id: str,
        stakeholder_id: str,
        proposal_id: str,
        vote: str,  # "for", "against", "abstain"
        reasoning: Optional[str] = None,
    ) -> bool:
        """
        Cast a vote on a proposal.

        Args:
            session_id: Session containing the proposal
            stakeholder_id: Voting stakeholder
            proposal_id: Proposal being voted on
            vote: Vote type ("for", "against", "abstain")
            reasoning: Optional reasoning for the vote

        Returns:
            Success of vote casting
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        if stakeholder_id not in session.stakeholders:
            return False

        # Find proposal
        proposal = next((p for p in session.proposals if p.proposal_id == proposal_id), None)
        if not proposal:
            return False

        # Remove any existing vote from this stakeholder
        proposal.votes_for.discard(stakeholder_id)
        proposal.votes_against.discard(stakeholder_id)
        proposal.abstentions.discard(stakeholder_id)

        # Add new vote
        if vote == "for":
            proposal.votes_for.add(stakeholder_id)
        elif vote == "against":
            proposal.votes_against.add(stakeholder_id)
        elif vote == "abstain":
            proposal.abstentions.add(stakeholder_id)
        else:
            return False

        # Update stakeholder participation
        stakeholder = session.stakeholders[stakeholder_id]
        stakeholder.participation_count += 1

        # Update proposal phase if needed
        if session.current_phase == DeliberationPhase.PROPOSAL_SUBMISSION:
            session.current_phase = DeliberationPhase.INITIAL_VOTING

        logger.debug(f"Stakeholder {stakeholder_id} voted {vote} on proposal {proposal_id}")
        return True

    async def advance_deliberation_phase(self, session_id: str) -> bool:
        """
        Advance the deliberation session to the next phase.

        Returns:
            True if phase was advanced, False if session should continue in current phase
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # Check if deadline has passed
        if session.deadline and time.time() > session.deadline:
            session.current_phase = DeliberationPhase.DECISION_MADE
            await self._finalize_session(session)
            return True

        # Phase transition logic
        if session.current_phase == DeliberationPhase.INITIAL_VOTING:
            # Check if all stakeholders have voted
            total_stakeholders = len(session.stakeholders)
            voted_proposals = []

            for proposal in session.proposals:
                total_votes = (
                    len(proposal.votes_for)
                    + len(proposal.votes_against)
                    + len(proposal.abstentions)
                )
                if total_votes >= total_stakeholders * 0.8:  # 80% participation
                    voted_proposals.append(proposal)

            if len(voted_proposals) == len(session.proposals):
                session.current_phase = DeliberationPhase.CLUSTER_ANALYSIS
                await self._perform_cluster_analysis(session)
                return True

        elif session.current_phase == DeliberationPhase.CLUSTER_ANALYSIS:
            session.current_phase = DeliberationPhase.CROSS_GROUP_DIALOGUE
            await self._facilitate_cross_group_dialogue(session)
            return True

        elif session.current_phase == DeliberationPhase.CROSS_GROUP_DIALOGUE:
            # Check if consensus is building
            consensus_proposals = []
            for proposal in session.proposals:
                await self._calculate_consensus_score(proposal, session)
                if proposal.consensus_score >= self.consensus_threshold:
                    consensus_proposals.append(proposal)

            if consensus_proposals:
                session.current_phase = DeliberationPhase.CONSENSUS_BUILDING
                return True

        elif session.current_phase == DeliberationPhase.CONSENSUS_BUILDING:
            session.current_phase = DeliberationPhase.FINAL_VOTE
            return True

        elif session.current_phase == DeliberationPhase.FINAL_VOTE:
            session.current_phase = DeliberationPhase.DECISION_MADE
            await self._finalize_session(session)
            return True

        return False

    async def _perform_cluster_analysis(self, session: DeliberationSession) -> None:
        """Analyze voting patterns to identify stakeholder clusters."""
        # Simple clustering based on voting similarity
        # In practice, this would use more sophisticated clustering algorithms

        if not session.proposals:
            return

        # Calculate voting similarity matrix
        stakeholders = list(session.stakeholders.keys())
        similarity_matrix = {}

        for i, s1 in enumerate(stakeholders):
            for j, s2 in enumerate(stakeholders):
                if i < j:
                    similarity = self._calculate_voting_similarity(s1, s2, session.proposals)
                    similarity_matrix[(s1, s2)] = similarity

        # Create clusters based on similarity thresholds
        clusters = []
        processed = set()

        for stakeholder_id in stakeholders:
            if stakeholder_id in processed:
                continue

            # Find similar stakeholders
            cluster_members = {stakeholder_id}
            for other_id in stakeholders:
                if other_id != stakeholder_id and other_id not in processed:
                    similarity = similarity_matrix.get((stakeholder_id, other_id), 0)
                    if similarity > 0.7:  # High similarity threshold
                        cluster_members.add(other_id)

            if len(cluster_members) >= 2:  # Only create clusters with multiple members
                cluster = VotingCluster(
                    cluster_id=hashlib.sha256(f"cluster_{time.time()}".encode()).hexdigest()[:8],
                    stakeholders=cluster_members,
                    centroid_position={},  # Would calculate from voting patterns
                    polarization_score=self._calculate_cluster_polarization(
                        cluster_members, session.proposals
                    ),
                )
                clusters.append(cluster)
                processed.update(cluster_members)

        session.clusters = clusters
        logger.info(f"Identified {len(clusters)} voting clusters in session {session.session_id}")

    def _calculate_voting_similarity(
        self, stakeholder1: str, stakeholder2: str, proposals: List[Proposal]
    ) -> float:
        """Calculate voting similarity between two stakeholders."""
        agreements = 0
        total_comparisons = 0

        for proposal in proposals:
            vote1 = self._get_vote(proposal, stakeholder1)
            vote2 = self._get_vote(proposal, stakeholder2)

            if vote1 and vote2:  # Both voted
                total_comparisons += 1
                if vote1 == vote2:
                    agreements += 1

        return agreements / total_comparisons if total_comparisons > 0 else 0.0

    def _get_vote(self, proposal: Proposal, stakeholder_id: str) -> Optional[str]:
        """Get a stakeholder's vote on a proposal."""
        if stakeholder_id in proposal.votes_for:
            return "for"
        elif stakeholder_id in proposal.votes_against:
            return "against"
        elif stakeholder_id in proposal.abstentions:
            return "abstain"
        return None

    def _calculate_cluster_polarization(
        self, cluster_members: Set[str], proposals: List[Proposal]
    ) -> float:
        """Calculate polarization score for a cluster."""
        # Simple polarization metric: variance in voting patterns
        if not cluster_members or not proposals:
            return 0.0

        polarization_scores = []

        for proposal in proposals:
            for_votes = sum(1 for s in cluster_members if s in proposal.votes_for)
            against_votes = sum(1 for s in cluster_members if s in proposal.votes_against)
            abstain_votes = sum(1 for s in cluster_members if s in proposal.abstentions)

            total_votes = for_votes + against_votes + abstain_votes

            if total_votes > 0:
                # Calculate entropy as polarization measure
                proportions = [
                    for_votes / total_votes,
                    against_votes / total_votes,
                    abstain_votes / total_votes,
                ]
                proportions = [p for p in proportions if p > 0]

                if len(proportions) > 1:
                    entropy = -sum(p * (p**0.5) for p in proportions)  # Simplified entropy
                    polarization_scores.append(entropy)

        return sum(polarization_scores) / len(polarization_scores) if polarization_scores else 0.0

    async def _facilitate_cross_group_dialogue(self, session: DeliberationSession) -> None:
        """Facilitate dialogue between different stakeholder clusters."""
        # This would implement structured dialogue between clusters
        # For now, create placeholder dialogue threads

        dialogue_threads = []

        for i, cluster1 in enumerate(session.clusters):
            for j, cluster2 in enumerate(session.clusters):
                if i < j:  # Avoid duplicate pairs
                    # Check if clusters disagree on proposals
                    disagreements = []
                    for proposal in session.proposals:
                        cluster1_support = self._calculate_cluster_support(cluster1, proposal)
                        cluster2_support = self._calculate_cluster_support(cluster2, proposal)

                        if (
                            abs(cluster1_support - cluster2_support) > 0.5
                        ):  # Significant disagreement
                            disagreements.append(proposal.proposal_id)

                    if disagreements:
                        thread = {
                            "cluster1_id": cluster1.cluster_id,
                            "cluster2_id": cluster2.cluster_id,
                            "disagreements": disagreements,
                            "dialogue_started": time.time(),
                            "messages": [],
                        }
                        dialogue_threads.append(thread)

        # Add dialogue threads to session
        for proposal in session.proposals:
            proposal.dialogue_threads = dialogue_threads

        logger.info(
            f"Created {len(dialogue_threads)} dialogue threads for session {session.session_id}"
        )

    def _calculate_cluster_support(self, cluster: VotingCluster, proposal: Proposal) -> float:
        """Calculate cluster support for a proposal (0.0 to 1.0)."""
        cluster_votes = 0
        support_votes = 0

        for stakeholder_id in cluster.stakeholders:
            if stakeholder_id in proposal.votes_for:
                support_votes += 1
                cluster_votes += 1
            elif stakeholder_id in proposal.votes_against:
                cluster_votes += 1

        return support_votes / cluster_votes if cluster_votes > 0 else 0.5

    async def _calculate_consensus_score(
        self, proposal: Proposal, session: DeliberationSession
    ) -> None:
        """Calculate consensus score for a proposal."""
        votes_for = len(proposal.votes_for)
        votes_against = len(proposal.votes_against)
        abstentions = len(proposal.abstentions)

        # Consensus score: proportion of affirmative votes among participants
        participating_stakeholders = votes_for + votes_against + abstentions

        if participating_stakeholders == 0:
            proposal.consensus_score = 0.0
            proposal.consensus_level = ConsensusLevel.NO_CONSENSUS
            return

        # Weight affirmative votes higher than abstentions
        weighted_score = (votes_for * 1.0 + abstentions * 0.5) / participating_stakeholders

        proposal.consensus_score = weighted_score

        # Determine consensus level
        if weighted_score >= 0.95:
            proposal.consensus_level = ConsensusLevel.UNANIMOUS
        elif weighted_score >= 0.75:
            proposal.consensus_level = ConsensusLevel.SUPERMAJORITY
        elif weighted_score >= 0.5:
            proposal.consensus_level = ConsensusLevel.MAJORITY
        elif weighted_score >= 0.33:
            proposal.consensus_level = ConsensusLevel.PLURALITY
        elif weighted_score >= 0.25:
            proposal.consensus_level = ConsensusLevel.MINIMUM
        else:
            proposal.consensus_level = ConsensusLevel.NO_CONSENSUS

    async def _finalize_session(self, session: DeliberationSession) -> None:
        """Finalize a deliberation session and make decisions."""
        # Calculate final consensus for all proposals
        for proposal in session.proposals:
            await self._calculate_consensus_score(proposal, session)

            # Decide based on consensus threshold
            if proposal.consensus_score >= self.consensus_threshold:
                session.decisions_made.append(proposal)
                logger.info(
                    f"Proposal {proposal.proposal_id} approved with consensus "
                    f"{proposal.consensus_score:.2f}"
                )

                # Update stakeholder consensus contributions
                for stakeholder_id in proposal.votes_for:
                    if stakeholder_id in session.stakeholders:
                        session.stakeholders[stakeholder_id].consensus_contribution += 1.0

        # Move to history
        self.deliberation_history.append(session)
        del self.active_sessions[session.session_id]

        # Update metrics
        self._metrics["sessions_completed"] += 1
        if session.decisions_made:
            self._metrics["consensus_achieved"] += 1

        deliberation_time = time.time() - session.started_at
        self._update_avg_deliberation_time(deliberation_time)

        logger.info(
            f"Finalized session {session.session_id}: {len(session.decisions_made)} decisions made"
        )

    def _update_avg_deliberation_time(self, new_time: float) -> None:
        """Update running average deliberation time."""
        n = self._metrics["sessions_completed"]
        old_avg = self._metrics["avg_deliberation_time"]
        self._metrics["avg_deliberation_time"] = (old_avg * (n - 1) + new_time) / n

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a deliberation session."""
        session = self.active_sessions.get(session_id)
        if not session:
            # Check completed sessions
            session = next(
                (s for s in self.deliberation_history if s.session_id == session_id), None
            )
            if not session:
                return None

        return {
            "session_id": session.session_id,
            "current_phase": session.current_phase.value,
            "proposals_count": len(session.proposals),
            "stakeholders_count": len(session.stakeholders),
            "decisions_made": len(session.decisions_made),
            "consensus_threshold": session.consensus_threshold,
            "deadline": session.deadline,
            "time_remaining": (
                max(0, (session.deadline - time.time())) if session.deadline else None
            ),
            "clusters_identified": len(session.clusters),
            "constitutional_compliance": len(session.constitutional_violations) == 0,
        }

    def get_framework_metrics(self) -> Dict[str, Any]:
        """Get framework performance metrics."""
        success_rate = 0.0
        if self._metrics["sessions_completed"] > 0:
            success_rate = self._metrics["consensus_achieved"] / self._metrics["sessions_completed"]

        participation_rate = len(self.registered_stakeholders) / max(
            1, self._metrics["sessions_completed"] * 10
        )  # Rough estimate

        return {
            **self._metrics,
            "success_rate": success_rate,
            "participation_rate": participation_rate,
            "registered_stakeholders": len(self.registered_stakeholders),
            "active_sessions": len(self.active_sessions),
            "historical_sessions": len(self.deliberation_history),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def analyze_consensus_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in consensus formation."""
        patterns = {
            "successful_consensus_factors": [],
            "failure_patterns": [],
            "stakeholder_influence": {},
            "cluster_dynamics": {},
        }

        # Analyze successful sessions
        successful_sessions = [s for s in self.deliberation_history if s.decisions_made]

        for session in successful_sessions:
            # Analyze what led to success
            if session.clusters:
                patterns["successful_consensus_factors"].append("cluster_analysis_used")

            # Analyze stakeholder influence
            for stakeholder_id, stakeholder in session.stakeholders.items():
                if stakeholder.consensus_contribution > 0:
                    if stakeholder_id not in patterns["stakeholder_influence"]:
                        patterns["stakeholder_influence"][stakeholder_id] = 0
                    patterns["stakeholder_influence"][
                        stakeholder_id
                    ] += stakeholder.consensus_contribution

        return patterns
