"""
HITL Approvals API Module

FastAPI routers for HITL approval workflow endpoints.
"""

from app.api.approvals import router as approvals_router

__all__ = ["approvals_router"]
