"""
ACGS-2 SDPC - Intent Classifier
Constitutional Hash: cdd01ef066bc6cf2

Categorizes user intent for dynamic routing and prompt compilation.
Implements hybrid classification with LLM fallback for ambiguous cases.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

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

    def to_dict(self) -> Dict[str, Any]:
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
    async def acompletion(*args: Any, **kwargs: Any) -> Dict[str, Any]:
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

    # Supported LLM providers
    SUPPORTED_PROVIDERS: List[str] = ["openai", "anthropic"]
    # Default max tokens for Anthropic (required parameter)
    DEFAULT_ANTHROPIC_MAX_TOKENS: int = 100

    # LLM prompt template for intent classification
    LLM_CLASSIFICATION_PROMPT: str = """You are an intent classification expert. Classify the following user input into one of these categories:
- factual: Question about facts, data, history, or specific entities.
- creative: Request for story, poem, song, or creative writing.
- reasoning: Complex logical problem, math, or step-by-step analysis.
- general: Simple greeting, conversational filler, or ambiguous request.

User input: {content}

Respond with ONLY the category name in lowercase."""

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        llm_enabled: bool = True,
        llm_model_version: str = "openai/gpt-4o-mini",
        llm_cache_ttl: int = 3600,
        llm_confidence_threshold: float = 0.7,
        llm_max_tokens: int = 100,
        redis_url: Optional[str] = None,
        config: Optional[BusConfiguration] = None,
    ):
        """Initialize the IntentClassifier with optional LLM support.

        Args:
            model_name: Name of the classification model (for logging/metadata).
            llm_enabled: Whether to enable LLM-based classification for ambiguous cases.
            llm_model_version: LLM model with provider prefix (e.g., "openai/gpt-4o-mini").
            llm_cache_ttl: Cache TTL in seconds for LLM responses.
            llm_confidence_threshold: Confidence threshold below which LLM is invoked.
            llm_max_tokens: Maximum tokens for LLM response (required for Anthropic).
            redis_url: Redis URL for caching (e.g., "redis://localhost:6379/0").
            config: Optional BusConfiguration for backward compatibility.
        """
        self.model_name = model_name
        self.config = config or BusConfiguration()
        
        # LLM configuration
        self.llm_enabled = llm_enabled
        self.llm_model_version = llm_model_version
        self.llm_cache_ttl = llm_cache_ttl
        self.llm_confidence_threshold = llm_confidence_threshold
        self.llm_max_tokens = llm_max_tokens
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        # LLM client state
        self._llm_client_initialized = False
        self._cache_initialized = False
        # Cache reference for verification (points to litellm.cache when initialized)
        self.cache: Optional[Any] = None

        # Initialize LLM client if enabled
        if self.llm_enabled:
            self._init_llm_client()

        logger.info(
            f"IntentClassifier initialized with model: {model_name}, "
            f"llm_enabled: {llm_enabled}, llm_model: {llm_model_version}"
        )

    def _parse_redis_url(self) -> Dict[str, Any]:
        """Parse Redis URL to extract connection parameters for LiteLLM Cache.

        Returns:
            Dict with host, port, and optionally password for Redis connection.
        """
        try:
            parsed = urlparse(self.redis_url)
            result: Dict[str, Any] = {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 6379,
            }
            if parsed.password:
                result["password"] = parsed.password
            return result
        except Exception as e:
            logger.warning(f"Failed to parse Redis URL '{self.redis_url}': {e}")
            return {"host": "localhost", "port": 6379}

    def _get_provider(self) -> str:
        """Extract provider from model version string.

        Returns:
            Provider name (e.g., "openai", "anthropic").
        """
        if "/" in self.llm_model_version:
            return self.llm_model_version.split("/")[0].lower()
        return "openai"  # Default provider

    def _validate_provider(self) -> bool:
        """Validate that the configured provider is supported.

        Returns:
            True if provider is supported, False otherwise.
        """
        provider = self._get_provider()
        if provider not in self.SUPPORTED_PROVIDERS:
            logger.warning(
                f"Unsupported LLM provider '{provider}'. "
                f"Supported providers: {self.SUPPORTED_PROVIDERS}"
            )
            return False
        return True

    def _init_llm_client(self) -> bool:
        """Initialize the LLM client with Redis caching support.

        Initializes LiteLLM cache globally and validates provider configuration.

        Returns:
            True if initialization was successful, False otherwise.
        """
        if not LITELLM_AVAILABLE:
            logger.warning(
                "LiteLLM not available. LLM classification will fall back to rule-based."
            )
            self._llm_client_initialized = False
            return False

        # Validate provider
        if not self._validate_provider():
            self._llm_client_initialized = False
            return False

        # Initialize Redis cache for LiteLLM
        try:
            redis_params = self._parse_redis_url()
            litellm.cache = Cache(
                type="redis",
                host=redis_params["host"],
                port=redis_params["port"],
                password=redis_params.get("password"),
                ttl=self.llm_cache_ttl,
            )
            # Expose cache as instance attribute for verification/testing
            self.cache = litellm.cache
            self._cache_initialized = True
            logger.info(
                f"LiteLLM cache initialized with Redis at "
                f"{redis_params['host']}:{redis_params['port']}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize LiteLLM Redis cache: {e}. Proceeding without caching."
            )
            self._cache_initialized = False

        # Validate API key availability
        provider = self._get_provider()
        api_key_var = f"{provider.upper()}_API_KEY"
        if not os.environ.get(api_key_var):
            logger.warning(
                f"API key not found for provider '{provider}'. "
                f"Set {api_key_var} environment variable. "
                "LLM classification will fall back to rule-based."
            )
            self._llm_client_initialized = False
            return False

        self._llm_client_initialized = True
        logger.info(f"LLM client initialized successfully with model: {self.llm_model_version}")
        return True

    def _get_llm_params(self) -> Dict[str, Any]:
        """Get LLM completion parameters based on provider.

        Returns:
            Dict of parameters for LiteLLM acompletion call.
        """
        params: Dict[str, Any] = {
            "model": self.llm_model_version,
            "temperature": 0.1,  # Low temperature for consistent classification
            "caching": self._cache_initialized,  # Enable caching if available
        }

        # Anthropic requires max_tokens parameter
        provider = self._get_provider()
        if provider == "anthropic":
            params["max_tokens"] = self.llm_max_tokens
        elif provider == "openai":
            # OpenAI uses max_tokens optionally but we set it for consistency
            params["max_tokens"] = self.llm_max_tokens

        return params

    def is_llm_available(self) -> bool:
        """Check if LLM classification is available.

        Returns:
            True if LLM client is initialized and ready, False otherwise.
        """
        return self.llm_enabled and self._llm_client_initialized

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
        # 1. Try heuristic classification first
        intent = self.classify(content)

        # 2. If intent is GENERAL (ambiguous) or confidence is low, fallback to LLM
        if self.is_llm_available() and intent == IntentType.GENERAL:
            try:
                # Prepare prompt for intent classification
                system_prompt = f"""Classify the following user input into one of these categories:
