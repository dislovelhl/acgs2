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
