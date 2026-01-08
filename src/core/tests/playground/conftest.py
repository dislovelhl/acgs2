"""
Pytest configuration for playground tests.

This conftest.py sets up the Python path so that playground and cli modules
can be imported correctly regardless of where pytest is run from.
"""

import os
import sys

# Get the core directory (two levels up from this file)
_core_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Insert at the beginning of sys.path to take precedence
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)
