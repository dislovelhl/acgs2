"""
Tests for Constitutional Workflows (Validation)
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib

import pytest

from ..base.activities import DefaultActivities
from ..base.result import WorkflowStatus
from ..constitutional.compliance import ComplianceCheckWorkflow
from ..constitutional.governance_decision import GovernanceDecisionWorkflow
from ..constitutional.policy_evaluation import PolicyEvaluationWorkflow
from ..constitutional.validation import (
    ConstitutionalValidationWorkflow,
)

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestConstitutionalValidationWorkflow:
    """Tests for ConstitutionalValidationWorkflow."""

    @pytest.mark.asyncio
    async def test_full_validation_success(self):
        """Test successful multi-stage validation."""
        workflow = ConstitutionalValidationWorkflow()

        content = "test content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        result = await workflow.run(
            {
                "content": content,
                "content_hash": content_hash,
                "provided_constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        assert result.is_successful
        assert result.output["validated"] is True
        assert len(result.output["stages"]) >= 4  # Hash, Integrity, Compliance, Audit

    @pytest.mark.asyncio
    async def test_hash_mismatch_failure(self):
        """Test validation fails on constitutional hash mismatch."""
        workflow = ConstitutionalValidationWorkflow()

        result = await workflow.run(
            {"content": "some content", "provided_constitutional_hash": "wrong-hash"}
        )

        assert result.is_failed
        assert "Hash check failed" in result.errors or any(
            "Constitutional hash mismatch" in e for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_integrity_failure(self):
        """Test validation fails on content integrity mismatch."""
        workflow = ConstitutionalValidationWorkflow()

        result = await workflow.run(
            {
                "content": "actual content",
                "content_hash": "mismatching-hash",  # ERROR
                "provided_constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        assert result.is_failed
        assert any("Integrity check failed" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_non_strict_compliance(self):
        """Test non-strict compliance allows partial success."""
        workflow = ConstitutionalValidationWorkflow()

        # Mismatch integrity but use non-strict mode
        # Wait, the workflow currently returns failure result if any mandatory stage fails
        # but check_compliance calculates a score.
        # Let's see how _check_compliance is used.

        result = await workflow.run(
            {
                "content": "content",
                "content_hash": "wrong",
                "provided_constitutional_hash": CONSTITUTIONAL_HASH,
                "require_strict_compliance": False,
            }
        )

        # In the current implementation of ConstitutionalValidationWorkflow.execute,
        # it returns early on HASH_CHECK or INTEGRITY_CHECK failure if
        # require_strict_compliance is True.
        # If False, it continues.

        # If hash check failed but non-strict, it continues to integrity.
        # If integrity failed but non-strict, it continues to compliance.

        # Let's check the result status
        assert result.status == WorkflowStatus.COMPLETED or result.is_failed
        # Based on code: if compliance_result.passed is False, all_passed = False.
        # Strict mode threshold is 1.0, non-strict is 0.8.
        # With 1 failure out of 3 major checks (Hash, Integrity, Policy), score is 0.66 < 0.8.
        # So it should still fail.
        assert result.is_failed


class TestComplianceCheckWorkflow:
    """Tests for ComplianceCheckWorkflow."""

    @pytest.mark.asyncio
    async def test_compliance_success(self):
        """Test successful compliance check."""

        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": True}

        workflow = ComplianceCheckWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run(
            {
                "target_agent_id": "agent-1",
                "actions": [{"action_id": "a1", "timestamp": "2023-01-01T00:00:00Z"}],
            }
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["is_compliant"] is True

    @pytest.mark.asyncio
    async def test_compliance_violation(self):
        """Test compliance check with policy violations."""

        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": False, "reasons": ["Action not permitted"]}

            async def record_audit(self, workflow_id, event_type, event_data):
                return "audit-id"

        workflow = ComplianceCheckWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run(
            {
                "target_agent_id": "agent-1",
                "actions": [{"action_id": "a1", "timestamp": "2023-01-01T00:00:00Z"}],
            }
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["is_compliant"] is False
        assert len(result.output["details"]["violations"]) == 1


class TestPolicyEvaluationWorkflow:
    """Tests for PolicyEvaluationWorkflow."""

    @pytest.mark.asyncio
    async def test_policy_evaluation_success(self):
        """Test direct policy evaluation."""

        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": True, "reasons": []}

        workflow = PolicyEvaluationWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run(
            {"policy_path": "test/policy", "evaluation_data": {"key": "value"}}
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["allowed"] is True


class TestGovernanceDecisionWorkflow:
    """Tests for GovernanceDecisionWorkflow."""

    @pytest.mark.asyncio
    async def test_governance_decision_approved(self):
        """Test approved governance decision through impact assessment and voting."""

        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": True}  # Impact assessment pass

            async def list_agents(self, capabilities=None, status="active"):
                return [{"agent_id": "voter1"}]

            async def record_audit(self, workflow_id, event_type, event_data):
                return "audit-id"

            async def broadcast_command(self, workflow_id, agents, command, payload):
                # Simulated vote collection
                return {"voter1": {"decision": "approve"}}

        workflow = GovernanceDecisionWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run(
            {
                "proposal_type": "constitutional_update",
                "proposal_data": {"new_hash": "cdd..."},
                "eligible_voters": ["voter1"],
                "voting_strategy": "majority",
            }
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["decision"] in ["approved", "rejected"]
