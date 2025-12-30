"""
ACGS-2 Policy Registry - Crypto Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for CryptoService including:
- Ed25519 key pair generation
- Policy content signing and verification
- Key fingerprint generation
- Policy signature creation
- Agent JWT token issuance and verification
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def crypto_service():
    """Create a CryptoService instance."""
    from app.services.crypto_service import CryptoService

    return CryptoService()


@pytest.fixture
def keypair():
    """Generate a key pair for testing."""
    from app.services.crypto_service import CryptoService

    return CryptoService.generate_keypair()


@pytest.fixture
def sample_policy_content():
    """Sample policy content for testing."""
    return {
        "name": "test-policy",
        "version": "1.0.0",
        "rules": [
            {"action": "allow", "resource": "read:*"},
            {"action": "deny", "resource": "write:admin"},
        ],
        "metadata": {"author": "test-user", "description": "Test policy for unit tests"},
    }


@pytest.fixture
def sample_complex_content():
    """Complex nested policy content."""
    return {
        "nested": {"deep": {"value": 123, "list": [1, 2, 3], "unicode": "こんにちは"}},
        "boolean": True,
        "null_value": None,
        "numbers": [1.5, -2, 0, 1000000],
    }


# =============================================================================
# Key Pair Generation Tests
# =============================================================================


class TestKeyPairGeneration:
    """Tests for Ed25519 key pair generation."""

    def test_generate_keypair_returns_tuple(self, crypto_service):
        """Test that generate_keypair returns a tuple of two strings."""
        result = crypto_service.generate_keypair()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_generate_keypair_base64_encoded(self, crypto_service):
        """Test that keys are valid base64."""
        public_key, private_key = crypto_service.generate_keypair()

        # Should not raise on decode
        public_bytes = base64.b64decode(public_key)
        private_bytes = base64.b64decode(private_key)

        # Ed25519 keys are 32 bytes each
        assert len(public_bytes) == 32
        assert len(private_bytes) == 32

    def test_generate_keypair_unique(self, crypto_service):
        """Test that each keypair is unique."""
        pairs = [crypto_service.generate_keypair() for _ in range(5)]

        public_keys = [p[0] for p in pairs]
        private_keys = [p[1] for p in pairs]

        # All keys should be unique
        assert len(set(public_keys)) == 5
        assert len(set(private_keys)) == 5

    def test_generate_keypair_valid_ed25519(self, crypto_service):
        """Test that generated keys are valid Ed25519 keys."""
        public_key_b64, private_key_b64 = crypto_service.generate_keypair()

        # Should be loadable as Ed25519 keys
        private_bytes = base64.b64decode(private_key_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)

        public_bytes = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)

        assert private_key is not None
        assert public_key is not None


# =============================================================================
# Policy Signing Tests
# =============================================================================


class TestPolicySigning:
    """Tests for policy content signing."""

    def test_sign_policy_content(self, crypto_service, keypair, sample_policy_content):
        """Test signing policy content."""
        public_key, private_key = keypair

        signature = crypto_service.sign_policy_content(sample_policy_content, private_key)

        assert isinstance(signature, str)
        # Signature should be base64 decodable
        signature_bytes = base64.b64decode(signature)
        # Ed25519 signatures are 64 bytes
        assert len(signature_bytes) == 64

    def test_sign_policy_deterministic(self, crypto_service, keypair, sample_policy_content):
        """Test that signing is deterministic for same content."""
        public_key, private_key = keypair

        sig1 = crypto_service.sign_policy_content(sample_policy_content, private_key)
        sig2 = crypto_service.sign_policy_content(sample_policy_content, private_key)

        assert sig1 == sig2

    def test_sign_different_content_different_signature(self, crypto_service, keypair):
        """Test that different content produces different signatures."""
        public_key, private_key = keypair

        sig1 = crypto_service.sign_policy_content({"a": 1}, private_key)
        sig2 = crypto_service.sign_policy_content({"a": 2}, private_key)

        assert sig1 != sig2

    def test_sign_complex_content(self, crypto_service, keypair, sample_complex_content):
        """Test signing complex nested content."""
        public_key, private_key = keypair

        signature = crypto_service.sign_policy_content(sample_complex_content, private_key)

        assert isinstance(signature, str)
        assert len(base64.b64decode(signature)) == 64

    def test_sign_empty_content(self, crypto_service, keypair):
        """Test signing empty content."""
        public_key, private_key = keypair

        signature = crypto_service.sign_policy_content({}, private_key)

        assert isinstance(signature, str)


# =============================================================================
# Signature Verification Tests
# =============================================================================


class TestSignatureVerification:
    """Tests for signature verification."""

    def test_verify_valid_signature(self, crypto_service, keypair, sample_policy_content):
        """Test verifying a valid signature."""
        public_key, private_key = keypair

        signature = crypto_service.sign_policy_content(sample_policy_content, private_key)

        result = crypto_service.verify_policy_signature(
            sample_policy_content, signature, public_key
        )

        assert result is True

    def test_verify_invalid_signature(self, crypto_service, keypair, sample_policy_content):
        """Test verifying an invalid signature."""
        public_key, private_key = keypair

        # Create a random signature
        invalid_signature = base64.b64encode(b"x" * 64).decode()

        result = crypto_service.verify_policy_signature(
            sample_policy_content, invalid_signature, public_key
        )

        assert result is False

    def test_verify_tampered_content(self, crypto_service, keypair, sample_policy_content):
        """Test verification fails with tampered content."""
        public_key, private_key = keypair

        signature = crypto_service.sign_policy_content(sample_policy_content, private_key)

        # Tamper with content
        tampered_content = sample_policy_content.copy()
        tampered_content["name"] = "tampered-policy"

        result = crypto_service.verify_policy_signature(tampered_content, signature, public_key)

        assert result is False

    def test_verify_wrong_public_key(self, crypto_service, keypair, sample_policy_content):
        """Test verification fails with wrong public key."""
        public_key, private_key = keypair
        wrong_public, _ = crypto_service.generate_keypair()

        signature = crypto_service.sign_policy_content(sample_policy_content, private_key)

        result = crypto_service.verify_policy_signature(
            sample_policy_content, signature, wrong_public
        )

        assert result is False

    def test_verify_malformed_signature(self, crypto_service, keypair, sample_policy_content):
        """Test verification handles malformed signature gracefully."""
        public_key, _ = keypair

        result = crypto_service.verify_policy_signature(
            sample_policy_content, "not-valid-base64!@#$", public_key
        )

        assert result is False

    def test_verify_malformed_public_key(self, crypto_service, keypair, sample_policy_content):
        """Test verification handles malformed public key gracefully."""
        _, private_key = keypair

        signature = crypto_service.sign_policy_content(sample_policy_content, private_key)

        result = crypto_service.verify_policy_signature(
            sample_policy_content, signature, "invalid-key"
        )

        assert result is False


# =============================================================================
# Fingerprint Tests
# =============================================================================


class TestFingerprint:
    """Tests for key fingerprint generation."""

    def test_generate_fingerprint(self, crypto_service, keypair):
        """Test fingerprint generation."""
        public_key, _ = keypair

        fingerprint = crypto_service.generate_fingerprint(public_key)

        assert isinstance(fingerprint, str)
        # SHA256 hex is 64 characters
        assert len(fingerprint) == 64
        # Should be valid hex
        int(fingerprint, 16)

    def test_fingerprint_deterministic(self, crypto_service, keypair):
        """Test fingerprint is deterministic."""
        public_key, _ = keypair

        fp1 = crypto_service.generate_fingerprint(public_key)
        fp2 = crypto_service.generate_fingerprint(public_key)

        assert fp1 == fp2

    def test_fingerprint_unique_per_key(self, crypto_service):
        """Test each key has unique fingerprint."""
        fingerprints = []
        for _ in range(5):
            public_key, _ = crypto_service.generate_keypair()
            fingerprints.append(crypto_service.generate_fingerprint(public_key))

        assert len(set(fingerprints)) == 5


# =============================================================================
# Policy Signature Creation Tests
# =============================================================================


class TestPolicySignatureCreation:
    """Tests for policy signature object creation."""

    def test_create_policy_signature(self, crypto_service, keypair, sample_policy_content):
        """Test creating a policy signature object."""
        public_key, private_key = keypair

        policy_sig = crypto_service.create_policy_signature(
            policy_id="policy-123",
            version="1.0.0",
            content=sample_policy_content,
            private_key_b64=private_key,
            public_key_b64=public_key,
        )

        assert policy_sig.policy_id == "policy-123"
        assert policy_sig.version == "1.0.0"
        assert policy_sig.public_key == public_key
        assert policy_sig.signature is not None
        assert policy_sig.key_fingerprint is not None

    def test_policy_signature_verifiable(self, crypto_service, keypair, sample_policy_content):
        """Test that created policy signature is verifiable."""
        public_key, private_key = keypair

        policy_sig = crypto_service.create_policy_signature(
            policy_id="policy-123",
            version="1.0.0",
            content=sample_policy_content,
            private_key_b64=private_key,
            public_key_b64=public_key,
        )

        # Verify the signature
        is_valid = crypto_service.verify_policy_signature(
            sample_policy_content, policy_sig.signature, policy_sig.public_key
        )

        assert is_valid is True

    def test_policy_signature_fingerprint_matches(
        self, crypto_service, keypair, sample_policy_content
    ):
        """Test that signature fingerprint matches public key."""
        public_key, private_key = keypair

        policy_sig = crypto_service.create_policy_signature(
            policy_id="policy-123",
            version="1.0.0",
            content=sample_policy_content,
            private_key_b64=private_key,
            public_key_b64=public_key,
        )

        expected_fingerprint = crypto_service.generate_fingerprint(public_key)
        assert policy_sig.key_fingerprint == expected_fingerprint


# =============================================================================
# Signature Integrity Validation Tests
# =============================================================================


class TestSignatureIntegrityValidation:
    """Tests for signature integrity validation."""

    def test_validate_signature_integrity_valid(
        self, crypto_service, keypair, sample_policy_content
    ):
        """Test integrity validation for valid signature."""
        public_key, private_key = keypair

        policy_sig = crypto_service.create_policy_signature(
            policy_id="policy-123",
            version="1.0.0",
            content=sample_policy_content,
            private_key_b64=private_key,
            public_key_b64=public_key,
        )

        is_valid = crypto_service.validate_signature_integrity(policy_sig)
        assert is_valid is True

    def test_validate_signature_integrity_invalid_fingerprint(
        self, crypto_service, keypair, sample_policy_content
    ):
        """Test integrity validation fails with wrong fingerprint."""
        public_key, private_key = keypair

        policy_sig = crypto_service.create_policy_signature(
            policy_id="policy-123",
            version="1.0.0",
            content=sample_policy_content,
            private_key_b64=private_key,
            public_key_b64=public_key,
        )

        # Tamper with fingerprint
        policy_sig.key_fingerprint = "0" * 64

        is_valid = crypto_service.validate_signature_integrity(policy_sig)
        assert is_valid is False


# =============================================================================
# Agent Token Tests
# =============================================================================


class TestAgentTokenIssuance:
    """Tests for agent JWT token issuance."""

    def test_issue_agent_token(self, crypto_service, keypair):
        """Test issuing an agent token."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read", "write"],
            private_key_b64=private_key,
            ttl_hours=24,
        )

        assert isinstance(token, str)
        # JWT has 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_issue_agent_token_custom_ttl(self, crypto_service, keypair):
        """Test issuing token with custom TTL."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
            ttl_hours=1,
        )

        # Decode without verification to check claims
        unverified = jwt.decode(token, options={"verify_signature": False})

        # Check expiration is approximately 1 hour from now
        exp = unverified["exp"]
        iat = unverified["iat"]
        assert (exp - iat) == 3600  # 1 hour in seconds

    def test_issue_agent_token_contains_constitutional_hash(self, crypto_service, keypair):
        """Test that token contains constitutional hash."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
        )

        unverified = jwt.decode(token, options={"verify_signature": False})

        assert unverified["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_issue_agent_token_spiffe_format(self, crypto_service, keypair):
        """Test that token subject is in SPIFFE format."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
        )

        unverified = jwt.decode(token, options={"verify_signature": False})

        expected_sub = "spiffe://acgs2/tenant/tenant-456/agent/agent-123"
        assert unverified["sub"] == expected_sub


# =============================================================================
# Agent Token Verification Tests
# =============================================================================


class TestAgentTokenVerification:
    """Tests for agent token verification."""

    def test_verify_valid_token(self, crypto_service, keypair):
        """Test verifying a valid token."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read", "write"],
            private_key_b64=private_key,
        )

        payload = crypto_service.verify_agent_token(token, public_key)

        assert payload["agent_id"] == "agent-123"
        assert payload["tenant_id"] == "tenant-456"
        assert payload["capabilities"] == ["read", "write"]

    def test_verify_expired_token(self, crypto_service, keypair):
        """Test that expired token raises error."""
        public_key, private_key = keypair

        # Issue token that expires immediately
        with patch("app.services.crypto_service.datetime") as mock_dt:
            # Set time to 2 hours ago
            past_time = datetime.now(timezone.utc) - timedelta(hours=2)
            mock_dt.now.return_value = past_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            token = crypto_service.issue_agent_token(
                agent_id="agent-123",
                tenant_id="tenant-456",
                capabilities=["read"],
                private_key_b64=private_key,
                ttl_hours=1,
            )

        # Now verify (will be expired)
        with pytest.raises(ValueError, match="Token has expired"):
            crypto_service.verify_agent_token(token, public_key)

    def test_verify_wrong_public_key(self, crypto_service, keypair):
        """Test verification fails with wrong public key."""
        public_key, private_key = keypair
        wrong_public, _ = crypto_service.generate_keypair()

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
        )

        with pytest.raises(ValueError, match="Invalid token"):
            crypto_service.verify_agent_token(token, wrong_public)

    def test_verify_invalid_token(self, crypto_service, keypair):
        """Test verification fails with invalid token."""
        public_key, _ = keypair

        with pytest.raises(ValueError):
            crypto_service.verify_agent_token("invalid.token.here", public_key)

    def test_verify_tampered_token(self, crypto_service, keypair):
        """Test verification fails with tampered token."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
        )

        # Tamper with the token
        parts = token.split(".")
        # Modify the payload
        parts[1] = parts[1] + "tampered"
        tampered_token = ".".join(parts)

        with pytest.raises(ValueError):
            crypto_service.verify_agent_token(tampered_token, public_key)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_sign_unicode_content(self, crypto_service, keypair):
        """Test signing content with unicode characters."""
        public_key, private_key = keypair

        unicode_content = {
            "japanese": "こんにちは",
            "emoji": "🔐🔑",
            "arabic": "مرحبا",
            "chinese": "你好",
        }

        signature = crypto_service.sign_policy_content(unicode_content, private_key)

        is_valid = crypto_service.verify_policy_signature(unicode_content, signature, public_key)

        assert is_valid is True

    def test_sign_content_with_special_json_chars(self, crypto_service, keypair):
        """Test signing content with special JSON characters."""
        public_key, private_key = keypair

        special_content = {
            "quotes": 'He said "hello"',
            "backslash": "path\\to\\file",
            "newline": "line1\nline2",
            "tab": "col1\tcol2",
        }

        signature = crypto_service.sign_policy_content(special_content, private_key)

        is_valid = crypto_service.verify_policy_signature(special_content, signature, public_key)

        assert is_valid is True

    def test_sign_large_content(self, crypto_service, keypair):
        """Test signing large content."""
        public_key, private_key = keypair

        large_content = {"rules": [f"rule-{i}" for i in range(1000)], "data": "x" * 10000}

        signature = crypto_service.sign_policy_content(large_content, private_key)

        is_valid = crypto_service.verify_policy_signature(large_content, signature, public_key)

        assert is_valid is True

    def test_multiple_capabilities_in_token(self, crypto_service, keypair):
        """Test token with many capabilities."""
        public_key, private_key = keypair

        capabilities = [f"capability-{i}" for i in range(50)]

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=capabilities,
            private_key_b64=private_key,
        )

        payload = crypto_service.verify_agent_token(token, public_key)
        assert payload["capabilities"] == capabilities


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_constitutional_hash_constant(self):
        """Verify constitutional hash is correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_token_contains_constitutional_hash(self, crypto_service, keypair):
        """Test that issued tokens contain constitutional hash."""
        public_key, private_key = keypair

        token = crypto_service.issue_agent_token(
            agent_id="agent-123",
            tenant_id="tenant-456",
            capabilities=["read"],
            private_key_b64=private_key,
        )

        payload = crypto_service.verify_agent_token(token, public_key)
        assert payload["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_crypto_service_module_exists(self):
        """Test that crypto service module can be imported."""
        from app.services.crypto_service import CryptoService

        assert CryptoService is not None

    def test_all_static_methods_available(self):
        """Test that all expected static methods are available."""
        from app.services.crypto_service import CryptoService

        assert hasattr(CryptoService, "generate_keypair")
        assert hasattr(CryptoService, "sign_policy_content")
        assert hasattr(CryptoService, "verify_policy_signature")
        assert hasattr(CryptoService, "generate_fingerprint")
        assert hasattr(CryptoService, "create_policy_signature")
        assert hasattr(CryptoService, "validate_signature_integrity")
        assert hasattr(CryptoService, "issue_agent_token")
        assert hasattr(CryptoService, "verify_agent_token")
