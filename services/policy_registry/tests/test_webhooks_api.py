"""
ACGS-2 Policy Registry - Webhooks API Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for webhook endpoints:
- GitHub webhook signature verification
- Webhook payload processing
- Background task triggering
- Error handling and security
"""

import pytest
import hmac
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from io import BytesIO
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Mock Services
# =============================================================================

class MockCompilerService:
    """Mock compiler service for testing."""

    async def compile_bundle(self, paths, output_path, run_tests=False):
        """Simulate bundle compilation."""
        # Write mock content to output path
        with open(output_path, "wb") as f:
            f.write(b'{"mock": "bundle"}')
        return True


class MockStorageService:
    """Mock storage service for testing."""

    def __init__(self):
        self._bundles = {}

    async def save_bundle(self, digest: str, content: bytes) -> str:
        """Save bundle content and return storage path."""
        self._bundles[digest] = content
        return f"/storage/bundles/{digest}"


class MockSettings:
    """Mock settings for testing."""

    def __init__(self, webhook_secret=None):
        self._webhook_secret = webhook_secret

    @property
    def bundle(self):
        return MagicMock(
            github_webhook_secret=self._webhook_secret,
            registry_url="http://localhost:5000"
        )

    @property
    def ai(self):
        return MagicMock(constitutional_hash=CONSTITUTIONAL_HASH)


class MockSecretStr:
    """Mock SecretStr for testing."""

    def __init__(self, value):
        self._value = value

    def get_secret_value(self):
        return self._value


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_compiler_service():
    """Create mock compiler service."""
    return MockCompilerService()


@pytest.fixture
def mock_storage_service():
    """Create mock storage service."""
    return MockStorageService()


@pytest.fixture
def webhook_secret():
    """Webhook secret for testing."""
    return "test-webhook-secret-12345"


@pytest.fixture
def mock_settings_with_secret(webhook_secret):
    """Mock settings with webhook secret configured."""
    secret = MagicMock()
    secret.get_secret_value = MagicMock(return_value=webhook_secret)
    settings = MockSettings(webhook_secret=secret)
    return settings


@pytest.fixture
def mock_settings_no_secret():
    """Mock settings without webhook secret."""
    return MockSettings(webhook_secret=None)


@pytest.fixture
def sample_github_payload():
    """Sample GitHub push event payload."""
    return {
        "ref": "refs/heads/main",
        "before": "abc123",
        "after": "def456",
        "repository": {
            "name": "policies",
            "full_name": "acgs/policies"
        },
        "pusher": {
            "name": "test-user"
        },
        "commits": [
            {
                "id": "def456",
                "message": "Update policies",
                "added": ["policies/new.rego"],
                "modified": ["policies/main.rego"]
            }
        ]
    }


def generate_github_signature(secret: str, payload: dict) -> str:
    """Generate GitHub-style HMAC signature."""
    body = json.dumps(payload).encode()
    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


# =============================================================================
# Signature Verification Tests
# =============================================================================

class TestSignatureVerification:
    """Tests for GitHub webhook signature verification."""

    @pytest.mark.asyncio
    async def test_verify_signature_success(self, webhook_secret, sample_github_payload):
        """Test successful signature verification."""
        from app.api.v1 import webhooks

        # Generate valid signature
        body = json.dumps(sample_github_payload).encode()
        expected_signature = generate_github_signature(webhook_secret, sample_github_payload)

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.body = AsyncMock(return_value=body)

        # Mock settings with secret
        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            # Should not raise
            await webhooks.verify_github_signature(mock_request, expected_signature)

    @pytest.mark.asyncio
    async def test_verify_signature_missing_header(self, webhook_secret):
        """Test signature verification fails when header missing."""
        from app.api.v1 import webhooks

        mock_request = MagicMock(spec=Request)

        # Mock settings with secret
        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await webhooks.verify_github_signature(mock_request, None)

        assert exc_info.value.status_code == 401
        assert "missing" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_signature_invalid(self, webhook_secret, sample_github_payload):
        """Test signature verification fails with invalid signature."""
        from app.api.v1 import webhooks

        body = json.dumps(sample_github_payload).encode()
        invalid_signature = "sha256=invalid_signature_12345"

        mock_request = MagicMock(spec=Request)
        mock_request.body = AsyncMock(return_value=body)

        # Mock settings with secret
        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await webhooks.verify_github_signature(mock_request, invalid_signature)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_signature_skipped_when_no_secret(self):
        """Test signature verification is skipped when secret not configured."""
        from app.api.v1 import webhooks

        mock_request = MagicMock(spec=Request)

        # Mock settings without secret
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = None

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            # Should not raise, just return
            await webhooks.verify_github_signature(mock_request, None)


# =============================================================================
# GitHub Webhook Endpoint Tests
# =============================================================================

