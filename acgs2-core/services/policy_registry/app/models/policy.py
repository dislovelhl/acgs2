"""
Policy data model for constitutional policies
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, field_serializer, Field


class PolicyStatus(str, Enum):
    """Policy status enumeration"""

    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Policy(BaseModel):
    """Constitutional policy model"""

    policy_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    format: str = Field(default="json", pattern="^(json|yaml)$")
    status: PolicyStatus = Field(default=PolicyStatus.DRAFT)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, value: datetime) -> str:
        return value.isoformat()

    def __init__(self, **data):
        super().__init__(**data)
        if not self.policy_id:
            self.policy_id = str(uuid4())

    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
