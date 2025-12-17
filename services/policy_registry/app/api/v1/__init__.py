"""
API v1 package
"""

from fastapi import APIRouter

from .policies import router as policies_router
from .health import router as health_router
from .websocket import router as websocket_router

router = APIRouter()
router.include_router(policies_router, prefix="/policies", tags=["policies"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(websocket_router, prefix="/ws", tags=["websocket"])

__all__ = ["router"]
