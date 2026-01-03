"""
API package for Compliance Documentation Service

FastAPI endpoints for evidence export, template listing, and compliance report generation.
"""

from .evidence import router as evidence_router
from .templates import router as templates_router

__all__ = [
    "evidence_router",
    "templates_router",
]
