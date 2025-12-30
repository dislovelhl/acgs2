"""
API v1 package
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .bundles import router as bundles_router
from .health import router as health_router
from .policies import router as policies_router
from .webhooks import router as webhooks_router
from .websocket import router as websocket_router

router = APIRouter()
router.include_router(policies_router, prefix="/policies", tags=["policies"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(bundles_router, prefix="/bundles", tags=["bundles"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

__all__ = ["router"]
