"""
ACGS-2 Vault Crypto Service - Models and Types
Constitutional Hash: cdd01ef066bc6cf2

Data models and enums for Vault cryptographic operations.
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

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


__all__ = [
    "CONSTITUTIONAL_HASH",
    "VaultKeyType",
    "VaultOperation",
    "VaultAuditEntry",
    "VaultConfig",
]
