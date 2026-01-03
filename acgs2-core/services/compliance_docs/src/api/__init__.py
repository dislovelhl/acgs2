"""
API package for Compliance Documentation Service

FastAPI endpoints for evidence export and compliance report generation.
"""

from .evidence import router as evidence_router

__all__ = [
    "evidence_router",
]
