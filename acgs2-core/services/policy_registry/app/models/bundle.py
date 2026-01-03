"""Constitutional Hash: cdd01ef066bc6cf2
Bundle Model
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BundleStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    REVOKED = "revoked"


class Bundle(BaseModel):
    id: str = Field(..., description="Bundle ID (usually digest or name:tag)")
    version: str
    revision: str
    constitutional_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    roots: List[str]
    signatures: List[Dict[str, str]]
    metadata: Dict[str, Any] = {}
    status: BundleStatus = BundleStatus.DRAFT
    media_type: str = "application/vnd.opa.bundle.layer.v1+gzip"
    size: int
    digest: str

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
