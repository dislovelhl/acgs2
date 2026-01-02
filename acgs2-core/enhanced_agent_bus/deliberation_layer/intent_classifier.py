"""
ACGS-2 SDPC - Intent Classifier
Constitutional Hash: cdd01ef066bc6cf2

Categorizes user intent for dynamic routing and prompt compilation.
Implements hybrid classification with LLM fallback for ambiguous cases.
"""

import json
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class IntentType(Enum):
    FACTUAL = "factual"  # High precision, requires GraphCheck & ASC
    CREATIVE = "creative"  # High fluency, relaxed factual constraints
    REASONING = "reasoning"  # Complex logic, triggers AMPO branching
    GENERAL = "general"  # Default/conversational intent


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

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        llm_enabled: bool = True,
        llm_model_version: str = "openai/gpt-4o-mini",
        llm_cache_ttl: int = 3600,
        llm_confidence_threshold: float = 0.7,
        llm_max_tokens: int = 100,
        redis_url: Optional[str] = None,
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
        """
        self.model_name = model_name
        self.llm_enabled = llm_enabled
        self.llm_model_version = llm_model_version
        self.llm_cache_ttl = llm_cache_ttl
        self.llm_confidence_threshold = llm_confidence_threshold
        self.llm_max_tokens = llm_max_tokens
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        # LLM client state
        self._llm_client_initialized = False
        self._cache_initialized = False

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
            self._cache_initialized = True
            logger.info(
                f"LiteLLM cache initialized with Redis at "
                f"{redis_params['host']}:{redis_params['port']}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize LiteLLM Redis cache: {e}. " "Proceeding without caching."
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

    async def _invoke_llm_classification(self, content: str) -> Optional[Dict[str, Any]]:
        """Invoke LLM for intent classification.

        Args:
            content: The user input to classify.

        Returns:
            Dict with intent, confidence, and reasoning, or None on failure.
        """
        if not self.is_llm_available():
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

    def _parse_llm_intent(self, llm_result: Dict[str, Any]) -> Optional[IntentType]:
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

    async def classify_async(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> IntentType:
        """Asynchronous classification with optional context/LLM fallback.

        Uses hybrid classification strategy:
        1. First attempts rule-based classification with confidence scoring
        2. If confidence is below threshold and LLM is available, invokes LLM
        3. Falls back to rule-based result on LLM failure

        Args:
            content: The user input to classify.
            context: Optional context dict (reserved for future use).

        Returns:
            IntentType classification result.
        """
        # Handle empty/whitespace input - return GENERAL without invoking LLM
        if not content or not content.strip():
            logger.debug("Empty input received, returning GENERAL intent")
            return IntentType.GENERAL

        # Step 1: Get rule-based classification with confidence
        rule_based_intent, confidence = self.classify_with_confidence(content)

        # Step 2: Check if LLM should be invoked (low confidence + LLM available)
        if confidence >= self.llm_confidence_threshold:
            # High confidence - use rule-based result (fast path)
            logger.debug(
                f"High confidence ({confidence:.2f}) rule-based classification: {rule_based_intent.value}"
            )
            return rule_based_intent

        # Step 3: Low confidence - try LLM classification if available
        if not self.is_llm_available():
            logger.debug(
                f"LLM not available, using rule-based result with low confidence ({confidence:.2f})"
            )
            return rule_based_intent

        logger.debug(f"Low confidence ({confidence:.2f}), invoking LLM classification")

        # Step 4: Invoke LLM
        llm_result = await self._invoke_llm_classification(content)

        if llm_result:
            # Parse LLM result
            llm_intent = self._parse_llm_intent(llm_result)
            if llm_intent:
                llm_confidence = llm_result.get("confidence", 0.8)
                logger.info(
                    f"LLM classification: {llm_intent.value} "
                    f"(confidence: {llm_confidence:.2f}, reasoning: {llm_result.get('reasoning', 'N/A')})"
                )
                return llm_intent

        # Step 5: Fallback to rule-based on LLM failure
        logger.warning(
            f"LLM classification failed, falling back to rule-based: {rule_based_intent.value}"
        )
        return rule_based_intent
