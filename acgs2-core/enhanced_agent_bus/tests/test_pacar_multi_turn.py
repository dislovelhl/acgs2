"""
Tests for PACAR multi-turn support.
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from enhanced_agent_bus.sdpc.pacar_manager import PACARManager
from enhanced_agent_bus.sdpc.pacar_verifier import PACARVerifier
from enhanced_agent_bus.sdpc.conversation import MessageRole, ConversationState
from enhanced_agent_bus.config import BusConfiguration


@pytest.fixture
def bus_config():
    return BusConfiguration(redis_url="redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_pacar_manager_add_message(bus_config):
    manager = PACARManager(config=bus_config)

    # Mock redis
    mock_redis = AsyncMock()
    with patch.object(PACARManager, "_get_redis", return_value=mock_redis):
        session_id = "test_session_1"
        content = "Test message"

        state = await manager.add_message(session_id, MessageRole.USER, content)

        assert state.session_id == session_id
        assert len(state.messages) == 1
        assert state.messages[0].content == content
        assert state.messages[0].role == MessageRole.USER

        # Verify redis call
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_pacar_verifier_multi_turn(bus_config):
    # Mock components
    mock_assistant = AsyncMock()
    mock_assistant.analyze_message_impact.return_value = {
        "risk_level": "low",
        "confidence": 0.9,
        "reasoning": ["Test review"]
    }
    mock_assistant.ainvoke_multi_turn.return_value = {
        "recommended_decision": "approve",
        "risk_level": "low",
        "confidence": 0.95,
        "reasoning": ["Content is safe."]
    }

    with patch("enhanced_agent_bus.sdpc.pacar_verifier.get_llm_assistant", return_value=mock_assistant):
        verifier = PACARVerifier(config=bus_config)

        # Mock manager
        verifier.manager = AsyncMock(spec=PACARManager)
        # Ensure get_state returns a mock ConversationState
        verifier.manager.get_state.return_value = MagicMock(messages=[])

        session_id = "test_session_multi"
        content = "Check this content"
        intent = "factual"

        result = await verifier.verify_with_context(content, intent, session_id=session_id)

        assert result["is_valid"] is True
        assert verifier.manager.add_message.call_count == 3 # User, Critique, Result

        # Check first call (user)
        verifier.manager.add_message.assert_any_call(
            session_id, MessageRole.USER, content, {"intent": intent}
        )


@pytest.mark.asyncio
async def test_pacar_manager_redis_failure_fallback(bus_config):
    manager = PACARManager(config=bus_config)

    # Mock redis to fail
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection error")
    mock_redis.setex.side_effect = Exception("Redis connection error")

    with patch.object(PACARManager, "_get_redis", return_value=mock_redis):
        session_id = "test_session_fail"

        # Should still work locally
        state = await manager.add_message(session_id, MessageRole.USER, "Hello")
        assert state.session_id == session_id
        assert len(state.messages) == 1

        # Second call should find it in local history
        state2 = await manager.get_state(session_id)
        assert state2 == state


@pytest.mark.asyncio
async def test_conversation_pruning(bus_config):
    """Test conversation pruning logic to enforce context window."""
    verifier = PACARVerifier(config=bus_config)

    # Create a conversation with 60 messages
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(60)]
    conversation_data = {
        "session_id": "prune_test",
        "messages": messages,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Prune to max 50
    pruned = verifier._prune_conversation(conversation_data, max_messages=50)

    assert len(pruned["messages"]) == 50
    # Should keep the LAST 50 messages
    assert pruned["messages"][0]["content"] == "msg 10"
    assert pruned["messages"][-1]["content"] == "msg 59"


@pytest.mark.asyncio
async def test_pacar_verifier_redis_fallback(bus_config):
    """Test graceful degradation to single-turn when Redis is missing."""
    # Mock verifier with NO redis client
    verifier = PACARVerifier(config=bus_config)
    verifier.redis_client = None  # Simulate connection failure/absence

    # Mock assistant to avoid actual LLM calls
    verifier.assistant = AsyncMock()
    verifier.assistant.ainvoke_multi_turn.return_value = {
        "recommended_decision": "approve",
        "risk_level": "low",
        "confidence": 0.8,
        "reasoning": ["Fallback test safe"]
    }
    verifier.assistant.analyze_message_impact.return_value = {
        "risk_level": "low",
        "confidence": 0.8
    }

    # Mock manager to avoid errors
    verifier.manager = AsyncMock()
    verifier.manager.get_state.return_value = MagicMock(messages=[])

    session_id = "fallback_session"
    content = "Test content"
    intent = "factual"

    # Verify with context should proceed (using empty/new context)
    result = await verifier.verify_with_context(content, intent, session_id=session_id)

    assert result["is_valid"] is True
    # Should use the multi-turn path (ainvoke_multi_turn) even if Redis is down
    # because it just starts a fresh conversation context
    assert verifier.assistant.ainvoke_multi_turn.called
