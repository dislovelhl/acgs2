"""Constitutional Hash: cdd01ef066bc6cf2
Central API router registration
"""

from fastapi import APIRouter

from .approvals import router as approvals_router
from .chains import router as chains_router

router = APIRouter()

router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
router.include_router(chains_router, prefix="/chains", tags=["chains"])
