"""
SQLAlchemy models for Policy Marketplace templates
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TemplateStatus(str, Enum):
    """Template status enumeration"""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TemplateFormat(str, Enum):
    """Supported template file formats"""

    JSON = "json"
    YAML = "yaml"
    REGO = "rego"


class TemplateCategory(str, Enum):
    """Template category enumeration"""

    COMPLIANCE = "compliance"
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    AUDIT = "audit"
    RATE_LIMITING = "rate_limiting"
    MULTI_TENANT = "multi_tenant"
    API_SECURITY = "api_security"
    DATA_RETENTION = "data_retention"
    CUSTOM = "custom"


class Template(Base):
    """Main template model for policy marketplace"""

    __tablename__ = "templates"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="json")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=TemplateStatus.DRAFT.value
    )

    # Access control
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Authorship
    author_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Versioning
    current_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    # Analytics
    downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    versions: Mapped[list["TemplateVersion"]] = relationship(
        "TemplateVersion", back_populates="template", cascade="all, delete-orphan"
    )
    ratings: Mapped[list["TemplateRating"]] = relationship(
        "TemplateRating", back_populates="template", cascade="all, delete-orphan"
    )

    # Indexes for query performance
    __table_args__ = (
        Index("ix_templates_organization_id", "organization_id"),
        Index("ix_templates_is_public", "is_public"),
        Index("ix_templates_category", "category"),
        Index("ix_templates_created_at", "created_at"),
        Index("ix_templates_is_verified", "is_verified"),
        Index("ix_templates_status", "status"),
        Index("ix_templates_is_deleted", "is_deleted"),
        UniqueConstraint("name", "organization_id", name="uq_templates_name_organization"),
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}', category='{self.category}')>"


class TemplateVersion(Base):
    """Version history for templates"""

    __tablename__ = "template_versions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to template
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False
    )

    # Version information
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Authorship
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    template: Mapped["Template"] = relationship("Template", back_populates="versions")

    # Indexes
    __table_args__ = (
        Index("ix_template_versions_template_id", "template_id"),
        Index("ix_template_versions_version", "version"),
        Index("ix_template_versions_created_at", "created_at"),
        UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
    )

    def __repr__(self) -> str:
        return f"<TemplateVersion(id={self.id}, template_id={self.template_id}, version='{self.version}')>"


class TemplateRating(Base):
    """User ratings for templates"""

    __tablename__ = "template_ratings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to template
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False
    )

    # User information
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Rating value (1-5)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional review comment
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    template: Mapped["Template"] = relationship("Template", back_populates="ratings")

    # Constraints and indexes
    __table_args__ = (
        Index("ix_template_ratings_template_id", "template_id"),
        Index("ix_template_ratings_user_id", "user_id"),
        UniqueConstraint("template_id", "user_id", name="uq_template_ratings_template_user"),
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateRating(id={self.id}, template_id={self.template_id}, rating={self.rating})>"
        )


class TemplateAnalytics(Base):
    """Analytics events for template interactions"""

    __tablename__ = "template_analytics"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to template
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False
    )

    # Event information
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # view, download, clone
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Additional event metadata
    metadata: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string for flexibility

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indexes for analytics queries
    __table_args__ = (
        Index("ix_template_analytics_template_id", "template_id"),
        Index("ix_template_analytics_event_type", "event_type"),
        Index("ix_template_analytics_created_at", "created_at"),
        Index(
            "ix_template_analytics_template_event",
            "template_id",
            "event_type",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<TemplateAnalytics(id={self.id}, template_id={self.template_id}, event_type='{self.event_type}')>"
