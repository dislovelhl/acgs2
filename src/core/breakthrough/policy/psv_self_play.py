"""
PSV Self-Play - Constitutional AI Self-Improvement
===================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements PSV-Verus self-play for continuous improvement:
- Propose: Generate increasingly challenging policy specifications
- Solve: Attempt to create verified implementations
- Verify: Validate solutions and learn from outcomes
- Self-Play: Improve system through iterative refinement

Design Principles:
- Self-improving through adversarial policy generation
- Continuous learning from verification failures
- Progressive difficulty scaling
- Constitutional constraint preservation
"""

import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from src.core.shared.policy.models import (
    PolicySpecification,
    VerifiedPolicy,
)
from src.core.shared.policy.unified_generator import (
    UnifiedVerifiedPolicyGenerator,
)

from ...shared.types import JSONDict
from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class SelfPlayMode(Enum):
    """Modes of self-play operation."""

    TRAINING = "training"  # Generate training data
    IMPROVEMENT = "improvement"  # Improve existing capabilities
    EXPLORATION = "exploration"  # Explore new problem spaces
    COMPETITION = "competition"  # Competitive self-play


class DifficultyLevel(Enum):
    """Difficulty levels for self-play challenges."""

    NOVICE = 1  # Basic policies
    INTERMEDIATE = 2  # Moderate complexity
    ADVANCED = 3  # Complex policies
    EXPERT = 4  # Very challenging
    MASTER = 5  # Near-impossible


@dataclass
class SelfPlayChallenge:
    """A challenge generated for self-play."""

    challenge_id: str
    natural_language_spec: str
    difficulty_level: DifficultyLevel
    category: str
    constraints: List[str]
    success_criteria: List[str]
    generated_at: float = field(default_factory=time.time)

    # Results
    attempted_solutions: List[JSONDict] = field(default_factory=list)
    best_solution: Optional[JSONDict] = None
    success_achieved: bool = False
    improvement_score: float = 0.0

    def __post_init__(self):
        if not self.challenge_id:
            self.challenge_id = hashlib.sha256(
                f"{self.natural_language_spec}_{self.difficulty_level.value}_{self.generated_at}".encode()
            ).hexdigest()[:16]


@dataclass
class SelfPlayRound:
    """A complete round of PSV self-play."""

    round_id: str
    mode: SelfPlayMode
    challenges: List[SelfPlayChallenge] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # Results
    challenges_attempted: int = 0
    challenges_solved: int = 0
    average_difficulty: float = 0.0
    improvement_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.round_id:
            self.round_id = hashlib.sha256(
                f"round_{self.mode.value}_{self.started_at}".encode()
            ).hexdigest()[:16]


@dataclass
class PSVAgent:
    """A PSV self-play agent."""

    agent_id: str
    capabilities: Set[str] = field(default_factory=set)
    performance_history: List[Dict[str, float]] = field(default_factory=list)
    specialization_areas: Set[str] = field(default_factory=set)

    # Learning state
    skill_levels: Dict[str, float] = field(default_factory=dict)
    adaptation_rate: float = 0.1
    last_improvement: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = hashlib.sha256(f"psv_agent_{time.time()}".encode()).hexdigest()[:12]


