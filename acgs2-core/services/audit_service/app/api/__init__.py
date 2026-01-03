"""
Audit Service API Module
Constitutional Hash: cdd01ef066bc6cf2
"""

from .governance import router as governance_router
from .reports import router as reports_router

__all__ = ["governance_router", "reports_router"]
