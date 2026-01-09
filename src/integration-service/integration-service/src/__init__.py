"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

import sys
from pathlib import Path

# Add src/core to Python path for shared module imports
# This allows integration-service to import from src/core/shared/ at runtime
_current_file = Path(__file__).resolve()
_repo_root = _current_file.parent.parent.parent
_core_path = _repo_root / "src/core"
if _core_path.exists() and str(_core_path) not in sys.path:
    sys.path.insert(0, str(_core_path))

from . import exceptions  # noqa: E402

__version__ = "1.0.0"
__service__ = "integration-service"

# Export exceptions module for easy access
__all__ = [
    "exceptions",
]
