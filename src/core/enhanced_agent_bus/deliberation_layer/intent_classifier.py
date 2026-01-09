"""
ACGS-2 SDPC - Intent Classifier
Constitutional Hash: cdd01ef066bc6cf2

Categorizes user intent for dynamic routing and prompt compilation.
Implements hybrid classification with LLM fallback for ambiguous cases.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any


from ..config import BusConfiguration


class IntentType(Enum):
    FACTUAL = "factual"  # High precision, requires GraphCheck & ASC
    CREATIVE = "creative"  # High fluency, relaxed factual constraints
    REASONING = "reasoning"  # Complex logic, triggers AMPO branching
    GENERAL = "general"  # Default/conversational intent


class RoutingPath(Enum):
    """Enumeration of classification routing paths for hybrid classification."""

    RULE_BASED = "rule_based"  # Fast path using keyword heuristics
    LLM = "llm"  # Slow path using LLM for ambiguous cases
    LLM_FALLBACK = "llm_fallback"  # LLM failed, fell back to rule-based
    EMPTY_INPUT = "empty_input"  # Empty/whitespace input, returned GENERAL


@dataclass
class ClassificationResult:
    """Result of intent classification with routing metadata.

    Provides detailed information about the classification decision,
    including which routing path was used and timing information.
    """

    intent: IntentType
    confidence: float
    routing_path: RoutingPath
    latency_ms: float
    rule_based_intent: Optional[IntentType] = None
    rule_based_confidence: Optional[float] = None
    llm_intent: Optional[IntentType] = None
    llm_confidence: Optional[float] = None
    llm_reasoning: Optional[str] = None
    cached: bool = False

    def to_dict(self) -> JSONDict:
        """Convert to dictionary for logging/serialization."""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "routing_path": self.routing_path.value,
            "latency_ms": round(self.latency_ms, 3),
            "rule_based_intent": self.rule_based_intent.value if self.rule_based_intent else None,
            "rule_based_confidence": self.rule_based_confidence,
            "llm_intent": self.llm_intent.value if self.llm_intent else None,
            "llm_confidence": self.llm_confidence,
            "llm_reasoning": self.llm_reasoning,
            "cached": self.cached,
        }


logger = logging.getLogger(__name__)

# LiteLLM availability flag
LITELLM_AVAILABLE = False


# Mock classes for test friendliness when LiteLLM is missing
class MockLiteLLMCache:
    """Mock cache class for when LiteLLM is not available."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockLiteLLM:
    """Mock LiteLLM module for when it's not available."""

    cache: Optional[Any] = None

    @staticmethod
    async def acompletion(*args: Any, **kwargs: Any) -> JSONDict:
        """Mock async completion that returns empty response."""
        return {"choices": [{"message": {"content": "{}"}}]}


# Attempt to import LiteLLM
try:
    import litellm
    from litellm import Cache

    LITELLM_AVAILABLE = True
except ImportError:
    litellm = MockLiteLLM()  # type: ignore[assignment]
    Cache = MockLiteLLMCache  # type: ignore[assignment, misc]


