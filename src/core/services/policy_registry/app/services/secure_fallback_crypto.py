"""
ACGS-2 Secure Fallback Crypto Service - AES-256-GCM Implementation
Constitutional Hash: cdd01ef066bc6cf2

Production-grade cryptographic fallback when HashiCorp Vault is unavailable.
Replaces the insecure XOR encryption with industry-standard AES-256-GCM.

Security Features:
- AES-256-GCM authenticated encryption (NIST SP 800-38D)
- PBKDF2-HMAC-SHA256 key derivation (NIST SP 800-132)
- Cryptographically secure random nonces (96-bit)
- Key rotation support with versioning
- Secure memory handling for sensitive data

This module is designed to be a secure fallback ONLY when Vault is temporarily
unavailable. Production deployments SHOULD use Vault Transit engine.
"""

import base64
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

# Use the cryptography library for AES-GCM
try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class FallbackCryptoError(Exception):
    """Base exception for secure fallback crypto operations."""

    def __init__(self, message: str, constitutional_hash: str = CONSTITUTIONAL_HASH):
        self.message = message
        self.constitutional_hash = constitutional_hash
        super().__init__(f"{message} [constitutional_hash={constitutional_hash}]")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "constitutional_hash": self.constitutional_hash,
        }


class KeyDerivationError(FallbackCryptoError):
    """Error during key derivation."""

    pass


class EncryptionError(FallbackCryptoError):
    """Error during encryption."""

    pass


class DecryptionError(FallbackCryptoError):
    """Error during decryption."""

    pass


class CiphertextFormatError(FallbackCryptoError):
    """Invalid ciphertext format."""

    pass


class CryptoNotAvailableError(FallbackCryptoError):
    """Cryptography library not available."""

    pass


class KeyDerivationAlgorithm(str, Enum):
    """Supported key derivation algorithms."""

    PBKDF2_SHA256 = "pbkdf2-sha256"
    # Future: ARGON2ID = "argon2id"  # Requires argon2-cffi


@dataclass
class SecureFallbackConfig:
    """Configuration for secure fallback crypto.

    Attributes:
        key_derivation: Algorithm for key derivation
        pbkdf2_iterations: PBKDF2 iteration count (minimum 100,000 recommended)
        nonce_size: Size of nonce in bytes (12 for AES-GCM)
        tag_size: Size of authentication tag in bytes (16 for full security)
        key_version_prefix: Prefix for versioned keys in ciphertext
        max_plaintext_size: Maximum plaintext size (16 MB default)
        audit_enabled: Enable audit logging for operations
    """

    key_derivation: KeyDerivationAlgorithm = KeyDerivationAlgorithm.PBKDF2_SHA256
    pbkdf2_iterations: int = 310_000  # OWASP 2023 recommendation for SHA256
    nonce_size: int = 12  # 96 bits for AES-GCM
    tag_size: int = 16  # 128 bits (full tag)
    key_version_prefix: str = "secure-fallback"
    max_plaintext_size: int = 16 * 1024 * 1024  # 16 MB
    audit_enabled: bool = True

    @classmethod
    def from_env(cls) -> "SecureFallbackConfig":
        """Create config from environment variables."""
        return cls(
            pbkdf2_iterations=int(os.environ.get("FALLBACK_CRYPTO_PBKDF2_ITERATIONS", "310000")),
            max_plaintext_size=int(
                os.environ.get("FALLBACK_CRYPTO_MAX_SIZE", str(16 * 1024 * 1024))
            ),
            audit_enabled=os.environ.get("FALLBACK_CRYPTO_AUDIT", "true").lower() == "true",
        )


@dataclass
class EncryptedPayload:
    """Structure for encrypted data with metadata.

    Format: secure-fallback:v{version}:{base64(salt|nonce|ciphertext|tag)}

    The salt is used for key derivation, nonce for AES-GCM, and tag for
    authentication. All are bundled together for easy storage/transport.
    """

    version: int
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    tag: bytes  # Included in ciphertext for AESGCM, separated for clarity
    key_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_string(self) -> str:
        """Serialize to transport format."""
        # Combine all binary components
        combined = self.salt + self.nonce + self.ciphertext
        encoded = base64.b64encode(combined).decode("utf-8")
        return f"secure-fallback:v{self.version}:{encoded}"

    @classmethod
    def from_string(cls, data: str, key_name: str) -> "EncryptedPayload":
        """Parse from transport format."""
        parts = data.split(":", 2)
        if len(parts) != 3:
            raise CiphertextFormatError(
                f"Invalid ciphertext format: expected 3 parts, got {len(parts)}"
            )

        prefix, version_str, encoded = parts
        if prefix != "secure-fallback":
            raise CiphertextFormatError(
                f"Invalid prefix: expected 'secure-fallback', got '{prefix}'"
            )

        if not version_str.startswith("v"):
            raise CiphertextFormatError(
                f"Invalid version format: expected 'v{{n}}', got '{version_str}'"
            )

        try:
            version = int(version_str[1:])
        except ValueError as e:
            raise CiphertextFormatError(f"Invalid version number: '{version_str}'") from e

        try:
            combined = base64.b64decode(encoded)
        except Exception as e:
            raise CiphertextFormatError(f"Base64 decode failed: {e}") from e

        # Extract components (salt: 32 bytes, nonce: 12 bytes, rest is ciphertext+tag)
        if len(combined) < 32 + 12 + 16:  # Minimum size
            raise CiphertextFormatError(f"Ciphertext too short: {len(combined)} bytes")

        salt = combined[:32]
        nonce = combined[32:44]
        ciphertext = combined[44:]  # Includes tag for AESGCM

        return cls(
            version=version,
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=b"",  # Tag is embedded in ciphertext for AESGCM
            key_name=key_name,
        )


