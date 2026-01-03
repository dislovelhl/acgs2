"""
ACGS-2 SAML Outstanding Request Model for Replay Attack Prevention
Constitutional Hash: cdd01ef066bc6cf2

Defines the SAMLOutstandingRequest model for tracking SAML authentication
request IDs to prevent replay attacks. When a SAML AuthnRequest is sent,
the request ID is stored. Upon receiving a SAML Response, the corresponding
request ID must exist and be valid (not expired) for the response to be accepted.

Usage:
    from shared.models.saml_request import SAMLOutstandingRequest

    # Store an outstanding request
    request = SAMLOutstandingRequest(
        request_id="id-abc123",
        provider_id="provider-uuid",
    )

    # Check if request exists and is valid
    if request.is_valid:
        # Process the SAML response
        pass

    # Clean up expired requests
    expired_requests = session.query(SAMLOutstandingRequest).filter(
        SAMLOutstandingRequest.expires_at < datetime.now(timezone.utc)
    ).delete()
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

# Default expiration time for SAML requests (5 minutes)
DEFAULT_REQUEST_EXPIRY_MINUTES = 5


class SAMLOutstandingRequest(Base):
    """SAML Outstanding Request model for replay attack prevention.

    Tracks SAML AuthnRequest IDs to prevent replay attacks. When a SAML
    authentication request is initiated, the request ID is stored with an
    expiration time. The SAML Response must reference a valid, unexpired
    request ID to be accepted.

    This implements the SAML 2.0 security requirement for tracking outstanding
    authentication requests to prevent malicious actors from replaying captured
    SAML assertions.

    Attributes:
        id: Internal unique identifier (UUID).
        request_id: SAML request ID from the AuthnRequest (unique).
        provider_id: Reference to the SSO provider configuration.
        relay_state: Optional RelayState for redirect after authentication.
        created_at: Timestamp when the request was created.
        expires_at: Timestamp when the request expires (default: 5 minutes).

    Indexes:
        - Primary key on id
        - Unique index on request_id for fast lookups
        - Index on expires_at for efficient cleanup of expired requests
        - Index on provider_id for provider-specific queries

    Security Notes:
        - Request IDs should be deleted after successful authentication
        - Expired requests should be periodically cleaned up
        - Each request ID can only be used once (prevents replay attacks)
    """

    __tablename__ = "saml_outstanding_requests"

    # Internal primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Internal unique identifier (UUID)",
    )

    # SAML request ID (from AuthnRequest)
    request_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="SAML request ID from the AuthnRequest (must be unique)",
    )

    # Provider reference
    provider_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Reference to the SSO provider configuration (sso_providers.id)",
    )

    # Optional RelayState for post-authentication redirect
    relay_state: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional RelayState for redirect after authentication",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the request was created",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
        + timedelta(minutes=DEFAULT_REQUEST_EXPIRY_MINUTES),
        nullable=False,
        index=True,
        comment="Timestamp when the request expires (default: 5 minutes from creation)",
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_saml_outstanding_requests_provider_expires", "provider_id", "expires_at"),
        {"comment": "ACGS-2 SAML outstanding requests for replay attack prevention"},
    )

    def __repr__(self) -> str:
        """String representation of the outstanding request."""
        return (
            f"<SAMLOutstandingRequest(id={self.id!r}, "
            f"request_id={self.request_id!r}, expires_at={self.expires_at})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if the request has expired.

        Returns:
            True if the request has expired, False otherwise.
        """
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the request is still valid (not expired).

        Returns:
            True if the request is valid and can be used, False otherwise.
        """
        return not self.is_expired

    @property
    def time_remaining(self) -> timedelta:
        """Get the time remaining until expiration.

        Returns:
            Timedelta of remaining time. Will be negative if expired.
        """
        return self.expires_at - datetime.now(timezone.utc)

    @property
    def time_remaining_seconds(self) -> float:
        """Get the time remaining in seconds.

        Returns:
            Seconds remaining until expiration. Negative if expired.
        """
        return self.time_remaining.total_seconds()

    @classmethod
    def create_with_expiry(
        cls,
        request_id: str,
        provider_id: Optional[str] = None,
        relay_state: Optional[str] = None,
        expiry_minutes: int = DEFAULT_REQUEST_EXPIRY_MINUTES,
    ) -> "SAMLOutstandingRequest":
        """Factory method to create an outstanding request with custom expiry.

        Args:
            request_id: SAML request ID from the AuthnRequest.
            provider_id: Optional reference to SSO provider configuration.
            relay_state: Optional RelayState for post-auth redirect.
            expiry_minutes: Minutes until request expires (default: 5).

        Returns:
            New SAMLOutstandingRequest instance.

        Example:
            request = SAMLOutstandingRequest.create_with_expiry(
                request_id="id-abc123",
                provider_id="provider-uuid",
                expiry_minutes=10,
            )
        """
        now = datetime.now(timezone.utc)
        return cls(
            request_id=request_id,
            provider_id=provider_id,
            relay_state=relay_state,
            created_at=now,
            expires_at=now + timedelta(minutes=expiry_minutes),
        )

    def extend_expiry(self, additional_minutes: int = 5) -> None:
        """Extend the expiration time of this request.

        Args:
            additional_minutes: Minutes to add to the current expiration time.

        Note:
            This should only be used in exceptional circumstances, as extending
            request validity increases the window for potential attacks.
        """
        self.expires_at = self.expires_at + timedelta(minutes=additional_minutes)

    def to_outstanding_dict(self) -> dict[str, str]:
        """Convert to the dictionary format expected by PySAML2.

        PySAML2's parse_authn_request_response expects a dictionary mapping
        request IDs to their creation timestamps in ISO format.

        Returns:
            Dictionary with request_id as key and ISO timestamp as value.

        Example:
            outstanding = {req.request_id: req.created_at.isoformat() for req in requests}
            response = saml_client.parse_authn_request_response(
                saml_response, BINDING_HTTP_POST, outstanding=outstanding
            )
        """
        return {self.request_id: self.created_at.isoformat()}
