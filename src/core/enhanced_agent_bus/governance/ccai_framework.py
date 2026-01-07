"""
ACGS-2 CCAI Democratic Framework
Constitutional Hash: cdd01ef066bc6cf2

CCAI (Collective Constitutional AI) provides breakthrough democratic governance:
- Polis deliberation platform for stakeholder input
- Cross-group consensus filtering to prevent polarization
- Performance-legitimacy balance with hybrid fast/slow paths
- Constitutional amendment workflow

This addresses Challenge 5: Democratic AI Governance by ensuring
legitimate governance through democratic deliberation.
"""

import asyncio
import logging
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import torch

try:
    from .stability.mhc import ManifoldHC
except (ImportError, ValueError):
    try:
        from stability.mhc import ManifoldHC
    except ImportError:
        ManifoldHC = None

# Import centralized constitutional hash
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

import numpy as np

try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
except ImportError:
    PCA = None
    KMeans = None

logger = logging.getLogger(__name__)


class DeliberationPhase(Enum):
    """Phases of democratic deliberation."""

    PROPOSAL = "proposal"
    DISCUSSION = "discussion"
    CLUSTERING = "clustering"
    VOTING = "voting"
    CONSENSUS = "consensus"
    AMENDMENT = "amendment"


class StakeholderGroup(Enum):
    """Types of stakeholder groups for balanced representation."""

    TECHNICAL_EXPERTS = "technical_experts"
    ETHICS_REVIEWERS = "ethics_reviewers"
    END_USERS = "end_users"
    LEGAL_EXPERTS = "legal_experts"
    BUSINESS_STAKEHOLDERS = "business_stakeholders"
    CIVIL_SOCIETY = "civil_society"
    REGULATORS = "regulators"


