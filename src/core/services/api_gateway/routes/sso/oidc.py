"""
OIDC Authentication Routes
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from src.core.shared.auth.oidc_handler import OIDCConfigurationError, OIDCUserInfo
from src.core.shared.auth.provisioning import ProvisioningResult, get_provisioner
from src.core.shared.config import settings
from src.core.shared.types import JSONDict
from starlette.requests import Request as StarletteRequest

from .common import (
    SSOLogoutResponse,
    SSOProviderInfo,
    SSOUserInfoResponse,
    get_oidc_handler,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/providers", response_model=list[SSOProviderInfo])
async def list_oidc_providers(
    handler=Depends(get_oidc_handler),
) -> list[SSOProviderInfo]:
    providers = handler.list_providers()
    return [SSOProviderInfo(name=name, type="oidc", enabled=True) for name in providers]


@router.get("/login")
async def oidc_login(
    req: StarletteRequest,
    provider: str = Query(...),
    redirect_uri: Optional[str] = Query(None),
    handler=Depends(get_oidc_handler),
) -> RedirectResponse:
    if not settings.sso.enabled and not settings.sso.oidc_enabled:
        raise HTTPException(status_code=503, detail="SSO disabled")

    callback_url = redirect_uri or str(req.url_for("oidc_callback"))
    try:
        auth_url, state = await handler.initiate_login(
            provider_name=provider, redirect_uri=callback_url
        )
        req.session["oidc_state"] = state
        req.session["oidc_provider"] = provider
        req.session["oidc_callback_url"] = callback_url
        return RedirectResponse(url=auth_url, status_code=302)
    except OIDCConfigurationError as e:
        logger.warning(f"OIDC login failed: {e}")
        raise HTTPException(status_code=404, detail=f"OIDC provider not found: {str(e)}") from e
    except Exception as e:
        logger.error(f"OIDC login failed: {e}")
        raise HTTPException(status_code=500, detail="Login initiation failed") from e


@router.get("/callback", response_model=SSOUserInfoResponse)
async def oidc_callback(
    req: StarletteRequest,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    handler=Depends(get_oidc_handler),
) -> JSONDict:
    if error:
        raise HTTPException(status_code=401, detail=error_description or error)

    stored_state = req.session.get("oidc_state")
    stored_provider = req.session.get("oidc_provider")
    stored_callback_url = req.session.get("oidc_callback_url")

    if not stored_state or stored_state != state:
        raise HTTPException(status_code=401, detail="Invalid state")

    try:
        user_info: OIDCUserInfo = await handler.handle_callback(
            stored_provider, code, state, stored_callback_url
        )

        # JIT Provisioning
        provisioner = get_provisioner(
            auto_provision_enabled=settings.sso.auto_provision_users,
            default_roles=(
                [settings.sso.default_role_on_provision]
                if settings.sso.default_role_on_provision
                else None
            ),
            allowed_domains=settings.sso.allowed_domains,
        )

        provisioning_result: ProvisioningResult = await provisioner.get_or_create_user(
            email=user_info.email,
            name=user_info.name,
            sso_provider="oidc",
            idp_user_id=user_info.sub,
            provider_id=stored_provider,
            roles=user_info.groups,
        )

        req.session["user"] = {
            "id": provisioning_result.user.get("id"),
            "sub": user_info.sub,
            "email": provisioning_result.user.get("email"),
            "name": provisioning_result.user.get("name"),
            "roles": provisioning_result.user.get("roles", []),
            "provider": stored_provider,
            "auth_type": "oidc",
        }

        return user_info.__dict__  # Simplified for now
    except Exception as e:
        logger.error(f"OIDC callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication processing failed") from e


@router.post("/logout", response_model=SSOLogoutResponse)
async def oidc_logout(
    req: StarletteRequest,
    handler=Depends(get_oidc_handler),
) -> SSOLogoutResponse:
    user = req.session.get("user")
    provider_name = user.get("provider") if user else None
    redirect_url = None

    if provider_name:
        try:
            redirect_url = await handler.logout(provider_name, str(req.base_url))
        except Exception as e:
            logger.warning(f"IdP logout failed: {e}")

    req.session.clear()
    return SSOLogoutResponse(success=True, message="Logged out", redirect_url=redirect_url)
