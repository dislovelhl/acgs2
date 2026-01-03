"""
Constitutional Hash: cdd01ef066bc6cf2
"""

# ruff: noqa: I001
"""Initial database schema for Policy Marketplace

Creates all core tables for the policy marketplace:
- templates: Main template storage with metadata and access control
- template_versions: Version history with changelog
- template_ratings: User ratings (1-5) with one rating per user per template
- template_analytics: Event tracking for views, downloads, clones

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all policy marketplace tables."""
    # Create templates table
    op.create_table(
        "templates",
        # Primary key
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Basic information
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False, server_default="json"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        # Access control
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("organization_id", sa.String(length=100), nullable=True),
        # Authorship
        sa.Column("author_id", sa.String(length=100), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        # Versioning
        sa.Column("current_version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        # Analytics
        sa.Column("downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "organization_id", name="uq_templates_name_organization"),
    )

    # Create indexes on templates table
    op.create_index("ix_templates_organization_id", "templates", ["organization_id"])
    op.create_index("ix_templates_is_public", "templates", ["is_public"])
    op.create_index("ix_templates_category", "templates", ["category"])
    op.create_index("ix_templates_created_at", "templates", ["created_at"])
    op.create_index("ix_templates_is_verified", "templates", ["is_verified"])
    op.create_index("ix_templates_status", "templates", ["status"])
    op.create_index("ix_templates_is_deleted", "templates", ["is_deleted"])

    # Create template_versions table
    op.create_table(
        "template_versions",
        # Primary key
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Foreign key to template
        sa.Column("template_id", sa.Integer(), nullable=False),
        # Version information
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        # Authorship
        sa.Column("created_by", sa.String(length=100), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
    )

    # Create indexes on template_versions table
    op.create_index("ix_template_versions_template_id", "template_versions", ["template_id"])
    op.create_index("ix_template_versions_version", "template_versions", ["version"])
    op.create_index("ix_template_versions_created_at", "template_versions", ["created_at"])

    # Create template_ratings table
    op.create_table(
        "template_ratings",
        # Primary key
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Foreign key to template
        sa.Column("template_id", sa.Integer(), nullable=False),
        # User information
        sa.Column("user_id", sa.String(length=100), nullable=False),
        # Rating value (1-5)
        sa.Column("rating", sa.Integer(), nullable=False),
        # Optional review comment
        sa.Column("comment", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("template_id", "user_id", name="uq_template_ratings_template_user"),
    )

    # Create indexes on template_ratings table
    op.create_index("ix_template_ratings_template_id", "template_ratings", ["template_id"])
    op.create_index("ix_template_ratings_user_id", "template_ratings", ["user_id"])

    # Create template_analytics table
    op.create_table(
        "template_analytics",
        # Primary key
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Foreign key to template
        sa.Column("template_id", sa.Integer(), nullable=False),
        # Event information
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        # Additional event metadata (JSON string)
        sa.Column("metadata", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes on template_analytics table
    op.create_index("ix_template_analytics_template_id", "template_analytics", ["template_id"])
    op.create_index("ix_template_analytics_event_type", "template_analytics", ["event_type"])
    op.create_index("ix_template_analytics_created_at", "template_analytics", ["created_at"])
    op.create_index(
        "ix_template_analytics_template_event",
        "template_analytics",
        ["template_id", "event_type", "created_at"],
    )


def downgrade() -> None:
    """Drop all policy marketplace tables."""
    # Drop indexes first (in reverse order)
    op.drop_index("ix_template_analytics_template_event", table_name="template_analytics")
    op.drop_index("ix_template_analytics_created_at", table_name="template_analytics")
    op.drop_index("ix_template_analytics_event_type", table_name="template_analytics")
    op.drop_index("ix_template_analytics_template_id", table_name="template_analytics")

    op.drop_index("ix_template_ratings_user_id", table_name="template_ratings")
    op.drop_index("ix_template_ratings_template_id", table_name="template_ratings")

    op.drop_index("ix_template_versions_created_at", table_name="template_versions")
    op.drop_index("ix_template_versions_version", table_name="template_versions")
    op.drop_index("ix_template_versions_template_id", table_name="template_versions")

    op.drop_index("ix_templates_is_deleted", table_name="templates")
    op.drop_index("ix_templates_status", table_name="templates")
    op.drop_index("ix_templates_is_verified", table_name="templates")
    op.drop_index("ix_templates_created_at", table_name="templates")
    op.drop_index("ix_templates_category", table_name="templates")
    op.drop_index("ix_templates_is_public", table_name="templates")
    op.drop_index("ix_templates_organization_id", table_name="templates")

    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("template_analytics")
    op.drop_table("template_ratings")
    op.drop_table("template_versions")
    op.drop_table("templates")