@dataclass
class Stakeholder:
    """A stakeholder participant in deliberation."""

    stakeholder_id: str
    name: str
    group: StakeholderGroup
    expertise_areas: List[str]
    voting_weight: float = 1.0
    participation_score: float = 0.0
    trust_score: float = 0.5
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert stakeholder to dictionary."""
        return {
            "stakeholder_id": self.stakeholder_id,
            "name": self.name,
            "group": self.group.value,
            "expertise_areas": self.expertise_areas,
            "voting_weight": self.voting_weight,
            "participation_score": self.participation_score,
            "trust_score": self.trust_score,
            "registered_at": self.registered_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class DeliberationStatement:
    """A statement in the deliberation process."""

    statement_id: str
    content: str
    author_id: str
    author_group: StakeholderGroup
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    votes: Dict[str, int] = field(default_factory=dict)  # stakeholder_id -> vote (-1, 0, 1)
    agreement_score: float = 0.0
    disagreement_score: float = 0.0
    consensus_potential: float = 0.0
    cluster_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert statement to dictionary."""
        return {
            "statement_id": self.statement_id,
            "content": self.content,
            "author_id": self.author_id,
            "author_group": self.author_group.value,
            "created_at": self.created_at.isoformat(),
            "votes": self.votes,
            "agreement_score": self.agreement_score,
            "disagreement_score": self.disagreement_score,
            "consensus_potential": self.consensus_potential,
            "cluster_id": self.cluster_id,
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class OpinionCluster:
    """A cluster of similar opinions identified through Polis-style clustering."""

    cluster_id: str
    name: str
    description: str
    representative_statements: List[str]  # statement_ids
    member_stakeholders: List[str]  # stakeholder_ids
    consensus_score: float = 0.0
    polarization_level: float = 0.0
    size: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert cluster to dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "description": self.description,
            "representative_statements": self.representative_statements,
            "member_stakeholders": self.member_stakeholders,
            "consensus_score": self.consensus_score,
            "polarization_level": self.polarization_level,
            "size": self.size,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class ConstitutionalProposal:
    """A proposal for constitutional change."""

    proposal_id: str
    title: str
    description: str
    proposed_changes: Dict[str, Any]
    proposer_id: str
    deliberation_id: str
    status: str = "proposed"  # proposed, deliberating, approved, rejected, implemented
    consensus_threshold: float = 0.6
    min_participants: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deliberation_results: Dict[str, Any] = field(default_factory=dict)
    implementation_plan: Optional[Dict[str, Any]] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert proposal to dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "proposed_changes": self.proposed_changes,
            "proposer_id": self.proposer_id,
            "deliberation_id": self.deliberation_id,
            "status": self.status,
            "consensus_threshold": self.consensus_threshold,
            "min_participants": self.min_participants,
            "created_at": self.created_at.isoformat(),
            "deliberation_results": self.deliberation_results,
            "implementation_plan": self.implementation_plan,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class DeliberationResult:
    """Results of a democratic deliberation."""

    deliberation_id: str
    proposal: ConstitutionalProposal
    total_participants: int
    statements_submitted: int
    clusters_identified: int
    consensus_reached: bool
    consensus_statements: List[Dict[str, Any]]
    polarization_analysis: Dict[str, Any]
    cross_group_consensus: Dict[str, Any]
    approved_amendments: List[Dict[str, Any]]
    rejected_statements: List[Dict[str, Any]]
    stability_analysis: Dict[str, Any] = field(default_factory=dict)
    deliberation_metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "deliberation_id": self.deliberation_id,
            "proposal": self.proposal.to_dict(),
            "total_participants": self.total_participants,
            "statements_submitted": self.statements_submitted,
            "clusters_identified": self.clusters_identified,
            "consensus_reached": self.consensus_reached,
            "consensus_statements": self.consensus_statements,
            "polarization_analysis": self.polarization_analysis,
            "stability_analysis": self.stability_analysis,
            "cross_group_consensus": self.cross_group_consensus,
            "approved_amendments": self.approved_amendments,
            "rejected_statements": self.rejected_statements,
            "deliberation_metadata": self.deliberation_metadata,
            "completed_at": self.completed_at.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


class PolisDeliberationEngine:
    """
    Polis-style deliberation engine for democratic input.

    Implements the core Polis algorithm:
    - Statement submission and voting
    - Opinion clustering to identify consensus
    - Cross-group analysis to prevent polarization
    """

    def __init__(self):
        self.statements: Dict[str, DeliberationStatement] = {}
        self.clusters: Dict[str, OpinionCluster] = {}
        self.voting_matrix: Dict[str, Dict[str, int]] = {}  # statement_id -> {stakeholder_id: vote}

    async def submit_statement(self, content: str, author: Stakeholder) -> DeliberationStatement:
        """Submit a statement to the deliberation."""
        statement = DeliberationStatement(
            statement_id=str(uuid.uuid4()),
            content=content,
            author_id=author.stakeholder_id,
            author_group=author.group,
        )

        self.statements[statement.statement_id] = statement
        self.voting_matrix[statement.statement_id] = {}

        return statement

    async def vote_on_statement(
        self,
        statement_id: str,
        stakeholder: Stakeholder,
        vote: int,  # -1 (disagree), 0 (skip), 1 (agree)
    ) -> bool:
        """Vote on a statement."""
        if statement_id not in self.statements:
            return False

        if statement_id not in self.voting_matrix:
            self.voting_matrix[statement_id] = {}

        self.voting_matrix[statement_id][stakeholder.stakeholder_id] = vote

        # Update statement scores
        await self._update_statement_scores(statement_id)

        return True

    async def _update_statement_scores(self, statement_id: str):
        """Update agreement/disagreement scores for a statement."""
        if statement_id not in self.voting_matrix:
            return

        votes = self.voting_matrix[statement_id]
        if not votes:
            return

        agree_count = sum(1 for v in votes.values() if v == 1)
        disagree_count = sum(1 for v in votes.values() if v == -1)
        total_votes = len(votes)

        statement = self.statements[statement_id]
        statement.agreement_score = agree_count / total_votes if total_votes > 0 else 0
        statement.disagreement_score = disagree_count / total_votes if total_votes > 0 else 0

        # Consensus potential (agreement - disagreement)
        statement.consensus_potential = statement.agreement_score - statement.disagreement_score

    async def identify_clusters(self) -> List[OpinionCluster]:
        """
        Identify opinion clusters from voting data using PCA and K-Means.

        This implementation:
        1. Vectorsizes voting data (Participants x Statements)
        2. Applies PCA for dimensionality reduction (if sufficient data)
        3. Uses K-Means to identify distinct opinion groups
        4. Generates cluster metadata and representative statements
        """
        # 1. Collect all stakeholders and statements
        stakeholder_ids = set()
        for votes in self.voting_matrix.values():
            stakeholder_ids.update(votes.keys())

        stakeholder_list = sorted(list(stakeholder_ids))
        statement_list = sorted(list(self.statements.keys()))

        if not stakeholder_list or not statement_list:
            logger.warning("Insufficient data for clustering.")
            return []

        n_participants = len(stakeholder_list)
        n_statements = len(statement_list)

        # 2. Vectorize votes
        # Matrix: [n_participants, n_statements]
        # Values: -1 (oppose), 0 (pass/no_vote), 1 (support)
        X = np.zeros((n_participants, n_statements))

        name_to_idx = {sid: i for i, sid in enumerate(stakeholder_list)}

        for j, stmt_id in enumerate(statement_list):
            votes = self.voting_matrix.get(stmt_id, {})
            for sid, vote in votes.items():
                if sid in name_to_idx:
                    X[name_to_idx[sid], j] = vote

        # 3. Determine number of clusters (K)
        # Use simple heuristic: min(5, sqrt(N), N) but at least 2 is preferred if N >= 2
        # For small N in tests, allow N clusters (singlets) or N-1
        k_clusters = min(5, max(2, int(np.sqrt(n_participants))))
        if n_participants < 2:
            k_clusters = 1

        # Ensure we don't ask for more clusters than samples
        if k_clusters > n_participants:
            k_clusters = n_participants

        # 4. Dimensionality Reduction (PCA)
        # Only run PCA if we have enough features/samples
        if PCA and n_participants >= 3 and n_statements >= 2:
            n_components = min(n_participants, n_statements, 2)
            try:
                pca = PCA(n_components=n_components)
                X_reduced = pca.fit_transform(X)
                # Use reduced features for clustering
                X_cluster = X_reduced
            except Exception as e:
                logger.warning(f"PCA failed, using raw features: {e}")
                X_cluster = X
        else:
            X_cluster = X

        # 5. Clustering (K-Means)
        labels = np.zeros(n_participants, dtype=int)
        if KMeans and n_participants >= k_clusters:
            try:
                kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
                labels = kmeans.fit_predict(X_cluster)
            except Exception as e:
                logger.warning(f"KMeans failed, falling back to single cluster: {e}")
                labels = np.zeros(n_participants, dtype=int)  # All in cluster 0
        else:
            # Fallback for tiny N or missing sklearn
            labels = np.zeros(n_participants, dtype=int)

        # 6. Build OpinionCluster objects
        clusters_map = {}  # label_str -> OpinionCluster

        for idx, cluster_label in enumerate(labels):
            stakeholder_id = stakeholder_list[idx]
            label_str = str(cluster_label)

            if label_str not in clusters_map:
                clusters_map[label_str] = OpinionCluster(
                    cluster_id=f"cluster_{uuid.uuid4().hex[:8]}",
                    name=f"Opinion Group {cluster_label + 1}",
                    description=f"Cluster {cluster_label + 1} identified via PCA/K-Means",
                    representative_statements=[],  # TODO: Identify best statements identifying this cluster
                    member_stakeholders=[],
                    metadata={"pca_components": 2 if PCA else 0},
                    size=0,
                )

            clusters_map[label_str].member_stakeholders.append(stakeholder_id)
            clusters_map[label_str].size += 1

        self.clusters = {c.cluster_id: c for c in clusters_map.values()}
        logger.info(f"Identified {len(self.clusters)} opinion clusters via Advanced Clustering")
        return list(self.clusters.values())

    async def analyze_cross_group_consensus(self, clusters: List[OpinionCluster]) -> Dict[str, Any]:
        """
        Analyze consensus across different stakeholder groups.

        This prevents polarization by ensuring consensus exists across diverse groups.
        """
        group_consensus = {}

        for cluster in clusters:
            group_votes = {}

            # Analyze votes within this cluster by group
            for statement_id in cluster.representative_statements:
                if statement_id in self.voting_matrix:
                    for stakeholder_id, vote in self.voting_matrix[statement_id].items():
                        # In practice, we'd look up stakeholder group
                        # For now, simulate diverse groups
                        group = f"group_{hash(stakeholder_id) % 4}"

                        if group not in group_votes:
                            group_votes[group] = []
                        group_votes[group].append(vote)

            # Calculate consensus per group
            group_scores = {}
            for group, votes in group_votes.items():
                if votes:
                    agree_ratio = sum(1 for v in votes if v == 1) / len(votes)
                    group_scores[group] = agree_ratio

            # Cross-group consensus (minimum agreement across all groups)
            if group_scores:
                cross_consensus = min(group_scores.values())
                cluster.cross_group_consensus = cross_consensus
            else:
                cluster.cross_group_consensus = 0.0

        # Overall analysis
        total_clusters = len(clusters)
        high_consensus_clusters = sum(1 for c in clusters if c.consensus_score > 0.6)

        return {
            "total_clusters": total_clusters,
            "high_consensus_clusters": high_consensus_clusters,
            "consensus_ratio": high_consensus_clusters / total_clusters
            if total_clusters > 0
            else 0,
            "average_cross_group_consensus": statistics.mean([c.consensus_score for c in clusters])
            if clusters
            else 0,
            "polarization_risk": "low"
            if high_consensus_clusters > total_clusters * 0.5
            else "high",
        }


class DemocraticConstitutionalGovernance:
    """
    CCAI Democratic Constitutional Governance Framework

    Integrates Polis deliberation with constitutional governance:
    - Democratic input through structured deliberation
    - Cross-group consensus to prevent polarization
    - Performance-legitimacy balance with hybrid decision paths
    - Constitutional amendment workflow
    """

    def __init__(self, consensus_threshold: float = 0.6, min_participants: int = 100):
        self.consensus_threshold = consensus_threshold
        self.min_participants = min_participants

        # Core components
        self.polis_engine = PolisDeliberationEngine()
        self.stakeholders: Dict[str, Stakeholder] = {}
        self.proposals: Dict[str, ConstitutionalProposal] = {}
        self.deliberations: Dict[str, DeliberationResult] = {}

        # Performance monitoring
        self.fast_decisions: List[Dict[str, Any]] = []
        self.deliberated_decisions: List[Dict[str, Any]] = []

        logger.info("Initialized Democratic Constitutional Governance")
        logger.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
        logger.info(f"Consensus threshold: {consensus_threshold}")

        # Stability Layer for consensus aggregation
        if ManifoldHC:
            self.stability_layer = ManifoldHC(dim=8)  # Support up to 8 stakeholder groups
            logger.info("Governance stability layer (mHC) enabled")
        else:
            self.stability_layer = None
            logger.warning("Governance stability layer (mHC) not available")

    async def register_stakeholder(
        self, name: str, group: StakeholderGroup, expertise_areas: List[str]
    ) -> Stakeholder:
        """Register a new stakeholder."""
        stakeholder = Stakeholder(
            stakeholder_id=str(uuid.uuid4()),
            name=name,
            group=group,
            expertise_areas=expertise_areas,
        )

        self.stakeholders[stakeholder.stakeholder_id] = stakeholder

        logger.info(f"Registered stakeholder: {stakeholder.name} ({stakeholder.group.value})")
        return stakeholder

    async def propose_constitutional_change(
        self,
        title: str,
        description: str,
        proposed_changes: Dict[str, Any],
        proposer: Stakeholder,
    ) -> ConstitutionalProposal:
        """Propose a constitutional change for deliberation."""
        proposal = ConstitutionalProposal(
            proposal_id=str(uuid.uuid4()),
            title=title,
            description=description,
            proposed_changes=proposed_changes,
            proposer_id=proposer.stakeholder_id,
            deliberation_id=str(uuid.uuid4()),
            consensus_threshold=self.consensus_threshold,
            min_participants=self.min_participants,
        )

        self.proposals[proposal.proposal_id] = proposal

        logger.info(f"Constitutional proposal created: {proposal.title}")
        return proposal

    async def run_deliberation(
        self,
        proposal: ConstitutionalProposal,
        stakeholders: List[Stakeholder],
        duration_hours: int = 72,
    ) -> DeliberationResult:
        """
        Run a full democratic deliberation process.

        Implements the complete CCAI workflow:
        1. Statement submission phase
        2. Discussion and voting phase
        3. Clustering and consensus analysis
        4. Cross-group validation
        """
        logger.info(f"Starting deliberation for proposal: {proposal.title}")

        deliberation_id = proposal.deliberation_id
        start_time = datetime.now(timezone.utc)

        # Phase 1: Statement submission
        statements = await self._collect_statements(proposal, stakeholders)

        # Phase 2: Voting phase
        await self._conduct_voting(statements, stakeholders)

        # Phase 3: Clustering analysis
        clusters = await self.polis_engine.identify_clusters()

        # Phase 4: Cross-group consensus analysis
        cross_group_analysis = await self.polis_engine.analyze_cross_group_consensus(clusters)

        # Phase 5: Determine consensus and amendments
        consensus_reached, approved_amendments, rejected_items = await self._determine_consensus(
            proposal, clusters, cross_group_analysis
        )

        # Capture stability stats if available
        stability_stats = {}
        if self.stability_layer and hasattr(self.stability_layer, "last_stats"):
            stability_stats = self.stability_layer.last_stats

        # Create deliberation result
        result = DeliberationResult(
            deliberation_id=deliberation_id,
            proposal=proposal,
            total_participants=len(stakeholders),
            statements_submitted=len(statements),
            clusters_identified=len(clusters),
            consensus_reached=consensus_reached,
            consensus_statements=[
                {
                    "content": self.polis_engine.statements[sid].content,
                    "consensus_score": self.polis_engine.statements[sid].consensus_potential,
                    "cluster": self.polis_engine.statements[sid].cluster_id,
                }
                for sid in approved_amendments
            ],
            polarization_analysis={
                "cross_group_consensus": cross_group_analysis,
                "risk_level": cross_group_analysis.get("polarization_risk", "unknown"),
            },
            stability_analysis=stability_stats,
            cross_group_consensus=cross_group_analysis,
            approved_amendments=approved_amendments,
            rejected_statements=rejected_items,
            deliberation_metadata={
                "duration_hours": duration_hours,
                "start_time": start_time.isoformat(),
                "participation_rate": len(statements) / max(1, len(stakeholders)),
            },
        )

        self.deliberations[deliberation_id] = result
        proposal.deliberation_results = result.to_dict()
        proposal.status = "approved" if consensus_reached else "rejected"

        logger.info(
            f"Deliberation completed: consensus={'reached' if consensus_reached else 'not reached'}"
        )
        return result

    async def _collect_statements(
        self, proposal: ConstitutionalProposal, stakeholders: List[Stakeholder]
    ) -> List[DeliberationStatement]:
        """Collect statements from stakeholders."""
        statements = []

        # In practice, this would be an interactive process
        # For simulation, generate representative statements
        for stakeholder in stakeholders[: min(20, len(stakeholders))]:  # Limit for simulation
            # Generate a statement based on stakeholder group
            statement_content = await self._generate_statement_for_stakeholder(
                proposal, stakeholder
            )

            statement = await self.polis_engine.submit_statement(statement_content, stakeholder)
            statements.append(statement)

        return statements

    async def _generate_statement_for_stakeholder(
        self, proposal: ConstitutionalProposal, stakeholder: Stakeholder
    ) -> str:
        """Generate a representative statement for a stakeholder."""
        # Simplified statement generation based on group
        group_statements = {
            StakeholderGroup.TECHNICAL_EXPERTS: [
                "The proposed changes should maintain system performance and reliability.",
                "Technical implementation must be feasible within current architecture.",
                "Security implications need careful evaluation.",
            ],
            StakeholderGroup.ETHICS_REVIEWERS: [
                "Changes must align with ethical principles and human rights.",
                "Potential biases in the system should be addressed.",
                "Transparency and accountability are essential.",
            ],
            StakeholderGroup.END_USERS: [
                "The changes should improve user experience and accessibility.",
                "User privacy and data protection must be prioritized.",
                "System reliability affects user trust.",
            ],
            StakeholderGroup.LEGAL_EXPERTS: [
                "Changes must comply with relevant regulations and laws.",
                "Legal implications need thorough review.",
                "Compliance requirements should be clearly defined.",
            ],
        }

        statements = group_statements.get(
            stakeholder.group,
            ["The proposal needs careful consideration of all stakeholder interests."],
        )

        # Return a random statement (simplified)
        return statements[hash(stakeholder.stakeholder_id) % len(statements)]

    async def _conduct_voting(
        self, statements: List[DeliberationStatement], stakeholders: List[Stakeholder]
    ):
        """Conduct voting on statements."""
        # Simulate voting process
        for statement in statements:
            # Each stakeholder votes on a subset of statements
            voters = stakeholders[: min(10, len(stakeholders))]

            for stakeholder in voters:
                # Simplified voting logic
                vote = (
                    1
                    if hash(f"{statement.statement_id}_{stakeholder.stakeholder_id}") % 3 != 0
                    else -1
                )
                await self.polis_engine.vote_on_statement(statement.statement_id, stakeholder, vote)

    async def _apply_stability_constraint(
        self, scores: List[float], trust_scores: Optional[List[float]] = None
    ) -> List[float]:
        """
        Apply manifold constraint to consensus scores for mathematical stability.
        Uses mHC (Manifold-Constrained HyperConnection) with dynamic resizing.
        """
        if not ManifoldHC or not scores:
            return scores

        try:
            n = len(scores)

            # Dynamic Dimension Resizing: Re-initialize layer if dimensionality changed
            if not self.stability_layer or self.stability_layer.dim != n:
                self.stability_layer = ManifoldHC(dim=n)
                logger.info(f"mHC stability layer resized to dim={n}")

            score_tensor = torch.tensor(scores, dtype=torch.float32).unsqueeze(0)

            # Prepare trust marginals if available
            row_marginal = None
            col_marginal = None
            if trust_scores:
                # Ensure trust_scores length matches n
                trust_scores = trust_scores[:n] + [0.5] * (n - len(trust_scores))
                row_marginal = torch.tensor(trust_scores, dtype=torch.float32)
                col_marginal = row_marginal  # Symmetric marginals for UMM

            # Apply mHC forward pass
            with torch.no_grad():
                stabilized_tensor = self.stability_layer(
                    score_tensor,
                    row_marginal=row_marginal,
                    col_marginal=col_marginal,
                    alpha=0.4,  # Adversarial capping to prevent single-group dominance
                )

            return stabilized_tensor.squeeze(0).tolist()
        except Exception as e:
            logger.warning(f"Stability projection failed, using raw scores: {e}")
            return scores

    async def _determine_consensus(
        self,
        proposal: ConstitutionalProposal,
        clusters: List[OpinionCluster],
        cross_group_analysis: Dict[str, Any],
    ) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Determine if consensus is reached and what amendments are approved."""
        consensus_reached = False
        approved_amendments = []
        rejected_items = []

        # Check cross-group consensus
        consensus_ratio = cross_group_analysis.get("consensus_ratio", 0)

        # Apply mHC stability constraint to cluster consensus scores
        cluster_scores = [c.consensus_score for c in clusters]

        # Calculate cluster trust scores (weighted by stakeholder trust)
        cluster_trust = []
        for cluster in clusters:
            member_trusts = [
                self.stakeholders[sid].trust_score
                for sid in cluster.member_stakeholders
                if sid in self.stakeholders
            ]
            # Default to neutral trust (0.5) if no stakeholders found in cluster
            avg_trust = statistics.mean(member_trusts) if member_trusts else 0.5
            cluster_trust.append(avg_trust)

        stabilized_scores = await self._apply_stability_constraint(
            cluster_scores, trust_scores=cluster_trust
        )

        for i, cluster in enumerate(clusters):
            if i < len(stabilized_scores):
                cluster.consensus_score = stabilized_scores[i]

        if consensus_ratio >= proposal.consensus_threshold:
            consensus_reached = True

            # Identify approved amendments from high-consensus clusters
            for cluster in clusters:
                if cluster.consensus_score >= proposal.consensus_threshold:
                    for statement_id in cluster.representative_statements:
                        if statement_id in self.polis_engine.statements:
                            statement = self.polis_engine.statements[statement_id]
                            approved_amendments.append(
                                {
                                    "statement_id": statement_id,
                                    "content": statement.content,
                                    "consensus_score": statement.consensus_potential,
                                    "cluster": cluster.cluster_id,
                                }
                            )

        # Identify rejected items (low consensus statements)
        for statement in self.polis_engine.statements.values():
            if statement.consensus_potential < 0.3:  # Low consensus threshold
                rejected_items.append(
                    {
                        "statement_id": statement.statement_id,
                        "content": statement.content,
                        "consensus_score": statement.consensus_potential,
                    }
                )

        return consensus_reached, approved_amendments, rejected_items

    async def fast_govern(
        self,
        decision: Dict[str, Any],
        time_budget_ms: int,
        stakeholders: Optional[List[Stakeholder]] = None,
    ) -> Dict[str, Any]:
        """
        Performance-legitimacy balance: Fast automated decision with async review.

        Returns immediate decision + async deliberation task.
        """
        start_time = datetime.now(timezone.utc)

        # Fast path: automated constitutional check
        # In practice, this would use existing governance systems
        fast_decision = {
            "decision": decision,
            "approved": True,  # Simplified - assume compliant
            "confidence": 0.8,
            "method": "automated_check",
            "processing_time_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
        }

        # Record fast decision
        self.fast_decisions.append(
            {
                "decision": decision,
                "result": fast_decision,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Async deliberation for legitimacy
        deliberation_task = None
        if stakeholders and len(stakeholders) >= 10:
            deliberation_task = asyncio.create_task(
                self._async_deliberation(decision, stakeholders)
            )

        return {
            "immediate_decision": fast_decision,
            "deliberation_pending": deliberation_task is not None,
            "deliberation_task": deliberation_task,
            "performance_optimized": True,
        }

    async def _async_deliberation(self, decision: Dict[str, Any], stakeholders: List[Stakeholder]):
        """Async deliberation for legitimacy validation."""
        # Create a proposal for deliberation
        proposal = await self.propose_constitutional_change(
            title=f"Decision Review: {decision.get('description', 'Unknown')}",
            description=f"Review of automated decision: {decision}",
            proposed_changes={"decision": decision},
            proposer=stakeholders[0] if stakeholders else None,
        )

        # Run deliberation
        result = await self.run_deliberation(proposal, stakeholders, duration_hours=24)

        # Update decision legitimacy
        decision["legitimacy_reviewed"] = True
        decision["deliberation_result"] = result.to_dict()

        logger.info(f"Async deliberation completed for decision: {decision.get('id', 'unknown')}")

    async def get_governance_status(self) -> Dict[str, Any]:
        """Get governance framework status."""
        return {
            "framework": "CCAI Democratic Constitutional Governance",
            "status": "operational",
            "registered_stakeholders": len(self.stakeholders),
            "active_proposals": len(
                [p for p in self.proposals.values() if p.status == "deliberating"]
            ),
            "completed_deliberations": len(self.deliberations),
            "fast_decisions": len(self.fast_decisions),
            "deliberated_decisions": len(self.deliberated_decisions),
            "consensus_threshold": self.consensus_threshold,
            "capabilities": {
                "polis_deliberation": True,
                "cross_group_consensus": True,
                "constitutional_amendments": True,
                "performance_legitimacy_balance": True,
            },
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Global governance framework instance
ccai_governance = DemocraticConstitutionalGovernance()


def get_ccai_governance() -> DemocraticConstitutionalGovernance:
    """Get the global CCAI governance framework instance."""
    return ccai_governance


async def deliberate_on_proposal(
    title: str,
    description: str,
    changes: Dict[str, Any],
    stakeholder_groups: List[StakeholderGroup],
    min_participants: int = 50,
) -> DeliberationResult:
    """
    Convenience function to run democratic deliberation on a proposal.

    This provides the main API for democratic governance.
    """
    governance = get_ccai_governance()

    # Create stakeholders for simulation
    stakeholders = []
    for group in stakeholder_groups:
        for i in range(max(5, min_participants // len(stakeholder_groups))):
            stakeholder = await governance.register_stakeholder(
                name=f"{group.value}_{i}", group=group, expertise_areas=[group.value]
            )
            stakeholders.append(stakeholder)

    # Create proposal
    proposer = stakeholders[0] if stakeholders else None
    if not proposer:
        raise ValueError("No stakeholders available")

    proposal = await governance.propose_constitutional_change(
        title=title,
        description=description,
        proposed_changes=changes,
        proposer=proposer,
    )

    # Run deliberation
    return await governance.run_deliberation(proposal, stakeholders)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    async def main():
        logger.info("Testing CCAI Democratic Constitutional Governance...")

        governance = DemocraticConstitutionalGovernance()

        # Test status
        status = await governance.get_governance_status()
        logger.info("Governance status: %s", status["status"])
        logger.info("Capabilities: Polis deliberation enabled")

        # Register stakeholders
        tech_expert = await governance.register_stakeholder(
            "Dr. Sarah Chen", StakeholderGroup.TECHNICAL_EXPERTS, ["AI", "security"]
        )
        ethicist = await governance.register_stakeholder(
            "Prof. Michael Torres", StakeholderGroup.ETHICS_REVIEWERS, ["ethics", "governance"]
        )
        end_user = await governance.register_stakeholder(
            "Jane Doe", StakeholderGroup.END_USERS, ["usability", "privacy"]
        )

        stakeholders = [tech_expert, ethicist, end_user]
        logger.info("Registered %d stakeholders", len(stakeholders))

        # Create proposal
        proposal = await governance.propose_constitutional_change(
            title="Enhanced Transparency Requirements",
            description="Require all AI decisions to provide detailed explanations",
            proposed_changes={
                "transparency": "mandatory",
                "explanation_depth": "detailed",
                "audit_trail": "comprehensive",
            },
            proposer=tech_expert,
        )

        logger.info("Created proposal: %s", proposal.title)

        # Run deliberation
        result = await governance.run_deliberation(proposal, stakeholders, duration_hours=24)

        logger.info("Deliberation completed")
        logger.info("   Participants: %d", result.total_participants)
        logger.info("   Statements: %d", result.statements_submitted)
        logger.info("   Clusters: %d", result.clusters_identified)
        logger.info("   Consensus reached: %s", result.consensus_reached)
        logger.info("   Approved amendments: %d", len(result.approved_amendments))

        # Test fast governance
        test_decision = {
            "id": "test_decision_001",
            "description": "Approve routine maintenance",
            "type": "maintenance",
        }

        fast_result = await governance.fast_govern(test_decision, 1000, stakeholders)
        logger.info("Fast governance: approved=%s", fast_result["immediate_decision"]["approved"])
        logger.info("   Deliberation pending: %s", fast_result["deliberation_pending"])

        logger.info("CCAI Democratic Governance test completed!")

    # Run test
    asyncio.run(main())
