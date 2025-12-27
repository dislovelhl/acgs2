"""
Policy version data model
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VersionStatus(str, Enum):
    """Policy version status enumeration"""
    ACTIVE = "active"
    TESTING = "testing"
    RETIRED = "retired"
    DRAFT = "draft"


class ABTestGroup(str, Enum):
    """A/B testing group enumeration"""
    A = "A"
    B = "B"


class PolicyVersion(BaseModel):
    """Policy version model with content and metadata"""

    version_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str = Field(...)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")  # Semantic versioning
    content: Dict[str, Any] = Field(...)  # JSON/YAML policy content
    content_hash: str = Field(...)  # SHA256 hash of content
    predecessor_version: Optional[str] = Field(None)
    status: VersionStatus = Field(default=VersionStatus.DRAFT)
    ab_test_group: Optional[ABTestGroup] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def __init__(self, **data):
        super().__init__(**data)
        if not self.version_id:
            self.version_id = str(uuid4())

    @property
    def is_active(self) -> bool:
        """Check if version is active"""
        return self.status == VersionStatus.ACTIVE

    @property
    def is_testing(self) -> bool:
        """Check if version is in testing"""
        return self.status == VersionStatus.TESTING
