"""
ACGS-2 SDPC - Intent Classifier
Constitutional Hash: cdd01ef066bc6cf2

Categorizes user intent for dynamic routing and prompt compilation.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(Enum):
    FACTUAL = "factual"  # High precision, requires GraphCheck & ASC
    CREATIVE = "creative"  # High fluency, relaxed factual constraints
    REASONING = "reasoning"  # Complex logic, triggers AMPO branching
    GENERAL = "general"  # Default/conversational intent


logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user intent to determine optimal processing strategies."""

    # Keyword patterns for each intent type
    REASONING_KEYWORDS: List[str] = [
        "calculate",
        "prove",
        "reason",
        "step by step",
        "analyze",
        "derive",
        "solve",
        "logic",
        "deduce",
        "infer",
    ]
    FACTUAL_KEYWORDS: List[str] = [
        "tell me about",
        "who is",
        "what is",
        "where is",
        "what happened in",
        "date of",
        "historical",
        "how many",
        "when did",
        "facts about",
    ]
    CREATIVE_KEYWORDS: List[str] = [
        "write a story",
        "poem",
        "joke",
        "creative",
        "imagine",
        "song",
        "fiction",
        "invent",
        "compose",
    ]

    # Base confidence for rule-based classification
    BASE_CONFIDENCE: float = 0.7
    # Confidence boost per additional keyword match
    CONFIDENCE_BOOST_PER_MATCH: float = 0.05
    # Maximum confidence for rule-based classification
    MAX_RULE_CONFIDENCE: float = 0.95
    # Confidence for default/general classification
    DEFAULT_CONFIDENCE: float = 0.5

    def __init__(self, model_name: str = "distilbert-base-uncased"):
        self.model_name = model_name
        # In a real implementation, we would load a distilled LLM or BERT model here.
        # For Phase 1, we use dynamic heuristic pattern matching with an LLM fallback hook.
        logger.info(f"IntentClassifier initialized with model: {model_name}")

    def classify(self, content: str) -> IntentType:
        """Determines the intent type of the provided content."""
        content_lower = content.lower()

        # Heuristic Pattern Matching (Fast Path)
        if any(
            word in content_lower
            for word in ["calculate", "prove", "reason", "step by step", "analyze"]
        ):
            return IntentType.REASONING

        if any(
            word in content_lower
            for word in [
                "tell me about",
                "who is",
                "what is",
                "where is",
                "what happened in",
                "date of",
                "historical",
                "how many",
            ]
        ):
            return IntentType.FACTUAL

        if any(
            word in content_lower
            for word in ["write a story", "poem", "joke", "creative", "imagine", "song"]
        ):
            return IntentType.CREATIVE

        # Default to general intent
        return IntentType.GENERAL

    def _count_keyword_matches(self, content_lower: str, keywords: List[str]) -> int:
        """Count how many keywords from the list appear in the content."""
        return sum(1 for keyword in keywords if keyword in content_lower)

    def _calculate_confidence(self, match_count: int, is_default: bool = False) -> float:
        """Calculate confidence score based on keyword match count."""
        if is_default:
            return self.DEFAULT_CONFIDENCE
        if match_count == 0:
            return self.DEFAULT_CONFIDENCE
        # Base confidence + boost for each additional match beyond the first
        confidence = self.BASE_CONFIDENCE + (match_count - 1) * self.CONFIDENCE_BOOST_PER_MATCH
        return min(confidence, self.MAX_RULE_CONFIDENCE)

    def classify_with_confidence(self, content: str) -> Tuple[IntentType, float]:
        """
        Determines the intent type and confidence score of the provided content.

        Returns:
            Tuple of (IntentType, confidence) where confidence is a float between 0 and 1.
            Higher confidence indicates stronger keyword matches.
        """
        content_lower = content.lower()

        # Count matches for each intent type
        reasoning_matches = self._count_keyword_matches(content_lower, self.REASONING_KEYWORDS)
        factual_matches = self._count_keyword_matches(content_lower, self.FACTUAL_KEYWORDS)
        creative_matches = self._count_keyword_matches(content_lower, self.CREATIVE_KEYWORDS)

        # Determine intent based on highest match count, with priority order for ties
        match_counts = [
            (IntentType.REASONING, reasoning_matches),
            (IntentType.FACTUAL, factual_matches),
            (IntentType.CREATIVE, creative_matches),
        ]

        # Find the intent with the most matches
        best_intent = IntentType.GENERAL
        best_count = 0

        for intent_type, count in match_counts:
            if count > best_count:
                best_intent = intent_type
                best_count = count

        # Calculate confidence based on match strength
        if best_count > 0:
            confidence = self._calculate_confidence(best_count)
            return best_intent, confidence

        # Default to general with lower confidence
        return IntentType.GENERAL, self._calculate_confidence(0, is_default=True)

    async def classify_async(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> IntentType:
        """Asynchronous classification with optional context/LLM fallback."""
        # TODO: Implement LLM-based classification for high-ambiguity cases
        return self.classify(content)
