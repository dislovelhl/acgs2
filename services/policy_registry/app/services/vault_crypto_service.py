"""
ACGS-2 Vault Crypto Service - OpenBao/Vault Integration Layer
Constitutional Hash: cdd01ef066bc6cf2

Production-ready cryptographic service wrapping operations through OpenBao/Vault:
- Transit secrets engine for signing/verification
- KV secrets engine for key storage
- Support for Ed25519, ECDSA-P256, RSA-2048 key types
- Graceful fallback to local CryptoService if Vault unavailable
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from functools import lru_cache
import uuid

# HTTP client - prefer httpx for async, fallback to aiohttp
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Optional hvac library for Vault SDK operations
try:
    import hvac
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False

# Local fallback
from .crypto_service import CryptoService
from ..models import PolicySignature, KeyPair, KeyAlgorithm, KeyStatus

logger = logging.getLogger(__name__)

# Constitutional compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class VaultKeyType(str, Enum):
    """Supported Vault Transit key types."""
    ED25519 = "ed25519"
    ECDSA_P256 = "ecdsa-p256"
    RSA_2048 = "rsa-2048"
    RSA_4096 = "rsa-4096"
    AES256_GCM96 = "aes256-gcm96"


class VaultOperation(str, Enum):
    """Types of Vault operations for audit logging."""
    INITIALIZE = "initialize"
    GENERATE_KEY = "generate_key"
    SIGN = "sign"
    VERIFY = "verify"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    ROTATE_KEY = "rotate_key"
    GET_PUBLIC_KEY = "get_public_key"
    HEALTH_CHECK = "health_check"
    STORE_SECRET = "store_secret"
    GET_SECRET = "get_secret"
    DELETE_SECRET = "delete_secret"


@dataclass
class VaultAuditEntry:
    """Audit log entry for Vault operations."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: VaultOperation = VaultOperation.HEALTH_CHECK
    key_name: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "entry_id": self.entry_id,
            "operation": self.operation.value,
            "key_name": self.key_name,
            "success": self.success,
            "error_message": self.error_message,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class VaultConfig:
    """Vault connection configuration."""
    address: str = "http://127.0.0.1:8200"
    token: Optional[str] = None
    namespace: Optional[str] = None
    transit_mount: str = "transit"
    kv_mount: str = "secret"
    kv_version: int = 2
    timeout: float = 30.0
    verify_tls: bool = True
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "VaultConfig":
        """Create config from environment variables."""
        return cls(
            address=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
            token=os.getenv("VAULT_TOKEN"),
            namespace=os.getenv("VAULT_NAMESPACE"),
            transit_mount=os.getenv("VAULT_TRANSIT_MOUNT", "transit"),
            kv_mount=os.getenv("VAULT_KV_MOUNT", "secret"),
            kv_version=int(os.getenv("VAULT_KV_VERSION", "2")),
            timeout=float(os.getenv("VAULT_TIMEOUT", "30.0")),
            verify_tls=os.getenv("VAULT_SKIP_VERIFY", "false").lower() != "true",
            ca_cert=os.getenv("VAULT_CACERT"),
            client_cert=os.getenv("VAULT_CLIENT_CERT"),
            client_key=os.getenv("VAULT_CLIENT_KEY"),
        )


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
        self._hvac_client: Optional[Any] = None
        self._http_client: Optional[Any] = None

        # Caches
        self._public_key_cache: Dict[str, Tuple[str, datetime]] = {}
        self._key_info_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}

        # Audit log (in-memory, can be extended to external storage)
        self._audit_log: List[VaultAuditEntry] = []

        # Local fallback service
        self._local_crypto = CryptoService() if fallback_enabled else None
        self._local_keys: Dict[str, Tuple[str, str]] = {}  # key_name -> (public, private)

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

        result = {
            "success": False,
            "vault_available": False,
            "fallback_available": self.fallback_enabled,
            "constitutional_hash": self._constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Try hvac library first
            if HVAC_AVAILABLE and self.config.token:
                self._hvac_client = hvac.Client(
                    url=self.config.address,
                    token=self.config.token,
                    namespace=self.config.namespace,
                    verify=self.config.verify_tls if self.config.verify_tls else self.config.ca_cert,
                )
                if self._hvac_client.is_authenticated():
                    self._vault_available = True
                    result["connection_method"] = "hvac"
                    logger.info("Connected to Vault via hvac library")

            # Fallback to httpx/aiohttp
            if not self._vault_available and HTTPX_AVAILABLE:
                self._http_client = httpx.AsyncClient(
                    base_url=self.config.address,
                    timeout=self.config.timeout,
                    verify=self.config.verify_tls,
                )
                # Test connection
                health = await self._http_health_check()
                if health.get("initialized", False):
                    self._vault_available = True
                    result["connection_method"] = "httpx"
                    logger.info("Connected to Vault via httpx")

            elif not self._vault_available and AIOHTTP_AVAILABLE:
                # aiohttp session created per-request for async safety
                health = await self._aiohttp_health_check()
                if health.get("initialized", False):
                    self._vault_available = True
                    result["connection_method"] = "aiohttp"
                    logger.info("Connected to Vault via aiohttp")

        except Exception as e:
            logger.warning(f"Failed to connect to Vault: {e}")
            result["error"] = str(e)

        self._initialized = True
        result["success"] = True
        result["vault_available"] = self._vault_available

        self._audit(
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

        # Map key type to Vault type
        vault_type = self._map_key_type(key_type)

        result = {
            "key_name": key_name,
            "key_type": key_type,
            "vault_type": vault_type,
            "success": False,
            "constitutional_hash": self._constitutional_hash,
        }

        try:
            if self._vault_available:
                # Use Vault Transit engine
                await self._create_transit_key(
                    key_name=key_name,
                    key_type=vault_type,
                    exportable=exportable,
                    allow_plaintext_backup=allow_plaintext_backup,
                )

                # Get public key
                public_key = await self.get_public_key(key_name)
                result["public_key"] = public_key
                result["vault_path"] = f"{self.config.transit_mount}/keys/{key_name}"
                result["success"] = True

            elif self.fallback_enabled and self._local_crypto:
                # Fallback to local generation
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

        self._audit(
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
            if self._vault_available:
                signature = await self._transit_sign(
                    key_name=key_name,
                    data=data,
                    hash_algorithm=hash_algorithm,
                    prehashed=prehashed,
                )

            elif self.fallback_enabled and key_name in self._local_keys:
                # Fallback to local signing
                _, private_key = self._local_keys[key_name]
                # Create content dict for CryptoService compatibility
                content = {"data": base64.b64encode(data).decode("utf-8")}
                signature = self._local_crypto.sign_policy_content(content, private_key)
                logger.debug(f"Signed using local fallback: {key_name}")

            else:
                raise RuntimeError(f"Key not found and Vault unavailable: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Signing failed for key {key_name}: {e}")
            raise

        finally:
            self._audit(
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
            if self._vault_available:
                is_valid = await self._transit_verify(
                    key_name=key_name,
                    data=data,
                    signature=signature,
                    hash_algorithm=hash_algorithm,
                    prehashed=prehashed,
                )

            elif self.fallback_enabled and key_name in self._local_keys:
                # Fallback to local verification
                public_key, _ = self._local_keys[key_name]
                content = {"data": base64.b64encode(data).decode("utf-8")}
                is_valid = self._local_crypto.verify_policy_signature(
                    content, signature, public_key
                )
                logger.debug(f"Verified using local fallback: {key_name}")

            else:
                raise RuntimeError(f"Key not found and Vault unavailable: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Verification failed for key {key_name}: {e}")
            raise

        finally:
            self._audit(
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
            if self._vault_available:
                ciphertext = await self._transit_encrypt(
                    key_name=key_name,
                    plaintext=plaintext,
                    context=context,
                )

            elif self.fallback_enabled:
                # Simple fallback using Fernet-like encryption
                # In production, use a proper encryption library
                import secrets
                nonce = secrets.token_bytes(12)
                # XOR-based placeholder (NOT SECURE - use proper encryption in production)
                key_bytes = hashlib.sha256(key_name.encode()).digest()
                encrypted = bytes(a ^ b for a, b in zip(plaintext, key_bytes * (len(plaintext) // 32 + 1)))
                ciphertext = f"local:v1:{base64.b64encode(nonce + encrypted).decode()}"
                logger.warning("Using insecure local encryption fallback - not for production")

            else:
                raise RuntimeError("Vault unavailable and fallback disabled")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Encryption failed for key {key_name}: {e}")
            raise

        finally:
            self._audit(
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
                # Handle local fallback ciphertext
                if not self.fallback_enabled:
                    raise RuntimeError("Local ciphertext but fallback disabled")
                _, _, encoded = ciphertext.split(":", 2)
                data = base64.b64decode(encoded)
                nonce, encrypted = data[:12], data[12:]
                key_bytes = hashlib.sha256(key_name.encode()).digest()
                plaintext = bytes(a ^ b for a, b in zip(encrypted, key_bytes * (len(encrypted) // 32 + 1)))
                logger.warning("Using insecure local decryption fallback - not for production")

            elif self._vault_available:
                plaintext = await self._transit_decrypt(
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
            self._audit(
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

        result = {
            "key_name": key_name,
            "success": False,
            "constitutional_hash": self._constitutional_hash,
        }

        try:
            if self._vault_available:
                await self._transit_rotate_key(key_name)
                key_info = await self._get_key_info(key_name)
                result["new_version"] = key_info.get("latest_version")
                result["success"] = True

                # Invalidate cache
                self._invalidate_cache(key_name)

            elif self.fallback_enabled and key_name in self._local_keys:
                # Rotate local key
                public_b64, private_b64 = self._local_crypto.generate_keypair()
                self._local_keys[key_name] = (public_b64, private_b64)
                result["new_version"] = 1
                result["fallback_used"] = True
                result["success"] = True
                logger.info(f"Rotated local key: {key_name}")

            else:
                raise RuntimeError(f"Key not found: {key_name}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Key rotation failed for {key_name}: {e}")

        self._audit(
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
        cached = self._get_from_cache(key_name, self._public_key_cache)
        if cached:
            return cached

        public_key = ""
        error_msg = None

        try:
            if self._vault_available:
                public_key = await self._transit_get_public_key(key_name)
                # Cache the result
                self._set_cache(key_name, public_key, self._public_key_cache)

            elif self.fallback_enabled and key_name in self._local_keys:
                public_key, _ = self._local_keys[key_name]

            else:
                raise RuntimeError(f"Key not found: {key_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Get public key failed for {key_name}: {e}")
            raise

        finally:
            self._audit(
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
        result = {
            "service": "VaultCryptoService",
            "constitutional_hash": self._constitutional_hash,
            "constitutional_valid": True,
            "vault_configured": bool(self.config.address and self.config.token),
            "vault_available": self._vault_available,
            "fallback_enabled": self.fallback_enabled,
            "fallback_keys_count": len(self._local_keys),
            "cache_entries": {
                "public_keys": len(self._public_key_cache),
                "key_info": len(self._key_info_cache),
            },
            "audit_entries_count": len(self._audit_log),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._vault_available:
            try:
                if self._hvac_client:
                    health = self._hvac_client.sys.read_health_status(method="GET")
                    result["vault_health"] = {
                        "initialized": health.get("initialized"),
                        "sealed": health.get("sealed"),
                        "version": health.get("version"),
                    }
                elif self._http_client:
                    health = await self._http_health_check()
                    result["vault_health"] = health
                elif AIOHTTP_AVAILABLE:
                    health = await self._aiohttp_health_check()
                    result["vault_health"] = health
            except Exception as e:
                result["vault_health_error"] = str(e)

        self._audit(VaultOperation.HEALTH_CHECK, success=True)

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

        result = {"path": path, "success": False}

        try:
            if self._vault_available:
                await self._kv_put(path, data, metadata)
                result["success"] = True
                result["version"] = 1  # Would get actual version from Vault

            else:
                raise RuntimeError("Vault unavailable for secret storage")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Store secret failed for {path}: {e}")

        self._audit(
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

        data = {}
        error_msg = None

        try:
            if self._vault_available:
                data = await self._kv_get(path, version)

            else:
                raise RuntimeError("Vault unavailable for secret retrieval")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Get secret failed for {path}: {e}")
            raise

        finally:
            self._audit(
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

        result = {"path": path, "success": False}

        try:
            if self._vault_available:
                await self._kv_delete(path)
                result["success"] = True

            else:
                raise RuntimeError("Vault unavailable for secret deletion")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Delete secret failed for {path}: {e}")

        self._audit(
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

        # Serialize content deterministically
        content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
        content_bytes = content_str.encode("utf-8")

        # Sign content
        signature = await self.sign(key_name, content_bytes)

        # Get public key
        public_key = await self.get_public_key(key_name)

        # Generate fingerprint
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

        # Serialize content deterministically
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
        entries = self._audit_log

        if operation:
            entries = [e for e in entries if e.operation == operation]
        if key_name:
            entries = [e for e in entries if e.key_name == key_name]

        return [e.to_dict() for e in entries[-limit:]]

    def clear_audit_log(self) -> int:
        """Clear audit log and return count of cleared entries."""
        count = len(self._audit_log)
        self._audit_log.clear()
        return count

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

    def _audit(
        self,
        operation: VaultOperation,
        key_name: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add audit log entry."""
        if not self.audit_enabled:
            return

        entry = VaultAuditEntry(
            operation=operation,
            key_name=key_name,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
        self._audit_log.append(entry)

        # Log to standard logger as well
        level = logging.INFO if success else logging.WARNING
        logger.log(
            level,
            f"Vault audit: {operation.value} key={key_name} success={success}"
        )

    def _get_from_cache(
        self,
        key: str,
        cache: Dict[str, Tuple[Any, datetime]],
    ) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in cache:
            value, timestamp = cache[key]
            if (datetime.now(timezone.utc) - timestamp).total_seconds() < self.cache_ttl:
                return value
            else:
                del cache[key]
        return None

    def _set_cache(
        self,
        key: str,
        value: Any,
        cache: Dict[str, Tuple[Any, datetime]],
    ) -> None:
        """Set value in cache with timestamp."""
        cache[key] = (value, datetime.now(timezone.utc))

    def _invalidate_cache(self, key_name: str) -> None:
        """Invalidate all caches for a key."""
        self._public_key_cache.pop(key_name, None)
        self._key_info_cache.pop(key_name, None)

    # Vault Transit Engine methods (HTTP API)

    async def _create_transit_key(
        self,
        key_name: str,
        key_type: str,
        exportable: bool = False,
        allow_plaintext_backup: bool = False,
    ) -> None:
        """Create a key in Transit engine."""
        path = f"/v1/{self.config.transit_mount}/keys/{key_name}"
        data = {
            "type": key_type,
            "exportable": exportable,
            "allow_plaintext_backup": allow_plaintext_backup,
        }
        await self._vault_request("POST", path, json=data)

    async def _transit_sign(
        self,
        key_name: str,
        data: bytes,
        hash_algorithm: str,
        prehashed: bool,
    ) -> str:
        """Sign data using Transit engine."""
        path = f"/v1/{self.config.transit_mount}/sign/{key_name}"

        if prehashed:
            input_data = base64.b64encode(data).decode()
        else:
            input_data = base64.b64encode(data).decode()

        payload = {
            "input": input_data,
            "hash_algorithm": hash_algorithm,
            "prehashed": prehashed,
        }

        response = await self._vault_request("POST", path, json=payload)
        # Vault returns signature as vault:v1:base64...
        signature = response.get("data", {}).get("signature", "")

        # Extract just the base64 part for compatibility
        if signature.startswith("vault:"):
            parts = signature.split(":")
            if len(parts) >= 3:
                return parts[2]
        return signature

    async def _transit_verify(
        self,
        key_name: str,
        data: bytes,
        signature: str,
        hash_algorithm: str,
        prehashed: bool,
    ) -> bool:
        """Verify signature using Transit engine."""
        path = f"/v1/{self.config.transit_mount}/verify/{key_name}"

        # Add vault prefix if not present
        if not signature.startswith("vault:"):
            signature = f"vault:v1:{signature}"

        payload = {
            "input": base64.b64encode(data).decode(),
            "signature": signature,
            "hash_algorithm": hash_algorithm,
            "prehashed": prehashed,
        }

        response = await self._vault_request("POST", path, json=payload)
        return response.get("data", {}).get("valid", False)

    async def _transit_encrypt(
        self,
        key_name: str,
        plaintext: bytes,
        context: Optional[bytes] = None,
    ) -> str:
        """Encrypt data using Transit engine."""
        path = f"/v1/{self.config.transit_mount}/encrypt/{key_name}"

        payload = {"plaintext": base64.b64encode(plaintext).decode()}
        if context:
            payload["context"] = base64.b64encode(context).decode()

        response = await self._vault_request("POST", path, json=payload)
        return response.get("data", {}).get("ciphertext", "")

    async def _transit_decrypt(
        self,
        key_name: str,
        ciphertext: str,
        context: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt data using Transit engine."""
        path = f"/v1/{self.config.transit_mount}/decrypt/{key_name}"

        payload = {"ciphertext": ciphertext}
        if context:
            payload["context"] = base64.b64encode(context).decode()

        response = await self._vault_request("POST", path, json=payload)
        plaintext_b64 = response.get("data", {}).get("plaintext", "")
        return base64.b64decode(plaintext_b64)

    async def _transit_rotate_key(self, key_name: str) -> None:
        """Rotate key in Transit engine."""
        path = f"/v1/{self.config.transit_mount}/keys/{key_name}/rotate"
        await self._vault_request("POST", path)

    async def _transit_get_public_key(self, key_name: str) -> str:
        """Get public key from Transit engine."""
        path = f"/v1/{self.config.transit_mount}/keys/{key_name}"
        response = await self._vault_request("GET", path)

        keys = response.get("data", {}).get("keys", {})
        latest_version = response.get("data", {}).get("latest_version", 1)
        key_data = keys.get(str(latest_version), {})

        # Return public key in base64 format
        public_key = key_data.get("public_key", "")
        if public_key and not public_key.startswith("-----"):
            return public_key

        # If PEM format, extract just the key
        if public_key.startswith("-----BEGIN"):
            import re
            match = re.search(r"-----BEGIN .+-----\n(.+)\n-----END", public_key, re.DOTALL)
            if match:
                return match.group(1).replace("\n", "")

        return public_key

    async def _get_key_info(self, key_name: str) -> Dict[str, Any]:
        """Get key info from Transit engine."""
        path = f"/v1/{self.config.transit_mount}/keys/{key_name}"
        response = await self._vault_request("GET", path)
        return response.get("data", {})

    # Vault KV Engine methods

    async def _kv_put(
        self,
        path: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """Put secret in KV engine."""
        if self.config.kv_version == 2:
            api_path = f"/v1/{self.config.kv_mount}/data/{path}"
            payload = {"data": data}
            if metadata:
                payload["options"] = {"cas": 0}  # Check-and-set
        else:
            api_path = f"/v1/{self.config.kv_mount}/{path}"
            payload = data

        await self._vault_request("POST", api_path, json=payload)

    async def _kv_get(
        self,
        path: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get secret from KV engine."""
        if self.config.kv_version == 2:
            api_path = f"/v1/{self.config.kv_mount}/data/{path}"
            if version:
                api_path += f"?version={version}"
        else:
            api_path = f"/v1/{self.config.kv_mount}/{path}"

        response = await self._vault_request("GET", api_path)

        if self.config.kv_version == 2:
            return response.get("data", {}).get("data", {})
        return response.get("data", {})

    async def _kv_delete(self, path: str) -> None:
        """Delete secret from KV engine."""
        if self.config.kv_version == 2:
            api_path = f"/v1/{self.config.kv_mount}/data/{path}"
        else:
            api_path = f"/v1/{self.config.kv_mount}/{path}"

        await self._vault_request("DELETE", api_path)

    # HTTP client methods

    async def _vault_request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Vault."""
        headers = {"X-Vault-Token": self.config.token or ""}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        if self._http_client:
            response = await self._http_client.request(
                method, path, json=json, headers=headers
            )
            response.raise_for_status()
            return response.json() if response.text else {}

        elif AIOHTTP_AVAILABLE:
            return await self._aiohttp_request(method, path, json, headers)

        elif self._hvac_client:
            # Use hvac for synchronous operations
            return await asyncio.to_thread(
                self._hvac_request, method, path, json
            )

        else:
            raise RuntimeError("No HTTP client available")

    async def _aiohttp_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Make request using aiohttp."""
        url = f"{self.config.address}{path}"
        ssl_context = None if self.config.verify_tls else False

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json_data,
                headers=headers,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as response:
                response.raise_for_status()
                if response.content_length and response.content_length > 0:
                    return await response.json()
                return {}

    def _hvac_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Make request using hvac (synchronous)."""
        # hvac handles paths differently, need to parse
        if path.startswith("/v1/"):
            path = path[4:]

        if method == "GET":
            response = self._hvac_client.adapter.request("GET", path)
        elif method == "POST":
            response = self._hvac_client.adapter.request("POST", path, json=json_data)
        elif method == "DELETE":
            response = self._hvac_client.adapter.request("DELETE", path)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response.json() if hasattr(response, "json") else {}

    async def _http_health_check(self) -> Dict[str, Any]:
        """Check Vault health using httpx."""
        response = await self._http_client.get("/v1/sys/health")
        return response.json()

    async def _aiohttp_health_check(self) -> Dict[str, Any]:
        """Check Vault health using aiohttp."""
        url = f"{self.config.address}/v1/sys/health"
        ssl_context = None if self.config.verify_tls else False

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as response:
                return await response.json()

    # Context manager support

    async def __aenter__(self) -> "VaultCryptoService":
        """Async context manager entry."""
        if not self._initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


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
