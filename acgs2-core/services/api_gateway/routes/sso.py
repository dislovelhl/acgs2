"""
ACGS-2 SSO Authentication Endpoints
Constitutional Hash: cdd01ef066bc6cf2

Provides OpenID Connect (OIDC) and SAML 2.0 authentication endpoints
for enterprise Single Sign-On integration.

Endpoints:
    - GET /oidc/login - Initiate OIDC login flow
    - GET /oidc/callback - Handle OIDC callback after IdP authentication
    - POST /oidc/logout - OIDC logout
    - GET /oidc/providers - List available OIDC providers
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from shared.auth import OIDCHandler
from shared.auth.oidc_handler import (
    OIDCAuthenticationError,
    OIDCConfigurationError,
    OIDCProviderError,
    OIDCTokenError,
    OIDCUserInfo,
)
from shared.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Create router
router = APIRouter(tags=["SSO"])

# Global OIDC handler instance (singleton pattern)
_oidc_handler: Optional[OIDCHandler] = None


def get_oidc_handler() -> OIDCHandler:
    """Get or create the OIDC handler singleton.

    Returns:
        OIDCHandler instance with configured providers

    Raises:
        HTTPException: If OIDC is not enabled
    """
    global _oidc_handler

    if _oidc_handler is None:
        _oidc_handler = OIDCHandler()

        # Register providers from database or settings
        _register_default_providers(_oidc_handler)

    return _oidc_handler


def _register_default_providers(handler: OIDCHandler) -> None:
    """Register default OIDC providers from settings.

    Args:
        handler: OIDCHandler instance to register providers on
    """
    # Register Google provider if configured
    if settings.sso.oidc_enabled and settings.sso.oidc_client_id:
        try:
            client_secret = (
                settings.sso.oidc_client_secret.get_secret_value()
                if settings.sso.oidc_client_secret
                else ""
            )

            # Use issuer URL for discovery if available, otherwise construct
            discovery_url = settings.sso.oidc_issuer_url
            if discovery_url and not discovery_url.endswith("/.well-known/openid-configuration"):
                discovery_url = discovery_url.rstrip("/") + "/.well-known/openid-configuration"

            if discovery_url:
                handler.register_provider(
                    name="default",
                    client_id=settings.sso.oidc_client_id,
                    client_secret=client_secret,
                    server_metadata_url=discovery_url,
                    scopes=settings.sso.oidc_scopes,
                    use_pkce=settings.sso.oidc_use_pkce,
                )
                logger.info(
                    "Registered default OIDC provider",
                    extra={
                        "discovery_url": discovery_url,
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )
        except Exception as e:
            logger.warning(
                "Failed to register default OIDC provider",
                extra={
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

    # Common provider configurations (can be enabled via environment)
    provider_configs = {
        "google": {
            "metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        },
        "azure": {
            "metadata_url": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        },
        "okta": {
            # Okta requires a domain, will be constructed from env
            "metadata_url": None,
        },
    }

    # Log available provider templates
    logger.info(
        "OIDC provider templates available",
        extra={
            "providers": list(provider_configs.keys()),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )


# Response Models
class SSOLoginResponse(BaseModel):
    """Response for SSO login initiation."""

    redirect_url: str = Field(..., description="URL to redirect user for authentication")
    state: str = Field(..., description="State parameter for CSRF protection")
    provider: str = Field(..., description="Name of the SSO provider")


class SSOUserInfoResponse(BaseModel):
    """Response containing user information after SSO callback."""

    sub: str = Field(..., description="Subject identifier from IdP")
    email: Optional[str] = Field(None, description="User's email address")
    email_verified: bool = Field(False, description="Whether email is verified")
    name: Optional[str] = Field(None, description="User's full name")
    given_name: Optional[str] = Field(None, description="User's first name")
    family_name: Optional[str] = Field(None, description="User's last name")
    groups: list[str] = Field(default_factory=list, description="Group memberships")


class SSOProviderInfo(BaseModel):
    """Information about an available SSO provider."""

    name: str = Field(..., description="Provider name")
    type: str = Field("oidc", description="Provider type (oidc or saml)")
    enabled: bool = Field(True, description="Whether provider is enabled")


class SSOLogoutResponse(BaseModel):
    """Response for SSO logout."""

    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Logout status message")
    redirect_url: Optional[str] = Field(None, description="IdP logout URL if available")


# Exception handlers for SSO errors
async def handle_sso_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle SSO-related exceptions with proper error responses.

    Args:
        request: The incoming request
        exc: The exception to handle

    Returns:
        JSONResponse with appropriate error details
    """
    logger.error(
        "SSO error occurred",
        extra={
            "error_type": type(exc).__name__,
            "error": str(exc),
            "path": request.url.path,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    if isinstance(exc, OIDCConfigurationError):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "SSO provider not properly configured. Please contact administrator."
            },
        )
    elif isinstance(exc, OIDCAuthenticationError):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication failed. Please try again."},
        )
    elif isinstance(exc, OIDCTokenError):
        return JSONResponse(
            status_code=401,
            content={"detail": "Token validation failed. Please try logging in again."},
        )
    elif isinstance(exc, OIDCProviderError):
        return JSONResponse(
            status_code=502,
            content={"detail": "Unable to communicate with identity provider."},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred during authentication."},
        )


