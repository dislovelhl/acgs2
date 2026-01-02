"""
ACGS-2 API Gateway Routes
Constitutional Hash: cdd01ef066bc6cf2

This module contains route handlers for the API Gateway service,
including SSO authentication endpoints for OIDC and SAML protocols.
"""

from .sso import router as sso_router

__all__ = [
    "sso_router",
]
