"""
ACGS-2 Policy Registry - Policy Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for PolicyService including:
- Policy creation and management
- Version creation and activation
- Signature verification
- Caching behavior
- A/B testing support
- Error handling and edge cases
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models import ABTestGroup, PolicySignature, PolicyStatus, VersionStatus
from app.services.policy_service import PolicyService

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_crypto_service():
    """Create mock crypto service."""
    mock = MagicMock()

    # Mock signature creation
    mock.create_policy_signature = MagicMock(
        return_value=PolicySignature(
            policy_id="test-policy",
            version="1.0.0",
            signature="test-signature-base64",
            public_key="test-public-key-base64",
            algorithm="ed25519",
            key_fingerprint="test-fingerprint",
            signed_at=datetime.now(timezone.utc),
        )
    )

    # Mock signature verification
    mock.verify_policy_signature = MagicMock(return_value=True)

    return mock


@pytest.fixture
def mock_cache_service():
    """Create mock cache service."""
    mock = AsyncMock()
    mock.cache_store = {}

    async def mock_get(key):
        return mock.cache_store.get(key)

    async def mock_set(key, value, ttl=None):
        mock.cache_store[key] = value

    async def mock_delete(key):
        mock.cache_store.pop(key, None)

    async def mock_get_policy(policy_id, version):
        key = f"policy:{policy_id}:{version}"
        return mock.cache_store.get(key)

    async def mock_set_policy(policy_id, version, data):
        key = f"policy:{policy_id}:{version}"
        mock.cache_store[key] = data

    async def mock_set_public_key(fingerprint, key):
        mock.cache_store[f"pubkey:{fingerprint}"] = key

    async def mock_invalidate_policy(policy_id):
        keys_to_delete = [k for k in mock.cache_store.keys() if f"policy:{policy_id}" in k]
        for k in keys_to_delete:
            mock.cache_store.pop(k, None)

    mock.get = mock_get
    mock.set = mock_set
    mock.delete = mock_delete
    mock.get_policy = mock_get_policy
    mock.set_policy = mock_set_policy
    mock.set_public_key = mock_set_public_key
    mock.invalidate_policy = mock_invalidate_policy

    return mock


@pytest.fixture
def mock_notification_service():
    """Create mock notification service."""
    mock = AsyncMock()
    mock.notifications = []

    async def mock_notify(policy_id, version, event, data=None):
        mock.notifications.append(
            {
                "policy_id": policy_id,
                "version": version,
                "event": event,
                "data": data,
            }
        )

    mock.notify_policy_update = mock_notify
    return mock


@pytest.fixture
def mock_audit_client():
    """Create mock audit client."""
    mock = AsyncMock()
    mock.records = []

    async def mock_report(record):
        mock.records.append(record)

    mock.report_validation = mock_report
    return mock


@pytest.fixture
def policy_service(
    mock_crypto_service, mock_cache_service, mock_notification_service, mock_audit_client
):
    """Create PolicyService instance with all mock dependencies."""
    return PolicyService(
        crypto_service=mock_crypto_service,
        cache_service=mock_cache_service,
        notification_service=mock_notification_service,
        audit_client=mock_audit_client,
    )


@pytest.fixture
def sample_policy_content() -> Dict[str, Any]:
    """Sample policy content for tests."""
    return {
        "policy_id": "test-policy-001",
        "name": "Test Constitutional Policy",
        "version": "1.0.0",
        "rules": [
            {"id": "rule-1", "action": "allow", "resource": "governance/*"},
            {"id": "rule-2", "action": "deny", "resource": "admin/*"},
        ],
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@pytest.fixture
def sample_keys():
    """Sample key pair for signing tests."""
    return {
        "private_key": "dGVzdC1wcml2YXRlLWtleS1iYXNlNjQ=",  # base64 encoded
        "public_key": "dGVzdC1wdWJsaWMta2V5LWJhc2U2NA==",  # base64 encoded
    }


# =============================================================================
# Policy Creation Tests
# =============================================================================


class TestPolicyCreation:
    """Tests for policy creation functionality."""

    @pytest.mark.asyncio
    async def test_create_policy_basic(self, policy_service):
        """Test basic policy creation."""
        policy = await policy_service.create_policy(
            name="Test Policy",
            tenant_id="tenant-001",
            content={"rule": "test"},
            description="A test policy",
        )

        assert policy is not None
        assert policy.name == "Test Policy"
        assert policy.tenant_id == "tenant-001"
        assert policy.description == "A test policy"
        assert policy.status == PolicyStatus.DRAFT
        assert policy.format == "json"
        assert policy.policy_id is not None

    @pytest.mark.asyncio
    async def test_create_policy_with_yaml_format(self, policy_service):
        """Test policy creation with YAML format."""
        policy = await policy_service.create_policy(
            name="YAML Policy",
            tenant_id="tenant-001",
            content={"rule": "test"},
            format="yaml",
        )

        assert policy.format == "yaml"

    @pytest.mark.asyncio
    async def test_create_policy_initializes_versions_list(self, policy_service):
        """Test that creating a policy initializes empty versions list."""
        policy = await policy_service.create_policy(
            name="Test Policy",
            tenant_id="tenant-001",
            content={},
        )

        versions = await policy_service.list_policy_versions(policy.policy_id)
        assert versions == []

    @pytest.mark.asyncio
    async def test_create_multiple_policies(self, policy_service):
        """Test creating multiple policies."""
        policy1 = await policy_service.create_policy(
            name="Policy 1", tenant_id="tenant-001", content={}
        )
        policy2 = await policy_service.create_policy(
            name="Policy 2", tenant_id="tenant-001", content={}
        )

        assert policy1.policy_id != policy2.policy_id

        policies = await policy_service.list_policies()
        assert len(policies) == 2


# =============================================================================
# Policy Version Tests
# =============================================================================


class TestPolicyVersionCreation:
    """Tests for policy version creation functionality."""

    @pytest.mark.asyncio
    async def test_create_policy_version(self, policy_service, sample_policy_content, sample_keys):
        """Test creating a policy version."""
        # First create a policy
        policy = await policy_service.create_policy(
            name="Test Policy",
            tenant_id="tenant-001",
            content=sample_policy_content,
        )

        # Create a version
        version = await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        assert version is not None
        assert version.policy_id == policy.policy_id
        assert version.version == "1.0.0"
        assert version.content == sample_policy_content
        assert version.content_hash is not None
        assert version.status == VersionStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_version_generates_correct_hash(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that version creation generates correct content hash."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        version = await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        # Calculate expected hash
        content_str = json.dumps(sample_policy_content, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

        assert version.content_hash == expected_hash

    @pytest.mark.asyncio
    async def test_create_version_caches_policy(
        self, policy_service, mock_cache_service, sample_policy_content, sample_keys
    ):
        """Test that version creation caches the policy."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        # Verify cache was populated
        cache_key = f"policy:{policy.policy_id}:1.0.0"
        assert cache_key in mock_cache_service.cache_store

    @pytest.mark.asyncio
    async def test_create_version_sends_notification(
        self, policy_service, mock_notification_service, sample_policy_content, sample_keys
    ):
        """Test that version creation sends notification."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        # Verify notification was sent
        assert len(mock_notification_service.notifications) == 1
        notification = mock_notification_service.notifications[0]
        assert notification["event"] == "version_created"
        assert notification["policy_id"] == policy.policy_id
        assert notification["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_create_version_for_nonexistent_policy_fails(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that creating version for nonexistent policy fails."""
        with pytest.raises(ValueError, match="Policy .* not found"):
            await policy_service.create_policy_version(
                policy_id="nonexistent-policy",
                content=sample_policy_content,
                version="1.0.0",
                private_key_b64=sample_keys["private_key"],
                public_key_b64=sample_keys["public_key"],
            )

    @pytest.mark.asyncio
    async def test_create_version_with_ab_test_group(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test creating a version with A/B test group."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        version = await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
            ab_test_group=ABTestGroup.A,
        )

        assert version.ab_test_group == ABTestGroup.A


