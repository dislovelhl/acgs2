"""
API endpoints for compliance documentation service
"""

from .evidence import router as evidence_router
from .reports import router as reports_router
from .templates import router as templates_router

__all__ = ["evidence_router", "templates_router", "reports_router"]