class PSVSelfPlay:
    """
    PSV-Verus Self-Play System for Constitutional AI Improvement.

    Implements continuous self-improvement through:
    - Progressive challenge generation
    - Solution attempt and verification
    - Learning from successes and failures
    - Adaptation to improving capabilities

    This enables the system to get better at governance policy generation over time.
    """

    def __init__(
        self,
        policy_generator: UnifiedVerifiedPolicyGenerator,
        max_rounds_per_session: int = 10,
        improvement_threshold: float = 0.05,  # 5% improvement required
        adaptation_enabled: bool = True,
    ):
        """
        Initialize PSV Self-Play system.

        Args:
            policy_generator: The verified policy generator to improve
            max_rounds_per_session: Maximum self-play rounds per session
            improvement_threshold: Minimum improvement required to continue
            adaptation_enabled: Whether to enable adaptive difficulty
        """
        self.policy_generator = policy_generator
        self.max_rounds_per_session = max_rounds_per_session
        self.improvement_threshold = improvement_threshold
        self.adaptation_enabled = adaptation_enabled

        # Self-play state
        self.active_round: Optional[SelfPlayRound] = None
        self.completed_rounds: List[SelfPlayRound] = []

        # Challenge generation
        self.challenge_templates: Dict[str, JSONDict] = {}
        self.difficulty_progression: Dict[DifficultyLevel, JSONDict] = {}
        self._initialize_challenge_templates()

        # Learning and adaptation
        self.psv_agents: Dict[str, PSVAgent] = {}
        self.performance_baseline: Dict[str, float] = {}
        self.learning_history: List[JSONDict] = []

        # Performance tracking
        self._metrics = {
            "total_rounds": 0,
            "total_challenges": 0,
            "challenges_solved": 0,
            "average_success_rate": 0.0,
            "difficulty_progression": 0.0,
            "last_improvement": time.time(),
        }

        logger.info("Initialized PSV Self-Play system")

    def _initialize_challenge_templates(self):
        """Initialize challenge templates for different categories."""

        # Security policies
        self.challenge_templates["security"] = {
            "base_template": "A security policy that {requirement} while maintaining {constraint}",
            "requirements": [
                "prevents unauthorized access to sensitive data",
                "ensures data integrity across distributed systems",
                "provides audit trails for all security events",
                "implements zero-trust authentication",
                "prevents privilege escalation attacks",
                "ensures secure communication channels",
            ],
            "constraints": [
                "minimal performance impact",
                "backward compatibility",
                "user-friendly operation",
                "compliance with privacy regulations",
                "scalability to millions of users",
            ],
        }

        # Governance policies
        self.challenge_templates["governance"] = {
            "base_template": "A governance policy that {requirement} while ensuring {constraint}",
            "requirements": [
                "balances executive efficiency with judicial oversight",
                "enables democratic decision making at scale",
                "maintains constitutional compliance across all operations",
                "prevents concentration of power",
                "ensures transparency in decision processes",
                "facilitates stakeholder participation",
            ],
            "constraints": [
                "sub-millisecond response times",
                "mathematical verifiability",
                "resistance to manipulation",
                "cross-cultural applicability",
                "minimal resource consumption",
            ],
        }

        # Compliance policies
        self.challenge_templates["compliance"] = {
            "base_template": "A compliance policy that {requirement} and {additional_requirement}",
            "requirements": [
                "ensures GDPR compliance for data processing",
                "maintains HIPAA compliance for health data",
                "follows SOX requirements for financial reporting",
                "implements CIS security benchmarks",
                "ensures accessibility compliance (WCAG)",
                "maintains ISO 27001 information security",
            ],
            "additional_requirements": [
                "automates compliance monitoring",
                "provides audit-ready documentation",
                "minimizes false positives",
                "supports multi-jurisdictional compliance",
                "integrates with existing systems",
            ],
        }

        # Initialize difficulty progression
        for level in DifficultyLevel:
            self.difficulty_progression[level] = {
                "min_complexity": level.value,
                "max_categories": min(level.value, len(self.challenge_templates)),
                "allow_compound": level.value >= 3,
                "require_verification": level.value >= 2,
                "time_limit_seconds": 300 * level.value,
            }

    async def start_self_play_round(
        self,
        mode: SelfPlayMode = SelfPlayMode.IMPROVEMENT,
        target_difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    ) -> SelfPlayRound:
        """
        Start a new self-play round.

        Args:
            mode: Self-play mode
            target_difficulty: Target difficulty level

        Returns:
            New self-play round
        """
        round_obj = SelfPlayRound(round_id="", mode=mode)

        # Generate challenges for this round
        num_challenges = min(5, len(self.challenge_templates))  # 5 challenges per round

        for _ in range(num_challenges):
            challenge = await self._generate_challenge(target_difficulty, mode)
            if challenge:
                round_obj.challenges.append(challenge)

        self.active_round = round_obj

        logger.info(
            f"Started self-play round {round_obj.round_id} with "
            f"{len(round_obj.challenges)} challenges"
        )
        return round_obj

    async def _generate_challenge(
        self, target_difficulty: DifficultyLevel, mode: SelfPlayMode
    ) -> Optional[SelfPlayChallenge]:
        """Generate a single challenge."""

        # Select category based on mode
        if mode == SelfPlayMode.EXPLORATION:
            category = random.choice(list(self.challenge_templates.keys()))
        elif mode == SelfPlayMode.IMPROVEMENT:
            # Focus on weaker areas
            category = self._select_improvement_category()
        else:
            category = random.choice(list(self.challenge_templates.keys()))

        template = self.challenge_templates[category]
        difficulty_config = self.difficulty_progression[target_difficulty]

        # Generate natural language specification
        if category == "security":
            requirement = random.choice(template["requirements"])
            constraint = random.choice(template["constraints"])
            spec = template["base_template"].format(requirement=requirement, constraint=constraint)

        elif category == "governance":
            requirement = random.choice(template["requirements"])
            constraint = random.choice(template["constraints"])
            spec = template["base_template"].format(requirement=requirement, constraint=constraint)

        elif category == "compliance":
            requirement = random.choice(template["requirements"])
            additional = random.choice(template["additional_requirements"])
            spec = template["base_template"].format(
                requirement=requirement, additional_requirement=additional
            )

        else:
            return None

        # Add complexity based on difficulty
        if difficulty_config["allow_compound"] and random.random() < 0.3:
            spec += " and also handles edge cases involving conflicting requirements"

        # Generate constraints and success criteria
        constraints = [
            "Must be mathematically verifiable",
            "Must maintain constitutional compliance",
            f"Must be implementable within {difficulty_config['time_limit_seconds']} seconds",
        ]

        success_criteria = [
            "Policy generates without errors",
            "Formal verification succeeds",
            "Policy handles specified requirements",
            "No constitutional violations detected",
        ]

        if difficulty_config["require_verification"]:
            success_criteria.append("Passes all verification checks")

        challenge = SelfPlayChallenge(
            challenge_id="",
            natural_language_spec=spec,
            difficulty_level=target_difficulty,
            category=category,
            constraints=constraints,
            success_criteria=success_criteria,
        )

        return challenge

    def _select_improvement_category(self) -> str:
        """Select category that needs the most improvement."""
        # Analyze performance by category
        category_performance = {}

        for round_obj in self.completed_rounds[-10:]:  # Last 10 rounds
            for challenge in round_obj.challenges:
                cat = challenge.category
                if cat not in category_performance:
                    category_performance[cat] = {"attempted": 0, "solved": 0}

                category_performance[cat]["attempted"] += 1
                if challenge.success_achieved:
                    category_performance[cat]["solved"] += 1

        # Calculate success rates
        success_rates = {}
        for cat, stats in category_performance.items():
            if stats["attempted"] > 0:
                success_rates[cat] = stats["solved"] / stats["attempted"]

        # Select category with lowest success rate
        if success_rates:
            worst_category = min(success_rates, key=success_rates.get)
            return worst_category

        return random.choice(list(self.challenge_templates.keys()))

    async def execute_self_play_round(self, round_obj: SelfPlayRound) -> JSONDict:
        """
        Execute a complete self-play round.

        Args:
            round_obj: The round to execute

        Returns:
            Round execution results
        """
        results = {
            "round_id": round_obj.round_id,
            "challenges_attempted": 0,
            "challenges_solved": 0,
            "total_attempts": 0,
            "average_difficulty": 0.0,
            "improvement_metrics": {},
        }

        for challenge in round_obj.challenges:
            round_obj.challenges_attempted += 1

            # Attempt to solve the challenge
            solution_result = await self._attempt_challenge_solution(challenge)

            challenge.attempted_solutions.append(solution_result)

            if solution_result["success"]:
                challenge.success_achieved = True
                challenge.best_solution = solution_result
                round_obj.challenges_solved += 1

            results["challenges_attempted"] += 1
            results["total_attempts"] += solution_result.get("attempts", 1)

        # Calculate metrics
        if round_obj.challenges_attempted > 0:
            round_obj.average_difficulty = (
                sum(c.difficulty_level.value for c in round_obj.challenges)
                / round_obj.challenges_attempted
            )

            results["challenges_solved"] = round_obj.challenges_solved
            results["average_difficulty"] = round_obj.average_difficulty

        # Complete the round
        round_obj.completed_at = time.time()
        self.completed_rounds.append(round_obj)
        self.active_round = None

        # Update metrics
        self._update_metrics(round_obj)

        # Calculate improvement
        improvement = await self._calculate_improvement()
        results["improvement_metrics"] = improvement

        logger.info(
            f"Completed self-play round {round_obj.round_id}: "
            f"{round_obj.challenges_solved}/{round_obj.challenges_attempted} challenges solved"
        )

        return results

    async def _attempt_challenge_solution(self, challenge: SelfPlayChallenge) -> JSONDict:
        """Attempt to solve a self-play challenge."""
        start_time = time.time()
        attempts = 0
        max_attempts = 3  # Maximum attempts per challenge

        for _attempt in range(max_attempts):
            attempts += 1

            try:
                spec = PolicySpecification(
                    spec_id=hashlib.sha256(challenge.natural_language_spec.encode()).hexdigest()[:8],
                    natural_language=challenge.natural_language_spec,
                    category=challenge.category
                )
                policy = await self.policy_generator.generate_verified_policy(spec)

                # Validate against success criteria
                validation_result = await self._validate_solution(policy, challenge)

                if validation_result["valid"]:
                    execution_time = time.time() - start_time
                    return {
                        "success": True,
                        "policy": policy.to_dict(),
                        "attempts": attempts,
                        "execution_time": execution_time,
                        "validation": validation_result,
                    }

            except Exception as e:
                logger.error(f"Error in challenge attempt: {str(e)}")
                continue

            except Exception as e:
                logger.error(f"Unexpected error in challenge attempt: {str(e)}")
                continue

        # All attempts failed
        execution_time = time.time() - start_time
        return {
            "success": False,
            "attempts": attempts,
            "execution_time": execution_time,
            "error": "All solution attempts failed",
        }

    async def _validate_solution(
        self, policy: VerifiedPolicy, challenge: SelfPlayChallenge
    ) -> JSONDict:
        """Validate a solution against challenge criteria."""
        validation = {"valid": True, "criteria_met": [], "criteria_failed": [], "score": 0.0}

        # Check each success criterion
        for criterion in challenge.success_criteria:
            if "Policy generates without errors" in criterion:
                # Policy was generated successfully
                validation["criteria_met"].append(criterion)
                validation["score"] += 0.25

            elif "Formal verification succeeds" in criterion:
                # Check if verification succeeded
                if hasattr(policy, "proof") and policy.proof:
                    validation["criteria_met"].append(criterion)
                    validation["score"] += 0.25
                else:
                    validation["criteria_failed"].append(criterion)
                    validation["valid"] = False

            elif "Policy handles specified requirements" in criterion:
                # Basic check: ensure policy contains relevant keywords
                spec_lower = challenge.natural_language_spec.lower()
                rego_lower = policy.rego_code.lower()

                relevant_keywords = []
                if "security" in spec_lower or "access" in spec_lower:
                    relevant_keywords.extend(["allow", "deny", "access"])
                if "data" in spec_lower:
                    relevant_keywords.extend(["data", "integrity"])
                if "compliance" in spec_lower:
                    relevant_keywords.extend(["compliance", "audit"])

                keyword_matches = sum(1 for kw in relevant_keywords if kw in rego_lower)
                if keyword_matches >= len(relevant_keywords) * 0.6:
                    validation["criteria_met"].append(criterion)
                    validation["score"] += 0.25
                else:
                    validation["criteria_failed"].append(criterion)
                    validation["valid"] = False

            elif "No constitutional violations detected" in criterion:
                # Check constitutional hash
                if (
                    hasattr(policy, "constitutional_hash")
                    and policy.constitutional_hash == CONSTITUTIONAL_HASH
                ):
                    validation["criteria_met"].append(criterion)
                    validation["score"] += 0.25
                else:
                    validation["criteria_failed"].append(criterion)
                    validation["valid"] = False

        return validation

    def _update_metrics(self, round_obj: SelfPlayRound) -> None:
        """Update system metrics after a round."""
        self._metrics["total_rounds"] += 1
        self._metrics["total_challenges"] += round_obj.challenges_attempted
        self._metrics["challenges_solved"] += round_obj.challenges_solved

        # Update success rate
        if self._metrics["total_challenges"] > 0:
            self._metrics["average_success_rate"] = (
                self._metrics["challenges_solved"] / self._metrics["total_challenges"]
            )

        # Update difficulty progression
        if round_obj.challenges_attempted > 0:
            avg_difficulty = round_obj.average_difficulty
            self._metrics["difficulty_progression"] = avg_difficulty

    async def _calculate_improvement(self) -> Dict[str, float]:
        """Calculate improvement metrics compared to baseline."""
        improvement = {
            "success_rate_improvement": 0.0,
            "difficulty_improvement": 0.0,
            "speed_improvement": 0.0,
            "overall_improvement": 0.0,
        }

        # Compare to recent performance
        recent_rounds = self.completed_rounds[-5:]  # Last 5 rounds
        if len(recent_rounds) >= 2:
            current_success_rate = self._metrics["average_success_rate"]
            recent_avg_success = sum(
                r.challenges_solved / max(r.challenges_attempted, 1) for r in recent_rounds
            ) / len(recent_rounds)

            improvement["success_rate_improvement"] = current_success_rate - recent_avg_success

            # Difficulty improvement
            recent_avg_difficulty = sum(r.average_difficulty for r in recent_rounds) / len(
                recent_rounds
            )
            improvement["difficulty_improvement"] = (
                self._metrics["difficulty_progression"] - recent_avg_difficulty
            )

        # Calculate overall improvement score
        improvement["overall_improvement"] = (
            improvement["success_rate_improvement"] * 0.5
            + improvement["difficulty_improvement"] * 0.3
            + improvement["speed_improvement"] * 0.2
        )

        return improvement

    async def run_self_improvement_session(
        self, num_rounds: int = 5, adaptive_difficulty: bool = True
    ) -> JSONDict:
        """
        Run a complete self-improvement session.

        Args:
            num_rounds: Number of rounds to run
            adaptive_difficulty: Whether to adapt difficulty based on performance

        Returns:
            Session results
        """
        session_results = {
            "session_id": hashlib.sha256(f"session_{time.time()}".encode()).hexdigest()[:12],
            "rounds_completed": 0,
            "total_challenges": 0,
            "challenges_solved": 0,
            "improvement_achieved": False,
            "final_metrics": {},
            "round_summaries": [],
        }

        starting_success_rate = self._metrics["average_success_rate"]
        current_difficulty = DifficultyLevel.INTERMEDIATE

        for round_num in range(num_rounds):
            # Adapt difficulty if enabled
            if adaptive_difficulty and round_num > 0:
                current_difficulty = await self._adapt_difficulty(current_difficulty)

            # Run a round
            round_obj = await self.start_self_play_round(
                mode=SelfPlayMode.IMPROVEMENT, target_difficulty=current_difficulty
            )

            round_results = await self.execute_self_play_round(round_obj)

            session_results["round_summaries"].append(round_results)
            session_results["rounds_completed"] += 1
            session_results["total_challenges"] += round_results["challenges_attempted"]
            session_results["challenges_solved"] += round_results["challenges_solved"]

            # Check for significant improvement
            if (
                round_results["improvement_metrics"].get("overall_improvement", 0)
                > self.improvement_threshold
            ):
                session_results["improvement_achieved"] = True
                logger.info(f"Significant improvement detected in round {round_num + 1}")

        # Final assessment
        final_success_rate = self._metrics["average_success_rate"]
        session_results["final_metrics"] = self.get_system_metrics()
        session_results["success_rate_improvement"] = final_success_rate - starting_success_rate

        logger.info(
            f"Completed self-improvement session: "
            f"{session_results['challenges_solved']}/{session_results['total_challenges']} "
            f"challenges solved, success rate improvement: "
            f"{session_results['success_rate_improvement']:.3f}"
        )

        return session_results

    async def _adapt_difficulty(self, current_difficulty: DifficultyLevel) -> DifficultyLevel:
        """Adapt difficulty based on recent performance."""
        recent_success_rate = self._metrics["average_success_rate"]

        if recent_success_rate > 0.8:
            # Increase difficulty
            if current_difficulty.value < max(d.value for d in DifficultyLevel):
                new_difficulty = DifficultyLevel(current_difficulty.value + 1)
                logger.info(f"Increasing difficulty to {new_difficulty.name}")
                return new_difficulty

        elif recent_success_rate < 0.4:
            # Decrease difficulty
            if current_difficulty.value > min(d.value for d in DifficultyLevel):
                new_difficulty = DifficultyLevel(current_difficulty.value - 1)
                logger.info(f"Decreasing difficulty to {new_difficulty.name}")
                return new_difficulty

        return current_difficulty

    def get_system_metrics(self) -> JSONDict:
        """Get current system performance metrics."""
        return {
            **self._metrics,
            "active_round": self.active_round.round_id if self.active_round else None,
            "completed_rounds": len(self.completed_rounds),
            "available_categories": len(self.challenge_templates),
            "psv_agents": len(self.psv_agents),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def analyze_learning_patterns(self) -> JSONDict:
        """Analyze patterns in the learning process."""
        analysis = {
            "category_performance": {},
            "difficulty_progression": {},
            "learning_trends": {},
            "bottlenecks_identified": [],
        }

        # Analyze performance by category
        for round_obj in self.completed_rounds:
            for challenge in round_obj.challenges:
                cat = challenge.category
                if cat not in analysis["category_performance"]:
                    analysis["category_performance"][cat] = {"attempted": 0, "solved": 0}

                analysis["category_performance"][cat]["attempted"] += 1
                if challenge.success_achieved:
                    analysis["category_performance"][cat]["solved"] += 1

        # Calculate success rates
        for _, stats in analysis["category_performance"].items():
            if stats["attempted"] > 0:
                stats["success_rate"] = stats["solved"] / stats["attempted"]

        # Identify bottlenecks (categories with low success rates)
        for cat, stats in analysis["category_performance"].items():
            success_rate = stats.get("success_rate", 0)
            if success_rate < 0.5 and stats["attempted"] >= 3:
                analysis["bottlenecks_identified"].append(
                    {
                        "category": cat,
                        "success_rate": success_rate,
                        "recommendation": "Focus improvement efforts on this category",
                    }
                )

        return analysis
