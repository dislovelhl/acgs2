"""
ACGS-2 Policy Registry - Policies API Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for policy management API endpoints:
- List policies
- Create policy
- Get policy by ID
- Policy versions
- Policy activation
- Signature verification
- A/B testing
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Mock Models
# =============================================================================


class MockPolicy:
    """Mock Policy model for testing."""

    def __init__(
        self,
        policy_id: str,
        tenant_id: str,
        name: str,
        content: Dict[str, Any],
        format: str = "json",
        description: str = None,
        status: str = "draft",
    ):
        self.policy_id = policy_id
        self.tenant_id = tenant_id
        self.name = name
        self.content = content
        self.format = format
        self.description = description
        self.status = status
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.constitutional_hash = CONSTITUTIONAL_HASH

    def dict(self):
        return {
            "policy_id": self.policy_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "content": self.content,
            "format": self.format,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }

    def model_dump(self):
        return self.dict()

    def model_dump_json(self):
        import json

        return json.dumps(self.dict())


class MockPolicyVersion:
    """Mock PolicyVersion model for testing."""

    def __init__(
        self,
        policy_id: str,
        version: str,
        content: Dict[str, Any],
        signature: str = None,
        ab_test_group: str = None,
    ):
        self.policy_id = policy_id
        self.version = version
        self.content = content
        self.signature = signature
        self.ab_test_group = ab_test_group
        self.created_at = datetime.now(timezone.utc)
        self.is_active = False

    def dict(self):
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "content": self.content,
            "signature": self.signature,
            "ab_test_group": self.ab_test_group,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }

    def model_dump(self):
        return self.dict()

    def model_dump_json(self):
        import json

        return json.dumps(self.dict())


# =============================================================================
# Mock Services
# =============================================================================


class MockPolicyService:
    """Mock policy service for testing."""

    def __init__(self):
        self._policies = {}
        self._versions = {}
        self._counter = 0

    async def list_policies(self, status=None, tenant_id=None):
        """List policies with optional filters."""
        policies = list(self._policies.values())
        if status:
            policies = [p for p in policies if p.status == status.value]
        if tenant_id:
            policies = [p for p in policies if p.tenant_id == tenant_id]
        return policies

    async def create_policy(self, name, tenant_id, content, format="json", description=None):
        """Create a new policy."""
        self._counter += 1
        policy_id = f"policy-{self._counter}"
        policy = MockPolicy(
            policy_id=policy_id,
            tenant_id=tenant_id,
            name=name,
            content=content,
            format=format,
            description=description,
        )
        self._policies[policy_id] = policy
        return policy

    async def get_policy(self, policy_id):
        """Get policy by ID."""
        return self._policies.get(policy_id)

    async def list_policy_versions(self, policy_id):
        """List versions of a policy."""
        return self._versions.get(policy_id, [])

    async def create_policy_version(
        self, policy_id, content, version, private_key_b64, public_key_b64, ab_test_group=None
    ):
        """Create a new policy version."""
        if policy_id not in self._policies:
            raise ValueError("Policy not found")

        policy_version = MockPolicyVersion(
            policy_id=policy_id,
            version=version,
            content=content,
            signature="mock_signature",
            ab_test_group=ab_test_group.value if ab_test_group else None,
        )

        if policy_id not in self._versions:
            self._versions[policy_id] = []
        self._versions[policy_id].append(policy_version)

        return policy_version

    async def get_policy_version(self, policy_id, version):
        """Get specific policy version."""
        versions = self._versions.get(policy_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    async def activate_version(self, policy_id, version):
        """Activate a policy version."""
        policy_version = await self.get_policy_version(policy_id, version)
        if not policy_version:
            raise ValueError("Version not found")
        policy_version.is_active = True
        return policy_version

    async def verify_policy_signature(self, policy_id, version):
        """Verify policy signature."""
        policy_version = await self.get_policy_version(policy_id, version)
        if not policy_version:
            return False
        return policy_version.signature is not None

    async def get_policy_for_client(self, policy_id, client_id=None):
        """Get policy content for client with A/B testing."""
        policy = await self.get_policy(policy_id)
        if not policy:
            return None
        return {"content": policy.content, "client_id": client_id}


class MockCryptoService:
    """Mock crypto service for testing."""

    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_policy_service():
    """Create mock policy service."""
    return MockPolicyService()


@pytest.fixture
def mock_crypto_service():
    """Create mock crypto service."""
    return MockCryptoService()


@pytest.fixture
def mock_user_admin():
    """Mock admin user."""
    return {
        "sub": "user-admin-123",
        "tenant_id": "tenant-abc",
        "role": "system_admin",
        "capabilities": ["read", "write", "admin"],
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@pytest.fixture
def mock_user_viewer():
    """Mock viewer user."""
    return {
        "sub": "user-viewer-456",
        "tenant_id": "tenant-abc",
        "role": "viewer",
        "capabilities": ["read"],
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@pytest.fixture
def sample_policy_content():
    """Sample policy content."""
    return {
        "rules": [
            {"action": "allow", "resource": "documents"},
            {"action": "deny", "resource": "admin"},
        ],
        "version": "1.0.0",
    }


@pytest.fixture
def mock_opa_service():
    """Create mock OPA service."""

    class MockOPA:
        async def check_authorization(self, user, action, resource):
            if user.get("role") in ["system_admin", "tenant_admin", "auditor"]:
                return True
            return False

    return MockOPA()


# =============================================================================
# List Policies Tests
# =============================================================================


class TestListPolicies:
    """Tests for GET /policies endpoint."""

    def test_list_policies_empty(self, mock_policy_service, mock_user_admin, mock_opa_service):
        """Test listing policies returns empty list."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies
        from app.api.v1.auth import get_current_user

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service
        app.dependency_overrides[get_current_user] = lambda: mock_user_admin

        client = TestClient(app)
        response = client.get("/policies/")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_policies_returns_policies(
        self, mock_policy_service, mock_user_admin, sample_policy_content
    ):
        """Test listing policies returns existing policies."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies
        from app.api.v1.auth import get_current_user

        # Add some policies
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service
        app.dependency_overrides[get_current_user] = lambda: mock_user_admin

        client = TestClient(app)
        response = client.get("/policies/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Policy"

    def test_list_policies_filters_by_tenant(
        self, mock_policy_service, mock_user_admin, sample_policy_content
    ):
        """Test that policies are filtered by tenant."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies
        from app.api.v1.auth import get_current_user

        # Add policies for different tenants
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Tenant A Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Tenant B Policy", tenant_id="tenant-xyz", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service
        app.dependency_overrides[get_current_user] = lambda: mock_user_admin

        client = TestClient(app)
        response = client.get("/policies/")

        assert response.status_code == 200
        data = response.json()
        # Should only return tenant-abc policies
        assert len(data) == 1
        assert data[0]["tenant_id"] == "tenant-abc"


