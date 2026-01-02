"""
ACGS-2 User Model with SSO Integration
Constitutional Hash: cdd01ef066bc6cf2

Defines the User model with fields for SSO (SAML/OIDC) authentication.
Supports Just-In-Time (JIT) provisioning from identity providers.

Usage:
    from shared.models.user import User, SSOProviderType

    # Create a user with SSO
    user = User(
        email="user@example.com",
        name="John Doe",
        sso_enabled=True,
        sso_provider=SSOProviderType.OIDC,
        sso_idp_user_id="google-12345",
    )
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.database import Base
from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class SSOProviderType(str, enum.Enum):
    """SSO provider type enumeration.

    Identifies the authentication protocol used by the identity provider.
    """

    SAML = "saml"
    OIDC = "oidc"


class User(Base):
    """User model with SSO integration fields.

    Supports both local authentication and SSO (SAML 2.0 / OpenID Connect).
    Users can be provisioned Just-In-Time (JIT) from identity providers.

    Attributes:
        id: Unique identifier (UUID).
        email: User email address (unique, used as primary identifier for SSO).
        name: User display name.
        sso_enabled: Whether SSO authentication is enabled for this user.
        sso_provider: The SSO protocol type (saml or oidc).
        sso_idp_user_id: The user's ID from the identity provider.
        sso_name_id: SAML NameID for Single Logout (SLO) operations.
        sso_session_index: SAML SessionIndex for SLO operations.
        roles: Comma-separated list of assigned roles (mapped from IdP groups).
        created_at: Timestamp when user was created.
        updated_at: Timestamp of last update.
        last_login: Timestamp of last successful login.

    Indexes:
        - Primary key on id
        - Unique index on email
        - Index on sso_idp_user_id for IdP lookups
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique user identifier (UUID)",
    )

    # Core user fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address (unique identifier for SSO matching)",
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User display name",
    )

    # Password hash for local authentication (optional, null for SSO-only users)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt password hash for local auth (null for SSO-only users)",
    )

    # SSO authentication fields
    sso_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether SSO authentication is enabled for this user",
    )

    sso_provider: Mapped[Optional[str]] = mapped_column(
        Enum(SSOProviderType, name="sso_provider_type", create_constraint=True),
        nullable=True,
        comment="SSO protocol type (saml or oidc)",
    )

    sso_idp_user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User ID from the identity provider",
    )

    # SAML-specific fields for Single Logout (SLO)
    sso_name_id: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="SAML NameID for Single Logout operations",
    )

    sso_session_index: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="SAML SessionIndex for Single Logout operations",
    )

    # Provider configuration reference
    sso_provider_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="Reference to the SSO provider configuration (sso_providers.id)",
    )

    # Role management
    roles: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of assigned roles (mapped from IdP groups)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when user was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp of last update",
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful login",
    )

    # Add composite index for SSO lookups
    __table_args__ = (
        Index("ix_users_sso_provider_idp_user_id", "sso_provider", "sso_idp_user_id"),
        {"comment": "ACGS-2 users with SSO integration support"},
    )

    def __repr__(self) -> str:
        """String representation of the user."""
        return (
            f"<User(id={self.id!r}, email={self.email!r}, "
            f"sso_enabled={self.sso_enabled}, sso_provider={self.sso_provider})>"
        )

    @property
    def is_sso_user(self) -> bool:
        """Check if user authenticates via SSO."""
        return self.sso_enabled and self.sso_provider is not None

    @property
    def is_local_user(self) -> bool:
        """Check if user authenticates locally (password-based)."""
        return self.password_hash is not None and not self.sso_enabled

    @property
    def role_list(self) -> list[str]:
        """Get roles as a list.

        Returns:
            List of role names, or empty list if no roles assigned.
        """
        if not self.roles:
            return []
        return [r.strip() for r in self.roles.split(",") if r.strip()]

    def set_roles(self, roles: list[str]) -> None:
        """Set roles from a list.

        Args:
            roles: List of role names to assign.
        """
        self.roles = ",".join(sorted(set(roles))) if roles else None

    def add_role(self, role: str) -> None:
        """Add a role to the user.

        Args:
            role: Role name to add.
        """
        current_roles = set(self.role_list)
        current_roles.add(role)
        self.set_roles(list(current_roles))

    def remove_role(self, role: str) -> None:
        """Remove a role from the user.

        Args:
            role: Role name to remove.
        """
        current_roles = set(self.role_list)
        current_roles.discard(role)
        self.set_roles(list(current_roles))

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role.

        Args:
            role: Role name to check.

        Returns:
            True if user has the role, False otherwise.
        """
        return role in self.role_list

    def update_sso_info(
        self,
        provider: SSOProviderType,
        idp_user_id: str,
        provider_id: Optional[str] = None,
        name_id: Optional[str] = None,
        session_index: Optional[str] = None,
    ) -> None:
        """Update SSO-related information.

        Called during SSO login to update/refresh SSO metadata.

        Args:
            provider: SSO protocol type (saml or oidc).
            idp_user_id: User ID from the identity provider.
            provider_id: Reference to SSO provider configuration.
            name_id: SAML NameID (optional, for SAML).
            session_index: SAML SessionIndex (optional, for SAML).
        """
        self.sso_enabled = True
        self.sso_provider = provider
        self.sso_idp_user_id = idp_user_id

        if provider_id:
            self.sso_provider_id = provider_id

        if name_id:
            self.sso_name_id = name_id

        if session_index:
            self.sso_session_index = session_index

        self.last_login = datetime.now(timezone.utc)

    def clear_sso_session(self) -> None:
        """Clear SSO session data.

        Called during logout to clear session-specific SSO data.
        Preserves the SSO link but clears session identifiers.
        """
        self.sso_name_id = None
        self.sso_session_index = None
