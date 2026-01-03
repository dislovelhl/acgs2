"""
ACGS-2 Authentication Handlers
Constitutional Hash: cdd01ef066bc6cf2

This module provides authentication handlers for SSO integration,
supporting both OpenID Connect (OIDC) and SAML 2.0 protocols.

Usage:
    from shared.auth import OIDCHandler, SAMLHandler
    from shared.auth.oidc_handler import OIDCConfig
    from shared.auth.saml_config import SAMLSPConfig, SAMLIdPConfig

    # --- OIDC Authentication ---
    # Create OIDC handler with default settings
    oidc_handler = OIDCHandler()

    # Initialize a login flow
    auth_url, state = await oidc_handler.initiate_login(
        provider_name="google",
        redirect_uri="https://app.example.com/callback"
    )

    # Handle the callback after IdP authentication
    user_info = await oidc_handler.handle_callback(
        provider_name="google",
        code="authorization_code",
        state="state_from_session"
    )

    # --- SAML Authentication ---
    # Create SAML handler with default settings
    saml_handler = SAMLHandler()

    # Register an IdP
    saml_handler.register_idp(
        name="okta",
        metadata_url="https://dev-123.okta.com/app/exk123/sso/saml/metadata"
    )

    # Initiate SAML login
    redirect_url, request_id = await saml_handler.initiate_login("okta")

    # Process ACS callback
    user_info = await saml_handler.process_acs_response(saml_response, request_id)
"""

from .oidc_handler import OIDCHandler
from .saml_handler import SAMLHandler

__all__ = [
    "OIDCHandler",
    "SAMLHandler",
]
