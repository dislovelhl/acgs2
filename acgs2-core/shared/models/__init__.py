"""
ACGS-2 Shared Data Models
Constitutional Hash: cdd01ef066bc6cf2

This module provides shared data models for SSO authentication and
related functionality.

Usage:
    from shared.models import User, SSOProviderType, SSOProvider

    # Create a user
    user = User(email="user@example.com", name="John Doe")

    # Create an SSO user
    sso_user = User(
        email="sso_user@example.com",
        sso_enabled=True,
        sso_provider=SSOProviderType.OIDC,
    )

    # Create an OIDC provider
    provider = SSOProvider(
        name="Google Workspace",
        provider_type=SSOProviderType.OIDC,
        oidc_client_id="your-client-id",
        oidc_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    )
"""

from .sso_provider import SSOProvider
from .user import SSOProviderType, User

__all__ = [
    "SSOProvider",
    "SSOProviderType",
    "User",
]
