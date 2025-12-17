"""
Policy signature data model for cryptographic verification
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PolicySignature(BaseModel):
    """Policy signature model for Ed25519 verification"""

    signature_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str = Field(...)
    version: str = Field(...)
    public_key: str = Field(...)  # Base64 encoded Ed25519 public key
    signature: str = Field(...)   # Base64 encoded Ed25519 signature
    algorithm: str = Field(default="Ed25519")
    key_fingerprint: Optional[str] = Field(None)  # SHA256 fingerprint of public key

    # Timestamps
    signed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = Field(None)

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def __init__(self, **data):
        super().__init__(**data)
        if not self.signature_id:
            self.signature_id = str(uuid4())

    @property
    def is_expired(self) -> bool:
        """Check if signature is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if signature is valid (not expired)"""
        return not self.is_expired
