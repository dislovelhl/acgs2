"""
ACGS-2 Authentication Handlers
Constitutional Hash: cdd01ef066bc6cf2

This module provides authentication handlers for SSO integration,
supporting both OpenID Connect (OIDC) and SAML 2.0 protocols.

Usage:
    from shared.auth import OIDCHandler
    from shared.auth.oidc_handler import OIDCConfig

    # Create OIDC handler with default settings
    handler = OIDCHandler()

    # Initialize a login flow
    auth_url, state = await handler.initiate_login(
        provider_name="google",
        redirect_uri="https://app.example.com/callback"
    )

    # Handle the callback after IdP authentication
    user_info = await handler.handle_callback(
        provider_name="google",
        code="authorization_code",
        state="state_from_session"
    )
"""

from .oidc_handler import OIDCHandler

__all__ = [
    "OIDCHandler",
]
