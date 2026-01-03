"""
Unit tests for SDPC IntentClassifier.
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from enhanced_agent_bus.config import BusConfiguration
from enhanced_agent_bus.deliberation_layer.intent_classifier import (
    ClassificationResult,
    IntentClassifier,
    IntentType,
    RoutingPath,
)


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
async def test_classify_async_heuristic():
    classifier = IntentClassifier()
    result = await classifier.classify_async("What happened in 1989?")
    assert result == IntentType.FACTUAL


@pytest.mark.asyncio
async def test_llm_classification_ambiguous():
    """Test LLM classification is invoked for ambiguous low-confidence inputs."""
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

    # Test Case 3: LLM returns malformed response
    with patch(
        "enhanced_agent_bus.deliberation_layer.intent_classifier.litellm.acompletion",
        new_callable=AsyncMock,
        return_value={
            "choices": [
                {
                    "message": {
                        "content": "invalid json"
                    }
                }
            ]
        },
    ):
        result = await classifier.classify_async_with_metadata("Another query")

        assert result.routing_path == RoutingPath.LLM_FALLBACK
        assert result.intent == IntentType.GENERAL
        assert result.llm_intent is None