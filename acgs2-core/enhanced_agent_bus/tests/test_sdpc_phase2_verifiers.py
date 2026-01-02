"""
Tests for SDPC Phase 2 Verifiers
"""

import json
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


@pytest.mark.asyncio
async def test_pacar_verify_with_context_new_session():
    """Test PACAR verifier creates new conversation state for new session_id"""
    verifier = PACARVerifier()

    # Mock Redis client - return None to simulate no existing conversation
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    verifier.redis_client = mock_redis

    # Mock LLM Assistant
    mock_assistant = MagicMock()
    mock_assistant.analyze_message_impact = AsyncMock(
        return_value={
            "risk_level": "low",
            "confidence": 0.9,
            "reasoning": ["Content verified"],
            "mitigations": ["None"],
        }
    )
    verifier.assistant = mock_assistant

    result = await verifier.verify_with_context(
        content="Test content for new session",
        original_intent="test_intent",
        session_id="test-session-123",
        tenant_id="test-tenant",
    )

    # Verify result structure
    assert result["is_valid"] is True
    assert result["confidence"] == 0.9
    assert result["session_id"] == "test-session-123"
    assert result["message_count"] == 1
    assert result["consensus_reached"] is True

    # Verify Redis operations
    mock_redis.get.assert_called_once()
    mock_redis.setex.assert_called_once()

    # Verify the stored conversation data
    call_args = mock_redis.setex.call_args
    stored_key = call_args[0][0]
    stored_ttl = call_args[0][1]
    stored_data = call_args[0][2]

    assert "test-session-123" in stored_key
    assert stored_ttl == 3600  # Default TTL
    conversation_data = json.loads(stored_data)
    assert conversation_data["session_id"] == "test-session-123"
    assert conversation_data["tenant_id"] == "test-tenant"
    assert len(conversation_data["messages"]) == 1
    assert conversation_data["messages"][0]["role"] == "user"
    assert conversation_data["messages"][0]["content"] == "Test content for new session"