class IntentClassifier:
    """Classifies user intent to determine optimal processing strategies."""

    def __init__(
        self, model_name: str = "distilbert-base-uncased", config: Optional[BusConfiguration] = None
    ):
        self.model_name = model_name
        self.config = config or BusConfiguration()
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

    # LLM prompt template for intent classification
    LLM_CLASSIFICATION_PROMPT: str = """You are an intent classifier for a governance system. Classify the user's input into exactly one of these categories:

- FACTUAL: Questions seeking specific facts, data, historical information, or verifiable answers.
  Examples: "What is the capital of France?", "When did World War 2 end?", "How many users are in the system?"

- CREATIVE: Requests for creative content, storytelling, imagination, or artistic output.
  Examples: "Write a poem about spring", "Tell me a joke", "Create a story about a robot"

- REASONING: Complex analytical tasks requiring step-by-step logic, calculations, or problem-solving.
  Examples: "Calculate the derivative of x^2", "Explain why the sky is blue step by step", "Analyze this data"

- GENERAL: Conversational inputs, greetings, or anything that doesn't fit the above categories.
  Examples: "Hello", "How are you?", "Thanks for your help"

User input: {content}

Respond with ONLY a JSON object in this exact format:
{{"intent": "FACTUAL|CREATIVE|REASONING|GENERAL", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

    # Maximum content length to send to LLM (to control costs)
    MAX_CONTENT_LENGTH: int = 2000

    async def _invoke_llm_classification(self, content: str) -> Optional[JSONDict]:
        """Invoke LLM for intent classification.

        Args:
            content: The user input to classify.

        Returns:
            Dict with intent, confidence, and reasoning, or None on failure.
        """
        # Fallback to simple keyword matching if litellm fails
        if not LITELLM_AVAILABLE:
            return None

        # Truncate content if too long
        truncated_content = (
            content[: self.MAX_CONTENT_LENGTH]
            if len(content) > self.MAX_CONTENT_LENGTH
            else content
        )

        try:
            # Prepare the prompt
            prompt = self.LLM_CLASSIFICATION_PROMPT.format(content=truncated_content)

            # Get LLM parameters
            params = self._get_llm_params()

            # Call LiteLLM acompletion
            response = await litellm.acompletion(
                messages=[{"role": "user", "content": prompt}],
                **params,
            )

            # Extract response content
            if not response or not response.get("choices"):
                logger.warning("Empty LLM response received")
                return None

            response_content = response["choices"][0]["message"]["content"]

            # Parse JSON response
            try:
                result = json.loads(response_content.strip())
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Try to extract intent from plain text response
                response_upper = response_content.upper()
                for intent_type in IntentType:
                    if intent_type.name in response_upper:
                        return {
                            "intent": intent_type.name,
                            "confidence": 0.7,
                            "reasoning": "Extracted from text",
                        }
                return None

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return None

    def _parse_llm_intent(self, llm_result: JSONDict) -> Optional[IntentType]:
        """Parse LLM result to extract IntentType.

        Args:
            llm_result: Dict containing intent classification from LLM.

        Returns:
            IntentType if valid intent found, None otherwise.
        """
        intent_str = llm_result.get("intent", "").upper()

        # Map string to IntentType enum
        intent_map = {
            "FACTUAL": IntentType.FACTUAL,
            "CREATIVE": IntentType.CREATIVE,
            "REASONING": IntentType.REASONING,
            "GENERAL": IntentType.GENERAL,
        }

        return intent_map.get(intent_str)

    async def classify_async(self, content: str, context: Optional[JSONDict] = None) -> IntentType:
        """Asynchronous classification with optional context/LLM fallback."""
        # 1. Try heuristic classification first
        intent = self.classify(content)

        # 2. If intent is GENERAL (ambiguous), fallback to LLM
        if intent == IntentType.GENERAL and self.config.llm_model:
            try:
                # Prepare prompt for intent classification
                system_prompt = """
                Classify the following user input into one of these categories:
                - factual: Question about facts, data, history, or specific entities.
                - creative: Request for story, poem, song, or creative writing.
                - reasoning: Complex logical problem, math, or step-by-step analysis.
                - general: Simple greeting, conversational filler, or ambiguous request.

                Respond with ONLY the category name in lowercase.
                """

                response = await litellm.acompletion(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    max_tokens=self.config.llm_max_tokens,
                    temperature=0,
                    caching=self.config.llm_use_cache,
                )

                llm_intent = response.choices[0].message.content.strip().lower()

                # Map LLM response to IntentType
                for it in IntentType:
                    if it.value == llm_intent:
                        logger.info(
                            f"LLM classified intent as: {llm_intent} (heuristic was GENERAL)"
                        )
                        return it

                logger.warning(
                    f"LLM returned unknown intent: {llm_intent}, falling back to GENERAL"
                )

            except Exception as e:
                logger.error(f"LLM intent classification failed: {str(e)}")

        return intent
