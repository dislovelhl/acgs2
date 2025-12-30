"""
Tests for SDPC Phase 2 Verifiers
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from enhanced_agent_bus.deliberation_layer.intent_classifier import IntentType
from enhanced_agent_bus.sdpc.asc_verifier import ASCVerifier
from enhanced_agent_bus.sdpc.graph_check import GraphCheckVerifier
from enhanced_agent_bus.sdpc.pacar_verifier import PACARVerifier


@pytest.mark.asyncio
async def test_asc_verifier_skipped():
    verifier = ASCVerifier()
    result = await verifier.verify("Some content", IntentType.GENERAL)
    assert result["is_valid"] is True
    assert "skipped" in result["reason"]


@pytest.mark.asyncio
async def test_asc_verifier_factual():
    verifier = ASCVerifier()
    # Mock LLM Assistant
    mock_assistant = MagicMock()
    mock_assistant.analyze_message_impact = AsyncMock(
        return_value={"risk_level": "low", "confidence": 0.9, "reasoning": ["Verified consistent"]}
    )
    verifier.assistant = mock_assistant

    result = await verifier.verify("Factual content", IntentType.FACTUAL)
    assert result["is_valid"] is True
    assert result["confidence"] == 0.9


@pytest.mark.asyncio
async def test_graph_check_verifier():
    verifier = GraphCheckVerifier(db_type="mock")
    # Content with known mock keywords
    content = "The supply chain in Asia is at risk."
    result = await verifier.verify_entities(content)
    assert result["is_valid"] is True
    assert len(result["results"]) > 0
    assert any(r["status"] == "grounded" for r in result["results"])


@pytest.mark.asyncio
async def test_pacar_verifier():
    verifier = PACARVerifier()
    # Mock LLM Assistant
    mock_assistant = MagicMock()
    mock_assistant.analyze_message_impact = AsyncMock(
        return_value={
            "risk_level": "low",
            "confidence": 0.85,
            "reasoning": ["Red team found no issues", "Validator approved"],
            "mitigations": ["None"],
        }
    )
    verifier.assistant = mock_assistant

    result = await verifier.verify("Deliberative content", "Investigate risk")
    assert result["is_valid"] is True
    assert result["consensus_reached"] is True