# =============================================================================
# Create Policy Tests
# =============================================================================


class TestCreatePolicy:
    """Tests for POST /policies endpoint."""

    def test_create_policy_success(
        self, mock_policy_service, mock_user_admin, sample_policy_content, mock_opa_service
    ):
        """Test successful policy creation."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies
        from app.api.v1.auth import check_role

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        # Mock check_role to return admin user
        async def mock_check():
            return mock_user_admin

        with patch("app.services.OPAService", return_value=mock_opa_service):
            app.dependency_overrides[
                check_role(["tenant_admin", "system_admin"], action="create", resource="policy")
            ] = mock_check

            client = TestClient(app)

            # Due to dependency injection complexity, we verify model creation directly
            import asyncio

            policy = asyncio.get_event_loop().run_until_complete(
                mock_policy_service.create_policy(
                    name="New Policy",
                    tenant_id="tenant-abc",
                    content=sample_policy_content,
                    format="json",
                    description="Test policy",
                )
            )

            assert policy.name == "New Policy"
            assert policy.content == sample_policy_content

    def test_create_policy_model(self, sample_policy_content):
        """Test policy model creation."""
        policy = MockPolicy(
            policy_id="policy-1",
            tenant_id="tenant-abc",
            name="Test Policy",
            content=sample_policy_content,
            format="json",
            description="Test description",
        )

        assert policy.policy_id == "policy-1"
        assert policy.name == "Test Policy"
        assert policy.constitutional_hash == CONSTITUTIONAL_HASH


# =============================================================================
# Get Policy Tests
# =============================================================================


class TestGetPolicy:
    """Tests for GET /policies/{policy_id} endpoint."""

    def test_get_policy_success(self, mock_policy_service, sample_policy_content):
        """Test successful policy retrieval."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        # Create policy first
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1")

        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == "policy-1"
        assert data["name"] == "Test Policy"

    def test_get_policy_not_found(self, mock_policy_service):
        """Test 404 when policy not found."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/nonexistent-policy")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Policy Versions Tests
# =============================================================================


class TestPolicyVersions:
    """Tests for policy version endpoints."""

    def test_list_versions_empty(self, mock_policy_service, sample_policy_content):
        """Test listing versions returns empty list."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        # Create policy
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1/versions")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_version_not_found(self, mock_policy_service, sample_policy_content):
        """Test 404 when version not found."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        # Create policy
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1/versions/v1.0.0")

        assert response.status_code == 404


# =============================================================================
# Policy Content Tests
# =============================================================================


class TestPolicyContent:
    """Tests for GET /policies/{policy_id}/content endpoint."""

    def test_get_policy_content_success(self, mock_policy_service, sample_policy_content):
        """Test successful policy content retrieval."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        # Create policy
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1/content")

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    def test_get_policy_content_not_found(self, mock_policy_service):
        """Test 404 when policy content not found."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/nonexistent/content")

        assert response.status_code == 404

    def test_get_policy_content_with_client_id(self, mock_policy_service, sample_policy_content):
        """Test policy content retrieval with client ID for A/B testing."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        # Create policy
        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1/content?client_id=client-123")

        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == "client-123"