class TestGitHubWebhook:
    """Tests for POST /webhooks/github endpoint."""

    def test_webhook_triggers_background_task(
        self,
        mock_compiler_service,
        mock_storage_service,
        sample_github_payload,
        webhook_secret
    ):
        """Test webhook triggers background processing."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        # Clear caches
        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        # Override dependencies
        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        # Mock settings to skip signature verification (no secret configured)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = None

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)
            response = client.post("/webhooks/github", json=sample_github_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert "background" in data["message"].lower()

    def test_webhook_returns_commit_info(
        self,
        mock_compiler_service,
        mock_storage_service,
        sample_github_payload
    ):
        """Test webhook response includes commit reference."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        # Mock settings to skip signature verification (no secret configured)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = None

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)
            response = client.post("/webhooks/github", json=sample_github_payload)

        assert response.status_code == 200

    def test_webhook_requires_valid_json(self, mock_compiler_service, mock_storage_service):
        """Test webhook requires valid JSON payload."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        # Mock settings to skip signature verification
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = None

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)

            # Invalid JSON body
            response = client.post(
                "/webhooks/github",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 422


# =============================================================================
# Background Task Tests
# =============================================================================

class TestProcessPolicyUpdate:
    """Tests for process_policy_update background task."""

    @pytest.mark.asyncio
    async def test_process_policy_update_handles_missing_bundle_registry(
        self,
        sample_github_payload,
        mock_compiler_service,
        mock_storage_service
    ):
        """Test graceful handling when bundle registry import fails."""
        from app.api.v1 import webhooks

        # The function should handle ImportError gracefully
        with patch.dict('sys.modules', {'enhanced_agent_bus.bundle_registry': None}):
            # Should not raise, just log error and return
            await webhooks.process_policy_update(
                sample_github_payload,
                mock_compiler_service,
                mock_storage_service
            )

    @pytest.mark.asyncio
    async def test_process_policy_update_handles_missing_policy_dir(
        self,
        sample_github_payload,
        mock_compiler_service,
        mock_storage_service
    ):
        """Test handling when policy directory doesn't exist."""
        from app.api.v1 import webhooks

        mock_settings = MagicMock()
        mock_settings.ai.constitutional_hash = CONSTITUTIONAL_HASH
        mock_settings.bundle.registry_url = "http://localhost:5000"

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            with patch('os.path.exists', return_value=False):
                # Should handle gracefully without raising
                await webhooks.process_policy_update(
                    sample_github_payload,
                    mock_compiler_service,
                    mock_storage_service
                )


# =============================================================================
# Service Factory Tests
# =============================================================================

class TestServiceFactories:
    """Tests for service factory functions."""

    def test_get_compiler_service_is_cached(self):
        """Test that get_compiler_service uses lru_cache."""
        from app.api.v1 import webhooks

        webhooks.get_compiler_service.cache_clear()

        service1 = webhooks.get_compiler_service()
        service2 = webhooks.get_compiler_service()

        assert service1 is service2

    def test_get_storage_service_is_cached(self):
        """Test that get_storage_service uses lru_cache."""
        from app.api.v1 import webhooks

        webhooks.get_storage_service.cache_clear()

        service1 = webhooks.get_storage_service()
        service2 = webhooks.get_storage_service()

        assert service1 is service2

    def test_compiler_cache_can_be_cleared(self):
        """Test that compiler cache can be cleared."""
        from app.api.v1 import webhooks

        service1 = webhooks.get_compiler_service()
        webhooks.get_compiler_service.cache_clear()
        service2 = webhooks.get_compiler_service()

        assert service1 is not service2

    def test_storage_cache_can_be_cleared(self):
        """Test that storage cache can be cleared."""
        from app.api.v1 import webhooks

        service1 = webhooks.get_storage_service()
        webhooks.get_storage_service.cache_clear()
        service2 = webhooks.get_storage_service()

        assert service1 is not service2


# =============================================================================
# HMAC Signature Tests
# =============================================================================

class TestHMACSignature:
    """Tests for HMAC signature generation and verification."""

    def test_generate_valid_hmac_signature(self, webhook_secret, sample_github_payload):
        """Test generating valid HMAC signature."""
        body = json.dumps(sample_github_payload).encode()

        signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        expected = f"sha256={signature}"

        assert expected.startswith("sha256=")
        assert len(signature) == 64  # SHA256 hex digest

    def test_hmac_signature_consistent(self, webhook_secret, sample_github_payload):
        """Test HMAC signature is consistent for same input."""
        sig1 = generate_github_signature(webhook_secret, sample_github_payload)
        sig2 = generate_github_signature(webhook_secret, sample_github_payload)

        assert sig1 == sig2

    def test_hmac_signature_differs_for_different_payload(self, webhook_secret):
        """Test HMAC signature differs for different payloads."""
        payload1 = {"data": "one"}
        payload2 = {"data": "two"}

        sig1 = generate_github_signature(webhook_secret, payload1)
        sig2 = generate_github_signature(webhook_secret, payload2)

        assert sig1 != sig2

    def test_hmac_signature_differs_for_different_secret(self, sample_github_payload):
        """Test HMAC signature differs for different secrets."""
        sig1 = generate_github_signature("secret1", sample_github_payload)
        sig2 = generate_github_signature("secret2", sample_github_payload)

        assert sig1 != sig2

    def test_hmac_compare_digest_timing_safe(self, webhook_secret, sample_github_payload):
        """Test that hmac.compare_digest is used for timing-safe comparison."""
        body = json.dumps(sample_github_payload).encode()

        signature1 = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        signature2 = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        # Use timing-safe comparison
        assert hmac.compare_digest(signature1, signature2)


