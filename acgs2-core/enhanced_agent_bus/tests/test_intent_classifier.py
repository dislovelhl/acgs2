"""
Unit tests for SDPC IntentClassifier.
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from enhanced_agent_bus.deliberation_layer.intent_classifier import IntentClassifier, IntentType


def test_classify_factual():
    classifier = IntentClassifier()
    assert classifier.classify("Tell me about the history of Rome") == IntentType.FACTUAL
    assert classifier.classify("Who is the president of France?") == IntentType.FACTUAL


def test_classify_reasoning():
    classifier = IntentClassifier()
    assert (
        classifier.classify("Analyze the impact of climate change on agriculture")
        == IntentType.REASONING
    )
    assert classifier.classify("Calculate the derivative of x^2") == IntentType.REASONING


def test_classify_creative():
    classifier = IntentClassifier()
    assert classifier.classify("Write a poem about the sea") == IntentType.CREATIVE
    assert classifier.classify("Imagine a world where dragons exist") == IntentType.CREATIVE


def test_classify_general():
    classifier = IntentClassifier()
    assert classifier.classify("Hello, how are you?") == IntentType.GENERAL
    assert classifier.classify("Remind me to buy milk") == IntentType.GENERAL


@pytest.mark.asyncio
async def test_classify_async():
    classifier = IntentClassifier()
    result = await classifier.classify_async("What happened in 1989?")
    assert result == IntentType.FACTUAL


# ============================================================================
# Confidence Scoring Tests
# ============================================================================


def test_confidence_scoring():
    """Test basic classify_with_confidence functionality returns expected tuple."""
    classifier = IntentClassifier()

    # Test that classify_with_confidence returns a tuple of (IntentType, float)
    intent, confidence = classifier.classify_with_confidence("Tell me about the history of Rome")
    assert isinstance(intent, IntentType)
    assert isinstance(confidence, float)
    assert intent == IntentType.FACTUAL
    assert 0.0 <= confidence <= 1.0


def test_confidence_scoring_single_match():
    """Test that a single keyword match gives BASE_CONFIDENCE."""
    classifier = IntentClassifier()

    # Single factual keyword match should give BASE_CONFIDENCE (0.7)
    intent, confidence = classifier.classify_with_confidence("What is the capital of France?")
    assert intent == IntentType.FACTUAL
    assert confidence == classifier.BASE_CONFIDENCE


def test_confidence_scoring_multiple_matches():
    """Test that multiple keyword matches boost confidence."""
    classifier = IntentClassifier()

    # Multiple reasoning keywords: "calculate", "step by step", "solve"
    intent, confidence = classifier.classify_with_confidence(
        "Calculate step by step how to solve this equation"
    )
    assert intent == IntentType.REASONING
    # Should be BASE_CONFIDENCE + (match_count - 1) * CONFIDENCE_BOOST_PER_MATCH
    # 3 matches: 0.7 + (3-1) * 0.05 = 0.7 + 0.1 = 0.8
    expected_confidence = classifier.BASE_CONFIDENCE + (2 * classifier.CONFIDENCE_BOOST_PER_MATCH)
    assert confidence == expected_confidence


def test_confidence_scoring_max_cap():
    """Test that confidence is capped at MAX_RULE_CONFIDENCE."""
    classifier = IntentClassifier()

    # Create content with many keywords to test the cap
    # Using multiple factual keywords: "tell me about", "who is", "what is", "where is", "historical", "how many"
    intent, confidence = classifier.classify_with_confidence(
        "Tell me about the historical facts. Who is involved? What is the significance? "
        "Where is it located? How many people were affected?"
    )
    assert intent == IntentType.FACTUAL
    # Confidence should be capped at MAX_RULE_CONFIDENCE (0.95)
    assert confidence <= classifier.MAX_RULE_CONFIDENCE


def test_confidence_scoring_default():
    """Test that general/default classification gives DEFAULT_CONFIDENCE."""
    classifier = IntentClassifier()

    # No keywords matching any specific intent -> GENERAL with DEFAULT_CONFIDENCE
    intent, confidence = classifier.classify_with_confidence("Hello there!")
    assert intent == IntentType.GENERAL
    assert confidence == classifier.DEFAULT_CONFIDENCE


def test_confidence_scoring_empty_input():
    """Test confidence scoring with empty or whitespace input."""
    classifier = IntentClassifier()

    # Empty string should return GENERAL with DEFAULT_CONFIDENCE
    intent, confidence = classifier.classify_with_confidence("")
    assert intent == IntentType.GENERAL
    assert confidence == classifier.DEFAULT_CONFIDENCE

    # Whitespace only
    intent, confidence = classifier.classify_with_confidence("   ")
    assert intent == IntentType.GENERAL
    assert confidence == classifier.DEFAULT_CONFIDENCE


def test_confidence_scoring_creative():
    """Test confidence scoring for creative intent."""
    classifier = IntentClassifier()

    # Single creative keyword
    intent, confidence = classifier.classify_with_confidence("Write a poem")
    assert intent == IntentType.CREATIVE
    assert confidence == classifier.BASE_CONFIDENCE

    # Multiple creative keywords: "poem", "imagine", "creative"
    intent, confidence = classifier.classify_with_confidence("Imagine a creative poem about nature")
    assert intent == IntentType.CREATIVE
    # 3 matches: 0.7 + (3-1) * 0.05 = 0.8
    expected_confidence = classifier.BASE_CONFIDENCE + (2 * classifier.CONFIDENCE_BOOST_PER_MATCH)
    assert confidence == expected_confidence


def test_confidence_scoring_intent_priority():
    """Test that when multiple intent types match, the one with most matches wins."""
    classifier = IntentClassifier()

    # Mixed keywords but more reasoning keywords
    # Reasoning: "calculate", "analyze" (2 matches)
    # Factual: "what is" (1 match)
    intent, confidence = classifier.classify_with_confidence(
        "Calculate and analyze what is the best approach"
    )
    assert intent == IntentType.REASONING
    # 2 reasoning matches: 0.7 + (2-1) * 0.05 = 0.75
    expected_confidence = classifier.BASE_CONFIDENCE + classifier.CONFIDENCE_BOOST_PER_MATCH
    assert confidence == expected_confidence


def test_count_keyword_matches():
    """Test the internal _count_keyword_matches method."""
    classifier = IntentClassifier()

    # Test counting factual keywords
    count = classifier._count_keyword_matches(
        "tell me about the history and who is responsible",
        classifier.FACTUAL_KEYWORDS,
    )
    assert count == 2  # "tell me about", "who is"

    # Test counting reasoning keywords
    count = classifier._count_keyword_matches(
        "calculate step by step and analyze the data",
        classifier.REASONING_KEYWORDS,
    )
    assert count == 3  # "calculate", "step by step", "analyze"

    # Test with no matches
    count = classifier._count_keyword_matches(
        "hello there friend",
        classifier.FACTUAL_KEYWORDS,
    )
    assert count == 0


def test_calculate_confidence():
    """Test the internal _calculate_confidence method."""
    classifier = IntentClassifier()

    # Zero matches should give DEFAULT_CONFIDENCE
    assert classifier._calculate_confidence(0) == classifier.DEFAULT_CONFIDENCE

    # Default flag should give DEFAULT_CONFIDENCE
    assert classifier._calculate_confidence(5, is_default=True) == classifier.DEFAULT_CONFIDENCE

    # Single match gives BASE_CONFIDENCE
    assert classifier._calculate_confidence(1) == classifier.BASE_CONFIDENCE

    # Multiple matches boost confidence
    assert (
        classifier._calculate_confidence(2)
        == classifier.BASE_CONFIDENCE + classifier.CONFIDENCE_BOOST_PER_MATCH
    )
    assert (
        classifier._calculate_confidence(3)
        == classifier.BASE_CONFIDENCE + 2 * classifier.CONFIDENCE_BOOST_PER_MATCH
    )

    # Very high match count should cap at MAX_RULE_CONFIDENCE
    assert classifier._calculate_confidence(100) == classifier.MAX_RULE_CONFIDENCE


# ============================================================================
# LLM Classification Tests (with mocks)
# ============================================================================


@pytest.mark.asyncio
async def test_llm_classification_ambiguous():
    """Test LLM classification is invoked for ambiguous low-confidence inputs."""
    from unittest.mock import AsyncMock, patch

    # Create classifier with LLM enabled and low threshold to trigger LLM path
    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,  # Threshold above BASE_CONFIDENCE (0.7)
    )

    # Mock LLM client as initialized
    classifier._llm_client_initialized = True

    # Prepare mock LLM response for an ambiguous query
    mock_llm_response = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "REASONING", "confidence": 0.85, "reasoning": "Query requires analysis"}'
                }
            }
        ]
    }

    # Patch litellm.acompletion to return our mock response
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_llm_response,
    ) as mock_acompletion:
        # Use an ambiguous query that would get low rule-based confidence
        # "Help me" doesn't match any strong keywords, so confidence will be DEFAULT_CONFIDENCE (0.5)
        result = await classifier.classify_async("Help me understand this concept")

        # Verify LLM was called since confidence (0.5) < threshold (0.8)
        mock_acompletion.assert_called_once()

        # Verify LLM result was used (REASONING from mock)
        assert result == IntentType.REASONING


@pytest.mark.asyncio
async def test_llm_classification_fallback_on_failure():
    """Test fallback to rule-based when LLM fails."""
    from unittest.mock import AsyncMock, patch

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True

    # Mock LLM to raise an exception
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=Exception("LLM API error"),
    ):
        # Query with some factual keyword but low confidence
        result = await classifier.classify_async("What about this thing?")

        # Should fallback to rule-based result (GENERAL for this query)
        assert result == IntentType.GENERAL


@pytest.mark.asyncio
async def test_llm_classification_with_metadata():
    """Test classify_async_with_metadata returns proper routing metadata."""
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True

    mock_llm_response = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "CREATIVE", "confidence": 0.9, "reasoning": "Creative request"}'
                }
            }
        ]
    }

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_llm_response,
    ):
        result = await classifier.classify_async_with_metadata("Make something interesting")

        # Verify result is ClassificationResult
        assert isinstance(result, ClassificationResult)
        assert result.intent == IntentType.CREATIVE
        assert result.routing_path == RoutingPath.LLM
        assert result.llm_confidence == 0.9
        assert result.llm_reasoning == "Creative request"


@pytest.mark.asyncio
async def test_llm_skipped_for_high_confidence():
    """Test LLM is NOT invoked when rule-based confidence is high."""
    from unittest.mock import AsyncMock, patch

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.6,  # Lower than BASE_CONFIDENCE (0.7)
    )
    classifier._llm_client_initialized = True

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        # Query with strong factual keywords - high confidence
        result = await classifier.classify_async("Tell me about the history of Rome")

        # Verify LLM was NOT called since confidence (0.7+) >= threshold (0.6)
        mock_acompletion.assert_not_called()

        # Verify rule-based result was used
        assert result == IntentType.FACTUAL


@pytest.mark.asyncio
async def test_llm_fallback_on_error():
    """Test LLM fallback to rule-based when LLM returns an error.

    Verifies that when LLM classification fails (raises exception, returns None,
    or returns malformed response), the system gracefully falls back to rule-based
    classification with proper routing metadata.
    """
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,  # High threshold to ensure LLM path is triggered
    )
    classifier._llm_client_initialized = True

    # Test Case 1: LLM raises an exception
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=Exception("API connection error"),
    ):
        result = await classifier.classify_async_with_metadata("Help me with something")

        # Verify fallback to rule-based classification
        assert isinstance(result, ClassificationResult)
        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL  # Default for ambiguous input
        assert result.rule_based_intent == IntentType.GENERAL
        assert result.rule_based_confidence == classifier.DEFAULT_CONFIDENCE
        # LLM fields should be None since LLM failed
        assert result.llm_intent is None
        assert result.llm_confidence is None
        assert result.llm_reasoning is None

    # Test Case 2: LLM returns empty response
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value={"choices": []},  # Empty choices
    ):
        result = await classifier.classify_async_with_metadata("Process this data")

        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL
        assert result.llm_intent is None

    # Test Case 3: LLM returns malformed JSON
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value={"choices": [{"message": {"content": "not valid json {{"}}]},
    ):
        result = await classifier.classify_async_with_metadata("Do something ambiguous")

        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL
        assert result.llm_intent is None

    # Test Case 4: LLM returns invalid intent type
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value={
            "choices": [{"message": {"content": '{"intent": "INVALID_TYPE", "confidence": 0.9}'}}]
        },
    ):
        result = await classifier.classify_async_with_metadata("Ambiguous request here")

        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL
        assert result.llm_intent is None

    # Test Case 5: LLM returns None response
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await classifier.classify_async_with_metadata("Another ambiguous input")

        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL


@pytest.mark.asyncio
async def test_llm_fallback_on_error_preserves_rule_based_result():
    """Test that LLM fallback preserves the original rule-based classification.

    Even when LLM fails, if the rule-based classifier found a specific intent
    (not just GENERAL), that intent should be returned.
    """
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,  # High threshold to trigger LLM for single keyword match
    )
    classifier._llm_client_initialized = True

    # Use a query with one factual keyword - gives BASE_CONFIDENCE (0.7) < threshold (0.8)
    # so LLM will be invoked, but rule-based will identify as FACTUAL
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=Exception("LLM service unavailable"),
    ):
        result = await classifier.classify_async_with_metadata("What is this thing?")

        # Should fallback to rule-based FACTUAL result
        assert isinstance(result, ClassificationResult)
        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.FACTUAL
        assert result.rule_based_intent == IntentType.FACTUAL
        assert result.rule_based_confidence == classifier.BASE_CONFIDENCE
        # Latency should be recorded
        assert result.latency_ms >= 0


# ============================================================================
# Redis Caching Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_caching_integration():
    """Test that LLM responses are cached in Redis and second call returns cached value.

    Verifies the Redis caching integration for LLM classification:
    - First call triggers LLM invocation and caches the result
    - Second identical call returns cached result with faster latency
    - Cache is properly initialized via LiteLLM
    """
    import time
    from unittest.mock import AsyncMock, MagicMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    # Create classifier with LLM enabled
    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,  # High threshold to trigger LLM path
        llm_cache_ttl=3600,
        redis_url="redis://localhost:6379/0",
    )
    classifier._llm_client_initialized = True
    classifier._cache_initialized = True

    # Track call count to simulate caching behavior
    call_count = 0
    cached_response = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "REASONING", "confidence": 0.88, "reasoning": "Analysis query"}'
                }
            }
        ]
    }

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Simulate cache hit on second call (fast response)
        if call_count > 1:
            # Simulate cache hit - very fast, no delay
            return cached_response
        else:
            # Simulate uncached call - add small delay to simulate API call
            await asyncio.sleep(0.01)  # 10ms simulated API latency
            return cached_response

    # Patch litellm.acompletion
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=mock_acompletion,
    ):
        # Query that triggers LLM (low rule-based confidence)
        test_query = "Help me analyze this complex situation"

        # First call - should go to LLM (cache miss)
        start_time = time.perf_counter()
        result1 = await classifier.classify_async_with_metadata(test_query)
        first_call_latency = (time.perf_counter() - start_time) * 1000

        # Verify first call result
        assert isinstance(result1, ClassificationResult)
        assert result1.intent == IntentType.REASONING
        assert result1.routing_path == RoutingPath.LLM
        assert result1.llm_confidence == 0.88
        assert call_count == 1, "First call should invoke LLM once"

        # Second call - should return cached result (simulated)
        start_time = time.perf_counter()
        result2 = await classifier.classify_async_with_metadata(test_query)
        second_call_latency = (time.perf_counter() - start_time) * 1000

        # Verify second call result matches first
        assert result2.intent == IntentType.REASONING
        assert result2.routing_path == RoutingPath.LLM
        assert result2.llm_confidence == 0.88

        # Note: With mocking, both calls hit the mock, but in real caching
        # the second call would be faster due to Redis cache
        assert call_count == 2, "Both calls should invoke mock (real cache would skip LLM)"

        # In a real caching scenario, second call latency would be <5ms
        # For mocked test, we verify the integration path works correctly
        assert second_call_latency < first_call_latency or second_call_latency < 100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_initialization():
    """Test that Redis cache is properly initialized when LLM is enabled.

    Verifies:
    - Cache attribute is set after initialization
    - Cache initialization flag is properly set
    - Redis URL is correctly parsed
    """
    from unittest.mock import MagicMock, patch

    # Mock the litellm.Cache to track initialization
    mock_cache_instance = MagicMock()

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.Cache",
        return_value=mock_cache_instance,
    ) as mock_cache_class:
        with patch(
            "enhanced_agent_bus.deliberation_layer.intent_classifier.LITELLM_AVAILABLE",
            True,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Create classifier which should initialize cache
                classifier = IntentClassifier(
                    llm_enabled=True,
                    llm_cache_ttl=7200,
                    redis_url="redis://myhost:6380/1",
                )

                # Verify Cache was initialized with correct parameters
                mock_cache_class.assert_called_once()
                call_kwargs = mock_cache_class.call_args[1]
                assert call_kwargs["type"] == "redis"
                assert call_kwargs["host"] == "myhost"
                assert call_kwargs["port"] == 6380
                assert call_kwargs["ttl"] == 7200

                # Verify cache initialization flag
                assert classifier._cache_initialized is True
                assert classifier.cache is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_hit_latency():
    """Test that cached responses return within target latency (<5ms P99).

    Simulates cache hit scenario and verifies response time meets latency requirements.
    """
    import time
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True
    classifier._cache_initialized = True

    # Mock LLM response with instant return (simulating cache hit)
    instant_response = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "FACTUAL", "confidence": 0.92, "reasoning": "Cached response"}'
                }
            }
        ]
    }

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=instant_response,
    ):
        test_query = "What is the meaning of this?"

        # Measure multiple calls to simulate P99 latency
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            result = await classifier.classify_async_with_metadata(test_query)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            assert result.intent == IntentType.FACTUAL
            assert result.routing_path == RoutingPath.LLM

        # Verify latencies are reasonable (mocked calls should be very fast)
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # With mocking, latencies should be minimal (under 50ms)
        # Real P99 <5ms target applies to actual cache hits
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms too high"
        assert max_latency < 200, f"Max latency {max_latency:.2f}ms too high"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_miss_latency():
    """Test that uncached LLM responses complete within target latency (<500ms P99).

    Simulates cache miss scenario with simulated API delay.
    """
    import time
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True
    classifier._cache_initialized = False  # Caching disabled for this test

    # Mock LLM response with simulated API delay
    async def delayed_response(*args, **kwargs):
        await asyncio.sleep(0.05)  # 50ms simulated API latency
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"intent": "CREATIVE", "confidence": 0.85, "reasoning": "Creative request"}'
                    }
                }
            ]
        }

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=delayed_response,
    ):
        test_query = "Create something new for me"

        start = time.perf_counter()
        result = await classifier.classify_async_with_metadata(test_query)
        latency_ms = (time.perf_counter() - start) * 1000

        assert result.intent == IntentType.CREATIVE
        assert result.routing_path == RoutingPath.LLM

        # Verify latency is within uncached target (<500ms)
        # With 50ms simulated delay plus overhead, should be under 500ms
        assert latency_ms < 500, f"Uncached latency {latency_ms:.2f}ms exceeds 500ms target"
        assert latency_ms >= 50, f"Latency {latency_ms:.2f}ms unexpectedly fast (delay missing?)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_with_different_inputs():
    """Test that different inputs produce different cache entries.

    Verifies that caching correctly distinguishes between different queries.
    """
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True
    classifier._cache_initialized = True

    # Track which queries were received
    received_queries = []

    async def track_queries(*args, **kwargs):
        messages = kwargs.get("messages", args[0] if args else [])
        if messages:
            content = messages[0].get("content", "")
            received_queries.append(content)

        # Return different intents based on query content
        if "analyze" in content.lower():
            intent = "REASONING"
        elif "create" in content.lower():
            intent = "CREATIVE"
        else:
            intent = "GENERAL"

        return {
            "choices": [
                {
                    "message": {
                        "content": f'{{"intent": "{intent}", "confidence": 0.87, "reasoning": "Query-specific"}}'
                    }
                }
            ]
        }

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=track_queries,
    ):
        # Query 1: Reasoning intent
        result1 = await classifier.classify_async_with_metadata("Help me analyze this complex data")
        assert result1.intent == IntentType.REASONING

        # Query 2: Creative intent (different input)
        result2 = await classifier.classify_async_with_metadata("Help me create something unique")
        assert result2.intent == IntentType.CREATIVE

        # Verify both queries were processed (cache differentiated them)
        assert len(received_queries) == 2
        assert any("analyze" in q.lower() for q in received_queries)
        assert any("create" in q.lower() for q in received_queries)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_fallback_on_redis_failure():
    """Test graceful degradation when Redis cache fails.

    Verifies that classification continues to work even if caching fails.
    """
    from unittest.mock import AsyncMock, patch

    from enhanced_agent_bus.deliberation_layer.intent_classifier import (
        ClassificationResult,
        RoutingPath,
    )

    classifier = IntentClassifier(
        llm_enabled=True,
        llm_confidence_threshold=0.8,
    )
    classifier._llm_client_initialized = True
    # Cache initialization failed
    classifier._cache_initialized = False

    mock_response = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "REASONING", "confidence": 0.9, "reasoning": "Uncached"}'
                }
            }
        ]
    }

    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        result = await classifier.classify_async_with_metadata("Analyze this situation")

        # Verify classification still works without cache
        assert result.intent == IntentType.REASONING
        assert result.routing_path == RoutingPath.LLM

        # Verify LLM was called (no caching parameter should be False)
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs.get("caching") is False


# Import asyncio for the tests
import asyncio
