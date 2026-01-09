"""
ACGS-2 Policy Registry - VaultCryptoService Unit Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for Vault/OpenBao cryptographic service integration.
"""

import base64
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directories to path
policy_registry_dir = os.path.dirname(os.path.dirname(__file__))
app_dir = os.path.join(policy_registry_dir, "app")
if policy_registry_dir not in sys.path:
    sys.path.insert(0, policy_registry_dir)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Import the service
from app.services.vault_crypto_service import (  # noqa: E402
    CONSTITUTIONAL_HASH,
    VaultAuditEntry,
    VaultConfig,
    VaultCryptoService,
    VaultKeyType,
    VaultOperation,
    create_vault_crypto_service,
)


class TestVaultConfig:
    """Tests for VaultConfig configuration class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VaultConfig()

        assert config.address == "http://127.0.0.1:8200"
        assert config.token is None
        assert config.namespace is None
        assert config.transit_mount == "transit"
        assert config.kv_mount == "secret"
        assert config.kv_version == 2
        assert config.timeout == 30.0
        assert config.verify_tls is True

    def test_config_from_env(self):
        """Test configuration from environment variables."""
        env_vars = {
            "VAULT_ADDR": "http://vault.example.com:8200",
            "VAULT_TOKEN": "test-token-123",
            "VAULT_NAMESPACE": "test-ns",
            "VAULT_TRANSIT_MOUNT": "custom-transit",
            "VAULT_KV_MOUNT": "custom-secret",
            "VAULT_KV_VERSION": "1",
            "VAULT_TIMEOUT": "60.0",
            "VAULT_SKIP_VERIFY": "true",
        }

        with patch.dict(os.environ, env_vars):
            with patch("app.services.vault_models.global_settings", None):
                config = VaultConfig.from_env()

            assert config.address == "http://vault.example.com:8200"
            assert config.token == "test-token-123"
            assert config.namespace == "test-ns"
            assert config.transit_mount == "custom-transit"
            assert config.kv_mount == "custom-secret"
            assert config.kv_version == 1
            assert config.timeout == 60.0
            assert config.verify_tls is False


class TestVaultAuditEntry:
    """Tests for VaultAuditEntry audit logging."""

    def test_audit_entry_creation(self):
        """Test audit entry creation with defaults."""
        entry = VaultAuditEntry(
            operation=VaultOperation.SIGN,
            key_name="test-key",
        )

        assert entry.operation == VaultOperation.SIGN
        assert entry.key_name == "test-key"
        assert entry.success is True
        assert entry.error_message is None
        assert entry.constitutional_hash == CONSTITUTIONAL_HASH
        assert isinstance(entry.timestamp, datetime)
        assert entry.metadata == {}

    def test_audit_entry_to_dict(self):
        """Test audit entry serialization."""
        entry = VaultAuditEntry(
            operation=VaultOperation.ENCRYPT,
            key_name="encryption-key",
            success=False,
            error_message="Test error",
            metadata={"key_type": "aes256-gcm96"},
        )

        result = entry.to_dict()

        assert result["operation"] == "encrypt"
        assert result["key_name"] == "encryption-key"
        assert result["success"] is False
        assert result["error_message"] == "Test error"
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert result["metadata"]["key_type"] == "aes256-gcm96"
        assert "timestamp" in result
        assert "entry_id" in result


class TestVaultCryptoServiceInit:
    """Tests for VaultCryptoService initialization."""

    def test_service_init_default(self):
        """Test service initialization with defaults."""
        service = VaultCryptoService()

        assert service.fallback_enabled is True
        assert service.cache_ttl == 300
        assert service.audit_enabled is True
        assert service._constitutional_hash == CONSTITUTIONAL_HASH
        assert service._initialized is False
        assert service._vault_available is False

    def test_service_init_with_config(self, vault_config):
        """Test service initialization with custom config."""
        service = VaultCryptoService(
            config=vault_config,
            fallback_enabled=False,
            cache_ttl=600,
            audit_enabled=False,
        )

        assert service.config == vault_config
        assert service.fallback_enabled is False
        assert service.cache_ttl == 600
        assert service.audit_enabled is False


class TestVaultCryptoServiceInitialize:
    """Tests for VaultCryptoService.initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_without_vault(self):
        """Test initialization when Vault is not available."""
        service = VaultCryptoService(fallback_enabled=True)

        # Mock no HTTP clients available
        with patch.dict("sys.modules", {"httpx": None, "aiohttp": None, "hvac": None}):
            result = await service.initialize()

        assert result["success"] is True
        assert result["vault_available"] is False
        assert result["fallback_available"] is True
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_initialize_with_httpx(
        self, vault_config, mock_httpx_client, mock_health_response
    ):
        """Test initialization with httpx client."""
        service = VaultCryptoService(config=vault_config)

        with patch("app.services.vault_http_client.HTTPX_AVAILABLE", True):
            with patch("app.services.vault_http_client.httpx") as mock_httpx:
                # Create mock client
                mock_client = MagicMock()
                mock_httpx.AsyncClient.return_value = mock_client

                async def mock_get(path):
                    response = MagicMock()
                    response.json.return_value = mock_health_response
                    return response

                mock_client.get = AsyncMock(side_effect=mock_get)

                result = await service.initialize()

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_initialize_with_override_params(self):
        """Test initialization with override parameters."""
        service = VaultCryptoService()

        result = await service.initialize(
            vault_addr="http://custom-vault:8200",
            token="custom-token",
        )

        assert service.config.address == "http://custom-vault:8200"
        assert service.config.token == "custom-token"
        assert result["success"] is True


