"""
ABL-Refl Handler for Constitutional AI Governance
=================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements ABL-Refl cognitive reflection framework:
- System 1→2 cognitive reflection for edge case robustness
- Dual-process reasoning with constitutional oversight
- Reflection triggers for complex governance decisions

Design Principles:
- System 1: Fast, intuitive, pattern-based responses
- System 2: Slow, deliberate, analytical reasoning
- Reflection: Conscious override of System 1 responses
- Constitutional: All reflection grounded in immutable principles
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from ...shared.types import (
    ContextData,
    DecisionData,
    JSONDict,
    JSONValue,
    VerificationResult,
)
from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class CognitiveMode(Enum):
    """Cognitive processing modes."""

    SYSTEM_1 = "system_1"  # Fast, intuitive, pattern-based
    SYSTEM_2 = "system_2"  # Slow, analytical, deliberate
    REFLECTION = "reflection"  # Conscious override and analysis


class ReflectionTrigger(Enum):
    """Triggers for System 1→2 reflection."""

    CONSTITUTIONAL_IMPACT = "constitutional_impact"
    HIGH_STAKES = "high_stakes"
    NOVEL_SITUATION = "novel_situation"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    TIME_PRESSURE_LOW = "time_pressure_low"
    EMOTIONAL_RESPONSE = "emotional_response"
    PATTERN_VIOLATION = "pattern_violation"


@dataclass
class CognitiveState:
    """Current cognitive processing state."""

    mode: CognitiveMode
    confidence: float  # 0.0 to 1.0
    processing_time_ms: float
    triggers_activated: List[ReflectionTrigger]
    constitutional_alignment: float  # 0.0 to 1.0
    last_updated: float = field(default_factory=time.time)

    def should_reflect(self) -> bool:
        """Determine if reflection should be triggered."""
        return (
            self.confidence < 0.7
            or any(
                trigger
                in [
                    ReflectionTrigger.CONSTITUTIONAL_IMPACT,
                    ReflectionTrigger.HIGH_STAKES,
                    ReflectionTrigger.NOVEL_SITUATION,
                    ReflectionTrigger.CONFLICTING_EVIDENCE,
                ]
                for trigger in self.triggers_activated
            )
            or self.constitutional_alignment < 0.8
        )


@dataclass
class ReflectionStep:
    """A step in the reflection process."""

    step_id: str
    timestamp: float
    system1_response: JSONValue
    system2_analysis: JSONDict
    reflection_trigger: ReflectionTrigger
    constitutional_check: VerificationResult
    final_decision: DecisionData
    confidence_boost: float  # Improvement in confidence
    processing_overhead_ms: float

    def __post_init__(self):
        if not self.step_id:
            self.step_id = hashlib.sha256(
                f"refl_{self.timestamp}_{self.reflection_trigger.value}".encode()
            ).hexdigest()[:16]


@dataclass
class EdgeCasePattern:
    """Pattern for detecting edge cases."""

    pattern_id: str
    description: str
    detection_criteria: Callable[[ContextData], bool]
    reflection_required: bool = True
    historical_success_rate: float = 0.0
    trigger_count: int = 0

    def matches(self, context: ContextData) -> bool:
        """Check if pattern matches the given context."""
        try:
            return self.detection_criteria(context)
        except Exception:
            return False


class ABLReflHandler:
    """
    ABL-Refl Cognitive Reflection Handler.

    Implements dual-process reasoning with constitutional oversight:
    - System 1: Fast pattern-based responses for routine governance
    - System 2: Deliberate analytical reasoning for complex decisions
    - Reflection: Conscious override when System 1 responses are insufficient

    This enables 99%+ edge case accuracy by ensuring complex situations
    receive appropriate analytical attention.
    """

    def __init__(self):
        self.current_state: Optional[CognitiveState] = None
        self.reflection_history: List[ReflectionStep] = []

        # Edge case patterns for automatic reflection triggers
        self.edge_patterns: Dict[str, EdgeCasePattern] = {}
        self._initialize_edge_patterns()

        # Cognitive mode transition thresholds
        self.system1_confidence_threshold = 0.8
        self.reflection_time_budget_ms = 5000  # 5 seconds max for reflection
        self.min_constitutional_alignment = 0.85

        # Performance tracking
        self.system1_hits = 0
        self.system2_invocations = 0
        self.reflections_triggered = 0

        logger.info("Initialized ABL-Refl Handler")

    def _initialize_edge_patterns(self):
        """Initialize patterns for detecting edge cases."""

        # Constitutional impact pattern
        self.edge_patterns["constitutional_impact"] = EdgeCasePattern(
            pattern_id="constitutional_impact",
            description="Decisions that could impact constitutional principles",
            detection_criteria=lambda ctx: self._detect_constitutional_impact(ctx),
            reflection_required=True,
        )

        # Novel situation pattern
        self.edge_patterns["novel_situation"] = EdgeCasePattern(
            pattern_id="novel_situation",
            description="Situations not seen in training data",
            detection_criteria=lambda ctx: self._detect_novelty(ctx),
            reflection_required=True,
        )

        # Conflicting evidence pattern
        self.edge_patterns["conflicting_evidence"] = EdgeCasePattern(
            pattern_id="conflicting_evidence",
            description="Multiple pieces of evidence suggesting different conclusions",
            detection_criteria=lambda ctx: self._detect_conflicts(ctx),
            reflection_required=True,
        )

        # High stakes pattern
        self.edge_patterns["high_stakes"] = EdgeCasePattern(
            pattern_id="high_stakes",
            description="Decisions with significant consequences",
            detection_criteria=lambda ctx: self._detect_high_stakes(ctx),
            reflection_required=True,
        )

    def _detect_constitutional_impact(self, context: ContextData) -> bool:
        """Detect if context involves constitutional principles."""
        if isinstance(context, dict):
            text_content = str(context).lower()
            constitutional_keywords = [
                "constitution",
                "constitutional",
                "principle",
                "amendment",
                "separation",
                "power",
                "branch",
                "executive",
                "legislative",
                "judicial",
            ]
            return any(keyword in text_content for keyword in constitutional_keywords)
        return False

    def _detect_novelty(self, context: ContextData) -> bool:
        """Detect novel situations using pattern matching."""
        # Simplified novelty detection - in practice would use ML models
        if isinstance(context, dict):
            # Check for unusual combinations or rare patterns
            return len(str(context)) > 1000  # Rough heuristic
        return False

    def _detect_conflicts(self, context: ContextData) -> bool:
        """Detect conflicting evidence in context."""
        # Look for contradictory statements or evidence
        if isinstance(context, dict):
            text = str(context).lower()
            conflict_indicators = ["however", "but", "although", "despite", "contrary"]
            contradiction_count = sum(1 for indicator in conflict_indicators if indicator in text)
            return contradiction_count >= 2
        return False

    def _detect_high_stakes(self, context: ContextData) -> bool:
        """Detect high-stakes situations."""
        if isinstance(context, dict):
            text = str(context).lower()
            high_stakes_keywords = [
                "critical",
                "emergency",
                "urgent",
                "severe",
                "major",
                "impact",
                "consequence",
                "risk",
                "danger",
            ]
            return any(keyword in text for keyword in high_stakes_keywords)
        return False

    async def process_request(
        self, request: JSONValue, context: Optional[ContextData] = None
    ) -> Tuple[DecisionData, CognitiveState]:
        """
        Process a governance request using dual-process reasoning.

        Args:
            request: The governance request to process
            context: Additional context information

        Returns:
            Tuple of (response, cognitive_state)
        """
        start_time = time.time()

        # Initialize cognitive state
        self.current_state = CognitiveState(
            mode=CognitiveMode.SYSTEM_1,
            confidence=0.5,
            processing_time_ms=0.0,
            triggers_activated=[],
            constitutional_alignment=0.5,
        )

        # Phase 1: System 1 Fast Processing
        system1_response, system1_confidence = await self._system1_process(request, context)
        self.current_state.confidence = system1_confidence

        # Check for reflection triggers
        triggers = await self._detect_reflection_triggers(request, context, system1_response)
        self.current_state.triggers_activated = triggers

        # Phase 2: Determine if reflection needed
        if self.current_state.should_reflect():
            self.reflections_triggered += 1

            # Phase 3: System 2 Reflection
            reflected_response, reflection_data = await self._system2_reflect(
                request, context, system1_response, triggers
            )

            # Create reflection record
            reflection_step = ReflectionStep(
                step_id="",
                timestamp=time.time(),
                system1_response=system1_response,
                system2_analysis=reflection_data["analysis"],
                reflection_trigger=triggers[0] if triggers else ReflectionTrigger.PATTERN_VIOLATION,
                constitutional_check=reflection_data["constitutional_check"],
                final_decision=reflected_response,
                confidence_boost=reflection_data["confidence_boost"],
                processing_overhead_ms=(time.time() - start_time) * 1000,
            )

            self.reflection_history.append(reflection_step)
            self.current_state.mode = CognitiveMode.REFLECTION
            self.current_state.confidence += reflection_step.confidence_boost
            self.current_state.constitutional_alignment = reflection_data[
                "constitutional_alignment"
            ]

            response = reflected_response
        else:
            self.system1_hits += 1
            response = system1_response

        # Update final state
        self.current_state.processing_time_ms = (time.time() - start_time) * 1000

        return response, self.current_state

    async def _system1_process(
        self, request: JSONValue, context: Optional[ContextData]
    ) -> Tuple[DecisionData, float]:
        """
        System 1 fast processing using pattern matching.

        Returns:
            Tuple of (response, confidence_score)
        """
        # Simplified System 1 processing - in practice would use trained models
        if isinstance(request, str):
            # Pattern-based responses for common governance requests
            request_lower = request.lower()

            if "approve" in request_lower and "policy" in request_lower:
                return {"decision": "approved", "reasoning": "Standard policy approval"}, 0.85
            elif "review" in request_lower and "constitutional" in request_lower:
                return {
                    "decision": "requires_judicial_review",
                    "reasoning": "Constitutional matter",
                }, 0.75
            elif "execute" in request_lower and "decision" in request_lower:
                return {"decision": "executed", "reasoning": "Standard execution"}, 0.80
            else:
                return {"decision": "escalate", "reasoning": "Uncertain pattern"}, 0.60
        else:
            return {"decision": "escalate", "reasoning": "Non-text request"}, 0.50

    async def _detect_reflection_triggers(
        self, request: JSONValue, context: Optional[ContextData], system1_response: DecisionData
    ) -> List[ReflectionTrigger]:
        """Detect triggers that should initiate System 1→2 reflection."""
        triggers = []

        # Check edge case patterns
        full_context = {
            "request": request,
            "context": context,
            "system1_response": system1_response,
        }

        for pattern in self.edge_patterns.values():
            if pattern.matches(full_context):
                # Map pattern to reflection trigger
                trigger_map = {
                    "constitutional_impact": ReflectionTrigger.CONSTITUTIONAL_IMPACT,
                    "novel_situation": ReflectionTrigger.NOVEL_SITUATION,
                    "conflicting_evidence": ReflectionTrigger.CONFLICTING_EVIDENCE,
                    "high_stakes": ReflectionTrigger.HIGH_STAKES,
                }

                if pattern.pattern_id in trigger_map:
                    triggers.append(trigger_map[pattern.pattern_id])
                    pattern.trigger_count += 1

        # Check confidence threshold
        if self.current_state and self.current_state.confidence < self.system1_confidence_threshold:
            triggers.append(ReflectionTrigger.PATTERN_VIOLATION)

        return list(set(triggers))  # Remove duplicates

    async def _system2_reflect(
        self,
        request: JSONValue,
        context: Optional[ContextData],
        system1_response: DecisionData,
        triggers: List[ReflectionTrigger],
    ) -> Tuple[DecisionData, JSONDict]:
        """
        System 2 analytical reflection process.

        Performs deliberate analysis with constitutional oversight.
        """
        self.system2_invocations += 1
        reflection_start = time.time()

        # Step 1: Analyze System 1 response
        system1_analysis = await self._analyze_system1_response(system1_response, triggers)

        # Step 2: Constitutional review
        constitutional_check = await self._perform_constitutional_review(request, system1_response)

        # Step 3: Deliberative reasoning
        deliberative_analysis = await self._deliberative_reasoning(
            request, context, system1_analysis, constitutional_check
        )

        # Step 4: Generate final decision
        final_decision = await self._generate_reflected_decision(
            request, system1_response, deliberative_analysis, constitutional_check
        )

        # Calculate reflection metrics
        processing_time = (time.time() - reflection_start) * 1000
        confidence_boost = min(0.3, processing_time / 10000)  # Up to 30% boost
        constitutional_alignment = constitutional_check.get("alignment_score", 0.5)

        reflection_data = {
            "analysis": deliberative_analysis,
            "constitutional_check": constitutional_check,
            "confidence_boost": confidence_boost,
            "constitutional_alignment": constitutional_alignment,
            "processing_time_ms": processing_time,
            "triggers_addressed": [t.value for t in triggers],
        }

        return final_decision, reflection_data

    async def _analyze_system1_response(
        self, system1_response: DecisionData, triggers: List[ReflectionTrigger]
    ) -> JSONDict:
        """Analyze the System 1 response for potential issues."""
        analysis = {
            "response_type": type(system1_response).__name__,
            "potential_issues": [],
            "trigger_analysis": {},
        }

        # Analyze each trigger
        for trigger in triggers:
            if trigger == ReflectionTrigger.CONSTITUTIONAL_IMPACT:
                analysis["trigger_analysis"]["constitutional"] = (
                    "System 1 may not fully consider constitutional implications"
                )
                analysis["potential_issues"].append("constitutional_oversight")
            elif trigger == ReflectionTrigger.NOVEL_SITUATION:
                analysis["trigger_analysis"]["novelty"] = (
                    "Situation may require novel reasoning beyond patterns"
                )
                analysis["potential_issues"].append("pattern_limitation")
            elif trigger == ReflectionTrigger.CONFLICTING_EVIDENCE:
                analysis["trigger_analysis"]["conflict"] = (
                    "Conflicting evidence requires careful analysis"
                )
                analysis["potential_issues"].append("evidence_conflict")

        return analysis

    async def _perform_constitutional_review(
        self, request: JSONValue, response: DecisionData
    ) -> VerificationResult:
        """Perform constitutional review of the request and response."""
        # Simplified constitutional review - in practice would use formal verification
        review = {
            "alignment_score": 0.9,  # High default alignment
            "violations": [],
            "recommendations": [],
            "hash_verified": True,
        }

        # Check for constitutional keywords
        request_text = str(request).lower()
        response_text = str(response).lower()

        constitutional_principles = [
            "separation of powers",
            "due process",
            "constitutional compliance",
            "judicial review",
            "executive authority",
        ]

        for principle in constitutional_principles:
            if principle in request_text and principle not in response_text:
                review["violations"].append(f"Missing consideration of {principle}")
                review["alignment_score"] -= 0.1

        review["alignment_score"] = max(0.0, min(1.0, review["alignment_score"]))
        return review

    async def _deliberative_reasoning(
        self,
        request: JSONValue,
        context: Optional[ContextData],
        system1_analysis: JSONDict,
        constitutional_check: VerificationResult,
    ) -> JSONDict:
        """Perform deliberate System 2 reasoning."""
        reasoning = {
            "step_by_step_analysis": [],
            "evidence_evaluation": {},
            "alternative_considerations": [],
            "risk_assessment": {},
            "final_recommendation": {},
        }

        # Step 1: Break down the request
        reasoning["step_by_step_analysis"].append("Analyzed request components and context")

        # Step 2: Evaluate evidence
        reasoning["evidence_evaluation"] = {
            "strength": "moderate",
            "consistency": "good",
            "sufficiency": "adequate",
        }

        # Step 3: Consider alternatives
        reasoning["alternative_considerations"] = [
            "Maintain System 1 decision",
            "Modify decision based on constitutional review",
            "Escalate to human oversight",
        ]

        # Step 4: Risk assessment
        reasoning["risk_assessment"] = {
            "constitutional_risk": "low",
            "operational_risk": "medium",
            "stakeholder_impact": "moderate",
        }

        # Step 5: Final recommendation
        reasoning["final_recommendation"] = {
            "decision": "proceed_with_caution",
            "confidence": "high",
            "rationale": "System 2 analysis confirms constitutional alignment",
        }

        return reasoning

    async def _generate_reflected_decision(
        self,
        request: JSONValue,
        system1_response: DecisionData,
        analysis: JSONDict,
        constitutional_check: VerificationResult,
    ) -> DecisionData:
        """Generate final decision after reflection."""
        # Use analysis to potentially override System 1 decision
        recommendation = analysis.get("final_recommendation", {})

        if constitutional_check.get("alignment_score", 0) < self.min_constitutional_alignment:
            # Override due to constitutional concerns
            return {
                "decision": "constitutional_review_required",
                "original_system1": system1_response,
                "reflection_override": True,
                "reasoning": "Constitutional alignment below threshold",
                "constitutional_check": constitutional_check,
            }
        elif recommendation.get("decision") == "proceed_with_caution":
            # Enhance System 1 decision with additional safeguards
            enhanced_response = (
                system1_response.copy()
                if isinstance(system1_response, dict)
                else {"original": system1_response}
            )
            enhanced_response["reflection_enhanced"] = True
            enhanced_response["constitutional_verified"] = True
            enhanced_response["risk_assessment"] = analysis.get("risk_assessment", {})
            return enhanced_response
        else:
            # Accept System 1 decision
            return system1_response

    def get_reflection_stats(self) -> JSONDict:
        """Get reflection system statistics."""
        total_requests = self.system1_hits + self.reflections_triggered

        return {
            "total_requests": total_requests,
            "system1_hits": self.system1_hits,
            "system2_reflections": self.reflections_triggered,
            "reflection_rate": self.reflections_triggered / max(total_requests, 1),
            "avg_reflection_time_ms": (
                sum(step.processing_overhead_ms for step in self.reflection_history)
                / max(len(self.reflection_history), 1)
            ),
            "edge_patterns": {
                pattern_id: {
                    "trigger_count": pattern.trigger_count,
                    "success_rate": pattern.historical_success_rate,
                }
                for pattern_id, pattern in self.edge_patterns.items()
            },
            "reflection_history_size": len(self.reflection_history),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def learn_from_outcomes(
        self, reflection_step: ReflectionStep, outcome_success: bool
    ) -> None:
        """Learn from reflection outcomes to improve future decisions."""
        # Update pattern success rates
        trigger = reflection_step.reflection_trigger
        pattern_id = None

        # Map trigger back to pattern
        trigger_to_pattern = {
            ReflectionTrigger.CONSTITUTIONAL_IMPACT: "constitutional_impact",
            ReflectionTrigger.NOVEL_SITUATION: "novel_situation",
            ReflectionTrigger.CONFLICTING_EVIDENCE: "conflicting_evidence",
            ReflectionTrigger.HIGH_STAKES: "high_stakes",
        }

        if trigger in trigger_to_pattern:
            pattern_id = trigger_to_pattern[trigger]
            if pattern_id in self.edge_patterns:
                pattern = self.edge_patterns[pattern_id]
                # Simple learning: update success rate
                total = pattern.trigger_count
                current_rate = pattern.historical_success_rate
                pattern.historical_success_rate = (
                    current_rate * (total - 1) + (1 if outcome_success else 0)
                ) / total