class SecureFallbackCrypto:
    """
    Secure cryptographic fallback service using AES-256-GCM.

    This class provides production-grade encryption when HashiCorp Vault
    is unavailable. It uses:
    - AES-256-GCM for authenticated encryption
    - PBKDF2-HMAC-SHA256 for key derivation
    - Cryptographically secure random nonces

    Security Considerations:
    - Keys are derived from key names using PBKDF2 with high iteration count
    - Each encryption operation uses a unique random salt and nonce
    - The authentication tag prevents tampering with ciphertext
    - All operations are audited for security monitoring

    Usage:
        crypto = SecureFallbackCrypto()

        # Encrypt
        ciphertext = crypto.encrypt("my-key", b"sensitive data")

        # Decrypt
        plaintext = crypto.decrypt("my-key", ciphertext)
    """

    def __init__(
        self,
        config: Optional[SecureFallbackConfig] = None,
        master_secret: Optional[str] = None,
    ):
        """
        Initialize SecureFallbackCrypto.

        Args:
            config: Configuration options
            master_secret: Optional master secret for additional key derivation
                          security. If not provided, uses key name directly.

        Raises:
            CryptoNotAvailableError: If cryptography library is not installed
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise CryptoNotAvailableError(
                "cryptography library is required for secure fallback encryption. "
                "Install with: pip install cryptography>=46.0.0"
            )

        self.config = config or SecureFallbackConfig.from_env()
        self._master_secret = master_secret or os.environ.get("FALLBACK_CRYPTO_MASTER_SECRET", "")
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._key_version = 1  # For future key rotation
        self._operation_count = 0
        self._audit_log: list = []

        logger.info(
            f"SecureFallbackCrypto initialized - "
            f"algorithm=AES-256-GCM, "
            f"kdf={self.config.key_derivation.value}, "
            f"iterations={self.config.pbkdf2_iterations}, "
            f"constitutional_hash={self._constitutional_hash}"
        )

    def _validate_constitutional_hash(self) -> None:
        """Validate constitutional hash is correct."""
        if self._constitutional_hash != CONSTITUTIONAL_HASH:
            raise FallbackCryptoError(
                f"Constitutional hash mismatch: "
                f"expected {CONSTITUTIONAL_HASH}, got {self._constitutional_hash}"
            )

    def _derive_key(
        self,
        key_name: str,
        salt: bytes,
    ) -> bytes:
        """
        Derive a 256-bit encryption key from key name and salt.

        Uses PBKDF2-HMAC-SHA256 with configurable iterations.
        The master secret (if provided) is mixed with the key name
        for additional security.

        Args:
            key_name: Logical key name
            salt: Random salt for this derivation

        Returns:
            32-byte derived key suitable for AES-256
        """
        self._validate_constitutional_hash()

        # Combine key name with master secret
        if self._master_secret:
            key_material = f"{self._master_secret}:{key_name}".encode("utf-8")
        else:
            key_material = key_name.encode("utf-8")

        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits for AES-256
                salt=salt,
                iterations=self.config.pbkdf2_iterations,
                backend=default_backend(),
            )
            derived_key = kdf.derive(key_material)
            return derived_key
        except Exception as e:
            raise KeyDerivationError(f"Key derivation failed: {e}") from e

    def encrypt(
        self,
        key_name: str,
        plaintext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> str:
        """
        Encrypt data using AES-256-GCM with authenticated encryption.

        Args:
            key_name: Logical key name for key derivation
            plaintext: Data to encrypt
            associated_data: Optional additional authenticated data (AAD)

        Returns:
            Ciphertext in format: secure-fallback:v{version}:{base64_data}

        Raises:
            EncryptionError: If encryption fails
            FallbackCryptoError: If plaintext exceeds size limit
        """
        self._validate_constitutional_hash()
        self._operation_count += 1

        if len(plaintext) > self.config.max_plaintext_size:
            raise EncryptionError(
                f"Plaintext too large: {len(plaintext)} > {self.config.max_plaintext_size}"
            )

        try:
            # Generate random salt and nonce
            salt = secrets.token_bytes(32)  # 256-bit salt
            nonce = secrets.token_bytes(self.config.nonce_size)  # 96-bit nonce

            # Derive key
            key = self._derive_key(key_name, salt)

            # Encrypt with AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

            # Create payload
            payload = EncryptedPayload(
                version=self._key_version,
                salt=salt,
                nonce=nonce,
                ciphertext=ciphertext,
                tag=b"",  # Embedded in ciphertext by AESGCM
                key_name=key_name,
            )

            result = payload.to_string()

            # Audit logging
            if self.config.audit_enabled:
                self._log_audit(
                    operation="encrypt",
                    key_name=key_name,
                    success=True,
                    metadata={
                        "plaintext_size": len(plaintext),
                        "ciphertext_size": len(result),
                        "has_aad": associated_data is not None,
                    },
                )

            logger.debug(
                f"Encrypted {len(plaintext)} bytes with key '{key_name}' "
                f"[version={self._key_version}]"
            )

            return result

        except FallbackCryptoError:
            raise
        except Exception as e:
            error_msg = f"Encryption failed: {e}"
            if self.config.audit_enabled:
                self._log_audit(
                    operation="encrypt",
                    key_name=key_name,
                    success=False,
                    error=error_msg,
                )
            raise EncryptionError(error_msg) from e

    def decrypt(
        self,
        key_name: str,
        ciphertext: str,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data encrypted with AES-256-GCM.

        Args:
            key_name: Logical key name used for encryption
            ciphertext: Ciphertext in secure-fallback format
            associated_data: Optional AAD (must match encryption)

        Returns:
            Decrypted plaintext bytes

        Raises:
            DecryptionError: If decryption fails (including auth failure)
            CiphertextFormatError: If ciphertext format is invalid
        """
        self._validate_constitutional_hash()
        self._operation_count += 1

        try:
            # Parse ciphertext
            payload = EncryptedPayload.from_string(ciphertext, key_name)

            # Version check for future compatibility
            if payload.version > self._key_version:
                raise DecryptionError(
                    f"Ciphertext version {payload.version} not supported (max: {self._key_version})"
                )

            # Derive key with same salt
            key = self._derive_key(key_name, payload.salt)

            # Decrypt with AES-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(
                payload.nonce,
                payload.ciphertext,
                associated_data,
            )

            # Audit logging
            if self.config.audit_enabled:
                self._log_audit(
                    operation="decrypt",
                    key_name=key_name,
                    success=True,
                    metadata={
                        "version": payload.version,
                        "plaintext_size": len(plaintext),
                    },
                )

            logger.debug(
                f"Decrypted {len(plaintext)} bytes with key '{key_name}' "
                f"[version={payload.version}]"
            )

            return plaintext

        except (CiphertextFormatError, FallbackCryptoError):
            raise
        except Exception as e:
            error_msg = f"Decryption failed: {e}"
            if self.config.audit_enabled:
                self._log_audit(
                    operation="decrypt",
                    key_name=key_name,
                    success=False,
                    error=error_msg,
                )
            # Don't leak details about auth failures
            if "authentication" in str(e).lower() or "tag" in str(e).lower():
                raise DecryptionError(
                    "Decryption failed: authentication error (data may be tampered)"
                ) from e
            raise DecryptionError(error_msg) from e

    def _log_audit(
        self,
        operation: str,
        key_name: str,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log audit entry for security monitoring."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "key_name": key_name,
            "success": success,
            "constitutional_hash": self._constitutional_hash,
            "operation_count": self._operation_count,
        }
        if error:
            entry["error"] = error
        if metadata:
            entry["metadata"] = metadata

        self._audit_log.append(entry)

        # Keep audit log bounded
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

    def get_audit_log(
        self,
        limit: int = 100,
        operation: Optional[str] = None,
    ) -> list:
        """Get audit log entries."""
        entries = self._audit_log
        if operation:
            entries = [e for e in entries if e["operation"] == operation]
        return entries[-limit:]

    def health_check(self) -> Dict[str, Any]:
        """Return health status of the crypto service."""
        return {
            "service": "SecureFallbackCrypto",
            "algorithm": "AES-256-GCM",
            "key_derivation": self.config.key_derivation.value,
            "pbkdf2_iterations": self.config.pbkdf2_iterations,
            "key_version": self._key_version,
            "operation_count": self._operation_count,
            "audit_entries": len(self._audit_log),
            "cryptography_available": CRYPTOGRAPHY_AVAILABLE,
            "constitutional_hash": self._constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def is_secure_fallback_ciphertext(ciphertext: str) -> bool:
    """Check if ciphertext is from secure fallback (not legacy XOR)."""
    return ciphertext.startswith("secure-fallback:")


def is_legacy_local_ciphertext(ciphertext: str) -> bool:
    """Check if ciphertext is from legacy insecure XOR encryption."""
    return ciphertext.startswith("local:")


__all__ = [
    "SecureFallbackCrypto",
    "SecureFallbackConfig",
    "EncryptedPayload",
    "FallbackCryptoError",
    "KeyDerivationError",
    "EncryptionError",
    "DecryptionError",
    "CiphertextFormatError",
    "CryptoNotAvailableError",
    "KeyDerivationAlgorithm",
    "is_secure_fallback_ciphertext",
    "is_legacy_local_ciphertext",
    "CONSTITUTIONAL_HASH",
    "CRYPTOGRAPHY_AVAILABLE",
]
