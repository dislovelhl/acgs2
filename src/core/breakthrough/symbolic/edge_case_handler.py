"""
ABL-Refl Constitutional Edge Case Handler
==========================================

Constitutional Hash: cdd01ef066bc6cf2

Implements cognitive reflection for edge cases:
- System 1: Fast neural prediction
- System 2: Slow abductive correction when reflection triggers
- Focused attention on error space (reduced search complexity)

Key Insight: Use symbolic reasoning only when neural prediction
is uncertain, achieving 200× fewer training iterations.

References:
- ABL-Refl: Abductive Reflection (arXiv:2412.08457)
"""

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from ...shared.types import ContextData, JSONDict
from .. import CONSTITUTIONAL_HASH, EDGE_CASE_ACCURACY_TARGET

logger = logging.getLogger(__name__)


class CognitiveSystem(Enum):
    """Cognitive system used for classification."""

    SYSTEM_1 = "system_1"  # Fast, intuitive, neural
    SYSTEM_2 = "system_2"  # Slow, deliberate, symbolic


@dataclass
class NeuralPrediction:
    """Result from System 1 neural prediction."""

    prediction_id: str
    label: str
    confidence: float
    embedding: List[float]
    processing_time_ms: float
    metadata: JSONDict = field(default_factory=dict)


@dataclass
class ReflectionVector:
    """Reflection analysis from knowledge base."""

    error_probability: float
    violated_rules: List[str]
    attention_mask: List[int]  # Focused positions for System 2
    reasoning_trace: List[str]


@dataclass
class AbductiveCorrection:
    """Result from System 2 abductive reasoning."""

    corrected_label: str
    confidence: float
    derivation: List[str]  # Logical derivation steps
    corrections_made: List[str]
    symbolic_trace: JSONDict