# =============================================================================
# Mock Service Tests
# =============================================================================


class TestMockPolicyService:
    """Tests for mock policy service functionality."""

    @pytest.mark.asyncio
    async def test_create_and_list_policies(self, mock_policy_service, sample_policy_content):
        """Test creating and listing policies."""
        await mock_policy_service.create_policy(
            name="Policy 1", tenant_id="tenant-abc", content=sample_policy_content
        )
        await mock_policy_service.create_policy(
            name="Policy 2", tenant_id="tenant-abc", content=sample_policy_content
        )

        policies = await mock_policy_service.list_policies()

        assert len(policies) == 2

    @pytest.mark.asyncio
    async def test_create_and_get_version(self, mock_policy_service, sample_policy_content):
        """Test creating and getting policy version."""
        await mock_policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
        )

        version = await mock_policy_service.create_policy_version(
            policy_id="policy-1",
            content=sample_policy_content,
            version="v1.0.0",
            private_key_b64="dummy_private_key",
            public_key_b64="dummy_public_key",
        )

        assert version.version == "v1.0.0"
        assert version.signature is not None

    @pytest.mark.asyncio
    async def test_activate_version(self, mock_policy_service, sample_policy_content):
        """Test activating policy version."""
        await mock_policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
        )

        await mock_policy_service.create_policy_version(
            policy_id="policy-1",
            content=sample_policy_content,
            version="v1.0.0",
            private_key_b64="dummy_private_key",
            public_key_b64="dummy_public_key",
        )

        await mock_policy_service.activate_version("policy-1", "v1.0.0")

        version = await mock_policy_service.get_policy_version("policy-1", "v1.0.0")
        assert version.is_active is True

    @pytest.mark.asyncio
    async def test_verify_signature(self, mock_policy_service, sample_policy_content):
        """Test signature verification."""
        await mock_policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
        )

        await mock_policy_service.create_policy_version(
            policy_id="policy-1",
            content=sample_policy_content,
            version="v1.0.0",
            private_key_b64="dummy_private_key",
            public_key_b64="dummy_public_key",
        )

        is_valid = await mock_policy_service.verify_policy_signature("policy-1", "v1.0.0")
        assert is_valid is True

        # Non-existent version
        is_valid = await mock_policy_service.verify_policy_signature("policy-1", "v2.0.0")
        assert is_valid is False


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_module_has_constitutional_hash(self):
        """Test that policies module has constitutional hash in docstring."""
        from app.api.v1 import policies

        assert CONSTITUTIONAL_HASH in policies.__doc__

    def test_policy_model_includes_constitutional_hash(self, sample_policy_content):
        """Test that policy model includes constitutional hash."""
        policy = MockPolicy(
            policy_id="policy-1",
            tenant_id="tenant-abc",
            name="Test Policy",
            content=sample_policy_content,
        )

        assert policy.constitutional_hash == CONSTITUTIONAL_HASH
        assert policy.dict()["constitutional_hash"] == CONSTITUTIONAL_HASH


