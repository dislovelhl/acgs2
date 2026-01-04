"""
Webhook authentication result models for ACGS-2 Integration Service.

This module defines data models for authentication results and OAuth tokens,
providing structured representations of authentication attempts and OAuth 2.0
token information with expiration tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from ..models import WebhookAuthType


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    authenticated: bool = Field(..., description="Whether authentication succeeded")
    auth_type: WebhookAuthType = Field(..., description="Type of authentication used")
    principal: Optional[str] = Field(
        None, description="Authenticated principal (user, key ID, etc.)"
    )
    scopes: List[str] = Field(default_factory=list, description="Granted scopes/permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional auth metadata")

    # Error details (if not authenticated)
    error_code: Optional[str] = Field(None, description="Error code if authentication failed")
    error_message: Optional[str] = Field(None, description="Error message if authentication failed")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def success(
        cls,
        auth_type: WebhookAuthType,
        principal: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthResult":
        """Create a successful authentication result."""
        return cls(
            authenticated=True,
            auth_type=auth_type,
            principal=principal,
            scopes=scopes or [],
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        auth_type: WebhookAuthType,
        error_code: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthResult":
        """Create a failed authentication result."""
        return cls(
            authenticated=False,
            auth_type=auth_type,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {},
        )


class OAuthToken(BaseModel):
    """OAuth 2.0 token model."""

    access_token: SecretStr = Field(..., description="The access token")
    token_type: str = Field(default="Bearer", description="Token type (usually Bearer)")
    expires_in: Optional[int] = Field(None, description="Token lifetime in seconds")
    refresh_token: Optional[SecretStr] = Field(None, description="Refresh token if available")
    scope: Optional[str] = Field(None, description="Granted scopes (space-separated)")

    # Computed fields
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the token was issued",
    )
    expires_at: Optional[datetime] = Field(None, description="When the token expires")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def model_post_init(self, _: Any) -> None:
        """Calculate expiration time if not set."""
        if self.expires_at is None and self.expires_in is not None:
            self.expires_at = self.issued_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        # Add 30 second buffer for clock skew
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=30))

    @property
    def scopes(self) -> List[str]:
        """Get scopes as a list."""
        if self.scope is None:
            return []
        return self.scope.split()


__all__ = [
    "AuthResult",
    "OAuthToken",
]
