"""
ACGS-2 Service-to-Service Authentication
Constitutional Hash: cdd01ef066bc6cf2

Provides JWT-based identity and authentication for inter-service communication.
"""

import logging
import os
import time
from typing import Optional

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Service secret for signing internal tokens
SERVICE_SECRET = os.environ.get("ACGS2_SERVICE_SECRET", "dev-service-secret")
SERVICE_ALGORITHM = "HS256"


class ServiceAuth:
    """Manager for service identity and verification."""

    @staticmethod
    def create_service_token(service_name: str, expires_in: int = 3600) -> str:
        """Create a JWT token for a service."""
        payload = {
            "sub": service_name,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "iss": "acgs2-internal",
            "type": "service",
        }
        return jwt.encode(payload, SERVICE_SECRET, algorithm=SERVICE_ALGORITHM)

    @staticmethod
    def verify_service_token(token: str) -> Optional[str]:
        """Verify a service JWT token and return service name."""
        try:
            payload = jwt.decode(
                token, SERVICE_SECRET, algorithms=[SERVICE_ALGORITHM], issuer="acgs2-internal"
            )
            if payload.get("type") != "service":
                return None
            return payload.get("sub")
        except jwt.PyJWTError as e:
            logger.warning(f"Service token verification failed: {e}")
            return None


security = HTTPBearer()


async def require_service_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """FastAPI dependency to require service authentication."""
    service_name = ServiceAuth.verify_service_token(credentials.credentials)
    if not service_name:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return service_name


__all__ = ["ServiceAuth", "require_service_auth"]
