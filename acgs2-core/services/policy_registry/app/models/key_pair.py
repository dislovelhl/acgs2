"""
Key pair data model for cryptographic key management
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, field_serializer, Field


class KeyAlgorithm(str, Enum):
    """Supported cryptographic algorithms"""

    ED25519 = "Ed25519"
    RSA = "RSA"
    ECDSA = "ECDSA"


class KeyStatus(str, Enum):
    """Key status enumeration"""

    ACTIVE = "active"
    ROTATED = "rotated"
    COMPROMISED = "compromised"
    EXPIRED = "expired"


class KeyPair(BaseModel):
    """Cryptographic key pair model"""

    key_id: str = Field(default_factory=lambda: str(uuid4()))
    public_key: str = Field(...)  # Base64 encoded public key
    vault_path: str = Field(...)  # Path in HashiCorp Vault for private key
    algorithm: KeyAlgorithm = Field(default=KeyAlgorithm.ED25519)
    status: KeyStatus = Field(default=KeyStatus.ACTIVE)
    fingerprint: str = Field(...)  # SHA256 fingerprint of public key
    metadata: dict = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None)
    rotated_at: Optional[datetime] = Field(None)

    @field_serializer("created_at", "expires_at", "rotated_at", when_used="unless-none")
    def serialize_datetimes(self, value: datetime) -> str:
        return value.isoformat()

    def __init__(self, **data):
        super().__init__(**data)
        if not self.key_id:
            self.key_id = str(uuid4())

    @property
    def is_active(self) -> bool:
        """Check if key is active"""
        return self.status == KeyStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)"""
        return self.is_active and not self.is_expired
