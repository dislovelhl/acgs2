"""
ACGS-2 SDK Governance Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for GovernanceService including:
- Approval request creation and management
- Decision submission and retrieval
- Escalation workflows
- Constitutional validation
- Metrics and dashboard retrieval
- All decision branches and paths
"""


import pytest

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, GOVERNANCE_ENDPOINT
from acgs2_sdk.models import (
    ApprovalRequest,
    ApprovalStatus,
    CreateApprovalRequest,
    GovernanceDecision,
    PaginatedResponse,
    SubmitApprovalDecision,
)
from acgs2_sdk.services.governance import GovernanceService

# =============================================================================
# Approval Request Creation Tests
# =============================================================================


class TestApprovalRequestCreation:
    """Tests for approval request creation functionality."""

    @pytest.mark.asyncio
    async def test_create_approval_request_success(
        self,
        governance_service,
        mock_client,
        sample_create_approval_request,
        sample_approval_request_data,
    ):
        """Test successful creation of approval request."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        result = await governance_service.create_approval_request(sample_create_approval_request)

        assert isinstance(result, ApprovalRequest)
        assert str(result.id) == sample_approval_request_data["id"]
        assert result.request_type == sample_approval_request_data["requestType"]
        assert result.status == ApprovalStatus.PENDING
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{GOVERNANCE_ENDPOINT}/approvals"
        assert "constitutionalHash" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_create_approval_request_includes_constitutional_hash(
        self,
        governance_service,
        mock_client,
        sample_create_approval_request,
        sample_approval_request_data,
    ):
        """Test that create request includes constitutional hash."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        await governance_service.create_approval_request(sample_create_approval_request)

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["constitutionalHash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_create_approval_request_with_risk_score(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test creating approval request with custom risk score."""
        request = CreateApprovalRequest(
            request_type="high_risk_action",
            payload={"action": "delete_data"},
            risk_score=95.0,
            required_approvers=3,
        )
        mock_client.post.return_value = {"data": sample_approval_request_data}

        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["riskScore"] == 95.0
        assert json_payload["requiredApprovers"] == 3

    @pytest.mark.asyncio
    async def test_create_approval_request_without_optional_fields(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test creating approval request without optional fields."""
        request = CreateApprovalRequest(
            request_type="simple_action",
            payload={"action": "test"},
        )
        mock_client.post.return_value = {"data": sample_approval_request_data}

        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert "riskScore" not in json_payload or json_payload["riskScore"] is None

    @pytest.mark.asyncio
    async def test_create_approval_request_response_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test handling response without 'data' wrapper."""
        # API returns data directly without 'data' wrapper
        mock_client.post.return_value = sample_approval_request_data

        request = CreateApprovalRequest(
            request_type="simple_action",
            payload={"action": "test"},
        )

        result = await governance_service.create_approval_request(request)

        assert isinstance(result, ApprovalRequest)
        assert str(result.id) == sample_approval_request_data["id"]


# =============================================================================
# Approval Request Retrieval Tests
# =============================================================================


class TestApprovalRequestRetrieval:
    """Tests for approval request retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_approval_request_success(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test successful retrieval of approval request by ID."""
        mock_client.get.return_value = {"data": sample_approval_request_data}

        result = await governance_service.get_approval_request(sample_approval_request_id)

        assert isinstance(result, ApprovalRequest)
        assert str(result.id) == sample_approval_request_id
        assert result.status == ApprovalStatus.PENDING
        mock_client.get.assert_called_once_with(
            f"{GOVERNANCE_ENDPOINT}/approvals/{sample_approval_request_id}"
        )

    @pytest.mark.asyncio
    async def test_get_approval_request_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test retrieval when response lacks 'data' wrapper."""
        mock_client.get.return_value = sample_approval_request_data

        result = await governance_service.get_approval_request(sample_approval_request_id)

        assert isinstance(result, ApprovalRequest)
        assert str(result.id) == sample_approval_request_id


# =============================================================================
# Approval Request Listing Tests
# =============================================================================


class TestApprovalRequestListing:
    """Tests for approval request listing functionality."""

    @pytest.mark.asyncio
    async def test_list_approval_requests_default_params(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests with default parameters."""
        mock_client.get.return_value = sample_paginated_response

        result = await governance_service.list_approval_requests()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 1
        assert isinstance(result.data[0], ApprovalRequest)
        assert result.total == 1
        assert result.page == 1
        assert result.page_size == 50

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["page"] == 1
        assert params["pageSize"] == 50

    @pytest.mark.asyncio
    async def test_list_approval_requests_with_pagination(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests with custom pagination."""
        mock_client.get.return_value = sample_paginated_response

        await governance_service.list_approval_requests(page=2, page_size=25)

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["page"] == 2
        assert params["pageSize"] == 25

    @pytest.mark.asyncio
    async def test_list_approval_requests_with_status_filter(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests filtered by status."""
        mock_client.get.return_value = sample_paginated_response

        await governance_service.list_approval_requests(status=ApprovalStatus.PENDING)

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_approval_requests_with_requester_filter(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests filtered by requester."""
        mock_client.get.return_value = sample_paginated_response

        await governance_service.list_approval_requests(requester_id="user-001")

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["requesterId"] == "user-001"

    @pytest.mark.asyncio
    async def test_list_approval_requests_with_pending_for_filter(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests pending for a specific reviewer."""
        mock_client.get.return_value = sample_paginated_response

        await governance_service.list_approval_requests(pending_for="reviewer-001")

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["pendingFor"] == "reviewer-001"

    @pytest.mark.asyncio
    async def test_list_approval_requests_with_all_filters(
        self,
        governance_service,
        mock_client,
        sample_paginated_response,
    ):
        """Test listing approval requests with all filters combined."""
        mock_client.get.return_value = sample_paginated_response

        await governance_service.list_approval_requests(
            page=2,
            page_size=10,
            status=ApprovalStatus.ESCALATED,
            requester_id="user-002",
            pending_for="reviewer-002",
        )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["page"] == 2
        assert params["pageSize"] == 10
        assert params["status"] == "escalated"
        assert params["requesterId"] == "user-002"
        assert params["pendingFor"] == "reviewer-002"

    @pytest.mark.asyncio
    async def test_list_approval_requests_empty_result(
        self,
        governance_service,
        mock_client,
        sample_empty_paginated_response,
    ):
        """Test listing approval requests with empty result."""
        mock_client.get.return_value = sample_empty_paginated_response

        result = await governance_service.list_approval_requests()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0
        assert result.total == 0
        assert result.total_pages == 0


# =============================================================================
# Decision Submission Tests
# =============================================================================


class TestDecisionSubmission:
    """Tests for decision submission functionality."""

    @pytest.mark.asyncio
    async def test_submit_decision_approve(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test submitting an approval decision."""
        # Update status to approved for response
        approved_data = sample_approval_request_data.copy()
        approved_data["status"] = "approved"
        mock_client.post.return_value = {"data": approved_data}

        decision = SubmitApprovalDecision(
            decision="approve",
            reasoning="All criteria met",
        )

        result = await governance_service.submit_decision(sample_approval_request_id, decision)

        assert isinstance(result, ApprovalRequest)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == f"{GOVERNANCE_ENDPOINT}/approvals/{sample_approval_request_id}/decisions"
        )

    @pytest.mark.asyncio
    async def test_submit_decision_reject(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test submitting a rejection decision."""
        rejected_data = sample_approval_request_data.copy()
        rejected_data["status"] = "rejected"
        mock_client.post.return_value = {"data": rejected_data}

        decision = SubmitApprovalDecision(
            decision="reject",
            reasoning="Policy violations detected",
        )

        result = await governance_service.submit_decision(sample_approval_request_id, decision)

        assert isinstance(result, ApprovalRequest)
        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["decision"] == "reject"
        assert json_payload["reasoning"] == "Policy violations detected"

    @pytest.mark.asyncio
    async def test_submit_decision_includes_timestamp(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test that decision submission includes timestamp."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        decision = SubmitApprovalDecision(decision="approve", reasoning="Test")

        await governance_service.submit_decision(sample_approval_request_id, decision)

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert "timestamp" in json_payload
        assert "constitutionalHash" in json_payload

    @pytest.mark.asyncio
    async def test_submit_decision_includes_constitutional_hash(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test that decision submission includes constitutional hash."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        decision = SubmitApprovalDecision(decision="approve", reasoning="Test")

        await governance_service.submit_decision(sample_approval_request_id, decision)

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["constitutionalHash"] == CONSTITUTIONAL_HASH


# =============================================================================
# Escalation Tests
# =============================================================================


class TestEscalation:
    """Tests for escalation functionality."""

    @pytest.mark.asyncio
    async def test_escalate_approval_request(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test escalating an approval request."""
        escalated_data = sample_approval_request_data.copy()
        escalated_data["status"] = "escalated"
        mock_client.post.return_value = {"data": escalated_data}

        result = await governance_service.escalate(
            sample_approval_request_id,
            reason="Risk score exceeds threshold",
        )

        assert isinstance(result, ApprovalRequest)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == f"{GOVERNANCE_ENDPOINT}/approvals/{sample_approval_request_id}/escalate"
        )
        assert call_args[1]["json"]["reason"] == "Risk score exceeds threshold"

    @pytest.mark.asyncio
    async def test_escalate_with_detailed_reason(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
        sample_approval_request_data,
    ):
        """Test escalating with detailed reasoning."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        detailed_reason = (
            "Multiple policy violations detected. "
            "Risk score of 95.5 exceeds critical threshold. "
            "Requires senior management approval."
        )

        await governance_service.escalate(sample_approval_request_id, reason=detailed_reason)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["reason"] == detailed_reason


# =============================================================================
# Cancellation Tests
# =============================================================================


class TestCancellation:
    """Tests for cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_approval_request_with_reason(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
    ):
        """Test cancelling an approval request with reason."""
        mock_client.post.return_value = {}

        await governance_service.cancel_approval_request(
            sample_approval_request_id,
            reason="No longer needed",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == f"{GOVERNANCE_ENDPOINT}/approvals/{sample_approval_request_id}/cancel"
        )
        assert call_args[1]["json"]["reason"] == "No longer needed"

    @pytest.mark.asyncio
    async def test_cancel_approval_request_without_reason(
        self,
        governance_service,
        mock_client,
        sample_approval_request_id,
    ):
        """Test cancelling an approval request without reason."""
        mock_client.post.return_value = {}

        await governance_service.cancel_approval_request(sample_approval_request_id)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["reason"] is None


# =============================================================================
# Governance Decision Tests
# =============================================================================


class TestGovernanceDecisions:
    """Tests for governance decision retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_decision(
        self,
        governance_service,
        mock_client,
        sample_decision_id,
        sample_governance_decision_data,
    ):
        """Test retrieving a governance decision by ID."""
        mock_client.get.return_value = {"data": sample_governance_decision_data}

        result = await governance_service.get_decision(sample_decision_id)

        assert isinstance(result, GovernanceDecision)
        assert str(result.id) == sample_decision_id
        assert result.decision == "approve"
        assert result.constitutional_hash == CONSTITUTIONAL_HASH
        mock_client.get.assert_called_once_with(
            f"{GOVERNANCE_ENDPOINT}/decisions/{sample_decision_id}"
        )

    @pytest.mark.asyncio
    async def test_get_decision_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_decision_id,
        sample_governance_decision_data,
    ):
        """Test retrieving decision when response lacks 'data' wrapper."""
        mock_client.get.return_value = sample_governance_decision_data

        result = await governance_service.get_decision(sample_decision_id)

        assert isinstance(result, GovernanceDecision)

    @pytest.mark.asyncio
    async def test_list_decisions_default_params(
        self,
        governance_service,
        mock_client,
        sample_governance_decision_data,
    ):
        """Test listing decisions with default parameters."""
        mock_client.get.return_value = {
            "data": {
                "data": [sample_governance_decision_data],
                "total": 1,
                "page": 1,
                "pageSize": 50,
                "totalPages": 1,
            }
        }

        result = await governance_service.list_decisions()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 1
        assert isinstance(result.data[0], GovernanceDecision)

    @pytest.mark.asyncio
    async def test_list_decisions_with_filters(
        self,
        governance_service,
        mock_client,
        sample_governance_decision_data,
        sample_approval_request_id,
    ):
        """Test listing decisions with filters."""
        mock_client.get.return_value = {
            "data": {
                "data": [sample_governance_decision_data],
                "total": 1,
                "page": 1,
                "pageSize": 50,
                "totalPages": 1,
            }
        }

        await governance_service.list_decisions(
            decision="approve",
            request_id=sample_approval_request_id,
            reviewer_id="reviewer-001",
        )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["decision"] == "approve"
        assert params["requestId"] == sample_approval_request_id
        assert params["reviewerId"] == "reviewer-001"

    @pytest.mark.asyncio
    async def test_list_decisions_with_pagination(
        self,
        governance_service,
        mock_client,
        sample_governance_decision_data,
    ):
        """Test listing decisions with pagination."""
        mock_client.get.return_value = {
            "data": {
                "data": [sample_governance_decision_data],
                "total": 100,
                "page": 3,
                "pageSize": 20,
                "totalPages": 5,
            }
        }

        result = await governance_service.list_decisions(page=3, page_size=20)

        assert result.page == 3
        assert result.page_size == 20
        assert result.total == 100
        assert result.total_pages == 5


# =============================================================================
# Blockchain Anchor Verification Tests
# =============================================================================


class TestAnchorVerification:
    """Tests for blockchain anchor verification."""

    @pytest.mark.asyncio
    async def test_verify_decision_anchor_success(
        self,
        governance_service,
        mock_client,
        sample_decision_id,
        sample_verify_anchor_response,
    ):
        """Test successful anchor verification."""
        mock_client.get.return_value = {"data": sample_verify_anchor_response}

        result = await governance_service.verify_decision_anchor(sample_decision_id)

        assert result["verified"] is True
        assert "anchor" in result
        assert "network" in result
        mock_client.get.assert_called_once_with(
            f"{GOVERNANCE_ENDPOINT}/decisions/{sample_decision_id}/verify"
        )

    @pytest.mark.asyncio
    async def test_verify_decision_anchor_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_decision_id,
        sample_verify_anchor_response,
    ):
        """Test anchor verification when response lacks 'data' wrapper."""
        mock_client.get.return_value = sample_verify_anchor_response

        result = await governance_service.verify_decision_anchor(sample_decision_id)

        assert result["verified"] is True


# =============================================================================
# Constitutional Validation Tests
# =============================================================================


class TestConstitutionalValidation:
    """Tests for constitutional validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_constitutional_success(
        self,
        governance_service,
        mock_client,
        sample_validate_constitutional_response,
    ):
        """Test successful constitutional validation."""
        mock_client.post.return_value = {"data": sample_validate_constitutional_response}

        result = await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="execute_command",
            context={"command": "safe_operation", "target": "data-001"},
        )

        assert result["valid"] is True
        assert len(result["violations"]) == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{GOVERNANCE_ENDPOINT}/constitutional/validate"

    @pytest.mark.asyncio
    async def test_validate_constitutional_includes_required_fields(
        self,
        governance_service,
        mock_client,
        sample_validate_constitutional_response,
    ):
        """Test that validation includes all required fields."""
        mock_client.post.return_value = {"data": sample_validate_constitutional_response}

        await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="execute_command",
            context={"command": "test"},
        )

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["agentId"] == "agent-001"
        assert json_payload["action"] == "execute_command"
        assert json_payload["context"] == {"command": "test"}
        assert json_payload["constitutionalHash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_validate_constitutional_with_metadata(
        self,
        governance_service,
        mock_client,
        sample_validate_constitutional_response,
    ):
        """Test constitutional validation with metadata."""
        mock_client.post.return_value = {"data": sample_validate_constitutional_response}

        metadata = {"source": "automated", "priority": "high"}
        await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="execute_command",
            context={"command": "test"},
            metadata=metadata,
        )

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_validate_constitutional_without_metadata(
        self,
        governance_service,
        mock_client,
        sample_validate_constitutional_response,
    ):
        """Test constitutional validation without metadata."""
        mock_client.post.return_value = {"data": sample_validate_constitutional_response}

        await governance_service.validate_constitutional(
            agent_id="agent-001",
            action="execute_command",
            context={"command": "test"},
        )

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["metadata"] is None


# =============================================================================
# Constitutional Principles Tests
# =============================================================================


class TestConstitutionalPrinciples:
    """Tests for constitutional principles retrieval."""

    @pytest.mark.asyncio
    async def test_get_constitutional_principles(
        self,
        governance_service,
        mock_client,
        sample_constitutional_principles,
    ):
        """Test retrieving constitutional principles."""
        mock_client.get.return_value = {"data": sample_constitutional_principles}

        result = await governance_service.get_constitutional_principles()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Transparency"
        mock_client.get.assert_called_once_with(f"{GOVERNANCE_ENDPOINT}/constitutional/principles")

    @pytest.mark.asyncio
    async def test_get_constitutional_principles_empty(
        self,
        governance_service,
        mock_client,
    ):
        """Test retrieving empty principles list."""
        mock_client.get.return_value = {"data": []}

        result = await governance_service.get_constitutional_principles()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_constitutional_principles_no_data_key(
        self,
        governance_service,
        mock_client,
    ):
        """Test retrieving principles when response lacks 'data' key."""
        mock_client.get.return_value = {}

        result = await governance_service.get_constitutional_principles()

        assert isinstance(result, list)
        assert len(result) == 0


# =============================================================================
# Metrics Tests
# =============================================================================


class TestMetrics:
    """Tests for metrics retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_metrics_default(
        self,
        governance_service,
        mock_client,
        sample_metrics_data,
    ):
        """Test retrieving metrics with default parameters."""
        mock_client.get.return_value = {"data": sample_metrics_data}

        result = await governance_service.get_metrics()

        assert result["totalRequests"] == 100
        assert result["approvalRate"] == 85.5
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[1]["params"] == {}

    @pytest.mark.asyncio
    async def test_get_metrics_with_date_range(
        self,
        governance_service,
        mock_client,
        sample_metrics_data,
    ):
        """Test retrieving metrics with date range filter."""
        mock_client.get.return_value = {"data": sample_metrics_data}

        await governance_service.get_metrics(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["startDate"] == "2024-01-01"
        assert params["endDate"] == "2024-01-31"

    @pytest.mark.asyncio
    async def test_get_metrics_with_policy_filter(
        self,
        governance_service,
        mock_client,
        sample_metrics_data,
    ):
        """Test retrieving metrics filtered by policy."""
        mock_client.get.return_value = {"data": sample_metrics_data}

        await governance_service.get_metrics(policy_id="policy-001")

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["policyId"] == "policy-001"

    @pytest.mark.asyncio
    async def test_get_metrics_with_all_filters(
        self,
        governance_service,
        mock_client,
        sample_metrics_data,
    ):
        """Test retrieving metrics with all filters."""
        mock_client.get.return_value = {"data": sample_metrics_data}

        await governance_service.get_metrics(
            start_date="2024-01-01",
            end_date="2024-01-31",
            policy_id="policy-001",
        )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["startDate"] == "2024-01-01"
        assert params["endDate"] == "2024-01-31"
        assert params["policyId"] == "policy-001"

    @pytest.mark.asyncio
    async def test_get_metrics_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_metrics_data,
    ):
        """Test retrieving metrics when response lacks 'data' wrapper."""
        mock_client.get.return_value = sample_metrics_data

        result = await governance_service.get_metrics()

        assert result["totalRequests"] == 100


# =============================================================================
# Dashboard Tests
# =============================================================================


class TestDashboard:
    """Tests for dashboard data retrieval."""

    @pytest.mark.asyncio
    async def test_get_dashboard(
        self,
        governance_service,
        mock_client,
        sample_dashboard_data,
    ):
        """Test retrieving dashboard data."""
        mock_client.get.return_value = {"data": sample_dashboard_data}

        result = await governance_service.get_dashboard()

        assert "overview" in result
        assert result["overview"]["totalPolicies"] == 25
        assert result["overview"]["complianceScore"] == 92.5
        mock_client.get.assert_called_once_with(f"{GOVERNANCE_ENDPOINT}/dashboard")

    @pytest.mark.asyncio
    async def test_get_dashboard_without_data_wrapper(
        self,
        governance_service,
        mock_client,
        sample_dashboard_data,
    ):
        """Test retrieving dashboard when response lacks 'data' wrapper."""
        mock_client.get.return_value = sample_dashboard_data

        result = await governance_service.get_dashboard()

        assert "overview" in result


# =============================================================================
# Service Initialization Tests
# =============================================================================


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_service_initialization(self, mock_client):
        """Test GovernanceService initialization."""
        service = GovernanceService(mock_client)

        assert service._client == mock_client
        assert service._base_path == GOVERNANCE_ENDPOINT

    def test_service_base_path(self, governance_service):
        """Test that service uses correct base path."""
        assert governance_service._base_path == "/api/v1/governance"


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


@pytest.mark.constitutional
class TestConstitutionalCompliance:
    """Tests for constitutional compliance features."""

    @pytest.mark.asyncio
    async def test_all_requests_include_constitutional_hash(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test that all POST requests include constitutional hash."""
        mock_client.post.return_value = {"data": sample_approval_request_data}

        request = CreateApprovalRequest(
            request_type="test",
            payload={"test": True},
        )
        await governance_service.create_approval_request(request)

        call_args = mock_client.post.call_args
        json_payload = call_args[1]["json"]
        assert json_payload["constitutionalHash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_response_models_include_constitutional_hash(
        self,
        governance_service,
        mock_client,
        sample_approval_request_data,
    ):
        """Test that response models include constitutional hash."""
        mock_client.get.return_value = {"data": sample_approval_request_data}

        result = await governance_service.get_approval_request("test-id")

        assert result.constitutional_hash == CONSTITUTIONAL_HASH
