from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.core.services.hitl_approvals.app.models.approval_chain import ApprovalChain
from src.core.services.hitl_approvals.app.services.approval_chain_engine import ApprovalChainEngine


@pytest.mark.asyncio
async def test_resolve_chain_id_opa_recommended():
    # Setup
    db = AsyncMock()
    engine = ApprovalChainEngine(db)

    chain_id = uuid4()
    mock_chain = MagicMock(spec=ApprovalChain)
    mock_chain.id = chain_id

    # Mock OPA client
    mock_opa_client = AsyncMock()
    mock_opa_client.evaluate_routing.return_value = {"allowed": True, "chain_id": str(chain_id)}

    # Mock DB result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_chain
    db.execute.return_value = mock_result

    with patch(
        "src.core.services.hitl_approvals.app.services.approval_chain_engine.get_opa_client",
        return_value=mock_opa_client,
    ):
        # Execute
        resolved_id = await engine._resolve_chain_id(
            decision_id="test_decision",
            tenant_id="tenant_1",
            priority="high",
            context={"requester_role": "admin"},
        )

        # Verify
        assert resolved_id == chain_id
        mock_opa_client.evaluate_routing.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_chain_id_fallback_to_priority():
    # Setup
    db = AsyncMock()
    engine = ApprovalChainEngine(db)

    chain_id = uuid4()
    mock_chain = MagicMock(spec=ApprovalChain)
    mock_chain.id = chain_id

    # Mock OPA client (fails or denies)
    mock_opa_client = AsyncMock()
    mock_opa_client.evaluate_routing.return_value = {"allowed": False}

    # Mock DB result for priority fallback
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_chain
    db.execute.return_value = mock_result

    with patch(
        "src.core.services.hitl_approvals.app.services.approval_chain_engine.get_opa_client",
        return_value=mock_opa_client,
    ):
        # Execute
        resolved_id = await engine._resolve_chain_id(
            decision_id="test_decision", tenant_id="tenant_1", priority="high", context={}
        )

        # Verify
        assert resolved_id == chain_id
        # Double check that OPA was called but we still returned a chain id
        mock_opa_client.evaluate_routing.assert_called_once()
