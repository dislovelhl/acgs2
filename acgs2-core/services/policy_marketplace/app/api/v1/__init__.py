"""
API v1 package for Policy Marketplace Service
"""

from fastapi import APIRouter

from .templates import router as templates_router
from .versions import router as versions_router

router = APIRouter()

# Include templates endpoints
router.include_router(templates_router, prefix="/templates", tags=["templates"])

# Include versions endpoints (nested under templates)
router.include_router(versions_router, prefix="/templates", tags=["versions"])

__all__ = ["router"]