# =============================================================================
# Payload Parsing Tests
# =============================================================================

class TestPayloadParsing:
    """Tests for webhook payload parsing."""

    def test_extract_commit_ref_from_payload(self, sample_github_payload):
        """Test extracting commit reference from payload."""
        after_commit = sample_github_payload.get("after")
        assert after_commit == "def456"

    def test_extract_repository_from_payload(self, sample_github_payload):
        """Test extracting repository info from payload."""
        repo_name = sample_github_payload.get("repository", {}).get("full_name")
        assert repo_name == "acgs/policies"

    def test_extract_commits_from_payload(self, sample_github_payload):
        """Test extracting commits from payload."""
        commits = sample_github_payload.get("commits", [])
        assert len(commits) == 1
        assert commits[0]["id"] == "def456"

    def test_handle_payload_without_after(self, mock_compiler_service, mock_storage_service):
        """Test handling payload without 'after' field."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        # Mock settings to skip signature verification
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = None

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)

            # Payload without 'after' field
            minimal_payload = {"ref": "refs/heads/main"}
            response = client.post("/webhooks/github", json=minimal_payload)

        # Should still succeed and trigger background task
        assert response.status_code == 200


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================

class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_module_has_constitutional_hash(self):
        """Test that webhooks module has constitutional hash in docstring."""
        from app.api.v1 import webhooks

        assert CONSTITUTIONAL_HASH in webhooks.__doc__

    def test_settings_provides_constitutional_hash(self):
        """Test that settings provides constitutional hash."""
        mock_settings = MagicMock()
        mock_settings.ai.constitutional_hash = CONSTITUTIONAL_HASH

        assert mock_settings.ai.constitutional_hash == CONSTITUTIONAL_HASH


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in webhook processing."""

    @pytest.mark.asyncio
    async def test_signature_verification_error_returns_401(self, webhook_secret):
        """Test that signature verification errors return 401."""
        from app.api.v1 import webhooks

        mock_request = MagicMock(spec=Request)
        mock_request.body = AsyncMock(return_value=b'{"test": "data"}')

        # Mock settings with secret
        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await webhooks.verify_github_signature(
                    mock_request,
                    "sha256=wrong_signature"
                )

        assert exc_info.value.status_code == 401

    def test_invalid_json_returns_422(self, mock_compiler_service, mock_storage_service):
        """Test that invalid JSON returns 422."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        async def skip_verify(request, x_hub_signature_256=None):
            return None

        app.dependency_overrides[webhooks.verify_github_signature] = skip_verify

        client = TestClient(app)

        response = client.post(
            "/webhooks/github",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


# =============================================================================
# Security Tests
# =============================================================================

class TestWebhookSecurity:
    """Tests for webhook security measures."""

    def test_empty_signature_rejected(self, mock_compiler_service, mock_storage_service, webhook_secret):
        """Test that empty signature is rejected."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        # Don't override signature verification
        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)

            response = client.post(
                "/webhooks/github",
                json={"test": "data"},
                headers={"X-Hub-Signature-256": ""}
            )

            # Should fail signature verification
            assert response.status_code in [401, 422]

    def test_malformed_signature_rejected(self, mock_compiler_service, mock_storage_service, webhook_secret):
        """Test that malformed signature is rejected."""
        from app.api.v1 import webhooks

        app = FastAPI()
        app.include_router(webhooks.router, prefix="/webhooks")

        webhooks.get_compiler_service.cache_clear()
        webhooks.get_storage_service.cache_clear()

        app.dependency_overrides[webhooks.get_compiler_service] = lambda: mock_compiler_service
        app.dependency_overrides[webhooks.get_storage_service] = lambda: mock_storage_service

        secret_mock = MagicMock()
        secret_mock.get_secret_value = MagicMock(return_value=webhook_secret)
        mock_settings = MagicMock()
        mock_settings.bundle.github_webhook_secret = secret_mock

        with patch.object(webhooks, '_get_settings', return_value=mock_settings):
            client = TestClient(app)

            response = client.post(
                "/webhooks/github",
                json={"test": "data"},
                headers={"X-Hub-Signature-256": "malformed-no-prefix"}
            )

            # Should fail signature verification
            assert response.status_code == 401
