"""
ACGS-2 SSO Role Mapping Model for IdP Group Translation
Constitutional Hash: cdd01ef066bc6cf2

Defines the SSORoleMapping model for mapping identity provider groups
to internal ACGS-2 roles. This enables automatic role assignment during
Just-In-Time (JIT) user provisioning from SSO authentication.

Usage:
    from src.core.shared.models.sso_role_mapping import SSORoleMapping

    # Create a role mapping (IdP group -> ACGS-2 role)
    mapping = SSORoleMapping(
        provider_id="sso-provider-uuid",
        idp_group="Engineering",
        acgs_role="developer",
    )

    # Map multiple IdP groups to roles
    admin_mapping = SSORoleMapping(
        provider_id="sso-provider-uuid",
        idp_group="Administrators",
        acgs_role="admin",
        priority=10,
    )
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.shared.database import Base


class SSORoleMapping(Base):
    """SSO Role Mapping model for IdP group to role translation.

    Maps identity provider groups/claims to internal ACGS-2 roles.
    When a user authenticates via SSO, their IdP group memberships
    are translated to internal roles using these mappings.

    Attributes:
        id: Unique identifier (UUID).
        provider_id: Reference to the SSO provider (sso_providers.id).
        idp_group: Group name from the identity provider.
        acgs_role: Internal ACGS-2 role identifier.
        priority: Mapping priority (higher = applied first for conflicts).
        description: Optional description of this mapping.
        created_at: Timestamp when mapping was created.
        updated_at: Timestamp of last update.

    Indexes:
        - Primary key on id
        - Unique constraint on (provider_id, idp_group)
        - Index on provider_id for provider lookups
        - Index on idp_group for group lookups
    """

    __tablename__ = "sso_role_mappings"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique mapping identifier (UUID)",
    )

    # Provider reference
    provider_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Reference to the SSO provider (sso_providers.id)",
    )

    # IdP group name
    idp_group: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Group name from the identity provider",
    )

    # ACGS-2 internal role
    acgs_role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Internal ACGS-2 role identifier",
    )

    # Priority for conflict resolution
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Mapping priority (higher = applied first for conflicts)",
    )

    # Optional description
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of this mapping",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when mapping was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp of last update",
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "idp_group",
            name="uq_sso_role_mappings_provider_group",
        ),
        Index("ix_sso_role_mappings_provider_id_idp_group", "provider_id", "idp_group"),
        Index("ix_sso_role_mappings_acgs_role", "acgs_role"),
        {"comment": "ACGS-2 SSO role mappings for IdP group translation"},
    )

    def __repr__(self) -> str:
        """String representation of the mapping."""
        return (
            f"<SSORoleMapping(id={self.id!r}, provider_id={self.provider_id!r}, "
            f"idp_group={self.idp_group!r}, acgs_role={self.acgs_role!r})>"
        )

    @classmethod
    def create_mapping(
        cls,
        provider_id: str,
        idp_group: str,
        acgs_role: str,
        priority: int = 0,
        description: Optional[str] = None,
    ) -> "SSORoleMapping":
        """Factory method to create a role mapping.

        Args:
            provider_id: SSO provider UUID.
            idp_group: IdP group name to map.
            acgs_role: ACGS-2 role to assign.
            priority: Mapping priority for conflict resolution.
            description: Optional description.

        Returns:
            New SSORoleMapping instance.
        """
        return cls(
            provider_id=provider_id,
            idp_group=idp_group,
            acgs_role=acgs_role,
            priority=priority,
            description=description,
        )

    def matches_group(self, group_name: str, case_sensitive: bool = False) -> bool:
        """Check if this mapping matches a given IdP group name.

        Args:
            group_name: Group name to check.
            case_sensitive: Whether to perform case-sensitive matching.

        Returns:
            True if the group name matches, False otherwise.
        """
        if case_sensitive:
            return self.idp_group == group_name
        return self.idp_group.lower() == group_name.lower()