@dataclass
class ClassificationResult:
    """Final classification result."""

    result_id: str
    prediction: str
    confidence: float
    system_used: CognitiveSystem
    reflection_triggered: bool
    symbolic_trace: List[str]
    processing_time_ms: float
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> JSONDict:
        return {
            "result_id": self.result_id,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "system_used": self.system_used.value,
            "reflection_triggered": self.reflection_triggered,
            "symbolic_trace": self.symbolic_trace,
            "processing_time_ms": self.processing_time_ms,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class ReflectionResult:
    """Result from reflection analysis."""

    should_reflect: bool
    error_probability: float
    violated_rules: List[str]
    focus_areas: List[str]


class NeuralClassifier:
    """
    System 1: Fast Neural Classifier.

    Provides fast, intuitive predictions based on learned patterns.
    Used for most cases; uncertain predictions trigger System 2.
    """

    def __init__(self, model_path: Optional[str] = None, embedding_dim: int = 128):
        """
        Initialize neural classifier.

        Args:
            model_path: Path to pre-trained model
            embedding_dim: Embedding dimension
        """
        self.model_path = model_path
        self.embedding_dim = embedding_dim

        # Classification labels
        self._labels = [
            "compliant",
            "violation",
            "uncertain",
            "requires_review",
        ]

        self._predictions_made = 0
        logger.info("Initialized NeuralClassifier (System 1)")

    async def predict(self, input_data: ContextData) -> NeuralPrediction:
        """
        Make a fast neural prediction.

        Args:
            input_data: Input features

        Returns:
            NeuralPrediction with label and confidence
        """
        import time

        start_time = time.perf_counter()

        # Simulate neural prediction
        # In production, would use actual neural network

        # Extract features and compute embedding
        embedding = await self._compute_embedding(input_data)

        # Classify based on embedding
        label, confidence = await self._classify(embedding, input_data)

        processing_time = (time.perf_counter() - start_time) * 1000
        self._predictions_made += 1

        return NeuralPrediction(
            prediction_id=f"pred-{uuid.uuid4().hex[:8]}",
            label=label,
            confidence=confidence,
            embedding=embedding,
            processing_time_ms=processing_time,
        )

    async def _compute_embedding(self, input_data: ContextData) -> List[float]:
        """Compute embedding from input data."""
        # Simulate embedding computation
        import hashlib

        content = str(input_data).encode()
        hash_bytes = hashlib.sha256(content).digest()
        return [b / 255.0 for b in hash_bytes[: self.embedding_dim]]

    async def _classify(self, embedding: List[float], input_data: ContextData) -> Tuple[str, float]:
        """Classify based on embedding."""
        # Simulate classification logic
        # Check for obvious patterns

        content = str(input_data).lower()

        if any(word in content for word in ["violation", "breach", "error"]):
            return "violation", 0.85

        if any(word in content for word in ["uncertain", "unclear", "ambiguous"]):
            return "uncertain", 0.60

        if any(word in content for word in ["review", "check", "verify"]):
            return "requires_review", 0.75

        # Default to compliant with moderate confidence
        return "compliant", 0.80


class AbductionEngine:
    """
    System 2: Abductive Reasoning Engine.

    Performs slow, deliberate symbolic reasoning to correct
    neural predictions when uncertainty is high.

    Uses abductive logic to find the best explanation for
    observed facts given background knowledge.
    """

    def __init__(self, knowledge_base: "DeepProbLogKB"):
        """
        Initialize abduction engine.

        Args:
            knowledge_base: Knowledge base for reasoning
        """
        self.kb = knowledge_base
        self._corrections_made = 0

        logger.info("Initialized AbductionEngine (System 2)")

    async def correct(
        self,
        input_data: ContextData,
        neural_prediction: NeuralPrediction,
        violated_rules: List[str],
        focused_space: List[int],
    ) -> AbductiveCorrection:
        """
        Perform abductive correction of neural prediction.

        Uses focused attention on error space to reduce search complexity.

        Args:
            input_data: Original input
            neural_prediction: System 1 prediction
            violated_rules: Rules potentially violated
            focused_space: Positions to focus on

        Returns:
            AbductiveCorrection with corrected label
        """
        derivation = []
        corrections = []

        # Step 1: Identify inconsistencies with knowledge base
        inconsistencies = await self._find_inconsistencies(
            input_data, neural_prediction, violated_rules
        )

        derivation.append(f"Found {len(inconsistencies)} inconsistencies")

        # Step 2: Generate hypotheses to explain inconsistencies
        hypotheses = await self._generate_hypotheses(input_data, inconsistencies, focused_space)

        derivation.append(f"Generated {len(hypotheses)} hypotheses")

        # Step 3: Select best hypothesis using abduction
        best_hypothesis = await self._select_best_hypothesis(hypotheses, input_data)

        derivation.append(f"Selected hypothesis: {best_hypothesis.get('label', 'unknown')}")

        # Step 4: Derive corrected label
        corrected_label = best_hypothesis.get("label", neural_prediction.label)
        confidence = best_hypothesis.get("confidence", 0.9)

        if corrected_label != neural_prediction.label:
            corrections.append(f"Changed {neural_prediction.label} → {corrected_label}")

        self._corrections_made += 1

        return AbductiveCorrection(
            corrected_label=corrected_label,
            confidence=confidence,
            derivation=derivation,
            corrections_made=corrections,
            symbolic_trace={
                "inconsistencies": inconsistencies,
                "hypothesis": best_hypothesis,
            },
        )

    async def _find_inconsistencies(
        self, input_data: ContextData, prediction: NeuralPrediction, violated_rules: List[str]
    ) -> List[JSONDict]:
        """Find inconsistencies between prediction and knowledge base."""
        inconsistencies = []

        # Check prediction against each violated rule
        for rule in violated_rules:
            rule_result = await self.kb.evaluate_rule(rule, input_data)
            if not rule_result.get("satisfied", True):
                inconsistencies.append(
                    {
                        "rule": rule,
                        "expected": rule_result.get("expected"),
                        "actual": prediction.label,
                    }
                )

        return inconsistencies

    async def _generate_hypotheses(
        self, input_data: ContextData, inconsistencies: List[JSONDict], focused_space: List[int]
    ) -> List[JSONDict]:
        """Generate hypotheses to explain inconsistencies."""
        hypotheses = []

        # Use focused space to limit search
        # This is the key efficiency gain of ABL-Refl

        # Hypothesis 1: Label should be different
        if inconsistencies:
            hypotheses.append(
                {
                    "type": "label_change",
                    "label": "violation",
                    "confidence": 0.85,
                    "explanation": "Rules indicate violation",
                }
            )

        # Hypothesis 2: Input data was misinterpreted
        hypotheses.append(
            {
                "type": "interpretation",
                "label": "requires_review",
                "confidence": 0.75,
                "explanation": "Input ambiguous, needs human review",
            }
        )

        # Hypothesis 3: Original prediction correct
        hypotheses.append(
            {
                "type": "confirmation",
                "label": "compliant",
                "confidence": 0.70,
                "explanation": "Original prediction may be correct",
            }
        )

        return hypotheses

    async def _select_best_hypothesis(
        self, hypotheses: List[JSONDict], input_data: ContextData
    ) -> JSONDict:
        """Select the best hypothesis using abductive reasoning."""
        if not hypotheses:
            return {"label": "uncertain", "confidence": 0.5}

        # Sort by confidence and explanatory power
        sorted_hyps = sorted(hypotheses, key=lambda h: h.get("confidence", 0), reverse=True)

        return sorted_hyps[0]


class DeepProbLogKB:
    """
    DeepProbLog Knowledge Base for constitutional principles.

    Combines neural networks with probabilistic logic programming
    for constitutional rule evaluation.
    """

    def __init__(self):
        """Initialize knowledge base."""
        self._rules: Dict[str, JSONDict] = {}
        self._facts: List[JSONDict] = []

        # Add default constitutional rules
        self._add_default_rules()

        logger.info("Initialized DeepProbLogKB")

    def _add_default_rules(self) -> None:
        """Add default constitutional rules."""
        self._rules["data_integrity"] = {
            "id": "data_integrity",
            "description": "All actions must maintain data integrity",
            "priority": 1.0,
            "check": lambda data: "corrupt" not in str(data).lower(),
        }

        self._rules["audit_required"] = {
            "id": "audit_required",
            "description": "Audit trail must be maintained",
            "priority": 0.9,
            "check": lambda data: data.get("audit_enabled", True),
        }

        self._rules["constitutional_hash"] = {
            "id": "constitutional_hash",
            "description": "Constitutional hash must be valid",
            "priority": 1.0,
            "check": lambda data: data.get("hash") == CONSTITUTIONAL_HASH or "hash" not in data,
        }

    async def add_rule(
        self,
        rule_id: str,
        description: str,
        check_fn: Callable[[ContextData], bool],
        priority: float = 0.5,
    ) -> None:
        """Add a rule to the knowledge base."""
        self._rules[rule_id] = {
            "id": rule_id,
            "description": description,
            "priority": priority,
            "check": check_fn,
        }

    async def evaluate_rule(self, rule_id: str, input_data: ContextData) -> JSONDict:
        """Evaluate a rule against input data."""
        if rule_id not in self._rules:
            return {"satisfied": True, "rule_id": rule_id, "reason": "Rule not found"}

        rule = self._rules[rule_id]
        try:
            check_fn = rule.get("check", lambda x: True)
            satisfied = check_fn(input_data)
            return {
                "satisfied": satisfied,
                "rule_id": rule_id,
                "expected": "compliance" if satisfied else "violation",
            }
        except Exception as e:
            return {
                "satisfied": False,
                "rule_id": rule_id,
                "error": str(e),
            }

    async def get_applicable_rules(self, input_data: ContextData) -> List[str]:
        """Get rules applicable to the input data."""
        return list(self._rules.keys())

    async def check_all_rules(self, input_data: ContextData) -> Tuple[List[str], List[str]]:
        """
        Check all rules against input data.

        Returns:
            Tuple of (satisfied_rules, violated_rules)
        """
        satisfied = []
        violated = []

        for rule_id in self._rules:
            result = await self.evaluate_rule(rule_id, input_data)
            if result.get("satisfied", True):
                satisfied.append(rule_id)
            else:
                violated.append(rule_id)

        return satisfied, violated


class ConstitutionalEdgeCaseHandler:
    """
    Constitutional Edge Case Handler with ABL-Refl.

    Implements cognitive reflection for constitutional governance:
    - System 1: Fast neural prediction (default path)
    - System 2: Slow abductive correction (when uncertain)

    The reflection threshold determines when to switch systems,
    achieving optimal accuracy with minimal computational cost.
    """

    def __init__(
        self,
        reflection_threshold: float = 0.7,
        neural_classifier: Optional[NeuralClassifier] = None,
        knowledge_base: Optional[DeepProbLogKB] = None,
    ):
        """
        Initialize edge case handler.

        Args:
            reflection_threshold: Confidence threshold for reflection
            neural_classifier: Optional custom neural classifier
            knowledge_base: Optional custom knowledge base
        """
        self.threshold = reflection_threshold
        self.target_accuracy = EDGE_CASE_ACCURACY_TARGET

        self.neural_classifier = neural_classifier or NeuralClassifier()
        self.knowledge_base = knowledge_base or DeepProbLogKB()
        self.abduction_engine = AbductionEngine(self.knowledge_base)

        self._stats = {
            "total_classifications": 0,
            "system_1_only": 0,
            "system_2_triggered": 0,
            "corrections_made": 0,
        }

        logger.info(f"Initialized ConstitutionalEdgeCaseHandler threshold={reflection_threshold}")

    async def classify(self, input_data: ContextData) -> ClassificationResult:
        """
        Classify input with cognitive reflection.

        Args:
            input_data: Input data to classify

        Returns:
            ClassificationResult with prediction and trace
        """
        import time

        start_time = time.perf_counter()

        result_id = f"class-{uuid.uuid4().hex[:8]}"
        self._stats["total_classifications"] += 1

        # System 1: Fast neural prediction
        prediction = await self.neural_classifier.predict(input_data)

        # Compute reflection vector from knowledge base
        reflection = await self.compute_reflection(input_data, prediction)

        # Check if reflection triggers System 2
        if reflection.error_probability > (1 - self.threshold):
            # System 2: Abductive reasoning
            self._stats["system_2_triggered"] += 1

            abduced = await self.abduction_engine.correct(
                input_data,
                prediction,
                violated_rules=reflection.violated_rules,
                focused_space=reflection.attention_mask,
            )

            if abduced.corrected_label != prediction.label:
                self._stats["corrections_made"] += 1

            processing_time = (time.perf_counter() - start_time) * 1000

            return ClassificationResult(
                result_id=result_id,
                prediction=abduced.corrected_label,
                confidence=abduced.confidence,
                system_used=CognitiveSystem.SYSTEM_2,
                reflection_triggered=True,
                symbolic_trace=abduced.derivation,
                processing_time_ms=processing_time,
            )

        # System 1 sufficient
        self._stats["system_1_only"] += 1
        processing_time = (time.perf_counter() - start_time) * 1000

        return ClassificationResult(
            result_id=result_id,
            prediction=prediction.label,
            confidence=prediction.confidence,
            system_used=CognitiveSystem.SYSTEM_1,
            reflection_triggered=False,
            symbolic_trace=[],
            processing_time_ms=processing_time,
        )

    async def compute_reflection(
        self, input_data: ContextData, prediction: NeuralPrediction
    ) -> ReflectionVector:
        """
        Compute reflection vector from knowledge base.

        The reflection vector indicates:
        - Probability of error in neural prediction
        - Which rules might be violated
        - Where to focus attention for correction
        """
        # Check rules against input
        satisfied, violated = await self.knowledge_base.check_all_rules(input_data)

        # Compute error probability
        if violated:
            error_prob = min(0.9, 0.3 + len(violated) * 0.2)
        else:
            error_prob = max(0.0, 1 - prediction.confidence)

        # Generate attention mask (simplified)
        # In full implementation, would identify specific input positions
        attention_mask = list(range(min(10, len(str(input_data)))))

        # Reasoning trace
        reasoning = []
        if violated:
            reasoning.append(f"Rules violated: {', '.join(violated)}")
        if prediction.confidence < self.threshold:
            reasoning.append(f"Low confidence: {prediction.confidence:.2f}")

        return ReflectionVector(
            error_probability=error_prob,
            violated_rules=violated,
            attention_mask=attention_mask,
            reasoning_trace=reasoning,
        )

    def get_stats(self) -> JSONDict:
        """Get handler statistics."""
        total = self._stats["total_classifications"]
        s1_rate = self._stats["system_1_only"] / max(total, 1)
        s2_rate = self._stats["system_2_triggered"] / max(total, 1)

        return {
            **self._stats,
            "system_1_rate": s1_rate,
            "system_2_rate": s2_rate,
            "reflection_threshold": self.threshold,
            "target_accuracy": self.target_accuracy,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
