"""
ACGS-2 Constitutional Retrieval System - Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configures pytest for this module by adding the directory to sys.path,
allowing tests to import from sibling modules despite the hyphenated directory name.
"""
import sys
import os

# Add current directory to path for local imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
