"""Constitutional Hash: cdd01ef066bc6cf2
API v1 package for Policy Marketplace Service
"""

from fastapi import APIRouter

from .analytics import router as analytics_router
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

# Include analytics endpoints for tracking downloads, ratings, usage
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

__all__ = ["router"]
