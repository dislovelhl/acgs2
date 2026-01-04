"""
ACGS-2 SSO Provider Model for IdP Configurations
Constitutional Hash: cdd01ef066bc6cf2

Defines the SSOProvider model for storing identity provider configurations.
Supports both SAML 2.0 and OpenID Connect (OIDC) providers.

Usage:
    from src.core.shared.models.sso_provider import SSOProvider

    # Create an OIDC provider (Google Workspace)
    google_provider = SSOProvider(
        name="Google Workspace",
        provider_type=SSOProviderType.OIDC,
        enabled=True,
        oidc_client_id="your-client-id.apps.googleusercontent.com",
        oidc_client_secret="your-secret",
        oidc_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    )

    # Create a SAML provider (Okta)
    okta_provider = SSOProvider(
        name="Okta",
        provider_type=SSOProviderType.SAML,
        enabled=True,
        saml_entity_id="http://www.okta.com/exk123",
        saml_metadata_url="https://dev-123.okta.com/app/exk123/sso/saml/metadata",
    )
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.shared.database import Base
from src.core.shared.models.user import SSOProviderType


class SSOProvider(Base):
    """SSO Provider model for identity provider configurations.

    Stores configuration for SAML 2.0 and OIDC identity providers.
    Each provider can be enabled/disabled independently.

    Attributes:
        id: Unique identifier (UUID).
        name: Human-readable provider name (e.g., "Google Workspace", "Okta").
        provider_type: Protocol type (saml or oidc).
        enabled: Whether this provider is active for authentication.

        OIDC-specific:
        oidc_client_id: OAuth 2.0 client ID from the IdP.
        oidc_client_secret: OAuth 2.0 client secret (encrypted at rest).
        oidc_metadata_url: OpenID Connect discovery URL (.well-known/openid-configuration).
        oidc_scopes: Space-separated OAuth scopes to request.

        SAML-specific:
        saml_entity_id: IdP entity ID from SAML metadata.
        saml_metadata_url: URL to fetch IdP SAML metadata XML.
        saml_metadata_xml: Cached IdP metadata XML content.
        saml_sp_cert: SP certificate (PEM format) for signing.
        saml_sp_key: SP private key (PEM format, encrypted at rest).
        saml_sign_requests: Whether to sign SAML AuthnRequests.
        saml_sign_assertions: Whether IdP should sign assertions.
        saml_want_encrypted_assertions: Whether to expect encrypted assertions.

        General:
        config: JSON field for additional provider-specific configuration.
        allowed_domains: Comma-separated list of allowed email domains.
        default_roles: Comma-separated list of default roles for new users.
        created_at: Timestamp when provider was created.
        updated_at: Timestamp of last update.
        metadata_last_fetched: When IdP metadata was last refreshed.

    Indexes:
        - Primary key on id
        - Unique index on name
        - Index on provider_type for filtering by protocol
    """

    __tablename__ = "sso_providers"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique provider identifier (UUID)",
    )

    # Core provider fields
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Human-readable provider name (e.g., 'Google Workspace', 'Okta')",
    )

    provider_type: Mapped[str] = mapped_column(
        Enum(SSOProviderType, name="sso_provider_type", create_constraint=True),
        nullable=False,
        comment="SSO protocol type (saml or oidc)",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this provider is active for authentication",
    )

    # OIDC-specific fields
    oidc_client_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="OAuth 2.0 client ID from the IdP",
    )

    oidc_client_secret: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="OAuth 2.0 client secret (should be encrypted at rest)",
    )

    oidc_metadata_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="OpenID Connect discovery URL (.well-known/openid-configuration)",
    )

    oidc_scopes: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        default="openid profile email",
        comment="Space-separated OAuth scopes to request",
    )

    # SAML-specific fields
    saml_entity_id: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="IdP entity ID from SAML metadata",
    )

    saml_metadata_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="URL to fetch IdP SAML metadata XML",
    )

    saml_metadata_xml: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Cached IdP metadata XML content",
    )

    saml_sp_cert: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SP certificate (PEM format) for signing SAML requests",
    )

    saml_sp_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SP private key (PEM format, should be encrypted at rest)",
    )

    saml_sign_requests: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to sign SAML AuthnRequests",
    )

    saml_sign_assertions: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether IdP should sign assertions (validation enforced)",
    )

    saml_want_encrypted_assertions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether to expect encrypted assertions from IdP",
    )

    # General configuration
    config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON field for additional provider-specific configuration",
    )

    allowed_domains: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Comma-separated list of allowed email domains (null = all)",
    )

    default_roles: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Comma-separated list of default roles for new users from this provider",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when provider was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp of last update",
    )

    metadata_last_fetched: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When IdP metadata was last refreshed",
    )

    # Indexes
    __table_args__ = (
        Index("ix_sso_providers_provider_type", "provider_type"),
        Index("ix_sso_providers_enabled", "enabled"),
        {"comment": "ACGS-2 SSO provider configurations for SAML/OIDC IdPs"},
    )

    def __repr__(self) -> str:
        """String representation of the provider."""
        return (
            f"<SSOProvider(id={self.id!r}, name={self.name!r}, "
            f"type={self.provider_type}, enabled={self.enabled})>"
        )

    @property
    def is_oidc(self) -> bool:
        """Check if this is an OIDC provider."""
        return self.provider_type == SSOProviderType.OIDC

    @property
    def is_saml(self) -> bool:
        """Check if this is a SAML provider."""
        return self.provider_type == SSOProviderType.SAML

    @property
    def allowed_domain_list(self) -> list[str]:
        """Get allowed domains as a list.

        Returns:
            List of allowed email domains, or empty list if all domains allowed.
        """
        if not self.allowed_domains:
            return []
        return [d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()]

    @property
    def default_role_list(self) -> list[str]:
        """Get default roles as a list.

        Returns:
            List of default role names, or empty list if no defaults.
        """
        if not self.default_roles:
            return []
        return [r.strip() for r in self.default_roles.split(",") if r.strip()]

    @property
    def oidc_scope_list(self) -> list[str]:
        """Get OIDC scopes as a list.

        Returns:
            List of OAuth scopes to request.
        """
        if not self.oidc_scopes:
            return ["openid", "profile", "email"]
        return [s.strip() for s in self.oidc_scopes.split() if s.strip()]

    def set_allowed_domains(self, domains: list[str]) -> None:
        """Set allowed domains from a list.

        Args:
            domains: List of email domains to allow.
        """
        if domains:
            self.allowed_domains = ",".join(sorted(set(d.lower() for d in domains)))
        else:
            self.allowed_domains = None

    def set_default_roles(self, roles: list[str]) -> None:
        """Set default roles from a list.

        Args:
            roles: List of role names to assign by default.
        """
        self.default_roles = ",".join(sorted(set(roles))) if roles else None

    def is_domain_allowed(self, email: str) -> bool:
        """Check if an email domain is allowed for this provider.

        Args:
            email: Email address to check.

        Returns:
            True if domain is allowed (or no restrictions), False otherwise.
        """
        allowed = self.allowed_domain_list
        if not allowed:
            return True  # No restrictions

        domain = email.split("@")[-1].lower()
        return domain in allowed

    def get_config(self) -> dict[str, Any]:
        """Get additional configuration as a dictionary.

        Returns:
            Parsed JSON configuration, or empty dict if not set.
        """
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict[str, Any]) -> None:
        """Set additional configuration from a dictionary.

        Args:
            config: Configuration dictionary to store.
        """
        self.config = json.dumps(config) if config else None

    def update_metadata_timestamp(self) -> None:
        """Update the metadata last fetched timestamp to now."""
        self.metadata_last_fetched = datetime.now(timezone.utc)

    def needs_metadata_refresh(self, max_age_hours: int = 24) -> bool:
        """Check if IdP metadata needs to be refreshed.

        Args:
            max_age_hours: Maximum age of cached metadata in hours.

        Returns:
            True if metadata should be refreshed, False otherwise.
        """
        if not self.metadata_last_fetched:
            return True

        age = datetime.now(timezone.utc) - self.metadata_last_fetched
        return age.total_seconds() > (max_age_hours * 3600)

    def validate_oidc_config(self) -> list[str]:
        """Validate OIDC provider configuration.

        Returns:
            List of validation errors, empty if valid.
        """
        errors = []
        if not self.is_oidc:
            return errors

        if not self.oidc_client_id:
            errors.append("OIDC client ID is required")
        if not self.oidc_client_secret:
            errors.append("OIDC client secret is required")
        if not self.oidc_metadata_url:
            errors.append("OIDC metadata URL is required")

        return errors

    def validate_saml_config(self) -> list[str]:
        """Validate SAML provider configuration.

        Returns:
            List of validation errors, empty if valid.
        """
        errors = []
        if not self.is_saml:
            return errors

        if not self.saml_entity_id and not self.saml_metadata_url:
            errors.append("SAML entity ID or metadata URL is required")
        if not self.saml_sp_cert:
            errors.append("SAML SP certificate is required for signing")
        if not self.saml_sp_key:
            errors.append("SAML SP private key is required for signing")

        return errors

    def validate(self) -> list[str]:
        """Validate provider configuration based on type.

        Returns:
            List of validation errors, empty if valid.
        """
        errors = []

        if not self.name:
            errors.append("Provider name is required")

        if self.is_oidc:
            errors.extend(self.validate_oidc_config())
        elif self.is_saml:
            errors.extend(self.validate_saml_config())

        return errors
