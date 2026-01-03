"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

from . import exceptions

__version__ = "1.0.0"
__service__ = "integration-service"

# Export exceptions module for easy access
__all__ = [
    "exceptions",
]
