"""
ACGS-2 SDK Governance Service Edge Case Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive edge case coverage for GovernanceService including:
- Empty and null input handling
- Boundary value testing
- Response format variations
- Error scenarios and graceful degradation
- Multi-page pagination scenarios
- Status transition edge cases
- Constitutional hash validation edge cases
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, GOVERNANCE_ENDPOINT
from acgs2_sdk.models import (
    ApprovalRequest,
    ApprovalStatus,
    CreateApprovalRequest,
    PaginatedResponse,
    SubmitApprovalDecision,
)

# =============================================================================
# Empty Input Edge Cases
# =============================================================================


class TestEmptyInputs:
    """Tests for handling empty inputs."""

    @pytest.mark.asyncio
    async def test_create_approval_with_empty_payload(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test creating approval request with empty payload."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="test",
            payload={},
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["payload"] == {}

    @pytest.mark.asyncio
    async def test_list_approval_requests_empty_result(
        self,
        governance_service,
        mock_client,
    ):
        """Test listing approval requests with empty result set."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 0,
                "page": 1,
                "pageSize": 50,
                "totalPages": 0,
            }
        }

        result = await governance_service.list_approval_requests()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_decisions_empty_result(
        self,
        governance_service,
        mock_client,
    ):
        """Test listing decisions with empty result set."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 0,
                "page": 1,
                "pageSize": 50,
                "totalPages": 0,
            }
        }

        result = await governance_service.list_decisions()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_validate_constitutional_with_empty_context(
        self,
        governance_service,
        mock_client,
    ):
        """Test constitutional validation with empty context."""
        mock_client.post.return_value = {
            "data": {
                "valid": True,
                "violations": [],
                "recommendations": [],
            }
        }

        result = await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="test_action",
            context={},
        )

        assert result["valid"] is True
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["context"] == {}

    @pytest.mark.asyncio
    async def test_escalate_with_empty_reason(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test escalation with empty reason string."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        result = await governance_service.escalate("request-001", reason="")

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["reason"] == ""

    @pytest.mark.asyncio
    async def test_cancel_with_none_reason(
        self,
        governance_service,
        mock_client,
    ):
        """Test cancellation with None reason."""
        mock_client.post.return_value = {}

        await governance_service.cancel_approval_request("request-001", reason=None)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["reason"] is None


# =============================================================================
# Boundary Value Edge Cases
# =============================================================================


class TestBoundaryValues:
    """Tests for boundary value handling."""

    @pytest.mark.asyncio
    async def test_risk_score_minimum_boundary(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test risk score at minimum boundary (0)."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="low_risk",
            payload={"action": "read"},
            risk_score=0.0,
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["riskScore"] == 0.0

    @pytest.mark.asyncio
    async def test_risk_score_maximum_boundary(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test risk score at maximum boundary (100)."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="critical_risk",
            payload={"action": "delete_all"},
            risk_score=100.0,
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["riskScore"] == 100.0

    @pytest.mark.asyncio
    async def test_required_approvers_minimum(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test required approvers at minimum (1)."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="simple_action",
            payload={"action": "test"},
            required_approvers=1,
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["requiredApprovers"] == 1

    @pytest.mark.asyncio
    async def test_pagination_page_one(
        self,
        governance_service,
        mock_client,
    ):
        """Test pagination at first page."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 100,
                "page": 1,
                "pageSize": 10,
                "totalPages": 10,
            }
        }

        result = await governance_service.list_approval_requests(page=1)

        assert result.page == 1

    @pytest.mark.asyncio
    async def test_pagination_large_page_number(
        self,
        governance_service,
        mock_client,
    ):
        """Test pagination with large page number."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 100,
                "page": 999,
                "pageSize": 10,
                "totalPages": 10,
            }
        }

        await governance_service.list_approval_requests(page=999)

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["page"] == 999

    @pytest.mark.asyncio
    async def test_pagination_page_size_minimum(
        self,
        governance_service,
        mock_client,
    ):
        """Test pagination with minimum page size."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 100,
                "page": 1,
                "pageSize": 1,
                "totalPages": 100,
            }
        }

        await governance_service.list_approval_requests(page_size=1)

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["pageSize"] == 1

    @pytest.mark.asyncio
    async def test_pagination_large_page_size(
        self,
        governance_service,
        mock_client,
    ):
        """Test pagination with large page size."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 1000,
                "page": 1,
                "pageSize": 1000,
                "totalPages": 1,
            }
        }

        await governance_service.list_approval_requests(page_size=1000)

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["pageSize"] == 1000


# =============================================================================
# Response Format Edge Cases
# =============================================================================


class TestResponseFormats:
    """Tests for handling various response formats."""

    @pytest.mark.asyncio
    async def test_response_with_nested_data(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling deeply nested response data."""
        nested_data = sample_approval_request_data.copy()
        nested_data["payload"] = {"nested": {"deeply": {"nested": {"value": "test"}}}}
        mock_client.get.return_value = {"data": nested_data}

        result = await governance_service.get_approval_request("test-id")

        assert result.payload["nested"]["deeply"]["nested"]["value"] == "test"

    @pytest.mark.asyncio
    async def test_response_with_null_optional_fields(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling response with null optional fields."""
        data = sample_approval_request_data.copy()
        data["expiresAt"] = None
        mock_client.get.return_value = {"data": data}

        result = await governance_service.get_approval_request("test-id")

        assert result.expires_at is None

    @pytest.mark.asyncio
    async def test_response_with_extra_fields(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling response with extra unknown fields."""
        data = sample_approval_request_data.copy()
        data["unknownField"] = "should be ignored"
        data["anotherUnknown"] = {"nested": True}
        mock_client.get.return_value = {"data": data}

        result = await governance_service.get_approval_request("test-id")

        assert isinstance(result, ApprovalRequest)

    @pytest.mark.asyncio
    async def test_dashboard_response_structure_variations(
        self,
        governance_service,
        mock_client,
    ):
        """Test dashboard with minimal response structure."""
        minimal_dashboard = {
            "overview": {},
            "recentActivity": [],
            "alerts": [],
        }
        mock_client.get.return_value = {"data": minimal_dashboard}

        result = await governance_service.get_dashboard()

        assert "overview" in result
        assert result["recentActivity"] == []

    @pytest.mark.asyncio
    async def test_metrics_with_zero_values(
        self,
        governance_service,
        mock_client,
    ):
        """Test metrics with all zero values."""
        zero_metrics = {
            "totalRequests": 0,
            "approvalRate": 0.0,
            "averageDecisionTime": 0,
            "pendingRequests": 0,
            "escalatedRequests": 0,
        }
        mock_client.get.return_value = {"data": zero_metrics}

        result = await governance_service.get_metrics()

        assert result["totalRequests"] == 0
        assert result["approvalRate"] == 0.0


# =============================================================================
# Status Transition Edge Cases
# =============================================================================


class TestStatusTransitions:
    """Tests for status transition scenarios."""

    @pytest.mark.asyncio
    async def test_list_all_status_types(
        self,
        governance_service,
        mock_client,
    ):
        """Test filtering by all possible status types."""
        mock_client.get.return_value = {
            "data": {
                "data": [],
                "total": 0,
                "page": 1,
                "pageSize": 50,
                "totalPages": 0,
            }
        }

        for status in ApprovalStatus:
            await governance_service.list_approval_requests(status=status)

        # Should have been called for each status
        assert mock_client.get.call_count == len(ApprovalStatus)

    @pytest.mark.asyncio
    async def test_approval_with_expired_status(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling approval request with expired status."""
        expired_data = sample_approval_request_data.copy()
        expired_data["status"] = "expired"
        expired_data["expiresAt"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        mock_client.get.return_value = {"data": expired_data}

        result = await governance_service.get_approval_request("test-id")

        assert result.status == ApprovalStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_approval_with_all_possible_statuses(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test parsing approval requests with all possible statuses."""
        for status in ApprovalStatus:
            data = sample_approval_request_data.copy()
            data["status"] = status.value
            mock_client.get.return_value = {"data": data}

            result = await governance_service.get_approval_request("test-id")

            assert result.status == status


# =============================================================================
# Special Characters and Encoding Edge Cases
# =============================================================================


class TestSpecialCharacters:
    """Tests for special character handling."""

    @pytest.mark.asyncio
    async def test_request_type_with_special_characters(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test request type with special characters."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="policy/change:v2.0",
            payload={"action": "test"},
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)

    @pytest.mark.asyncio
    async def test_reasoning_with_unicode(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test decision reasoning with unicode characters."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        decision = SubmitApprovalDecision(
            decision="approve",
            reasoning="Approved with conditions: \u2713 Pass audit \u2713 Review complete",
        )
        await governance_service.submit_decision("request-001", decision)

        call_args = mock_client.post.call_args
        assert "\u2713" in call_args[1]["json"]["reasoning"]

    @pytest.mark.asyncio
    async def test_payload_with_unicode(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test payload with unicode characters."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="test",
            payload={"message": "Test \u4e2d\u6587 \u0420\u0443\u0441\u0441\u043a\u0438\u0439"},
        )
        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)

    @pytest.mark.asyncio
    async def test_escalation_reason_with_newlines(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test escalation reason with newlines."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        reason = (
            "Line 1: Critical issue\n"
            "Line 2: Requires immediate attention\n"
            "Line 3: Senior approval needed"
        )
        await governance_service.escalate("request-001", reason=reason)

        call_args = mock_client.post.call_args
        assert "\n" in call_args[1]["json"]["reason"]

    @pytest.mark.asyncio
    async def test_request_id_with_dashes(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test request ID with dashes (UUID format)."""
        uuid_id = str(uuid4())
        mock_client.get.return_value = {"data": sample_approval_request_data}

        await governance_service.get_approval_request(uuid_id)

        mock_client.get.assert_called_with(f"{GOVERNANCE_ENDPOINT}/approvals/{uuid_id}")


# =============================================================================
# Multiple Items Edge Cases
# =============================================================================


class TestMultipleItems:
    """Tests for handling multiple items."""

    @pytest.mark.asyncio
    async def test_multiple_decisions_in_approval(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test approval request with multiple decisions."""
        data = sample_approval_request_data.copy()
        data["decisions"] = [
            {
                "approverId": "reviewer-001",
                "decision": "approved",
                "reasoning": "First review passed",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "approverId": "reviewer-002",
                "decision": "approved",
                "reasoning": "Second review passed",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "approverId": "reviewer-003",
                "decision": "approved",
                "reasoning": "Third review passed",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]
        data["currentApprovals"] = 3
        mock_client.get.return_value = {"data": data}

        result = await governance_service.get_approval_request("test-id")

        assert len(result.decisions) == 3
        assert result.current_approvals == 3

    @pytest.mark.asyncio
    async def test_large_paginated_result(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling large paginated results."""
        # Create list of 100 items
        items = []
        for _i in range(100):
            item = sample_approval_request_data.copy()
            item["id"] = str(uuid4())
            items.append(item)

        mock_client.get.return_value = {
            "data": {
                "data": items,
                "total": 1000,
                "page": 1,
                "pageSize": 100,
                "totalPages": 10,
            }
        }

        result = await governance_service.list_approval_requests(page_size=100)

        assert len(result.data) == 100
        assert result.total == 1000
        assert result.total_pages == 10

    @pytest.mark.asyncio
    async def test_multiple_policy_violations(
        self,
        governance_service,
        mock_client,
        sample_decision_id,
        sample_approval_request_id,
        constitutional_hash,
    ):
        """Test decision with multiple policy violations."""
        decision_data = {
            "id": sample_decision_id,
            "requestId": sample_approval_request_id,
            "decision": "deny",
            "reasoning": "Multiple policy violations detected",
            "policyViolations": [
                "violation-001: Exceeds risk threshold",
                "violation-002: Missing required approval",
                "violation-003: Conflicts with existing policy",
                "violation-004: Insufficient documentation",
            ],
            "riskScore": 95.0,
            "reviewerIds": ["reviewer-001"],
            "timestamp": datetime.now(UTC).isoformat(),
            "blockchainAnchor": None,
            "constitutionalHash": constitutional_hash,
        }
        mock_client.get.return_value = {"data": decision_data}

        result = await governance_service.get_decision(sample_decision_id)

        assert len(result.policy_violations) == 4
        assert result.decision == "deny"

    @pytest.mark.asyncio
    async def test_multiple_reviewer_ids(
        self,
        governance_service,
        mock_client,
        sample_governance_decision_data,
    ):
        """Test decision with multiple reviewers."""
        data = sample_governance_decision_data.copy()
        data["reviewerIds"] = [
            "reviewer-001",
            "reviewer-002",
            "reviewer-003",
            "reviewer-004",
            "reviewer-005",
        ]
        mock_client.get.return_value = {"data": data}

        result = await governance_service.get_decision("test-id")

        assert len(result.reviewer_ids) == 5


# =============================================================================
# Constitutional Hash Edge Cases
# =============================================================================


@pytest.mark.constitutional
class TestConstitutionalHashEdgeCases:
    """Tests for constitutional hash edge cases."""

    @pytest.mark.asyncio
    async def test_response_with_different_hash_key_names(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test response with 'constitutionalHash' key (camelCase)."""
        mock_client.get.return_value = {"data": sample_approval_request_data}

        result = await governance_service.get_approval_request("test-id")

        # Should use constitutionalHash (camelCase)
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_validate_constitutional_response_with_hash(
        self,
        governance_service,
        mock_client,
    ):
        """Test constitutional validation response includes hash."""
        response_data = {
            "valid": True,
            "violations": [],
            "recommendations": [],
            "constitutionalHash": CONSTITUTIONAL_HASH,
        }
        mock_client.post.return_value = {"data": response_data}

        result = await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="test",
            context={},
        )

        assert result["constitutionalHash"] == CONSTITUTIONAL_HASH


# =============================================================================
# Concurrent Request Edge Cases
# =============================================================================


class TestConcurrentScenarios:
    """Tests simulating concurrent request scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test making multiple sequential requests."""
        mock_client.get.return_value = {"data": sample_approval_request_data}

        # Make 5 sequential requests
        results = []
        for i in range(5):
            result = await governance_service.get_approval_request(f"request-{i}")
            results.append(result)

        assert len(results) == 5
        assert mock_client.get.call_count == 5

    @pytest.mark.asyncio
    async def test_mixed_operation_sequence(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
        sample_governance_decision_data,
        sample_metrics_data,
    ):
        """Test mixed sequence of different operations."""
        # Setup mock returns
        mock_client.get.side_effect = [
            {"data": sample_approval_request_data},
            {"data": sample_governance_decision_data},
            {"data": sample_metrics_data},
        ]
        mock_client.post.return_value = {"data": sample_approval_request_data}

        # Perform mixed operations
        await governance_service.get_approval_request("request-001")
        await governance_service.get_decision("decision-001")
        await governance_service.get_metrics()

        assert mock_client.get.call_count == 3


# =============================================================================
# Error Recovery Edge Cases
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_list_with_missing_pagination_fields(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test list operation with missing pagination fields in response."""
        # Response missing some pagination fields
        mock_client.get.return_value = {
            "data": {
                "data": [sample_approval_request_data],
                "total": 1,
                # Missing 'page', 'pageSize', 'totalPages'
            }
        }

        result = await governance_service.list_approval_requests()

        # Should handle missing fields gracefully using defaults
        assert len(result.data) == 1
        assert result.total == 1
        # page should default to the requested page
        assert result.page == 1
        # page_size should default to the requested page_size
        assert result.page_size == 50

    @pytest.mark.asyncio
    async def test_empty_decisions_list(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test approval request with empty decisions list."""
        data = sample_approval_request_data.copy()
        data["decisions"] = []
        data["currentApprovals"] = 0
        mock_client.get.return_value = {"data": data}

        result = await governance_service.get_approval_request("test-id")

        assert len(result.decisions) == 0
        assert result.current_approvals == 0


# =============================================================================
# Integration-like Scenarios
# =============================================================================


class TestRealisticScenarios:
    """Tests simulating realistic usage scenarios."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test complete approval workflow from creation to decision."""
        # Step 1: Create request
        mock_client.post.return_value = {"data": sample_approval_request_data}
        request = CreateApprovalRequest(
            request_type="policy_change",
            payload={"policyId": "policy-001"},
            risk_score=50.0,
            required_approvers=2,
        )
        created = await governance_service.create_approval_request(request)
        request_id = str(created.id)

        # Step 2: Get request details
        mock_client.get.return_value = {"data": sample_approval_request_data}
        await governance_service.get_approval_request(request_id)

        # Step 3: Submit first decision
        decision = SubmitApprovalDecision(decision="approve", reasoning="Looks good")
        await governance_service.submit_decision(request_id, decision)

        # Step 4: Submit second decision (final approval)
        approved_data = sample_approval_request_data.copy()
        approved_data["status"] = "approved"
        approved_data["currentApprovals"] = 2
        mock_client.post.return_value = {"data": approved_data}
        final = await governance_service.submit_decision(request_id, decision)

        assert final.status == ApprovalStatus.APPROVED
        assert final.current_approvals == 2

    @pytest.mark.asyncio
    async def test_escalation_workflow(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test escalation workflow."""
        # Step 1: Create high-risk request
        mock_client.post.return_value = {"data": sample_approval_request_data}
        request = CreateApprovalRequest(
            request_type="critical_action",
            payload={"action": "production_change"},
            risk_score=95.0,
            required_approvers=3,
        )
        created = await governance_service.create_approval_request(request)

        # Step 2: Escalate due to high risk
        escalated_data = sample_approval_request_data.copy()
        escalated_data["status"] = "escalated"
        mock_client.post.return_value = {"data": escalated_data}
        escalated = await governance_service.escalate(
            str(created.id),
            reason="Risk score 95% exceeds critical threshold",
        )

        assert escalated.status == ApprovalStatus.ESCALATED

    @pytest.mark.asyncio
    async def test_cancellation_workflow(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test cancellation workflow."""
        # Step 1: Create request
        mock_client.post.return_value = {"data": sample_approval_request_data}
        request = CreateApprovalRequest(
            request_type="test_action",
            payload={"action": "test"},
        )
        created = await governance_service.create_approval_request(request)

        # Step 2: Cancel request
        mock_client.post.return_value = {}
        await governance_service.cancel_approval_request(
            str(created.id),
            reason="Request no longer needed",
        )

        # Verify cancel was called
        assert mock_client.post.call_count == 2
        last_call = mock_client.post.call_args
        assert "cancel" in last_call[0][0]

    @pytest.mark.asyncio
    async def test_compliance_check_workflow(
        self,
        governance_service,
        mock_client,
    ):
        """Test compliance checking workflow."""
        # Step 1: Validate action constitutionally
        mock_client.post.return_value = {
            "data": {
                "valid": True,
                "violations": [],
                "recommendations": ["Consider adding audit logging"],
            }
        }
        validation = await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="data_access",
            context={"dataType": "user_pii", "purpose": "analytics"},
            metadata={"requestor": "analytics-service"},
        )

        # Step 2: Get constitutional principles
        mock_client.get.return_value = {
            "data": [
                {"id": "principle-001", "name": "Data Minimization"},
                {"id": "principle-002", "name": "Purpose Limitation"},
            ]
        }
        principles = await governance_service.get_constitutional_principles()

        assert validation["valid"] is True
        assert len(principles) == 2
