"""
SQLAlchemy models for policy marketplace
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PolicyTemplate(Base):
    """Model for a policy template in the marketplace"""

    __tablename__ = "policy_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    organization_id = Column(String(100), nullable=True)
    author_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Analytics
    downloads = Column(Integer, default=0)
    rating = Column(Float, nullable=True)

    # Relationships
    versions = relationship(
        "TemplateVersion", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateVersion(Base):
    """Model for a specific version of a policy template"""

    __tablename__ = "template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("policy_templates.id"), nullable=False)
    version_string = Column(String(50), nullable=False)  # e.g. "1.0.0"
    content = Column(Text, nullable=False)  # The actual Rego/JSON content
    changelog = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("PolicyTemplate", back_populates="versions")
