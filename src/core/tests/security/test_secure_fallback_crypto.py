"""
Tests for Secure Fallback Crypto Service (AES-256-GCM)
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- AES-256-GCM encryption/decryption
- Key derivation security
- Authentication tag verification
- Error handling
- Backward compatibility with legacy format detection
"""

import base64
import os

# Set up path for imports
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.core.services.policy_registry.app.services.secure_fallback_crypto import (
    CONSTITUTIONAL_HASH,
    CRYPTOGRAPHY_AVAILABLE,
    CiphertextFormatError,
    DecryptionError,
    EncryptedPayload,
    EncryptionError,
    KeyDerivationAlgorithm,
    SecureFallbackConfig,
    SecureFallbackCrypto,
    is_legacy_local_ciphertext,
    is_secure_fallback_ciphertext,
)


@pytest.fixture
def crypto():
    """Create a SecureFallbackCrypto instance for testing."""
    config = SecureFallbackConfig(
        pbkdf2_iterations=1000,  # Lower for faster tests
        audit_enabled=True,
    )
    return SecureFallbackCrypto(config=config)


@pytest.fixture
def crypto_with_master():
    """Create instance with master secret."""
    config = SecureFallbackConfig(pbkdf2_iterations=1000)
    return SecureFallbackCrypto(config=config, master_secret="test-master-secret")


