"""
ACGS-2 SSO Authentication Router
Constitutional Hash: cdd01ef066bc6cf2

Provides a lean entry point for OIDC and SAML authentication routes.
Delegates implementation to sub-modules in routes/sso/.
"""

import logging
from typing import Dict

from fastapi import APIRouter
from src.core.shared.types import JSONDict
from starlette.requests import Request as StarletteRequest

from .common import get_oidc_handler, get_saml_handler, handle_sso_error
from .oidc import router as oidc_router
from .saml import router as saml_router

# Configure logging
logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Create main SSO router
router = APIRouter(tags=["SSO"])

# Export common handlers for tests
__all__ = ["router", "get_saml_handler", "get_oidc_handler", "handle_sso_error"]

# Include sub-routers
router.include_router(oidc_router, prefix="/oidc")
router.include_router(saml_router, prefix="/saml")


@router.get("/session")
async def get_session_info(request: StarletteRequest):
    """Get current session information."""
    user = request.session.get("user")
    return {
        "authenticated": user is not None,
        "user": user,
    }
