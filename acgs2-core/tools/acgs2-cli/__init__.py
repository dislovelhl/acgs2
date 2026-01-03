"""
ACGS-2 Unified CLI Tool
Constitutional Hash: cdd01ef066bc6cf2

A comprehensive command-line interface for ACGS-2 AI Constitutional Governance Platform.
"""

from acgs2_cli.config import CLIConfig, get_config
from acgs2_cli.main import cli

__version__ = "2.0.0"
__constitutional_hash__ = "cdd01ef066bc6cf2"

__all__ = [
    "cli",
    "CLIConfig",
    "get_config",
    "__version__",
    "__constitutional_hash__",
]
