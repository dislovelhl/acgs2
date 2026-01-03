"""
Unit tests for SDPC IntentClassifier.
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, patch
from enhanced_agent_bus.deliberation_layer.intent_classifier import IntentClassifier, IntentType
from enhanced_agent_bus.config import BusConfiguration


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
async def test_classify_async_heuristic():
    classifier = IntentClassifier()
    result = await classifier.classify_async("What happened in 1989?")
    assert result == IntentType.FACTUAL

@pytest.mark.asyncio
async def test_classify_async_llm_fallback():
    # Configure classifier with LLM enabled
    config = BusConfiguration(llm_model="test-model")
    classifier = IntentClassifier(config=config)

    # Ambiguous input that returns GENERAL in heuristic
    ambiguous_input = "Something very ambiguous that heuristic won't catch"

    # Mock litellm.acompletion
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="factual"))
    ]

    with patch("litellm.acompletion", return_value=mock_response) as mock_completion:
        result = await classifier.classify_async(ambiguous_input)

        # Verify LLM was called
        mock_completion.assert_called_once()
        assert result == IntentType.FACTUAL

@pytest.mark.asyncio
async def test_classify_async_llm_failure_fallback():
    # Configure classifier with LLM enabled
    config = BusConfiguration(llm_model="test-model")
    classifier = IntentClassifier(config=config)

    # Ambiguous input
    ambiguous_input = "Something very ambiguous"

    # Mock litellm.acompletion FAILURE
    with patch("litellm.acompletion", side_effect=Exception("LLM Down")):
        result = await classifier.classify_async(ambiguous_input)

        # Should fallback to GENERAL (the heuristic result)
        assert result == IntentType.GENERAL
