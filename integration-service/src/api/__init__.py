"""
ACGS-2 Integration Service API
API routers for health, service discovery, and integration endpoints
"""

from .health import router as health_router
from .policy_check import router as policy_check_router
from .webhooks import router as webhooks_router

__all__ = ["health_router", "policy_check_router", "webhooks_router"]
