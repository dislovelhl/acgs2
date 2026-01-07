import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from src.core.services.audit_service.app.api.governance import (
    _calculate_kpis_from_ledger,
    get_governance_kpis,
)
from src.core.services.audit_service.core.audit_ledger import (
    AuditLedger,
    AuditLedgerConfig,
    ValidationResult,
)


@pytest.mark.asyncio
async def test_calculate_kpis_with_opa_and_hitl():
    # Setup a fresh ledger
    config = AuditLedgerConfig(enable_blockchain_anchoring=False)
    ledger = AuditLedger(config=config)
    await ledger.start()  # Start worker

    # Add an OPA evaluation (allowed)
    vr_opa_allow = ValidationResult(
        is_valid=True,
        metadata={
            "type": "opa_evaluation",
            "policy": "data.hitl.routing",
            "result": {"allowed": True},
        },
    )
    await ledger.add_validation_result(vr_opa_allow)

    # Add an OPA evaluation (denied)
    vr_opa_deny = ValidationResult(
        is_valid=False,
        metadata={
            "type": "opa_evaluation",
            "policy": "data.hitl.authorization",
            "result": {"allowed": False},
        },
    )
    await ledger.add_validation_result(vr_opa_deny)

    # Add a HITL action
    vr_hitl = ValidationResult(
        is_valid=True, metadata={"type": "approval_request_created", "request_id": "req-123"}
    )
    await ledger.add_validation_result(vr_hitl)

    # Process the queue (since it's async background)
    # Give it a tiny bit of time to process
    count = 0
    while len(ledger.entries) < 3 and count < 10:
        await asyncio.sleep(0.1)
        count += 1

    # Mock get_audit_ledger to return our local ledger
    with patch(
        "src.core.services.audit_service.core.audit_ledger.get_audit_ledger", new_callable=MagicMock
    ) as mock_get_ledger:
        mock_get_ledger.return_value = asyncio.Future()
        mock_get_ledger.return_value.set_result(ledger)

        kpis = await _calculate_kpis_from_ledger("default")

        assert kpis["opa_metrics"]["total_evaluations"] == 2
        assert kpis["opa_metrics"]["allowed"] == 1
        assert kpis["opa_metrics"]["denied"] == 1
        assert kpis["hitl_metrics"]["total_actions"] == 1

        assert kpis["compliance_score"] == 70.0

    await ledger.stop()


@pytest.mark.asyncio
async def test_governance_kpis_endpoint():
    # Mocking the ledger and its metrics
    mock_ledger = MagicMock()
    mock_ledger.get_anchor_stats.return_value = {
        "total_anchored": 10,
        "last_updated": datetime.now(timezone.utc),
    }
    mock_ledger.get_recent_anchor_results.return_value = []

    async def mock_get_metrics(*args, **kwargs):
        return {"compliance_score": 80.0}

    mock_ledger.get_metrics_for_date = mock_get_metrics
    mock_ledger.entries = []

    # Use a real async wrapper for the mock
    async def mock_get_ledger_func():
        return mock_ledger

    # Patch get_audit_ledger at the source
    with patch(
        "src.core.services.audit_service.core.audit_ledger.get_audit_ledger",
        side_effect=mock_get_ledger_func,
    ):
        # Mock _calculate_kpis_from_ledger to avoid complex logic
        with patch(
            "src.core.services.audit_service.app.api.governance._calculate_kpis_from_ledger"
        ) as mock_calc:
            mock_calc.return_value = {
                "compliance_score": 75.0,
                "controls_passing": 5,
                "controls_failing": 1,
                "controls_total": 6,
                "recent_audits": 10,
                "high_risk_incidents": 1,
                "opa_metrics": {"total_evaluations": 2, "allowed": 1, "denied": 1},
                "hitl_metrics": {"total_actions": 3},
                "last_updated": datetime.now(timezone.utc),
                "data_stale": False,
            }

            try:
                response = await get_governance_kpis(tenant_id="test-tenant")
                assert response["compliance_score"] == 75.0
                assert "opa_metrics" in response
                assert "hitl_metrics" in response
                assert response["tenant_id"] == "test-tenant"
            except Exception as e:
                import traceback

                traceback.print_exc()
                raise e
