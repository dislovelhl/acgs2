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
