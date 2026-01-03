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
    - GET /saml/metadata - Get SP metadata XML
    - GET /saml/login - Initiate SAML login flow
    - POST /saml/acs - Assertion Consumer Service (handle SAML response)
    - GET/POST /saml/sls - Single Logout Service
    - GET /saml/providers - List available SAML providers
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from shared.auth import OIDCHandler, SAMLHandler
from shared.auth.oidc_handler import (
    OIDCAuthenticationError,
    OIDCConfigurationError,
    OIDCProviderError,
    OIDCTokenError,
    OIDCUserInfo,
)
from shared.auth.provisioning import (
    DomainNotAllowedError,
    ProvisioningDisabledError,
    ProvisioningError,
    ProvisioningResult,
    get_provisioner,
)
from shared.auth.saml_config import SAMLConfigurationError, SAMLSPConfig
from shared.auth.saml_handler import (
    SAMLAuthenticationError,
    SAMLError,
    SAMLProviderError,
    SAMLReplayError,
    SAMLUserInfo,
    SAMLValidationError,
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

# Global SAML handler instance (singleton pattern)
_saml_handler: Optional[SAMLHandler] = None


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


def get_saml_handler(request: Request) -> SAMLHandler:
    """Get or create the SAML handler singleton.

    Args:
        request: The incoming request (used to construct absolute URLs)

    Returns:
        SAMLHandler instance with configured providers

    Raises:
        HTTPException: If SAML is not enabled
    """
    global _saml_handler

    if _saml_handler is None:
        # Construct SP configuration with absolute URLs
        base_url = str(request.base_url).rstrip("/")

        sp_config = SAMLSPConfig(
            entity_id=settings.sso.saml_entity_id or f"{base_url}/sso/saml/metadata",
            acs_url=f"{base_url}/sso/saml/acs",
            sls_url=f"{base_url}/sso/saml/sls",
            metadata_url=f"{base_url}/sso/saml/metadata",
            sign_authn_requests=settings.sso.saml_sign_requests,
            want_assertions_signed=settings.sso.saml_want_assertions_signed,
            want_assertions_encrypted=settings.sso.saml_want_assertions_encrypted,
        )

        # Set SP certificate and key if configured
        if settings.sso.saml_sp_certificate:
            sp_config.cert_content = settings.sso.saml_sp_certificate
        if settings.sso.saml_sp_private_key:
            sp_config.key_content = settings.sso.saml_sp_private_key.get_secret_value()

        _saml_handler = SAMLHandler(sp_config=sp_config)

        # Register default IdP from settings
        _register_default_saml_providers(_saml_handler)

    return _saml_handler


def _register_default_saml_providers(handler: SAMLHandler) -> None:
    """Register default SAML IdP providers from settings.

    Args:
        handler: SAMLHandler instance to register providers on
    """
    if not settings.sso.saml_enabled:
        logger.info(
            "SAML SSO not enabled, skipping provider registration",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )
        return

    # Register IdP from settings if configured
    if settings.sso.saml_idp_metadata_url or settings.sso.saml_idp_sso_url:
        try:
            handler.register_idp(
                name="default",
                metadata_url=settings.sso.saml_idp_metadata_url,
                entity_id=settings.sso.saml_entity_id,
                sso_url=settings.sso.saml_idp_sso_url,
                slo_url=settings.sso.saml_idp_slo_url,
                certificate=settings.sso.saml_idp_certificate,
                want_assertions_signed=settings.sso.saml_want_assertions_signed,
            )
            logger.info(
                "Registered default SAML IdP",
                extra={
                    "has_metadata_url": bool(settings.sso.saml_idp_metadata_url),
                    "has_sso_url": bool(settings.sso.saml_idp_sso_url),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
        except SAMLConfigurationError as e:
            logger.warning(
                "Failed to register default SAML IdP",
                extra={
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
        except Exception as e:
            logger.warning(
                "Unexpected error registering default SAML IdP",
                extra={
                    "error": str(e),
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


class SAMLUserInfoResponse(BaseModel):
    """Response containing user information after SAML authentication."""

    name_id: str = Field(..., description="SAML NameID (unique user identifier)")
    email: Optional[str] = Field(None, description="User's email address")
    name: Optional[str] = Field(None, description="User's full name")
    given_name: Optional[str] = Field(None, description="User's first name")
    family_name: Optional[str] = Field(None, description="User's last name")
    groups: list[str] = Field(default_factory=list, description="Group memberships")
    session_index: Optional[str] = Field(None, description="Session index for logout")


class SAMLACSRequest(BaseModel):
    """Request model for SAML ACS endpoint."""

    SAMLResponse: str = Field(..., description="Base64-encoded SAML response")
    RelayState: Optional[str] = Field(None, description="Relay state for redirect")


class SAMLSLSRequest(BaseModel):
    """Request model for SAML SLS endpoint."""

    SAMLResponse: Optional[str] = Field(None, description="Base64-encoded SAML logout response")
    SAMLRequest: Optional[str] = Field(None, description="Base64-encoded SAML logout request")
    RelayState: Optional[str] = Field(None, description="Relay state for redirect")


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

        # JIT Provisioning: Create or update user in database
        # Get default role as a list (provisioner expects list of roles)
        default_roles = None
        if (
            hasattr(settings.sso, "default_role_on_provision")
            and settings.sso.default_role_on_provision
        ):
            default_roles = [settings.sso.default_role_on_provision]

        provisioner = get_provisioner(
            auto_provision_enabled=settings.sso.auto_provision_users,
            default_roles=default_roles,
            allowed_domains=settings.sso.allowed_domains if settings.sso.allowed_domains else None,
        )

        # Provision the user (creates new user or updates existing)
        provisioning_result: ProvisioningResult = await provisioner.get_or_create_user(
            email=user_info.email,
            name=user_info.name,
            sso_provider="oidc",
            idp_user_id=user_info.sub,
            provider_id=stored_provider,
            roles=user_info.groups,  # Map IdP groups to roles
        )

        # Store user info in session with provisioned user data
        request.session["user"] = {
            "id": provisioning_result.user.get("id"),
            "sub": user_info.sub,
            "email": provisioning_result.user.get("email"),
            "name": provisioning_result.user.get("name"),
            "groups": user_info.groups,
            "roles": provisioning_result.user.get("roles", []),
            "provider": stored_provider,
            "auth_type": "oidc",
            "sso_enabled": True,
        }

        logger.info(
            "OIDC authentication and provisioning successful",
            extra={
                "provider": stored_provider,
                "user_sub": user_info.sub[:8] + "..." if user_info.sub else "N/A",
                "email": user_info.email,
                "user_created": provisioning_result.created,
                "roles_updated": provisioning_result.roles_updated,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        # Return user information with provisioning details
        return {
            "sub": user_info.sub,
            "email": user_info.email,
            "email_verified": user_info.email_verified,
            "name": user_info.name,
            "given_name": user_info.given_name,
            "family_name": user_info.family_name,
            "groups": user_info.groups,
        }

    except DomainNotAllowedError as e:
        logger.warning(
            "OIDC user domain not allowed",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=403,
            detail="Your email domain is not allowed for this SSO provider.",
        ) from e

    except ProvisioningDisabledError as e:
        logger.warning(
            "OIDC auto-provisioning disabled",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=403,
            detail=(
                "Auto-provisioning is disabled. "
                "Please contact an administrator to create your account."
            ),
        ) from e

    except ProvisioningError as e:
        logger.error(
            "OIDC user provisioning failed",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to provision user account. Please try again or contact support.",
        ) from e

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


# SAML Endpoints


@router.get("/saml/metadata")
async def saml_metadata(
    request: Request,
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> Response:
    """Get SAML Service Provider (SP) metadata.

    This endpoint returns the SP metadata XML document that contains:
    - Entity ID
    - Assertion Consumer Service (ACS) URL
    - Single Logout Service (SLS) URL
    - SP signing certificate
    - Name ID formats supported

    The metadata is used by Identity Providers (IdPs) to configure
    trust relationships with this SP.

    Returns:
        XML document containing SP metadata
    """
    try:
        metadata_xml = await handler.generate_metadata()

        logger.info(
            "SAML SP metadata generated",
            extra={
                "entity_id": handler.sp_config.entity_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": 'attachment; filename="sp-metadata.xml"',
            },
        )

    except SAMLError as e:
        logger.error(
            "Failed to generate SAML metadata",
            extra={
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate SP metadata.",
        ) from e


@router.get("/saml/providers", response_model=list[SSOProviderInfo])
async def list_saml_providers(
    request: Request,
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> list[SSOProviderInfo]:
    """List available SAML Identity Providers.

    Returns:
        List of registered SAML IdPs with their status
    """
    providers = handler.list_idps()
    return [SSOProviderInfo(name=name, type="saml", enabled=True) for name in providers]


@router.get("/saml/login")
async def saml_login(
    request: Request,
    provider: str = Query(..., description="SAML IdP name (e.g., okta, azure, default)"),
    relay_state: Optional[str] = Query(None, description="URL to redirect to after authentication"),
    force_authn: bool = Query(False, description="Force re-authentication"),
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> RedirectResponse:
    """Initiate SAML SP-initiated login flow.

    This endpoint creates a SAML AuthnRequest and redirects the user
    to the Identity Provider (IdP) for authentication. After the user
    authenticates, the IdP will redirect back to /saml/acs with a SAML
    Response containing the authentication assertion.

    Args:
        request: The incoming request
        provider: Name of the SAML IdP to use
        relay_state: Optional URL to redirect to after authentication
        force_authn: Force re-authentication even if user has IdP session
        handler: SAML handler dependency

    Returns:
        RedirectResponse to the IdP SSO endpoint

    Raises:
        HTTPException: If provider is not found or SSO is disabled
    """
    if not settings.sso.enabled and not settings.sso.saml_enabled:
        raise HTTPException(
            status_code=503,
            detail="SSO is not enabled. Please contact administrator.",
        )

    try:
        # Initiate login and get redirect URL
        redirect_url, request_id = await handler.initiate_login(
            idp_name=provider,
            relay_state=relay_state,
            force_authn=force_authn,
        )

        # Store request ID in session for validation on ACS callback
        request.session["saml_request_id"] = request_id
        request.session["saml_provider"] = provider
        request.session["saml_relay_state"] = relay_state

        logger.info(
            "SAML login initiated",
            extra={
                "provider": provider,
                "request_id": request_id[:16] + "...",
                "force_authn": force_authn,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        # Redirect to IdP
        return RedirectResponse(url=redirect_url, status_code=302)

    except SAMLConfigurationError as e:
        logger.error(
            "SAML provider not found",
            extra={
                "provider": provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=404,
            detail=f"SAML provider '{provider}' not found or not configured.",
        ) from e

    except SAMLProviderError as e:
        logger.error(
            "Failed to initiate SAML login",
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

    except SAMLError as e:
        logger.error(
            "SAML login error",
            extra={
                "provider": provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred initiating SAML login.",
        ) from e


@router.post("/saml/acs", response_model=SAMLUserInfoResponse)
async def saml_acs(
    request: Request,
    SAMLResponse: str = Form(..., description="Base64-encoded SAML response"),
    RelayState: Optional[str] = Form(None, description="Relay state for redirect"),
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> dict[str, Any]:
    """SAML Assertion Consumer Service (ACS) endpoint.

    This endpoint receives SAML responses from the IdP after user
    authentication. It validates the SAML assertion (signature,
    timestamps, audience, etc.) and extracts user information.

    The endpoint supports both:
    - SP-initiated SSO: Response to an AuthnRequest we sent
    - IdP-initiated SSO: Unsolicited response from IdP

    Args:
        request: The incoming request
        SAMLResponse: Base64-encoded SAML response from IdP
        RelayState: Optional relay state for post-authentication redirect
        handler: SAML handler dependency

    Returns:
        User information extracted from SAML assertion

    Raises:
        HTTPException: If SAML validation fails or authentication error
    """
    # Get stored request ID from session (for SP-initiated SSO)
    stored_request_id = request.session.get("saml_request_id")
    stored_provider = request.session.get("saml_provider")

    try:
        # Process the SAML response
        user_info: SAMLUserInfo = await handler.process_acs_response(
            saml_response=SAMLResponse,
            request_id=stored_request_id,
            idp_name=stored_provider,
        )

        # Clear SAML session data after successful authentication
        request.session.pop("saml_request_id", None)
        request.session.pop("saml_provider", None)
        request.session.pop("saml_relay_state", None)

        # Store user info in session
        request.session["user"] = {
            "sub": user_info.name_id,
            "email": user_info.email,
            "name": user_info.name,
            "groups": user_info.groups,
            "provider": stored_provider or "saml",
            "auth_type": "saml",
            "session_index": user_info.session_index,
            "name_id": user_info.name_id,
            "name_id_format": user_info.name_id_format,
        }

        logger.info(
            "SAML authentication successful",
            extra={
                "provider": stored_provider,
                "name_id": user_info.name_id[:16] + "..." if user_info.name_id else "N/A",
                "email": user_info.email,
                "groups_count": len(user_info.groups),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        # Return user information
        # Note: In a full implementation, this would trigger JIT provisioning
        # and redirect to RelayState. For now, return user info.
        return {
            "name_id": user_info.name_id,
            "email": user_info.email,
            "name": user_info.name,
            "given_name": user_info.given_name,
            "family_name": user_info.family_name,
            "groups": user_info.groups,
            "session_index": user_info.session_index,
        }

    except SAMLReplayError as e:
        logger.warning(
            "SAML replay attack detected",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail="SAML response replay detected. Please try logging in again.",
        ) from e

    except SAMLValidationError as e:
        logger.error(
            "SAML validation failed",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=401,
            detail="SAML response validation failed. Please try logging in again.",
        ) from e

    except SAMLAuthenticationError as e:
        logger.error(
            "SAML authentication failed",
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

    except SAMLError as e:
        logger.error(
            "SAML error during ACS processing",
            extra={
                "provider": stored_provider,
                "error": str(e),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing the SAML response.",
        ) from e


@router.get("/saml/sls")
@router.post("/saml/sls")
async def saml_sls(
    request: Request,
    SAMLResponse: Optional[str] = Query(None, description="Base64-encoded SAML logout response"),
    SAMLRequest: Optional[str] = Query(None, description="Base64-encoded SAML logout request"),
    RelayState: Optional[str] = Query(None, description="Relay state for redirect"),
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> SSOLogoutResponse:
    """SAML Single Logout Service (SLS) endpoint.

    This endpoint handles SAML logout requests and responses:
    - SP-initiated logout response: Response to a logout request we sent
    - IdP-initiated logout request: Request from IdP to log out user

    Args:
        request: The incoming request
        SAMLResponse: SAML logout response (from IdP after we initiated logout)
        SAMLRequest: SAML logout request (IdP-initiated logout)
        RelayState: Optional relay state for post-logout redirect
        handler: SAML handler dependency

    Returns:
        Logout response with status
    """
    user = request.session.get("user")
    provider_name = user.get("provider") if user else None

    # Handle logout response (after we initiated logout)
    if SAMLResponse and provider_name:
        try:
            success = await handler.process_sls_response(
                saml_response=SAMLResponse,
                idp_name=provider_name,
            )

            if success:
                request.session.clear()
                logger.info(
                    "SAML logout response processed successfully",
                    extra={
                        "provider": provider_name,
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )
                return SSOLogoutResponse(
                    success=True,
                    message="Successfully logged out",
                    redirect_url=RelayState,
                )
            else:
                logger.warning(
                    "SAML logout response indicated failure",
                    extra={
                        "provider": provider_name,
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )
                # Still clear local session
                request.session.clear()
                return SSOLogoutResponse(
                    success=False,
                    message="Logout may not be complete at identity provider",
                    redirect_url=RelayState,
                )

        except SAMLError as e:
            logger.error(
                "Failed to process SAML logout response",
                extra={
                    "provider": provider_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            # Still clear local session on error
            request.session.clear()
            return SSOLogoutResponse(
                success=False,
                message="Error processing logout response",
                redirect_url=RelayState,
            )

    # Handle IdP-initiated logout request
    if SAMLRequest:
        # For now, just clear the session and acknowledge
        # A full implementation would parse the request and send a response
        request.session.clear()
        logger.info(
            "SAML IdP-initiated logout processed",
            extra={
                "provider": provider_name,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )
        return SSOLogoutResponse(
            success=True,
            message="Session terminated",
            redirect_url=RelayState,
        )

    # No SAML message - just clear session
    request.session.clear()
    logger.info(
        "SAML local logout completed",
        extra={
            "provider": provider_name,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )
    return SSOLogoutResponse(
        success=True,
        message="Successfully logged out locally",
        redirect_url=RelayState,
    )


@router.post("/saml/logout", response_model=SSOLogoutResponse)
async def saml_logout(
    request: Request,
    handler: SAMLHandler = Depends(get_saml_handler),  # noqa: B008
) -> SSOLogoutResponse:
    """Initiate SAML SP-initiated logout.

    This endpoint initiates SAML Single Logout (SLO) by sending a
    logout request to the IdP. If the IdP supports SLO, it will
    terminate the user's session there as well.

    Args:
        request: The incoming request
        handler: SAML handler dependency

    Returns:
        Logout response with optional redirect URL to IdP
    """
    user = request.session.get("user")
    if not user:
        return SSOLogoutResponse(
            success=True,
            message="No active session",
            redirect_url=None,
        )

    provider_name = user.get("provider")
    name_id = user.get("name_id")
    session_index = user.get("session_index")
    redirect_url = None

    if provider_name and name_id:
        try:
            # Get IdP logout URL
            redirect_url = await handler.initiate_logout(
                idp_name=provider_name,
                name_id=name_id,
                session_index=session_index,
                relay_state=str(request.base_url),
            )
        except SAMLError as e:
            logger.warning(
                "Failed to initiate SAML logout",
                extra={
                    "provider": provider_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
        except Exception as e:
            logger.warning(
                "Unexpected error during SAML logout",
                extra={
                    "provider": provider_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

    # Clear local session
    request.session.clear()

    logger.info(
        "SAML logout initiated",
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
