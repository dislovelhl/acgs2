"""
API v1 package for Policy Marketplace Service
"""

from fastapi import APIRouter

from .reviews import router as reviews_router
from .templates import router as templates_router
from .versions import router as versions_router

router = APIRouter()

# Include templates endpoints
router.include_router(templates_router, prefix="/templates", tags=["templates"])

# Include versions endpoints (nested under templates)
router.include_router(versions_router, prefix="/templates", tags=["versions"])

# Include reviews endpoints for review workflow
router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])

__all__ = ["router"]
