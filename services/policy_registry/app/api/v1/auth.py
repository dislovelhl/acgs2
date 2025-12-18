"""
Authentication and Authorization API endpoints
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...services import CryptoService

router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    crypto_service: CryptoService = Depends()
) -> Dict[str, Any]:
    """
    Validate JWT and return payload
    """
    token = credentials.credentials
    # In a real scenario, we would fetch the public key from a secure store
    # For this design, we'll assume a system-wide public key for management
    # or use the one from the policy registry's active keypair.
    try:
        # This is a placeholder for actual public key retrieval
        # In production, this would be the IDP's public key
        public_key_b64 = "SYSTEM_PUBLIC_KEY_PLACEHOLDER" 
        payload = crypto_service.verify_agent_token(token, public_key_b64)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication: {e}"
        )


def check_role(allowed_roles: List[str]):
    """
    RBAC role check dependency
    """
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_role = user.get("role", "agent")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Role {user_role} not authorized for this action"
            )
        return user
    return role_checker


@router.post("/token", response_model=Dict[str, Any])
async def issue_token(
    agent_id: str,
    tenant_id: str,
    capabilities: List[str],
    private_key_b64: str,
    crypto_service: CryptoService = Depends()
):
    """
    Issue a new SVID (JWT) for an agent
    """
    try:
        token = crypto_service.issue_agent_token(
            agent_id=agent_id,
            tenant_id=tenant_id,
            capabilities=capabilities,
            private_key_b64=private_key_b64
        )
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