# =============================================================================
# Policy Retrieval Tests
# =============================================================================


class TestPolicyRetrieval:
    """Tests for policy retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_policy(self, policy_service):
        """Test retrieving a policy by ID."""
        created_policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        retrieved_policy = await policy_service.get_policy(created_policy.policy_id)

        assert retrieved_policy is not None
        assert retrieved_policy.policy_id == created_policy.policy_id
        assert retrieved_policy.name == "Test Policy"

    @pytest.mark.asyncio
    async def test_get_nonexistent_policy_returns_none(self, policy_service):
        """Test retrieving a nonexistent policy returns None."""
        result = await policy_service.get_policy("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_policy_version(self, policy_service, sample_policy_content, sample_keys):
        """Test retrieving a specific policy version."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        retrieved_version = await policy_service.get_policy_version(policy.policy_id, "1.0.0")

        assert retrieved_version is not None
        assert retrieved_version.version == "1.0.0"
        assert retrieved_version.content == sample_policy_content

    @pytest.mark.asyncio
    async def test_get_nonexistent_version_returns_none(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test retrieving a nonexistent version returns None."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        result = await policy_service.get_policy_version(policy.policy_id, "99.0.0")
        assert result is None


# =============================================================================
# Version Activation Tests
# =============================================================================


class TestVersionActivation:
    """Tests for policy version activation functionality."""

    @pytest.mark.asyncio
    async def test_activate_version(self, policy_service, sample_policy_content, sample_keys):
        """Test activating a policy version."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        await policy_service.activate_version(policy.policy_id, "1.0.0")

        version = await policy_service.get_policy_version(policy.policy_id, "1.0.0")
        assert version.status == VersionStatus.ACTIVE
        assert version.is_active is True

    @pytest.mark.asyncio
    async def test_activate_version_retires_previous(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that activating a version retires the previous active version."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        # Create and activate v1
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "1.0.0")

        # Create and activate v2
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content={"updated": True},
            version="2.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "2.0.0")

        # Check v1 is retired
        v1 = await policy_service.get_policy_version(policy.policy_id, "1.0.0")
        assert v1.status == VersionStatus.RETIRED

        # Check v2 is active
        v2 = await policy_service.get_policy_version(policy.policy_id, "2.0.0")
        assert v2.status == VersionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_version_invalidates_cache(
        self, policy_service, mock_cache_service, sample_policy_content, sample_keys
    ):
        """Test that activating a version invalidates cache."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        # Set active version cache
        mock_cache_service.cache_store[f"active_version:{policy.policy_id}"] = {"version": "old"}

        await policy_service.activate_version(policy.policy_id, "1.0.0")

        # Verify cache was invalidated
        assert f"active_version:{policy.policy_id}" not in mock_cache_service.cache_store

    @pytest.mark.asyncio
    async def test_activate_nonexistent_version_fails(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that activating a nonexistent version fails."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        with pytest.raises(ValueError, match="Version .* not found"):
            await policy_service.activate_version(policy.policy_id, "99.0.0")

    @pytest.mark.asyncio
    async def test_activate_version_for_nonexistent_policy_fails(self, policy_service):
        """Test that activating version for nonexistent policy fails."""
        with pytest.raises(ValueError, match="Policy .* not found"):
            await policy_service.activate_version("nonexistent-policy", "1.0.0")


# =============================================================================
# Active Version Retrieval Tests
# =============================================================================


class TestActiveVersionRetrieval:
    """Tests for getting active policy version."""

    @pytest.mark.asyncio
    async def test_get_active_version(self, policy_service, sample_policy_content, sample_keys):
        """Test getting the active version of a policy."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "1.0.0")

        active = await policy_service.get_active_version(policy.policy_id)

        assert active is not None
        assert active.version == "1.0.0"
        assert active.is_active is True

    @pytest.mark.asyncio
    async def test_get_active_version_uses_cache(
        self, policy_service, mock_cache_service, sample_policy_content, sample_keys
    ):
        """Test that get_active_version uses cache."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "1.0.0")

        # Set cache entry
        mock_cache_service.cache_store[f"active_version:{policy.policy_id}"] = {"version": "1.0.0"}

        # Get active version - should use cache
        active = await policy_service.get_active_version(policy.policy_id)

        assert active is not None
        assert active.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_active_version_returns_none_when_no_active(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that get_active_version returns None when no version is active."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        # Create version but don't activate
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        active = await policy_service.get_active_version(policy.policy_id)
        assert active is None


# =============================================================================
# Signature Verification Tests
# =============================================================================


class TestSignatureVerification:
    """Tests for policy signature verification."""

    @pytest.mark.asyncio
    async def test_verify_policy_signature_valid(
        self, policy_service, mock_crypto_service, sample_policy_content, sample_keys
    ):
        """Test verifying a valid policy signature."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        mock_crypto_service.verify_policy_signature.return_value = True

        is_valid = await policy_service.verify_policy_signature(policy.policy_id, "1.0.0")

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_policy_signature_invalid(
        self, policy_service, mock_crypto_service, sample_policy_content, sample_keys
    ):
        """Test verifying an invalid policy signature."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        mock_crypto_service.verify_policy_signature.return_value = False

        is_valid = await policy_service.verify_policy_signature(policy.policy_id, "1.0.0")

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_nonexistent_signature_returns_false(self, policy_service):
        """Test that verifying nonexistent signature returns False."""
        is_valid = await policy_service.verify_policy_signature("nonexistent-policy", "1.0.0")
        assert is_valid is False


# =============================================================================
# Policy Listing Tests
# =============================================================================


class TestPolicyListing:
    """Tests for policy listing functionality."""

    @pytest.mark.asyncio
    async def test_list_policies(self, policy_service):
        """Test listing all policies."""
        await policy_service.create_policy(name="Policy 1", tenant_id="tenant-001", content={})
        await policy_service.create_policy(name="Policy 2", tenant_id="tenant-002", content={})

        policies = await policy_service.list_policies()

        assert len(policies) == 2
        names = {p.name for p in policies}
        assert names == {"Policy 1", "Policy 2"}

    @pytest.mark.asyncio
    async def test_list_policies_with_status_filter(self, policy_service):
        """Test listing policies with status filter."""
        await policy_service.create_policy(name="Draft Policy", tenant_id="tenant-001", content={})
        policy2 = await policy_service.create_policy(
            name="Active Policy", tenant_id="tenant-001", content={}
        )

        # Manually set status (in real scenario, this would be through business logic)
        policy_service._policies[policy2.policy_id].status = PolicyStatus.ACTIVE

        draft_policies = await policy_service.list_policies(status=PolicyStatus.DRAFT)
        active_policies = await policy_service.list_policies(status=PolicyStatus.ACTIVE)

        assert len(draft_policies) == 1
        assert draft_policies[0].name == "Draft Policy"
        assert len(active_policies) == 1
        assert active_policies[0].name == "Active Policy"

    @pytest.mark.asyncio
    async def test_list_policy_versions(self, policy_service, sample_policy_content, sample_keys):
        """Test listing all versions of a policy."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content={"updated": True},
            version="2.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        versions = await policy_service.list_policy_versions(policy.policy_id)

        assert len(versions) == 2
        version_nums = {v.version for v in versions}
        assert version_nums == {"1.0.0", "2.0.0"}


# =============================================================================
# Client Policy Retrieval Tests
# =============================================================================


class TestClientPolicyRetrieval:
    """Tests for getting policy for clients (with A/B testing)."""

    @pytest.mark.asyncio
    async def test_get_policy_for_client_returns_active(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test getting policy for client returns active version content."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "1.0.0")

        content = await policy_service.get_policy_for_client(policy.policy_id)

        assert content == sample_policy_content

    @pytest.mark.asyncio
    async def test_get_policy_for_client_uses_cache(self, policy_service, mock_cache_service):
        """Test that get_policy_for_client uses cache."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        cached_content = {"cached": True}
        mock_cache_service.cache_store[f"policy:{policy.policy_id}:active"] = cached_content

        content = await policy_service.get_policy_for_client(policy.policy_id)

        assert content == cached_content

    @pytest.mark.asyncio
    async def test_get_policy_for_client_returns_none_when_no_active(self, policy_service):
        """Test that get_policy_for_client returns None when no active version."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        content = await policy_service.get_policy_for_client(policy.policy_id)

        assert content is None


# =============================================================================
# A/B Testing Tests
# =============================================================================


class TestABTesting:
    """Tests for A/B testing functionality."""

    def test_get_ab_test_group_deterministic(self, policy_service):
        """Test that A/B test group assignment is deterministic."""
        client_id = "test-client-123"

        group1 = policy_service._get_ab_test_group(client_id)
        group2 = policy_service._get_ab_test_group(client_id)

        assert group1 == group2

    def test_get_ab_test_group_distribution(self, policy_service):
        """Test that A/B test groups have reasonable distribution."""
        # Generate many client IDs and check distribution
        group_a_count = 0
        group_b_count = 0

        for i in range(1000):
            client_id = f"test-client-{i}"
            group = policy_service._get_ab_test_group(client_id)
            if group == ABTestGroup.A:
                group_a_count += 1
            else:
                group_b_count += 1

        # Should be roughly 50/50, allow 10% margin
        assert 400 < group_a_count < 600
        assert 400 < group_b_count < 600


# =============================================================================
# Fallback Policy Tests
# =============================================================================


class TestFallbackPolicy:
    """Tests for fallback policy functionality."""

    @pytest.mark.asyncio
    async def test_get_fallback_policy(self, policy_service, sample_policy_content, sample_keys):
        """Test getting fallback policy (most recent retired version)."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        # Create and activate v1
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content={"version": "1"},
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "1.0.0")

        # Create and activate v2 (retires v1)
        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content={"version": "2"},
            version="2.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        await policy_service.activate_version(policy.policy_id, "2.0.0")

        fallback = await policy_service._get_fallback_policy(policy.policy_id)

        assert fallback == {"version": "1"}

    @pytest.mark.asyncio
    async def test_get_fallback_policy_returns_none_when_no_retired(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that fallback returns None when no retired versions exist."""
        policy = await policy_service.create_policy(
            name="Test Policy", tenant_id="tenant-001", content={}
        )

        await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )
        # Don't activate - stays as DRAFT

        fallback = await policy_service._get_fallback_policy(policy.policy_id)

        assert fallback is None


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


@pytest.mark.constitutional
class TestConstitutionalCompliance:
    """Tests for constitutional compliance features."""

    @pytest.mark.asyncio
    async def test_policy_content_can_include_constitutional_hash(
        self, policy_service, sample_keys
    ):
        """Test that policy content can include constitutional hash."""
        policy = await policy_service.create_policy(
            name="Constitutional Policy",
            tenant_id="tenant-001",
            content={},
        )

        constitutional_content = {
            "rules": [],
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        version = await policy_service.create_policy_version(
            policy_id=policy.policy_id,
            content=constitutional_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        assert version.content["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_content_hash_is_deterministic(
        self, policy_service, sample_policy_content, sample_keys
    ):
        """Test that content hash is deterministic across different version creations."""
        policy1 = await policy_service.create_policy(
            name="Policy 1", tenant_id="tenant-001", content={}
        )
        policy2 = await policy_service.create_policy(
            name="Policy 2", tenant_id="tenant-002", content={}
        )

        version1 = await policy_service.create_policy_version(
            policy_id=policy1.policy_id,
            content=sample_policy_content,
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        version2 = await policy_service.create_policy_version(
            policy_id=policy2.policy_id,
            content=sample_policy_content,  # Same content
            version="1.0.0",
            private_key_b64=sample_keys["private_key"],
            public_key_b64=sample_keys["public_key"],
        )

        # Same content should produce same hash
        assert version1.content_hash == version2.content_hash
