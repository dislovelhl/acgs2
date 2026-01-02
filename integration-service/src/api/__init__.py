"""
ACGS-2 Integration Service API
API routers for health, service discovery, and integration endpoints
"""

from .health import router as health_router
from .webhooks import router as webhooks_router

__all__ = ["health_router", "webhooks_router"]