- factual: Question about facts, data, history, or specific entities.
- creative: Request for story, poem, song, or creative writing.
- reasoning: Complex logical problem, math, or step-by-step analysis.
- general: Simple greeting, conversational filler, or ambiguous request.

Respond with ONLY the category name in lowercase."""

                response = await litellm.acompletion(
                    model=self.llm_model_version,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    **self._get_llm_params(),
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

    async def classify_with_result(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Asynchronous classification returning detailed classification result.

        Returns:
            ClassificationResult with intent, confidence, routing path, and timing.
        """
        start_time = time.time()

        # Handle empty input
        if not content or not content.strip():
            latency_ms = (time.time() - start_time) * 1000
            return ClassificationResult(
                intent=IntentType.GENERAL,
                confidence=self.DEFAULT_CONFIDENCE,
                routing_path=RoutingPath.EMPTY_INPUT,
                latency_ms=latency_ms,
            )

        # Get rule-based classification with confidence
        rule_based_intent, rule_based_confidence = self.classify_with_confidence(content)

        # If confidence is high, return rule-based result
        if rule_based_confidence >= self.llm_confidence_threshold or not self.is_llm_available():
            latency_ms = (time.time() - start_time) * 1000
            return ClassificationResult(
                intent=rule_based_intent,
                confidence=rule_based_confidence,
                routing_path=RoutingPath.RULE_BASED,
                latency_ms=latency_ms,
                rule_based_intent=rule_based_intent,
                rule_based_confidence=rule_based_confidence,
            )

        # Try LLM classification for low-confidence cases
        try:
            response = await litellm.acompletion(
                model=self.llm_model_version,
                messages=[
                    {"role": "system", "content": self.LLM_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": content},
                ],
                **self._get_llm_params(),
            )

            llm_response = response.choices[0].message.content.strip().lower()
            llm_intent = IntentType.GENERAL
            llm_confidence = 0.5

            # Map LLM response to IntentType
            for it in IntentType:
                if it.value == llm_response:
                    llm_intent = it
                    llm_confidence = 0.9
                    break

            latency_ms = (time.time() - start_time) * 1000
            return ClassificationResult(
                intent=llm_intent,
                confidence=llm_confidence,
                routing_path=RoutingPath.LLM,
                latency_ms=latency_ms,
                rule_based_intent=rule_based_intent,
                rule_based_confidence=rule_based_confidence,
                llm_intent=llm_intent,
                llm_confidence=llm_confidence,
                cached=getattr(response, "cached", False),
            )

        except Exception as e:
            logger.error(f"LLM classification failed: {str(e)}, falling back to rule-based")
            latency_ms = (time.time() - start_time) * 1000
            return ClassificationResult(
                intent=rule_based_intent,
                confidence=rule_based_confidence,
                routing_path=RoutingPath.LLM_FALLBACK,
                latency_ms=latency_ms,
                rule_based_intent=rule_based_intent,
                rule_based_confidence=rule_based_confidence,
            )