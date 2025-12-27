"""
Tests for Policy Deployment Saga
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from ..base.context import WorkflowContext
from ..sagas.policy_deployment import PolicyDeploymentSaga
from ..sagas.base_saga import SagaStatus

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

class TestPolicyDeploymentSaga:
    """Test suite for PolicyDeploymentSaga."""

    @pytest.mark.asyncio
    async def test_successful_deployment(self):
        """Test happy path deployment."""
        saga = PolicyDeploymentSaga()
        context = WorkflowContext.create()

        result = await saga.execute(context, {
            "policy_id": "pol-123",
            "policy_content": {"rules": ["allow_all"]}
        })

        assert result.status == SagaStatus.COMPLETED
        assert result.output["active"] is True
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_deployment_rollback(self):
        """Test rollback when deployment fails."""
        saga = PolicyDeploymentSaga()
        context = WorkflowContext.create()

        # Trigger deployment failure
        result = await saga.execute(context, {
            "policy_id": "pol-123",
            "policy_content": {"rules": ["allow_all"]},
            "simulate_deploy_failure": True
        })

        # Expect COMPENSATED status (rollback successful)
        assert result.status == SagaStatus.COMPENSATED
        assert "Deployment simulation failure" in str(result.errors[0])

    @pytest.mark.asyncio
    async def test_verification_rollback(self):
        """Test rollback when verification fails (after deployment)."""
        saga = PolicyDeploymentSaga()
        context = WorkflowContext.create()

        # Trigger verification failure
        result = await saga.execute(context, {
            "policy_id": "pol-123",
            "policy_content": {"rules": ["allow_all"]},
            "simulate_verify_failure": True
        })

        assert result.status == SagaStatus.COMPENSATED
        assert "Policy verification failed" in str(result.errors[0])

    @pytest.mark.asyncio
    async def test_invalid_policy_rejection(self):
        """Test validation step rejects unsafe policies early."""
        saga = PolicyDeploymentSaga()
        context = WorkflowContext.create()

        result = await saga.execute(context, {
            "policy_id": "pol-123",
            "policy_content": {"unsafe": "true"}
        })

        # Expect FAILED because validation fail has no compensations (it's the first step/step failure before any compensated steps)
        assert result.status == SagaStatus.FAILED
        assert "Policy contains unsafe directives" in str(result.errors[0])
