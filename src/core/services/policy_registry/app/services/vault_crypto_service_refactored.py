"""
ACGS-2 Vault Crypto Service - OpenBao/Vault Integration Layer
Constitutional Hash: cdd01ef066bc6cf2

Production-ready cryptographic service wrapping operations through OpenBao/Vault:
- Transit secrets engine for signing/verification
- KV secrets engine for key storage
- Support for Ed25519, ECDSA-P256, RSA-2048 key types
- Graceful fallback to local CryptoService if Vault unavailable

This is the refactored version importing from focused modules:
- vault_models.py: Data models and enums
- vault_http_client.py: HTTP communication layer
- vault_transit.py: Transit engine operations
- vault_kv.py: KV secrets engine operations
- vault_audit.py: Audit logging
- vault_cache.py: Caching layer
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .vault_http_client import (
    VaultHttpClient,
)

# Import from refactored modules
from .vault_models import (
    CONSTITUTIONAL_HASH,
    VaultAuditEntry,
    VaultConfig,
    VaultKeyType,
    VaultOperation,
)

# Backward compatibility: re-export httpx for test patching
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore
from ..models import PolicySignature

# Local fallback
from .crypto_service import CryptoService
from .vault_audit import VaultAuditLogger
from .vault_cache import VaultCacheManager
from .vault_kv import VaultKVOperations
from .vault_transit import VaultTransitOperations

logger = logging.getLogger(__name__)


class VaultCryptoService:
    """
    Vault-backed cryptographic service for ACGS-2.

    Provides enterprise-grade cryptographic operations through HashiCorp Vault
    or OpenBao with graceful fallback to local CryptoService.

    Features:
    - Transit secrets engine for signing/verification/encryption
    - KV secrets engine for secure key storage
    - Support for Ed25519, ECDSA-P256, RSA-2048 key types
    - Public key caching for performance
    - Comprehensive audit logging
    - Constitutional hash validation on all operations
    """

    def __init__(
        self,
        config: Optional[VaultConfig] = None,
        fallback_enabled: bool = True,
        cache_ttl: int = 300,
        audit_enabled: bool = True,
    ):
        """
        Initialize VaultCryptoService.

        Args:
            config: Vault configuration (uses env vars if None)
            fallback_enabled: Enable fallback to local CryptoService
            cache_ttl: Cache TTL for public keys in seconds
            audit_enabled: Enable audit logging
        """
        self.config = config or VaultConfig.from_env()
        self.fallback_enabled = fallback_enabled
        self.cache_ttl = cache_ttl
        self.audit_enabled = audit_enabled

        # State
        self._initialized = False
        self._vault_available = False

        # Initialize HTTP client
        self._http_client = VaultHttpClient(self.config)

        # Initialize operation handlers
        self._transit: Optional[VaultTransitOperations] = None
        self._kv: Optional[VaultKVOperations] = None

        # Initialize cache manager
        self._cache = VaultCacheManager(default_ttl=cache_ttl)

        # Initialize audit logger
        self._audit_logger = VaultAuditLogger(enabled=audit_enabled)

        # Local fallback service
        self._local_crypto = CryptoService() if fallback_enabled else None
        self._local_keys: Dict[str, tuple[str, str]] = {}  # key_name -> (public, private)

        # Constitutional compliance
        self._constitutional_hash = CONSTITUTIONAL_HASH

        logger.info(
            f"VaultCryptoService initialized - "
            f"constitutional_hash={self._constitutional_hash}, "
            f"fallback_enabled={fallback_enabled}"
        )

    async def initialize(
        self,
        vault_addr: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initialize Vault client connection.

        Args:
            vault_addr: Vault server address (overrides config)
            token: Vault token (overrides config)

        Returns:
            Dict with initialization status and details
        """
        if vault_addr:
            self.config.address = vault_addr
        if token:
            self.config.token = token

        result = await self._http_client.initialize()
        self._vault_available = result.get("vault_available", False)

        # Success if vault is available OR fallback is enabled
        result["success"] = self._vault_available or self.fallback_enabled

        if self._vault_available:
            # Initialize operation handlers
            self._transit = VaultTransitOperations(
                self._http_client, transit_mount=self.config.transit_mount
            )
            self._kv = VaultKVOperations(
                self._http_client, kv_mount=self.config.kv_mount, kv_version=self.config.kv_version
            )

        result["fallback_available"] = self.fallback_enabled
        self._initialized = True

        self._audit_logger.log(
            VaultOperation.INITIALIZE,
            success=self._vault_available,
            error_message=result.get("error"),
            metadata={"connection_method": result.get("connection_method", "none")},
        )

        return result

    async def generate_keypair(
        self,
        key_name: str,
        key_type: str = "ed25519",
        exportable: bool = False,
        allow_plaintext_backup: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a new key pair in Vault Transit engine.

        Args:
            key_name: Name for the key in Vault
            key_type: Key type (ed25519, ecdsa-p256, rsa-2048, rsa-4096)
            exportable: Whether key can be exported
            allow_plaintext_backup: Allow plaintext backup of key

        Returns:
            Dict with key information including public key
        """
        self._validate_constitutional_hash()

        vault_type = self._map_key_type(key_type)
        result: Dict[str, Any] = {
            "key_name": key_name,
            "key_type": key_type,
            "vault_type": vault_type,
            "success": False,
            "constitutional_hash": self._constitutional_hash,
        }

        try:
            if self._vault_available and self._transit:
                await self._transit.create_key(
                    key_name=key_name,
                    key_type=vault_type,
                    exportable=exportable,
                    allow_plaintext_backup=allow_plaintext_backup,
                )
                public_key = await self.get_public_key(key_name)
                result["public_key"] = public_key
                result["vault_path"] = f"{self.config.transit_mount}/keys/{key_name}"
                result["success"] = True

            elif self.fallback_enabled and self._local_crypto:
                public_b64, private_b64 = self._local_crypto.generate_keypair()
                self._local_keys[key_name] = (public_b64, private_b64)
                result["public_key"] = public_b64
                result["vault_path"] = f"local://{key_name}"
                result["fallback_used"] = True
                result["success"] = True
                logger.info(f"Generated key locally (fallback): {key_name}")

            else:
                raise RuntimeError("Vault unavailable and fallback disabled")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Key generation failed for {key_name}: {e}")

        self._audit_logger.log(
            VaultOperation.GENERATE_KEY,
            key_name=key_name,
            success=result["success"],
            error_message=result.get("error"),
            metadata={"key_type": key_type, "exportable": exportable},
        )

        return result

    async def sign(
        self,
        key_name: str,
        data: bytes,
        hash_algorithm: str = "sha2-256",
        prehashed: bool = False,
    ) -> str:
        """
        Sign data using Vault Transit engine.

        Args:
            key_name: Name of the signing key
            data: Data to sign
            hash_algorithm: Hash algorithm (sha2-256, sha2-384, sha2-512)
            prehashed: Whether data is already hashed

        Returns:
            Base64-encoded signature
        """
        self._validate_constitutional_hash()

        signature = ""
        error_msg = None

        try:
            if self._vault_available and self._transit:
                signature = await self._transit.sign(
                    key_name=key_name,
                    data=data,
                    hash_algorithm=hash_algorithm,
                    prehashed=prehashed,
                )

            elif self.fallback_enabled and key_name in self._local_keys:
                _, private_key = self._local_keys[key_name]
                content = {"data": base64.b64encode(data).decode("utf-8")}
                signature = self._local_crypto.sign_policy_content(content, private_key)

            else:
                raise RuntimeError(f"Key not found and Vault unavailable: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Signing failed for key {key_name}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.SIGN,
                key_name=key_name,
                success=error_msg is None,
                error_message=error_msg,
                metadata={"hash_algorithm": hash_algorithm, "data_size": len(data)},
            )

        return signature

    async def verify(
        self,
        key_name: str,
        data: bytes,
        signature: str,
        hash_algorithm: str = "sha2-256",
        prehashed: bool = False,
    ) -> bool:
        """
        Verify signature using Vault Transit engine.

        Args:
            key_name: Name of the signing key
            data: Original data
            signature: Signature to verify
            hash_algorithm: Hash algorithm used for signing
            prehashed: Whether data is already hashed

        Returns:
            True if signature is valid
        """
        self._validate_constitutional_hash()

        is_valid = False
        error_msg = None

        try:
            if self._vault_available and self._transit:
                is_valid = await self._transit.verify(
                    key_name=key_name,
                    data=data,
                    signature=signature,
                    hash_algorithm=hash_algorithm,
                    prehashed=prehashed,
                )

            elif self.fallback_enabled and key_name in self._local_keys:
                public_key, _ = self._local_keys[key_name]
                content = {"data": base64.b64encode(data).decode("utf-8")}
                is_valid = self._local_crypto.verify_policy_signature(
                    content, signature, public_key
                )

            else:
                raise RuntimeError(f"Key not found and Vault unavailable: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Verification failed for key {key_name}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.VERIFY,
                key_name=key_name,
                success=error_msg is None,
                error_message=error_msg,
                metadata={"valid": is_valid, "hash_algorithm": hash_algorithm},
            )

        return is_valid

    async def encrypt(
        self,
        key_name: str,
        plaintext: bytes,
        context: Optional[bytes] = None,
    ) -> str:
        """
        Encrypt data using Vault Transit engine.

        Args:
            key_name: Name of the encryption key
            plaintext: Data to encrypt
            context: Optional context for key derivation

        Returns:
            Vault ciphertext string (vault:v1:...)
        """
        self._validate_constitutional_hash()

        ciphertext = ""
        error_msg = None

        try:
            if self._vault_available and self._transit:
                ciphertext = await self._transit.encrypt(
                    key_name=key_name,
                    plaintext=plaintext,
                    context=context,
                )

            elif self.fallback_enabled:
                import secrets

                nonce = secrets.token_bytes(12)
                key_bytes = hashlib.sha256(key_name.encode()).digest()
                encrypted = bytes(
                    a ^ b
                    for a, b in zip(plaintext, key_bytes * (len(plaintext) // 32 + 1), strict=False)
                )
                ciphertext = f"local:v1:{base64.b64encode(nonce + encrypted).decode()}"
                logger.warning("Using insecure local encryption fallback - not for production")

            else:
                raise RuntimeError("Vault unavailable and fallback disabled")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Encryption failed for key {key_name}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.ENCRYPT,
                key_name=key_name,
                success=error_msg is None,
                error_message=error_msg,
                metadata={"plaintext_size": len(plaintext)},
            )

        return ciphertext

    async def decrypt(
        self,
        key_name: str,
        ciphertext: str,
        context: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data using Vault Transit engine.

        Args:
            key_name: Name of the encryption key
            ciphertext: Vault ciphertext string
            context: Optional context for key derivation

        Returns:
            Decrypted plaintext bytes
        """
        self._validate_constitutional_hash()

        plaintext = b""
        error_msg = None

        try:
            if ciphertext.startswith("local:"):
                if not self.fallback_enabled:
                    raise RuntimeError("Local ciphertext but fallback disabled")
                _, _, encoded = ciphertext.split(":", 2)
                data = base64.b64decode(encoded)
                _nonce, encrypted = data[:12], data[12:]
                key_bytes = hashlib.sha256(key_name.encode()).digest()
                plaintext = bytes(
                    a ^ b
                    for a, b in zip(encrypted, key_bytes * (len(encrypted) // 32 + 1), strict=False)
                )
                logger.warning("Using insecure local decryption fallback - not for production")

            elif self._vault_available and self._transit:
                plaintext = await self._transit.decrypt(
                    key_name=key_name,
                    ciphertext=ciphertext,
                    context=context,
                )

            else:
                raise RuntimeError("Vault unavailable and cannot decrypt Vault ciphertext")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Decryption failed for key {key_name}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.DECRYPT,
                key_name=key_name,
                success=error_msg is None,
                error_message=error_msg,
            )

        return plaintext

    async def rotate_key(self, key_name: str) -> Dict[str, Any]:
        """
        Rotate encryption key in Vault Transit engine.

        Args:
            key_name: Name of the key to rotate

        Returns:
            Dict with rotation result and new key version
        """
        self._validate_constitutional_hash()

        result: Dict[str, Any] = {
            "key_name": key_name,
            "success": False,
            "constitutional_hash": self._constitutional_hash,
        }

        try:
            if self._vault_available and self._transit:
                await self._transit.rotate_key(key_name)
                key_info = await self._transit.get_key_info(key_name)
                result["new_version"] = key_info.get("latest_version")
                result["success"] = True
                self._cache.invalidate_key(key_name)

            elif self.fallback_enabled and key_name in self._local_keys:
                public_b64, private_b64 = self._local_crypto.generate_keypair()
                self._local_keys[key_name] = (public_b64, private_b64)
                result["new_version"] = 1
                result["fallback_used"] = True
                result["success"] = True
                # Invalidate cache for rotated key
                self._cache.invalidate_key(key_name)
                logger.info(f"Rotated local key: {key_name}")

            else:
                raise RuntimeError(f"Key not found: {key_name}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Key rotation failed for {key_name}: {e}")

        self._audit_logger.log(
            VaultOperation.ROTATE_KEY,
            key_name=key_name,
            success=result["success"],
            error_message=result.get("error"),
            metadata={"new_version": result.get("new_version")},
        )

        return result

    async def get_public_key(self, key_name: str) -> str:
        """
        Get public key from Vault Transit engine.

        Args:
            key_name: Name of the key

        Returns:
            Base64-encoded public key
        """
        self._validate_constitutional_hash()

        # Check cache first
        cached = self._cache.public_keys.get(key_name)
        if cached:
            return cached

        public_key = ""
        error_msg = None

        try:
            if self._vault_available and self._transit:
                public_key = await self._transit.get_public_key(key_name)
                self._cache.public_keys.set(key_name, public_key)

            elif self.fallback_enabled and key_name in self._local_keys:
                public_key, _ = self._local_keys[key_name]
                # Cache fallback public keys too
                self._cache.public_keys.set(key_name, public_key)

            else:
                raise RuntimeError(f"Key not found: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Get public key failed for {key_name}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.GET_PUBLIC_KEY,
                key_name=key_name,
                success=error_msg is None,
                error_message=error_msg,
            )

        return public_key

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health and service status.

        Returns:
            Dict with health status information
        """
        cache_stats = self._cache.get_stats()
        result = {
            "service": "VaultCryptoService",
            "constitutional_hash": self._constitutional_hash,
            "constitutional_valid": True,
            "vault_configured": bool(self.config.address and self.config.token),
            "vault_available": self._vault_available,
            "fallback_enabled": self.fallback_enabled,
            "fallback_keys_count": len(self._local_keys),
            "cache_stats": cache_stats,
            # Backward compatibility - total cache entries
            "cache_entries": (
                cache_stats.get("public_keys", {}).get("entries", 0)
                + cache_stats.get("key_info", {}).get("entries", 0)
            ),
            "audit_entries_count": self._audit_logger.entry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._vault_available:
            try:
                health = await self._http_client.health_check()
                result["vault_health"] = health.get("health", {})
            except Exception as e:
                result["vault_health_error"] = str(e)

        self._audit_logger.log(VaultOperation.HEALTH_CHECK, success=True)

        return result

    # KV Secrets Engine methods

    async def store_secret(
        self,
        path: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Store a secret in Vault KV engine.

        Args:
            path: Secret path
            data: Secret data
            metadata: Optional metadata

        Returns:
            Dict with storage result
        """
        self._validate_constitutional_hash()

        result: Dict[str, Any] = {"path": path, "success": False}

        try:
            if self._vault_available and self._kv:
                await self._kv.put(path, data, metadata)
                result["success"] = True
                result["version"] = 1

            else:
                raise RuntimeError("Vault unavailable for secret storage")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Store secret failed for {path}: {e}")

        self._audit_logger.log(
            VaultOperation.STORE_SECRET,
            success=result["success"],
            error_message=result.get("error"),
            metadata={"path": path},
        )

        return result

    async def get_secret(self, path: str, version: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a secret from Vault KV engine.

        Args:
            path: Secret path
            version: Specific version (None for latest)

        Returns:
            Secret data
        """
        self._validate_constitutional_hash()

        data: Dict[str, Any] = {}
        error_msg = None

        try:
            if self._vault_available and self._kv:
                data = await self._kv.get(path, version)

            else:
                raise RuntimeError("Vault unavailable for secret retrieval")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Get secret failed for {path}: {e}")
            raise

        finally:
            self._audit_logger.log(
                VaultOperation.GET_SECRET,
                success=error_msg is None,
                error_message=error_msg,
                metadata={"path": path, "version": version},
            )

        return data

    async def delete_secret(self, path: str) -> Dict[str, Any]:
        """
        Delete a secret from Vault KV engine.

        Args:
            path: Secret path

        Returns:
            Dict with deletion result
        """
        self._validate_constitutional_hash()

        result: Dict[str, Any] = {"path": path, "success": False}

        try:
            if self._vault_available and self._kv:
                await self._kv.delete(path)
                result["success"] = True

            else:
                raise RuntimeError("Vault unavailable for secret deletion")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Delete secret failed for {path}: {e}")

        self._audit_logger.log(
            VaultOperation.DELETE_SECRET,
            success=result["success"],
            error_message=result.get("error"),
            metadata={"path": path},
        )

        return result

    # Policy signature integration

    async def create_policy_signature(
        self,
        policy_id: str,
        version: str,
        content: Dict[str, Any],
        key_name: str,
    ) -> PolicySignature:
        """
        Create a policy signature using Vault.

        Args:
            policy_id: Policy identifier
            version: Policy version
            content: Policy content to sign
            key_name: Key to use for signing

        Returns:
            PolicySignature object
        """
        self._validate_constitutional_hash()

        content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
        content_bytes = content_str.encode("utf-8")

        signature = await self.sign(key_name, content_bytes)
        public_key = await self.get_public_key(key_name)

        public_bytes = base64.b64decode(public_key)
        fingerprint = hashlib.sha256(public_bytes).hexdigest()

        return PolicySignature(
            policy_id=policy_id,
            version=version,
            public_key=public_key,
            signature=signature,
            key_fingerprint=fingerprint,
        )

    async def verify_policy_signature(
        self,
        content: Dict[str, Any],
        signature: PolicySignature,
        key_name: str,
    ) -> bool:
        """
        Verify a policy signature using Vault.

        Args:
            content: Policy content
            signature: PolicySignature object
            key_name: Key used for signing

        Returns:
            True if signature is valid
        """
        self._validate_constitutional_hash()

        content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
        content_bytes = content_str.encode("utf-8")

        return await self.verify(key_name, content_bytes, signature.signature)

    # Audit methods

    def get_audit_log(
        self,
        limit: int = 100,
        operation: Optional[VaultOperation] = None,
        key_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            limit: Maximum entries to return
            operation: Filter by operation type
            key_name: Filter by key name

        Returns:
            List of audit entries
        """
        return self._audit_logger.get_entries(
            limit=limit,
            operation=operation,
            key_name=key_name,
        )

    def clear_audit_log(self) -> int:
        """Clear audit log and return count of cleared entries."""
        return self._audit_logger.clear()

    # Backward compatibility properties

    @property
    def _public_key_cache(self) -> Dict[str, Any]:
        """Backward compatibility: access public key cache dict."""
        # Return internal cache dict for test compatibility
        return self._cache.public_keys._cache

    @property
    def _key_info_cache(self) -> Dict[str, Any]:
        """Backward compatibility: access key info cache dict."""
        return self._cache.key_info._cache

    @property
    def _audit_log(self) -> List[VaultAuditEntry]:
        """Backward compatibility: access audit log list."""
        return self._audit_logger._audit_log

    # Private helper methods

    def _validate_constitutional_hash(self) -> None:
        """Validate constitutional hash is correct."""
        if self._constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(
                f"Constitutional hash mismatch: "
                f"expected {CONSTITUTIONAL_HASH}, got {self._constitutional_hash}"
            )

    def _map_key_type(self, key_type: str) -> str:
        """Map common key type names to Vault Transit types."""
        mapping = {
            "ed25519": "ed25519",
            "ecdsa": "ecdsa-p256",
            "ecdsa-p256": "ecdsa-p256",
            "ecdsa-p384": "ecdsa-p384",
            "ecdsa-p521": "ecdsa-p521",
            "rsa": "rsa-2048",
            "rsa-2048": "rsa-2048",
            "rsa-4096": "rsa-4096",
            "aes": "aes256-gcm96",
            "aes256-gcm96": "aes256-gcm96",
        }
        return mapping.get(key_type.lower(), key_type)

    # Context manager support

    async def __aenter__(self) -> "VaultCryptoService":
        """Async context manager entry."""
        if not self._initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self._http_client.close()


# Convenience functions


async def create_vault_crypto_service(
    vault_addr: Optional[str] = None,
    token: Optional[str] = None,
    fallback_enabled: bool = True,
) -> VaultCryptoService:
    """
    Create and initialize a VaultCryptoService.

    Args:
        vault_addr: Vault server address
        token: Vault token
        fallback_enabled: Enable local fallback

    Returns:
        Initialized VaultCryptoService
    """
    config = VaultConfig.from_env()
    if vault_addr:
        config.address = vault_addr
    if token:
        config.token = token

    service = VaultCryptoService(config=config, fallback_enabled=fallback_enabled)
    await service.initialize()
    return service


__all__ = [
    "VaultCryptoService",
    "VaultConfig",
    "VaultKeyType",
    "VaultOperation",
    "VaultAuditEntry",
    "create_vault_crypto_service",
    "CONSTITUTIONAL_HASH",
]
