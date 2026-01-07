"""
Shared SSO models, handlers and exception logic.
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from typing import List, Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.core.shared.auth import OIDCHandler, SAMLHandler
from src.core.shared.auth.oidc_handler import (
    OIDCAuthenticationError,
    OIDCConfigurationError,
    OIDCProviderError,
    OIDCTokenError,
)
from src.core.shared.auth.saml_config import SAMLSPConfig
from src.core.shared.config import settings
from starlette.requests import Request as StarletteRequest

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Global Handler instances
_oidc_handler: Optional[OIDCHandler] = None
_saml_handler: Optional[SAMLHandler] = None


# Response Models
class SSOLoginResponse(BaseModel):
    redirect_url: str
    state: str
    provider: str


class SSOUserInfoResponse(BaseModel):
    sub: str
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: List[str] = []


class SSOProviderInfo(BaseModel):
    name: str
    type: str = "oidc"
    enabled: bool = True


class SSOLogoutResponse(BaseModel):
    success: bool
    message: str
    redirect_url: Optional[str] = None


class SAMLUserInfoResponse(BaseModel):
    name_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: List[str] = []
    session_index: Optional[str] = None


# Handlers
def get_oidc_handler() -> OIDCHandler:
    global _oidc_handler
    if _oidc_handler is None:
        _oidc_handler = OIDCHandler()
        _register_default_providers(_oidc_handler)
    return _oidc_handler


def _register_default_providers(handler: OIDCHandler) -> None:
    if settings.sso.oidc_enabled and settings.sso.oidc_client_id:
        try:
            client_secret = (
                settings.sso.oidc_client_secret.get_secret_value()
                if settings.sso.oidc_client_secret
                else ""
            )
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
        except Exception as e:
            logger.warning(f"Failed to register default OIDC provider: {e}")


def get_saml_handler(req: StarletteRequest) -> SAMLHandler:
    global _saml_handler
    if _saml_handler is None:
        base_url = str(req.base_url).rstrip("/")
        sp_config = SAMLSPConfig(
            entity_id=settings.sso.saml_entity_id or f"{base_url}/sso/saml/metadata",
            acs_url=f"{base_url}/sso/saml/acs",
            sls_url=f"{base_url}/sso/saml/sls",
            metadata_url=f"{base_url}/sso/saml/metadata",
            sign_authn_requests=settings.sso.saml_sign_requests,
            want_assertions_signed=settings.sso.saml_want_assertions_signed,
            want_assertions_encrypted=settings.sso.saml_want_assertions_encrypted,
        )
        if settings.sso.saml_sp_certificate:
            sp_config.cert_content = settings.sso.saml_sp_certificate
        if settings.sso.saml_sp_private_key:
            sp_config.key_content = settings.sso.saml_sp_private_key.get_secret_value()

        _saml_handler = SAMLHandler(sp_config=sp_config)
        _register_default_saml_providers(_saml_handler)
    return _saml_handler


def _register_default_saml_providers(handler: SAMLHandler) -> None:
    if not settings.sso.saml_enabled:
        return
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
        except Exception as e:
            logger.warning(f"Failed to register default SAML IdP: {e}")


# Exception Handler
async def handle_sso_error(req: StarletteRequest, exc: Exception) -> JSONResponse:
    logger.error(f"SSO error: {exc}", extra={"error_type": type(exc).__name__})
    if isinstance(exc, OIDCConfigurationError):
        return JSONResponse(status_code=500, content={"detail": "SSO configuration error"})
    elif isinstance(exc, (OIDCAuthenticationError, OIDCTokenError)):
        return JSONResponse(status_code=401, content={"detail": "Authentication failed"})
    elif isinstance(exc, OIDCProviderError):
        return JSONResponse(status_code=502, content={"detail": "Identity provider error"})
    return JSONResponse(status_code=500, content={"detail": "Unexpected SSO error"})
