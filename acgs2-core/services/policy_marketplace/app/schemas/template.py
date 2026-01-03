"""
Pydantic schemas for policy marketplace
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TemplateVersionBase(BaseModel):
    version_string: str
    content: str
    changelog: Optional[str] = None


class TemplateVersionCreate(TemplateVersionBase):
    pass


class TemplateVersionSchema(TemplateVersionBase):
    id: UUID
    template_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateBase(BaseModel):
    name: str
    description: str
    category: str
    is_public: bool = True
    organization_id: Optional[str] = None


class TemplateCreate(TemplateBase):
    initial_version: TemplateVersionCreate
    author_id: str


class TemplateResponse(TemplateBase):
    id: UUID
    is_verified: bool
    downloads: int
    rating: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateDetailResponse(TemplateResponse):
    versions: List[TemplateVersionSchema]