# OIDC Endpoints


@router.get("/oidc/providers", response_model=list[SSOProviderInfo])
async def list_oidc_providers(
    handler: OIDCHandler = Depends(get_oidc_handler),  # noqa: B008
) -> list[SSOProviderInfo]:
    """List available OIDC providers.

    Returns:
        List of available OIDC providers with their configuration status
    """
    providers = handler.list_providers()
    return [SSOProviderInfo(name=name, type="oidc", enabled=True) for name in providers]


@router.get("/oidc/login")
async def oidc_login(
    request: Request,
    provider: str = Query(..., description="OIDC provider name (e.g., google, azure, okta)"),
    redirect_uri: Optional[str] = Query(
        None, description="Custom redirect URI after authentication"
    ),
    handler: OIDCHandler = Depends(get_oidc_handler),  # noqa: B008
) -> RedirectResponse:
    """Initiate OIDC login flow.

    This endpoint redirects the user to the IdP for authentication.
    After authentication, the IdP will redirect back to /oidc/callback.

    Args:
        request: The incoming request
        provider: Name of the OIDC provider to use
        redirect_uri: Optional custom redirect URI
        handler: OIDC handler dependency

    Returns:
        RedirectResponse to the IdP authorization endpoint

    Raises:
        HTTPException: If provider is not found or SSO is disabled
    """
    if not settings.sso.enabled and not settings.sso.oidc_enabled:
        raise HTTPException(
            status_code=503,
            detail="SSO is not enabled. Please contact administrator.",
        )

    # Construct callback URL
    callback_url = redirect_uri or str(request.url_for("oidc_callback"))

    try:
        # Initiate login and get authorization URL
        auth_url, state = await handler.initiate_login(
            provider_name=provider,
            redirect_uri=callback_url,
        )

        # Store state in session for validation on callback
        request.session["oidc_state"] = state
        request.session["oidc_provider"] = provider
        request.session["oidc_callback_url"] = callback_url

        logger.info(
            "OIDC login initiated",
            extra={
                "provider": provider,
                "state": state[:8] + "...",
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        # Redirect to IdP
        return RedirectResponse(url=auth_url, status_code=302)

    except OIDCConfigurationError as e:
        logger.error(
            "OIDC provider not found",
            extra={
                "provider": provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=404,
            detail=f"OIDC provider '{provider}' not found or not configured.",
        ) from e

    except OIDCProviderError as e:
        logger.error(
            "Failed to initiate OIDC login",
            extra={
                "provider": provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to identity provider. Please try again later.",
        ) from e


@router.get("/oidc/callback", response_model=SSOUserInfoResponse)
async def oidc_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from IdP"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(None, description="Error from IdP"),
    error_description: Optional[str] = Query(None, description="Error description from IdP"),
    handler: OIDCHandler = Depends(get_oidc_handler),  # noqa: B008
) -> dict[str, Any]:
    """Handle OIDC callback after IdP authentication.

    This endpoint processes the authorization code from the IdP,
    exchanges it for tokens, and retrieves user information.

    Args:
        request: The incoming request
        code: Authorization code from the IdP
        state: State parameter for CSRF validation
        error: Error code from IdP (if authentication failed)
        error_description: Detailed error description
        handler: OIDC handler dependency

    Returns:
        User information from the IdP

    Raises:
        HTTPException: If state validation fails or token exchange fails
    """
    # Handle IdP errors
    if error:
        logger.warning(
            "OIDC authentication error from IdP",
            extra={
                "error": error,
                "error_description": error_description,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail=error_description or f"Authentication failed: {error}",
        )

    # Validate state from session
    stored_state = request.session.get("oidc_state")
    stored_provider = request.session.get("oidc_provider")
    stored_callback_url = request.session.get("oidc_callback_url")

    if not stored_state or stored_state != state:
        logger.warning(
            "OIDC state mismatch - possible CSRF attack",
            extra={
                "received_state": state[:8] + "..." if state else "None",
                "stored_state": stored_state[:8] + "..." if stored_state else "None",
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid state parameter. Please try logging in again.",
        )

    if not stored_provider:
        raise HTTPException(
            status_code=400,
            detail="Missing provider information. Please try logging in again.",
        )

    try:
        # Handle the callback and exchange code for tokens
        user_info: OIDCUserInfo = await handler.handle_callback(
            provider_name=stored_provider,
            code=code,
            state=state,
            redirect_uri=stored_callback_url,
        )

        # Clear SSO session data after successful authentication
        request.session.pop("oidc_state", None)
        request.session.pop("oidc_provider", None)
        request.session.pop("oidc_callback_url", None)

        # Store user info in session
        request.session["user"] = {
            "sub": user_info.sub,
            "email": user_info.email,
            "name": user_info.name,
            "groups": user_info.groups,
            "provider": stored_provider,
            "auth_type": "oidc",
        }

        logger.info(
            "OIDC authentication successful",
            extra={
                "provider": stored_provider,
                "user_sub": user_info.sub[:8] + "..." if user_info.sub else "N/A",
                "email": user_info.email,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        # Return user information
        # Note: In a full implementation, this would trigger JIT provisioning
        # and redirect to the application. For now, return user info.
        return {
            "sub": user_info.sub,
            "email": user_info.email,
            "email_verified": user_info.email_verified,
            "name": user_info.name,
            "given_name": user_info.given_name,
            "family_name": user_info.family_name,
            "groups": user_info.groups,
        }

    except OIDCAuthenticationError as e:
        logger.error(
            "OIDC authentication failed",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Please try logging in again.",
        ) from e

    except OIDCTokenError as e:
        logger.error(
            "OIDC token exchange failed",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail="Token validation failed. Please try logging in again.",
        ) from e

    except OIDCProviderError as e:
        logger.error(
            "Failed to retrieve user info",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve user information from identity provider.",
        ) from e


@router.post("/oidc/logout", response_model=SSOLogoutResponse)
async def oidc_logout(
    request: Request,
    handler: OIDCHandler = Depends(get_oidc_handler),  # noqa: B008
) -> SSOLogoutResponse:
    """OIDC logout endpoint.

    Terminates the local session and optionally redirects to
    the IdP's logout endpoint for RP-initiated logout.

    Args:
        request: The incoming request
        handler: OIDC handler dependency

    Returns:
        Logout response with optional redirect URL to IdP
    """
    user = request.session.get("user")
    provider_name = user.get("provider") if user else None
    redirect_url = None

    if provider_name:
        try:
            # Get IdP logout URL
            redirect_url = await handler.logout(
                provider_name=provider_name,
                post_logout_redirect_uri=str(request.base_url),
            )
        except Exception as e:
            logger.warning(
                "Failed to get IdP logout URL",
                extra={
                    "provider": provider_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

    # Clear local session
    request.session.clear()

    logger.info(
        "OIDC logout completed",
        extra={
            "provider": provider_name,
            "has_idp_logout": bool(redirect_url),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return SSOLogoutResponse(
        success=True,
        message="Successfully logged out",
        redirect_url=redirect_url,
    )


@router.get("/session")
async def get_session_info(request: Request) -> dict[str, Any]:
    """Get current session information.

    Returns:
        Current session state including user information if authenticated
    """
    user = request.session.get("user")

    if not user:
        return {
            "authenticated": False,
            "user": None,
        }

    return {
        "authenticated": True,
        "user": {
            "email": user.get("email"),
            "name": user.get("name"),
            "provider": user.get("provider"),
            "auth_type": user.get("auth_type"),
        },
    }