class TestSecureFallbackCrypto:
    """Test suite for SecureFallbackCrypto."""

    def test_constitutional_hash_validation(self, crypto):
        """Verify constitutional hash is validated."""
        assert crypto._constitutional_hash == CONSTITUTIONAL_HASH
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_encrypt_decrypt_roundtrip(self, crypto):
        """Test basic encrypt/decrypt cycle."""
        key_name = "test-key"
        plaintext = b"Hello, Constitutional AI!"

        ciphertext = crypto.encrypt(key_name, plaintext)
        decrypted = crypto.decrypt(key_name, ciphertext)

        assert decrypted == plaintext

    def test_encrypt_returns_secure_format(self, crypto):
        """Verify ciphertext has correct format prefix."""
        ciphertext = crypto.encrypt("test-key", b"test data")

        assert ciphertext.startswith("secure-fallback:v1:")
        assert is_secure_fallback_ciphertext(ciphertext)
        assert not is_legacy_local_ciphertext(ciphertext)

    def test_encrypt_produces_unique_ciphertext(self, crypto):
        """Each encryption should produce different ciphertext (due to random salt/nonce)."""
        key_name = "test-key"
        plaintext = b"Same plaintext"

        ciphertext1 = crypto.encrypt(key_name, plaintext)
        ciphertext2 = crypto.encrypt(key_name, plaintext)

        # Ciphertexts should be different due to random salt and nonce
        assert ciphertext1 != ciphertext2

        # But both should decrypt to same plaintext
        assert crypto.decrypt(key_name, ciphertext1) == plaintext
        assert crypto.decrypt(key_name, ciphertext2) == plaintext

    def test_wrong_key_fails_decryption(self, crypto):
        """Decryption with wrong key should fail."""
        ciphertext = crypto.encrypt("correct-key", b"secret data")

        with pytest.raises(DecryptionError) as exc_info:
            crypto.decrypt("wrong-key", ciphertext)

        # Should be authentication error
        assert (
            "authentication" in str(exc_info.value).lower()
            or "failed" in str(exc_info.value).lower()
        )

    def test_tampered_ciphertext_fails(self, crypto):
        """Tampering with ciphertext should be detected."""
        ciphertext = crypto.encrypt("test-key", b"secret data")

        # Tamper with the ciphertext
        parts = ciphertext.split(":", 2)
        encoded_data = base64.b64decode(parts[2])
        tampered_data = bytes([b ^ 0xFF for b in encoded_data[:10]]) + encoded_data[10:]
        tampered_ciphertext = f"{parts[0]}:{parts[1]}:{base64.b64encode(tampered_data).decode()}"

        with pytest.raises((DecryptionError, CiphertextFormatError)):
            crypto.decrypt("test-key", tampered_ciphertext)

    def test_large_plaintext(self, crypto):
        """Test encryption of larger data."""
        plaintext = b"A" * 100000  # 100KB

        ciphertext = crypto.encrypt("test-key", plaintext)
        decrypted = crypto.decrypt("test-key", ciphertext)

        assert decrypted == plaintext

    def test_empty_plaintext(self, crypto):
        """Test encryption of empty data."""
        plaintext = b""

        ciphertext = crypto.encrypt("test-key", plaintext)
        decrypted = crypto.decrypt("test-key", ciphertext)

        assert decrypted == plaintext

    def test_binary_plaintext(self, crypto):
        """Test encryption of binary data."""
        plaintext = bytes(range(256))

        ciphertext = crypto.encrypt("test-key", plaintext)
        decrypted = crypto.decrypt("test-key", ciphertext)

        assert decrypted == plaintext

    def test_unicode_key_names(self, crypto):
        """Test with unicode key names."""
        key_name = "测试密钥-αβγ"
        plaintext = b"test data"

        ciphertext = crypto.encrypt(key_name, plaintext)
        decrypted = crypto.decrypt(key_name, ciphertext)

        assert decrypted == plaintext

    def test_master_secret_affects_encryption(self, crypto, crypto_with_master):
        """Master secret should produce different keys."""
        key_name = "test-key"
        plaintext = b"test data"

        ciphertext1 = crypto.encrypt(key_name, plaintext)

        # Without master secret, should not decrypt ciphertext encrypted with master
        # (This won't work as expected because they use different KDF inputs)
        # The ciphertext from crypto_with_master should work with crypto_with_master
        ciphertext2 = crypto_with_master.encrypt(key_name, plaintext)

        assert crypto.decrypt(key_name, ciphertext1) == plaintext
        assert crypto_with_master.decrypt(key_name, ciphertext2) == plaintext

        # Cross-decryption should fail
        with pytest.raises(DecryptionError):
            crypto.decrypt(key_name, ciphertext2)

    def test_max_plaintext_size_exceeded(self, crypto):
        """Test that exceeding max size raises error."""
        crypto.config.max_plaintext_size = 100  # Set low limit
        plaintext = b"A" * 200

        with pytest.raises(EncryptionError) as exc_info:
            crypto.encrypt("test-key", plaintext)

        assert "too large" in str(exc_info.value).lower()

    def test_audit_logging(self, crypto):
        """Test that operations are logged."""
        crypto.encrypt("test-key", b"data")
        crypto.encrypt("test-key", b"data")

        log = crypto.get_audit_log()
        assert len(log) >= 2

        # Check log entry structure
        entry = log[-1]
        assert "operation" in entry
        assert "key_name" in entry
        assert "success" in entry
        assert "constitutional_hash" in entry
        assert entry["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_health_check(self, crypto):
        """Test health check returns expected structure."""
        health = crypto.health_check()

        assert health["service"] == "SecureFallbackCrypto"
        assert health["algorithm"] == "AES-256-GCM"
        assert health["key_derivation"] == "pbkdf2-sha256"
        assert health["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "operation_count" in health
        assert "timestamp" in health


class TestEncryptedPayload:
    """Test EncryptedPayload serialization."""

    def test_to_string_and_from_string(self):
        """Test roundtrip serialization using crypto service."""
        # Use the actual crypto service for proper serialization
        config = SecureFallbackConfig(pbkdf2_iterations=1000)
        crypto = SecureFallbackCrypto(config=config)

        # Encrypt to get properly formatted ciphertext
        key_name = "test-key"
        plaintext = b"test data for roundtrip"
        ciphertext_str = crypto.encrypt(key_name, plaintext)

        # Parse the ciphertext
        parsed = EncryptedPayload.from_string(ciphertext_str, key_name)

        assert parsed.version == 1
        assert len(parsed.salt) == 32
        assert len(parsed.nonce) == 12
        assert len(parsed.ciphertext) > 0

    def test_invalid_format_raises_error(self):
        """Test invalid format detection."""
        with pytest.raises(CiphertextFormatError):
            EncryptedPayload.from_string("invalid-format", "key")

        with pytest.raises(CiphertextFormatError):
            EncryptedPayload.from_string("wrong:prefix:data", "key")

        with pytest.raises(CiphertextFormatError):
            EncryptedPayload.from_string("secure-fallback:vinvalid:data", "key")


class TestCiphertextDetection:
    """Test ciphertext format detection."""

    def test_detect_secure_fallback(self):
        """Test secure fallback detection."""
        assert is_secure_fallback_ciphertext("secure-fallback:v1:abc123")
        assert not is_secure_fallback_ciphertext("local:v1:abc123")
        assert not is_secure_fallback_ciphertext("vault:v1:abc123")

    def test_detect_legacy_local(self):
        """Test legacy local detection."""
        assert is_legacy_local_ciphertext("local:v1:abc123")
        assert not is_legacy_local_ciphertext("secure-fallback:v1:abc123")
        assert not is_legacy_local_ciphertext("vault:v1:abc123")


class TestConfigFromEnv:
    """Test configuration from environment."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SecureFallbackConfig()

        assert config.key_derivation == KeyDerivationAlgorithm.PBKDF2_SHA256
        assert config.pbkdf2_iterations == 310_000
        assert config.nonce_size == 12
        assert config.tag_size == 16

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("FALLBACK_CRYPTO_PBKDF2_ITERATIONS", "500000")
        monkeypatch.setenv("FALLBACK_CRYPTO_AUDIT", "false")

        config = SecureFallbackConfig.from_env()

        assert config.pbkdf2_iterations == 500000
        assert config.audit_enabled is False


@pytest.mark.skipif(not CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
class TestCryptographyDependency:
    """Test cryptography dependency handling."""

    def test_crypto_available(self):
        """Verify cryptography is available."""
        assert CRYPTOGRAPHY_AVAILABLE is True

    def test_aesgcm_operations(self):
        """Test direct AESGCM operations."""
        import secrets

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        plaintext = b"test data"

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)

        assert decrypted == plaintext


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
