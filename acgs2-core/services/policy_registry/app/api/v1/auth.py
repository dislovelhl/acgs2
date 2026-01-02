"""
Authentication and Authorization API endpoints
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from ..dependencies import get_crypto_service


class TokenRequest(BaseModel):
    """Request model for token issuance with validation."""

    agent_id: str = Field(..., min_length=1, max_length=100, description="Unique agent identifier")
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant identifier")
    capabilities: List[str] = Field(
        ..., min_items=1, max_items=50, description="List of agent capabilities"
    )

    @field_validator("agent_id", "tenant_id")
    @classmethod
    def validate_id_format(cls, v):
        """Validate ID format - alphanumeric with hyphens and underscores only."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "ID must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v):
        """Validate capability names."""
        import re

        for cap in v:
            if not re.match(r"^[a-zA-Z0-9:_-]+$", cap):
                raise ValueError(f"Invalid capability format: {cap}")
        return v


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    crypto_service=Depends(get_crypto_service),
) -> Dict[str, Any]:
    """
    Validate JWT and return payload
    """
    token = credentials.credentials
    # In a real scenario, we would fetch the public key from a secure store
    # For this design, we'll assume a system-wide public key for management
    # or use the one from the policy registry's active keypair.
    try:
        # Load system public key from settings or services
        # For ACGS-2, we typically use the constitutional public key
        from shared.config import settings

        public_key_b64 = (
            settings.security.jwt_public_key
            if hasattr(settings.security, "jwt_public_key")
            else "SYSTEM_PUBLIC_KEY_PLACEHOLDER"
        )

        payload = crypto_service.verify_agent_token(token, public_key_b64)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {e}")


def check_role(allowed_roles: List[str], action: str = "manage", resource: str = "policy"):
    """
    RBAC role check dependency using OPA for granular authorization.
    """

    async def role_checker(
        user: Dict[str, Any] = Depends(get_current_user),
        # We'll use a local import to avoid circular dependency if any
    ):
        from ...services import OPAService

        opa_service = OPAService()

        user_role = user.get("role", "agent")

        # Fast path check
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Basic RBAC: Role {user_role} not authorized for this action",
            )

        # Granular OPA check
        is_authorized = await opa_service.check_authorization(user, action, resource)
        if not is_authorized:
            raise HTTPException(
                status_code=403, detail=f"OPA RBAC: Access denied for {action} on {resource}"
            )

        return user

    return role_checker


@router.post("/token", response_model=Dict[str, Any])
async def issue_token(
    request: TokenRequest,
    private_key_b64: Optional[str] = None,
    crypto_service=Depends(get_crypto_service),
    # Requires admin/management identity for this endpoint
    current_user: Dict[str, Any] = Depends(
        check_role(["admin", "registry-admin"], action="issue_token")
    ),
):
    """
    Issue a new SVID (JWT) for an agent.
    If private_key_b64 is not provided, uses the system management key.
    """
    try:
        from shared.config import settings

        signing_key = private_key_b64
        if not signing_key:
            if settings.security.jwt_private_key:
                signing_key = settings.security.jwt_private_key.get_secret_value()
            else:
                raise HTTPException(status_code=500, detail="System private key not configured")

        token = crypto_service.issue_agent_token(
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            capabilities=request.capabilities,
            private_key_b64=signing_key,
        )
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=400,
            detail="Authentication failed. Please check your credentials and try again.",
        )