class TestVaultCryptoServiceKeyGeneration:
    """Tests for key generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_keypair_fallback(self):
        """Test key generation with local fallback."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        result = await service.generate_keypair(
            key_name="test-key",
            key_type="ed25519",
        )

        assert result["success"] is True
        assert result["key_name"] == "test-key"
        assert result["key_type"] == "ed25519"
        assert "public_key" in result
        assert result["vault_path"] == "local://test-key"
        assert result.get("fallback_used") is True

    @pytest.mark.asyncio
    async def test_generate_keypair_multiple_types(self):
        """Test key generation for different key types."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        key_types = ["ed25519", "ecdsa-p256", "rsa-2048"]

        for key_type in key_types:
            result = await service.generate_keypair(
                key_name=f"test-{key_type}",
                key_type=key_type,
            )
            assert result["success"] is True
            assert result["key_type"] == key_type

    @pytest.mark.asyncio
    async def test_generate_keypair_no_fallback(self):
        """Test key generation fails when fallback disabled and Vault unavailable."""
        service = VaultCryptoService(fallback_enabled=False)
        await service.initialize()

        result = await service.generate_keypair(key_name="test-key")

        assert result["success"] is False
        assert "error" in result


class TestVaultCryptoServiceSigning:
    """Tests for signing functionality."""

    @pytest.mark.asyncio
    async def test_sign_with_fallback(self):
        """Test signing with local fallback."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate a key first
        key_result = await service.generate_keypair(key_name="sign-key")
        assert key_result["success"] is True

        # Sign data
        test_data = b"Test data to sign"
        signature = await service.sign(key_name="sign-key", data=test_data)

        assert signature is not None
        assert len(signature) > 0

    @pytest.mark.asyncio
    async def test_sign_missing_key(self):
        """Test signing with non-existent key."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        with pytest.raises(RuntimeError, match="Key not found"):
            await service.sign(key_name="nonexistent-key", data=b"test")

    @pytest.mark.asyncio
    async def test_sign_verify_roundtrip(self):
        """Test sign and verify roundtrip."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="roundtrip-key")

        # Sign data
        test_data = b"Data for roundtrip test"
        signature = await service.sign(key_name="roundtrip-key", data=test_data)

        # Verify signature
        is_valid = await service.verify(
            key_name="roundtrip-key",
            data=test_data,
            signature=signature,
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_invalid_signature(self):
        """Test verification fails with invalid signature."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="verify-key")

        # Try to verify invalid signature
        test_data = b"Original data"
        invalid_signature = base64.b64encode(b"invalid-signature").decode()

        is_valid = await service.verify(
            key_name="verify-key",
            data=test_data,
            signature=invalid_signature,
        )

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_tampered_data(self):
        """Test verification fails with tampered data."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="tamper-key")

        # Sign original data
        original_data = b"Original data"
        signature = await service.sign(key_name="tamper-key", data=original_data)

        # Verify with tampered data
        tampered_data = b"Tampered data"
        is_valid = await service.verify(
            key_name="tamper-key",
            data=tampered_data,
            signature=signature,
        )

        assert is_valid is False


class TestVaultCryptoServiceEncryption:
    """Tests for encryption/decryption functionality."""

    @pytest.mark.asyncio
    async def test_encrypt_with_fallback(self):
        """Test encryption with local fallback."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        plaintext = b"Secret message"
        ciphertext = await service.encrypt(key_name="encrypt-key", plaintext=plaintext)

        assert ciphertext is not None
        assert ciphertext.startswith("secure-fallback:")
        assert ciphertext != plaintext.decode()

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        plaintext = b"Sensitive data for encryption test"
        ciphertext = await service.encrypt(key_name="roundtrip-enc-key", plaintext=plaintext)
        decrypted = await service.decrypt(key_name="roundtrip-enc-key", ciphertext=ciphertext)

        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_different_keys_produce_different_output(self):
        """Test that different keys produce different ciphertext."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        plaintext = b"Same message"
        ciphertext1 = await service.encrypt(key_name="key-1", plaintext=plaintext)
        ciphertext2 = await service.encrypt(key_name="key-2", plaintext=plaintext)

        assert ciphertext1 != ciphertext2


class TestVaultCryptoServiceKeyRotation:
    """Tests for key rotation functionality."""

    @pytest.mark.asyncio
    async def test_rotate_key_fallback(self):
        """Test key rotation with local fallback."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate initial key
        await service.generate_keypair(key_name="rotate-key")
        original_public_key = await service.get_public_key(key_name="rotate-key")

        # Rotate key
        result = await service.rotate_key(key_name="rotate-key")

        assert result["success"] is True
        assert result.get("fallback_used") is True

        # Get new public key
        new_public_key = await service.get_public_key(key_name="rotate-key")
        assert new_public_key != original_public_key

    @pytest.mark.asyncio
    async def test_rotate_nonexistent_key(self):
        """Test rotation of non-existent key fails."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        result = await service.rotate_key(key_name="nonexistent-key")

        assert result["success"] is False
        assert "error" in result


class TestVaultCryptoServicePublicKey:
    """Tests for public key retrieval."""

    @pytest.mark.asyncio
    async def test_get_public_key(self):
        """Test public key retrieval."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        result = await service.generate_keypair(key_name="pubkey-test")
        expected_public_key = result["public_key"]

        # Get public key
        public_key = await service.get_public_key(key_name="pubkey-test")

        assert public_key == expected_public_key

    @pytest.mark.asyncio
    async def test_get_public_key_caching(self):
        """Test public key caching."""
        service = VaultCryptoService(fallback_enabled=True, cache_ttl=300)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="cache-test")

        # Get public key twice
        pk1 = await service.get_public_key(key_name="cache-test")
        pk2 = await service.get_public_key(key_name="cache-test")

        assert pk1 == pk2
        # Verify cache has entry
        assert "cache-test" in service._public_key_cache


class TestVaultCryptoServiceHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check returns status."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        health = await service.health_check()

        assert health["service"] == "VaultCryptoService"
        assert health["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert health["constitutional_valid"] is True
        assert health["fallback_enabled"] is True
        assert "timestamp" in health
        assert "cache_entries" in health

    @pytest.mark.asyncio
    async def test_health_check_with_local_keys(self):
        """Test health check reports local keys count."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate some keys
        await service.generate_keypair(key_name="health-key-1")
        await service.generate_keypair(key_name="health-key-2")

        health = await service.health_check()

        assert health["fallback_keys_count"] == 2


class TestVaultCryptoServicePolicySignature:
    """Tests for policy signature integration."""

    @pytest.mark.asyncio
    async def test_create_policy_signature(self, sample_policy_content):
        """Test creating a policy signature."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="policy-key")

        # Create signature
        signature = await service.create_policy_signature(
            policy_id="test-policy-001",
            version="1.0.0",
            content=sample_policy_content,
            key_name="policy-key",
        )

        assert signature.policy_id == "test-policy-001"
        assert signature.version == "1.0.0"
        assert signature.public_key is not None
        assert signature.signature is not None
        assert signature.key_fingerprint is not None

    @pytest.mark.asyncio
    async def test_verify_policy_signature(self, sample_policy_content):
        """Test verifying a policy signature."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="verify-policy-key")

        # Create signature
        signature = await service.create_policy_signature(
            policy_id="test-policy-002",
            version="1.0.0",
            content=sample_policy_content,
            key_name="verify-policy-key",
        )

        # Verify signature
        is_valid = await service.verify_policy_signature(
            content=sample_policy_content,
            signature=signature,
            key_name="verify-policy-key",
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_policy_signature_tampered_content(self, sample_policy_content):
        """Test that tampered content fails verification."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="tamper-policy-key")

        # Create signature with original content
        signature = await service.create_policy_signature(
            policy_id="test-policy-003",
            version="1.0.0",
            content=sample_policy_content,
            key_name="tamper-policy-key",
        )

        # Tamper with content
        tampered_content = sample_policy_content.copy()
        tampered_content["name"] = "Malicious Policy"

        # Verify should fail
        is_valid = await service.verify_policy_signature(
            content=tampered_content,
            signature=signature,
            key_name="tamper-policy-key",
        )

        assert is_valid is False


class TestVaultCryptoServiceAudit:
    """Tests for audit logging functionality."""

    @pytest.mark.asyncio
    async def test_audit_log_operations(self):
        """Test audit log captures operations."""
        service = VaultCryptoService(fallback_enabled=True, audit_enabled=True)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="audit-key")

        # Get audit log
        audit_log = service.get_audit_log()

        assert len(audit_log) >= 2  # At least initialize and generate_key
        operations = [e["operation"] for e in audit_log]
        assert "initialize" in operations
        assert "generate_key" in operations

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_operation(self):
        """Test filtering audit log by operation."""
        service = VaultCryptoService(fallback_enabled=True, audit_enabled=True)
        await service.initialize()

        # Generate multiple keys
        await service.generate_keypair(key_name="filter-key-1")
        await service.generate_keypair(key_name="filter-key-2")
        await service.get_public_key(key_name="filter-key-1")

        # Filter by operation
        key_ops = service.get_audit_log(operation=VaultOperation.GENERATE_KEY)
        pubkey_ops = service.get_audit_log(operation=VaultOperation.GET_PUBLIC_KEY)

        assert len(key_ops) == 2
        assert len(pubkey_ops) == 1

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_key_name(self):
        """Test filtering audit log by key name."""
        service = VaultCryptoService(fallback_enabled=True, audit_enabled=True)
        await service.initialize()

        # Operations on different keys
        await service.generate_keypair(key_name="key-alpha")
        await service.generate_keypair(key_name="key-beta")
        await service.get_public_key(key_name="key-alpha")

        # Filter by key name
        alpha_ops = service.get_audit_log(key_name="key-alpha")
        beta_ops = service.get_audit_log(key_name="key-beta")

        assert len(alpha_ops) == 2  # generate + get_public_key
        assert len(beta_ops) == 1  # generate only

    @pytest.mark.asyncio
    async def test_audit_log_clear(self):
        """Test clearing audit log."""
        service = VaultCryptoService(fallback_enabled=True, audit_enabled=True)
        await service.initialize()

        # Generate some operations
        await service.generate_keypair(key_name="clear-key")

        # Clear log
        count = service.clear_audit_log()

        assert count > 0
        assert len(service.get_audit_log()) == 0

    @pytest.mark.asyncio
    async def test_audit_disabled(self):
        """Test audit logging can be disabled."""
        service = VaultCryptoService(fallback_enabled=True, audit_enabled=False)
        await service.initialize()

        await service.generate_keypair(key_name="no-audit-key")

        audit_log = service.get_audit_log()
        assert len(audit_log) == 0


class TestVaultCryptoServiceConstitutional:
    """Tests for constitutional hash validation."""

    @pytest.mark.asyncio
    async def test_constitutional_hash_in_operations(self):
        """Test constitutional hash is validated in operations."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        assert service._constitutional_hash == CONSTITUTIONAL_HASH

        # Operations should succeed with valid hash
        result = await service.generate_keypair(key_name="constitutional-key")
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_constitutional_hash_mismatch_raises(self):
        """Test that constitutional hash mismatch raises error."""
        service = VaultCryptoService(fallback_enabled=True)
        service._constitutional_hash = "invalid_hash"  # Tamper with hash

        with pytest.raises(ValueError, match="Constitutional hash mismatch"):
            await service.generate_keypair(key_name="tampered-key")

    @pytest.mark.asyncio
    async def test_health_check_constitutional_status(self):
        """Test health check reports constitutional status."""
        service = VaultCryptoService(fallback_enabled=True)
        await service.initialize()

        health = await service.health_check()

        assert health["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert health["constitutional_valid"] is True


class TestVaultCryptoServiceContextManager:
    """Tests for context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager usage."""
        async with VaultCryptoService(fallback_enabled=True) as service:
            assert service._initialized is True

            result = await service.generate_keypair(key_name="context-key")
            assert result["success"] is True


class TestVaultCryptoServiceKeyTypeMapping:
    """Tests for key type mapping functionality."""

    def test_map_key_type_ed25519(self):
        """Test ED25519 key type mapping."""
        service = VaultCryptoService()
        assert service._map_key_type("ed25519") == "ed25519"
        assert service._map_key_type("ED25519") == "ed25519"

    def test_map_key_type_ecdsa(self):
        """Test ECDSA key type mapping."""
        service = VaultCryptoService()
        assert service._map_key_type("ecdsa") == "ecdsa-p256"
        assert service._map_key_type("ecdsa-p256") == "ecdsa-p256"
        assert service._map_key_type("ecdsa-p384") == "ecdsa-p384"

    def test_map_key_type_rsa(self):
        """Test RSA key type mapping."""
        service = VaultCryptoService()
        assert service._map_key_type("rsa") == "rsa-2048"
        assert service._map_key_type("rsa-2048") == "rsa-2048"
        assert service._map_key_type("rsa-4096") == "rsa-4096"

    def test_map_key_type_aes(self):
        """Test AES key type mapping."""
        service = VaultCryptoService()
        assert service._map_key_type("aes") == "aes256-gcm96"
        assert service._map_key_type("aes256-gcm96") == "aes256-gcm96"

    def test_map_key_type_unknown(self):
        """Test unknown key type passes through."""
        service = VaultCryptoService()
        assert service._map_key_type("custom-type") == "custom-type"


class TestVaultCryptoServiceCaching:
    """Tests for caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit returns cached value."""
        service = VaultCryptoService(fallback_enabled=True, cache_ttl=300)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="cache-hit-key")

        # First call populates cache
        pk1 = await service.get_public_key(key_name="cache-hit-key")

        # Verify cache entry exists
        assert "cache-hit-key" in service._public_key_cache

        # Second call should use cache
        pk2 = await service.get_public_key(key_name="cache-hit-key")

        assert pk1 == pk2

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_rotation(self):
        """Test cache is invalidated on key rotation."""
        service = VaultCryptoService(fallback_enabled=True, cache_ttl=300)
        await service.initialize()

        # Generate key
        await service.generate_keypair(key_name="invalidate-key")

        # Populate cache
        await service.get_public_key(key_name="invalidate-key")
        assert "invalidate-key" in service._public_key_cache

        # Rotate key
        await service.rotate_key(key_name="invalidate-key")

        # Cache should be invalidated
        assert "invalidate-key" not in service._public_key_cache


class TestCreateVaultCryptoServiceHelper:
    """Tests for create_vault_crypto_service helper function."""

    @pytest.mark.asyncio
    async def test_create_helper_basic(self):
        """Test helper function creates initialized service."""
        service = await create_vault_crypto_service(fallback_enabled=True)

        assert service._initialized is True
        assert service.fallback_enabled is True

    @pytest.mark.asyncio
    async def test_create_helper_with_params(self):
        """Test helper function accepts parameters."""
        service = await create_vault_crypto_service(
            vault_addr="http://custom:8200",
            token="custom-token",
            fallback_enabled=True,
        )

        assert service.config.address == "http://custom:8200"
        assert service.config.token == "custom-token"


class TestVaultKeyTypeEnum:
    """Tests for VaultKeyType enum."""

    def test_vault_key_type_values(self):
        """Test VaultKeyType enum values."""
        assert VaultKeyType.ED25519.value == "ed25519"
        assert VaultKeyType.ECDSA_P256.value == "ecdsa-p256"
        assert VaultKeyType.RSA_2048.value == "rsa-2048"
        assert VaultKeyType.RSA_4096.value == "rsa-4096"
        assert VaultKeyType.AES256_GCM96.value == "aes256-gcm96"


class TestVaultOperationEnum:
    """Tests for VaultOperation enum."""

    def test_vault_operation_values(self):
        """Test VaultOperation enum values."""
        assert VaultOperation.INITIALIZE.value == "initialize"
        assert VaultOperation.SIGN.value == "sign"
        assert VaultOperation.VERIFY.value == "verify"
        assert VaultOperation.ENCRYPT.value == "encrypt"
        assert VaultOperation.DECRYPT.value == "decrypt"
        assert VaultOperation.ROTATE_KEY.value == "rotate_key"
        assert VaultOperation.HEALTH_CHECK.value == "health_check"


# Integration test markers
@pytest.mark.integration
@pytest.mark.vault
class TestVaultCryptoServiceIntegration:
    """Integration tests requiring actual Vault connection.

    These tests are skipped by default. Run with:
    VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=your-token pytest -m vault
    """

    @pytest.fixture
    def vault_available(self):
        """Check if Vault is available for integration tests."""
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        if not vault_addr or not vault_token:
            pytest.skip("Vault not configured for integration tests")
        return True

    @pytest.mark.asyncio
    async def test_real_vault_connection(self, vault_available):
        """Test real Vault connection."""
        service = VaultCryptoService(fallback_enabled=False)
        result = await service.initialize()

        assert result["vault_available"] is True

    @pytest.mark.asyncio
    async def test_real_vault_key_operations(self, vault_available):
        """Test real Vault key operations."""
        import uuid

        key_name = f"integration-test-{uuid.uuid4().hex[:8]}"

        service = VaultCryptoService(fallback_enabled=False)
        await service.initialize()

        try:
            # Generate key
            result = await service.generate_keypair(key_name=key_name)
            assert result["success"] is True

            # Sign and verify
            data = b"Integration test data"
            signature = await service.sign(key_name=key_name, data=data)
            is_valid = await service.verify(key_name=key_name, data=data, signature=signature)
            assert is_valid is True

        finally:
            # Cleanup - note: Transit keys cannot be deleted by default
            pass
