"""
ACGS-2 Shared Data Models
Constitutional Hash: cdd01ef066bc6cf2

This module provides shared data models for SSO authentication and
related functionality.

Usage:
    from src.core.shared.models import User, SSOProviderType, SSOProvider, SSORoleMapping
    from src.core.shared.models import SAMLOutstandingRequest

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

    # Create a role mapping (IdP group -> ACGS-2 role)
    mapping = SSORoleMapping(
        provider_id=provider.id,
        idp_group="Engineering",
        acgs_role="developer",
    )

    # Track SAML outstanding request (replay attack prevention)
    saml_request = SAMLOutstandingRequest(
        request_id="id-abc123",
        provider_id=provider.id,
    )
"""

from .saml_request import SAMLOutstandingRequest
from .sso_provider import SSOProvider
from .sso_role_mapping import SSORoleMapping
from .user import SSOProviderType, User

__all__ = [
    "SAMLOutstandingRequest",
    "SSOProvider",
    "SSOProviderType",
    "SSORoleMapping",
    "User",
]
