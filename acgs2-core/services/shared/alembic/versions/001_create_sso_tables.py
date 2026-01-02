"""Create SSO tables

Revision ID: 001_sso_tables
Revises:
Create Date: 2026-01-02
Constitutional Hash: cdd01ef066bc6cf2

Creates database tables for Enterprise SSO Integration:
- users: User accounts with SSO authentication fields
- sso_providers: SAML 2.0 and OIDC identity provider configurations
- sso_role_mappings: IdP group to ACGS-2 role mappings
- saml_outstanding_requests: SAML request tracking for replay attack prevention
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "001_sso_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create SSO database tables."""

    # Create enum type for SSO provider type
    # Using VARCHAR with check constraint for SQLite compatibility
    sso_provider_type = sa.Enum(
        "saml",
        "oidc",
        name="sso_provider_type",
        create_constraint=True,
    )

    # =========================================================================
    # Table: users
    # User accounts with SSO authentication support
    # =========================================================================
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            comment="Unique user identifier (UUID)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="User email address (unique identifier for SSO matching)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=True,
            comment="User display name",
        ),
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=True,
            comment="Bcrypt password hash for local auth (null for SSO-only users)",
        ),
        sa.Column(
            "sso_enabled",
            sa.Boolean(),
            nullable=False,
            default=False,
            server_default="0",
            comment="Whether SSO authentication is enabled for this user",
        ),
        sa.Column(
            "sso_provider",
            sso_provider_type,
            nullable=True,
            comment="SSO protocol type (saml or oidc)",
        ),
        sa.Column(
            "sso_idp_user_id",
            sa.String(255),
            nullable=True,
            comment="User ID from the identity provider",
        ),
        sa.Column(
            "sso_name_id",
            sa.String(512),
            nullable=True,
            comment="SAML NameID for Single Logout operations",
        ),
        sa.Column(
            "sso_session_index",
            sa.String(255),
            nullable=True,
            comment="SAML SessionIndex for Single Logout operations",
        ),
        sa.Column(
            "sso_provider_id",
            sa.String(36),
            nullable=True,
            comment="Reference to the SSO provider configuration (sso_providers.id)",
        ),
        sa.Column(
            "roles",
            sa.Text(),
            nullable=True,
            comment="Comma-separated list of assigned roles (mapped from IdP groups)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when user was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Timestamp of last update",
        ),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last successful login",
        ),
        comment="ACGS-2 users with SSO integration support",
    )

    # Users table indexes
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_sso_idp_user_id", "users", ["sso_idp_user_id"])
    op.create_index(
        "ix_users_sso_provider_idp_user_id",
        "users",
        ["sso_provider", "sso_idp_user_id"],
    )

    # =========================================================================
    # Table: sso_providers
    # Identity provider configurations for SAML 2.0 and OIDC
    # =========================================================================
    op.create_table(
        "sso_providers",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            comment="Unique provider identifier (UUID)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Human-readable provider name (e.g., 'Google Workspace', 'Okta')",
        ),
        sa.Column(
            "provider_type",
            sso_provider_type,
            nullable=False,
            comment="SSO protocol type (saml or oidc)",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            default=True,
            server_default="1",
            comment="Whether this provider is active for authentication",
        ),
        # OIDC-specific fields
        sa.Column(
            "oidc_client_id",
            sa.String(255),
            nullable=True,
            comment="OAuth 2.0 client ID from the IdP",
        ),
        sa.Column(
            "oidc_client_secret",
            sa.String(512),
            nullable=True,
            comment="OAuth 2.0 client secret (should be encrypted at rest)",
        ),
        sa.Column(
            "oidc_metadata_url",
            sa.String(1024),
            nullable=True,
            comment="OpenID Connect discovery URL (.well-known/openid-configuration)",
        ),
        sa.Column(
            "oidc_scopes",
            sa.String(512),
            nullable=True,
            default="openid profile email",
            server_default="openid profile email",
            comment="Space-separated OAuth scopes to request",
        ),
        # SAML-specific fields
        sa.Column(
            "saml_entity_id",
            sa.String(1024),
            nullable=True,
            comment="IdP entity ID from SAML metadata",
        ),
        sa.Column(
            "saml_metadata_url",
            sa.String(1024),
            nullable=True,
            comment="URL to fetch IdP SAML metadata XML",
        ),
        sa.Column(
            "saml_metadata_xml",
            sa.Text(),
            nullable=True,
            comment="Cached IdP metadata XML content",
        ),
        sa.Column(
            "saml_sp_cert",
            sa.Text(),
            nullable=True,
            comment="SP certificate (PEM format) for signing SAML requests",
        ),
        sa.Column(
            "saml_sp_key",
            sa.Text(),
            nullable=True,
            comment="SP private key (PEM format, should be encrypted at rest)",
        ),
        sa.Column(
            "saml_sign_requests",
            sa.Boolean(),
            nullable=False,
            default=True,
            server_default="1",
            comment="Whether to sign SAML AuthnRequests",
        ),
        sa.Column(
            "saml_sign_assertions",
            sa.Boolean(),
            nullable=False,
            default=True,
            server_default="1",
            comment="Whether IdP should sign assertions (validation enforced)",
        ),
        sa.Column(
            "saml_want_encrypted_assertions",
            sa.Boolean(),
            nullable=False,
            default=False,
            server_default="0",
            comment="Whether to expect encrypted assertions from IdP",
        ),
        # General configuration
        sa.Column(
            "config",
            sa.Text(),
            nullable=True,
            comment="JSON field for additional provider-specific configuration",
        ),
        sa.Column(
            "allowed_domains",
            sa.String(1024),
            nullable=True,
            comment="Comma-separated list of allowed email domains (null = all)",
        ),
        sa.Column(
            "default_roles",
            sa.String(512),
            nullable=True,
            comment="Comma-separated list of default roles for new users from this provider",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when provider was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Timestamp of last update",
        ),
        sa.Column(
            "metadata_last_fetched",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When IdP metadata was last refreshed",
        ),
        comment="ACGS-2 SSO provider configurations for SAML/OIDC IdPs",
    )

    # SSO Providers table indexes
    op.create_index("ix_sso_providers_name", "sso_providers", ["name"], unique=True)
    op.create_index("ix_sso_providers_provider_type", "sso_providers", ["provider_type"])
    op.create_index("ix_sso_providers_enabled", "sso_providers", ["enabled"])

    # =========================================================================
    # Table: sso_role_mappings
    # IdP group to ACGS-2 role mappings
    # =========================================================================
    op.create_table(
        "sso_role_mappings",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            comment="Unique mapping identifier (UUID)",
        ),
        sa.Column(
            "provider_id",
            sa.String(36),
            nullable=False,
            comment="Reference to the SSO provider (sso_providers.id)",
        ),
        sa.Column(
            "idp_group",
            sa.String(255),
            nullable=False,
            comment="Group name from the identity provider",
        ),
        sa.Column(
            "acgs_role",
            sa.String(100),
            nullable=False,
            comment="Internal ACGS-2 role identifier",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            default=0,
            server_default="0",
            comment="Mapping priority (higher = applied first for conflicts)",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional description of this mapping",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when mapping was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Timestamp of last update",
        ),
        comment="ACGS-2 SSO role mappings for IdP group translation",
    )

    # SSO Role Mappings table indexes and constraints
    op.create_index("ix_sso_role_mappings_provider_id", "sso_role_mappings", ["provider_id"])
    op.create_index("ix_sso_role_mappings_idp_group", "sso_role_mappings", ["idp_group"])
    op.create_index("ix_sso_role_mappings_acgs_role", "sso_role_mappings", ["acgs_role"])
    op.create_index(
        "ix_sso_role_mappings_provider_id_idp_group",
        "sso_role_mappings",
        ["provider_id", "idp_group"],
    )
    op.create_unique_constraint(
        "uq_sso_role_mappings_provider_group",
        "sso_role_mappings",
        ["provider_id", "idp_group"],
    )

    # Foreign key to sso_providers (if not using SQLite)
    # SQLite has limited ALTER TABLE support, so this is created with the table
    # For PostgreSQL, uncomment this:
    # op.create_foreign_key(
    #     "fk_sso_role_mappings_provider_id",
    #     "sso_role_mappings",
    #     "sso_providers",
    #     ["provider_id"],
    #     ["id"],
    #     ondelete="CASCADE",
    # )

    # =========================================================================
    # Table: saml_outstanding_requests
    # SAML request tracking for replay attack prevention
    # =========================================================================
    op.create_table(
        "saml_outstanding_requests",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            comment="Internal unique identifier (UUID)",
        ),
        sa.Column(
            "request_id",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="SAML request ID from the AuthnRequest (must be unique)",
        ),
        sa.Column(
            "provider_id",
            sa.String(36),
            nullable=True,
            comment="Reference to the SSO provider configuration (sso_providers.id)",
        ),
        sa.Column(
            "relay_state",
            sa.Text(),
            nullable=True,
            comment="Optional RelayState for redirect after authentication",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when the request was created",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the request expires (default: 5 minutes from creation)",
        ),
        comment="ACGS-2 SAML outstanding requests for replay attack prevention",
    )

    # SAML Outstanding Requests table indexes
    op.create_index(
        "ix_saml_outstanding_requests_request_id",
        "saml_outstanding_requests",
        ["request_id"],
        unique=True,
    )
    op.create_index(
        "ix_saml_outstanding_requests_expires_at",
        "saml_outstanding_requests",
        ["expires_at"],
    )
    op.create_index(
        "ix_saml_outstanding_requests_provider_id",
        "saml_outstanding_requests",
        ["provider_id"],
    )
    op.create_index(
        "ix_saml_outstanding_requests_provider_expires",
        "saml_outstanding_requests",
        ["provider_id", "expires_at"],
    )


def downgrade() -> None:
    """Drop SSO database tables."""

    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table("saml_outstanding_requests")
    op.drop_table("sso_role_mappings")
    op.drop_table("sso_providers")
    op.drop_table("users")

    # Drop the enum type (PostgreSQL only)
    # For SQLite, the enum is stored as VARCHAR with check constraint
    # which is dropped with the table
    sa.Enum(name="sso_provider_type").drop(op.get_bind(), checkfirst=True)
