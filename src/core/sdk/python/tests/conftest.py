"""
ACGS-2 SDK Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

Shared fixtures and test configuration for SDK tests.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from acgs2_sdk.config import ACGS2Config, RetryConfig
from acgs2_sdk.constants import CONSTITUTIONAL_HASH
from acgs2_sdk.services.governance import GovernanceService

# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def constitutional_hash():
    """Return constitutional hash constant."""
    return CONSTITUTIONAL_HASH


@pytest.fixture
def retry_config():
    """Create retry configuration for tests."""
    return RetryConfig(
        max_attempts=1,  # Disable retries for faster tests
        base_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter=False,
    )


@pytest.fixture
def client_config(retry_config):
    """Create client configuration for tests."""
    return ACGS2Config(
        base_url="http://test-api.example.com",
        api_key="test-api-key",
        tenant_id="test-tenant",
        timeout=5.0,
        retry=retry_config,
        validate_constitutional_hash=True,
    )


# =============================================================================
# Mock Client Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create a mock ACGS2Client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def governance_service(mock_client):
    """Create GovernanceService with mock client."""
    return GovernanceService(mock_client)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_approval_request_id():
    """Generate a sample approval request ID."""
    return str(uuid4())


@pytest.fixture
def sample_decision_id():
    """Generate a sample decision ID."""
    return str(uuid4())


@pytest.fixture
def sample_approval_request_data(sample_approval_request_id, constitutional_hash):
    """Create sample approval request data."""
    return {
        "id": sample_approval_request_id,
        "requestType": "policy_change",
        "requesterId": "user-001",
        "status": "pending",
        "riskScore": 65.5,
        "requiredApprovers": 2,
        "currentApprovals": 1,
        "decisions": [
            {
                "approverId": "reviewer-001",
                "decision": "approved",
                "reasoning": "Looks good",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ],
        "payload": {"policyId": "policy-001", "changes": {"version": "2.0.0"}},
        "createdAt": datetime.now(UTC).isoformat(),
        "expiresAt": None,
        "constitutionalHash": constitutional_hash,
    }


@pytest.fixture
def sample_governance_decision_data(
    sample_decision_id, sample_approval_request_id, constitutional_hash
):
    """Create sample governance decision data."""
    return {
        "id": sample_decision_id,
        "requestId": sample_approval_request_id,
        "decision": "approve",
        "reasoning": "All criteria met",
        "policyViolations": [],
        "riskScore": 25.0,
        "reviewerIds": ["reviewer-001", "reviewer-002"],
        "timestamp": datetime.now(UTC).isoformat(),
        "blockchainAnchor": "0x1234567890abcdef",
        "constitutionalHash": constitutional_hash,
    }


@pytest.fixture
def sample_create_approval_request():
    """Create sample create approval request payload."""
    from acgs2_sdk.models import CreateApprovalRequest

    return CreateApprovalRequest(
        request_type="policy_change",
        payload={"policyId": "policy-001", "changes": {"version": "2.0.0"}},
        risk_score=65.5,
        required_approvers=2,
    )


@pytest.fixture
def sample_submit_decision():
    """Create sample submit decision payload."""
    from acgs2_sdk.models import SubmitApprovalDecision

    return SubmitApprovalDecision(
        decision="approve",
        reasoning="All criteria met after thorough review",
    )


@pytest.fixture
def sample_paginated_response(sample_approval_request_data):
    """Create sample paginated response."""
    return {
        "data": {
            "data": [sample_approval_request_data],
            "total": 1,
            "page": 1,
            "pageSize": 50,
            "totalPages": 1,
        }
    }


@pytest.fixture
def sample_empty_paginated_response():
    """Create sample empty paginated response."""
    return {
        "data": {
            "data": [],
            "total": 0,
            "page": 1,
            "pageSize": 50,
            "totalPages": 0,
        }
    }


@pytest.fixture
def sample_constitutional_principles():
    """Create sample constitutional principles."""
    return [
        {
            "id": "principle-001",
            "name": "Transparency",
            "description": "All decisions must be auditable",
            "priority": 1,
        },
        {
            "id": "principle-002",
            "name": "Human Oversight",
            "description": "Critical decisions require human approval",
            "priority": 2,
        },
    ]


@pytest.fixture
def sample_metrics_data():
    """Create sample metrics data."""
    return {
        "totalRequests": 100,
        "approvalRate": 85.5,
        "averageDecisionTime": 3600,
        "pendingRequests": 5,
        "escalatedRequests": 2,
        "byPolicyId": {
            "policy-001": {"approved": 45, "rejected": 5, "pending": 3},
            "policy-002": {"approved": 38, "rejected": 7, "pending": 2},
        },
    }


@pytest.fixture
def sample_dashboard_data():
    """Create sample dashboard data."""
    return {
        "overview": {
            "totalPolicies": 25,
            "activePolicies": 20,
            "pendingApprovals": 5,
            "complianceScore": 92.5,
        },
        "recentActivity": [
            {
                "type": "approval",
                "requestId": "req-001",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "type": "policy_update",
                "policyId": "policy-001",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ],
        "alerts": [],
    }


@pytest.fixture
def sample_verify_anchor_response():
    """Create sample verify anchor response."""
    return {
        "verified": True,
        "anchor": "0x1234567890abcdef",
        "network": "solana-devnet",
        "timestamp": datetime.now(UTC).isoformat(),
        "blockHeight": 12345678,
    }


@pytest.fixture
def sample_validate_constitutional_response():
    """Create sample constitutional validation response."""
    return {
        "valid": True,
        "violations": [],
        "recommendations": [],
        "constitutionalHash": CONSTITUTIONAL_HASH,
    }
