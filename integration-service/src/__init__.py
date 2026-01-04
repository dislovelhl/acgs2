"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

import sys
from pathlib import Path

# Add acgs2-core to Python path for shared module imports
# This allows integration-service to import from acgs2-core/shared/ at runtime
_current_file = Path(__file__).resolve()
_repo_root = _current_file.parent.parent.parent
_acgs2_core_path = _repo_root / "acgs2-core"
if _acgs2_core_path.exists() and str(_acgs2_core_path) not in sys.path:
    sys.path.insert(0, str(_acgs2_core_path))

from . import exceptions

__version__ = "1.0.0"
__service__ = "integration-service"

# Export exceptions module for easy access
__all__ = [
    "exceptions",
]