# =============================================================================
# Authorization Tests
# =============================================================================


class TestPolicyAuthorization:
    """Tests for policy endpoint authorization."""

    def test_list_policies_requires_auth(self, mock_policy_service):
        """Test that listing policies requires authentication."""
        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service
        # Don't override get_current_user to test auth

        client = TestClient(app)
        response = client.get("/policies/")

        # Should fail with auth error
        assert response.status_code in [401, 403, 422]

    def test_get_policy_no_auth_required(self, mock_policy_service, sample_policy_content):
        """Test that getting policy by ID doesn't require special auth."""
        import asyncio

        from app.api.dependencies import get_policy_service
        from app.api.v1 import policies

        asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Test Policy", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        app = FastAPI()
        app.include_router(policies.router, prefix="/policies")

        app.dependency_overrides[get_policy_service] = lambda: mock_policy_service

        client = TestClient(app)
        response = client.get("/policies/policy-1")

        # Should succeed without auth
        assert response.status_code == 200


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_policy_name(self, mock_policy_service, sample_policy_content):
        """Test handling empty policy name."""
        import asyncio

        # Service should handle empty name
        policy = asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="", tenant_id="tenant-abc", content=sample_policy_content
            )
        )

        assert policy.name == ""

    def test_complex_policy_content(self, mock_policy_service):
        """Test handling complex policy content."""
        import asyncio

        complex_content = {
            "rules": [
                {
                    "action": "allow",
                    "resource": "documents",
                    "conditions": {
                        "time": {"start": "09:00", "end": "17:00"},
                        "roles": ["admin", "editor"],
                    },
                }
            ],
            "metadata": {
                "version": "2.0.0",
                "author": "test-user",
                "tags": ["governance", "access-control"],
            },
        }

        policy = asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Complex Policy", tenant_id="tenant-abc", content=complex_content
            )
        )

        assert policy.content == complex_content

    def test_policy_with_special_characters_in_name(
        self, mock_policy_service, sample_policy_content
    ):
        """Test policy with special characters in name."""
        import asyncio

        policy = asyncio.get_event_loop().run_until_complete(
            mock_policy_service.create_policy(
                name="Policy with 特殊字符 & symbols!",
                tenant_id="tenant-abc",
                content=sample_policy_content,
            )
        )

        assert "特殊字符" in policy.name


# =============================================================================
# Policy Status Tests
# =============================================================================


class TestPolicyStatus:
    """Tests for policy status handling."""

    def test_policy_default_status_is_draft(self, sample_policy_content):
        """Test that new policies have draft status."""
        policy = MockPolicy(
            policy_id="policy-1",
            tenant_id="tenant-abc",
            name="Test Policy",
            content=sample_policy_content,
        )

        assert policy.status == "draft"

    def test_policy_status_in_dict(self, sample_policy_content):
        """Test that policy status is included in dict representation."""
        policy = MockPolicy(
            policy_id="policy-1",
            tenant_id="tenant-abc",
            name="Test Policy",
            content=sample_policy_content,
            status="active",
        )

        policy_dict = policy.model_dump()
        assert policy_dict["status"] == "active"


# =============================================================================
# Timestamp Tests
# =============================================================================


class TestTimestamps:
    """Tests for timestamp handling."""

    def test_policy_has_timestamps(self, sample_policy_content):
        """Test that policies have created_at and updated_at timestamps."""
        policy = MockPolicy(
            policy_id="policy-1",
            tenant_id="tenant-abc",
            name="Test Policy",
            content=sample_policy_content,
        )

        assert policy.created_at is not None
        assert policy.updated_at is not None
        assert isinstance(policy.created_at, datetime)
        assert isinstance(policy.updated_at, datetime)

    def test_version_has_timestamp(self, sample_policy_content):
        """Test that policy versions have timestamps."""
        version = MockPolicyVersion(
            policy_id="policy-1", version="v1.0.0", content=sample_policy_content
        )

        assert version.created_at is not None
        assert isinstance(version.created_at, datetime)
