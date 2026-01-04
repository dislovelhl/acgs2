"""
ACGS-2 Enhanced Agent Bus - Root Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

This conftest.py ensures proper PYTHONPATH configuration for coverage collection.
"""

import os
import sys

# Add the enhanced_agent_bus directory to sys.path for proper module discovery
# This must happen BEFORE any coverage collection starts
_root_dir = os.path.dirname(os.path.abspath(__file__))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

# Also add parent directory for enhanced_agent_bus package imports
_parent_dir = os.path.dirname(_root_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Set PYTHONPATH environment variable for subprocesses
os.environ["PYTHONPATH"] = f"{_root_dir}:{_parent_dir}:{os.environ.get('PYTHONPATH', '')}"
