"""
Test for Audit Service integration with Unified Generator
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.core.enhanced_agent_bus.ai_assistant.context import ConversationContext
from src.core.enhanced_agent_bus.ai_assistant.integration import (
    AgentBusIntegration,
    IntegrationConfig,
)
from src.core.enhanced_agent_bus.ai_assistant.nlu import Intent, NLUResult


@pytest.mark.asyncio
async def test_governance_records_to_audit_ledger():
    # Mock NLU result
    nlu_result = NLUResult(
        primary_intent=Intent(name="delete_database", confidence=1.0),
        entities=[]
    )

    # Mock context
    context = ConversationContext(user_id="user_123", session_id="session_456")

    # Mock AuditLedger
    mock_ledger = AsyncMock()

    with patch("src.core.enhanced_agent_bus.ai_assistant.integration.get_audit_ledger", return_value=mock_ledger):
        config = IntegrationConfig(enable_governance=True)
        integration = AgentBusIntegration(config)

        # We need to mock generate_verified_policy to avoid real LLM/Formal tools calls if needed,
        # but here we want to see if it calls add_validation_result.

        await integration._check_governance(nlu_result, context)

        # Verify that add_validation_result was called
        assert mock_ledger.add_validation_result.called

        # Verify metadata contains SMT log
        call_args = mock_ledger.add_validation_result.call_args[0][0]
        assert call_args.metadata["type"] == "governance_psv_verus"
        assert "smt_log" in call_args.metadata
        assert "policy_id" in call_args.metadata
        print("✅ Audit Ledger integration verified!")

if __name__ == "__main__":
    asyncio.run(test_governance_records_to_audit_ledger())
