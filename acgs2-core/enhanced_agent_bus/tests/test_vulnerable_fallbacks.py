"""
Verification test for VULN-003 remediation.
Ensures that the Deliberation Layer fails closed instead of using mocks.
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import sys
from unittest.mock import patch

def test_deliberation_layer_fail_closed_on_missing_deps():
    """
    Test that importing the deliberation layer integration fails
    when critical dependencies are missing, instead of falling back to mocks.
    """
    # Force ImportError by patching __import__ or simply removing components from sys.modules
    # A more robust way is to patch the imports within the context of the module load.

    import builtins
    original_import = builtins.__import__

    def side_effect(name, *args, **kwargs):
        if name in ["interfaces", "impact_scorer", "adaptive_router", "deliberation_queue"]:
            raise ImportError(f"Simulated missing dependency: {name}")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=side_effect):

        # We need to reload the module to trigger the top-level import logic
        if "enhanced_agent_bus.deliberation_layer.integration" in sys.modules:
            del sys.modules["enhanced_agent_bus.deliberation_layer.integration"]

        with pytest.raises(RuntimeError) as excinfo:
            import enhanced_agent_bus.deliberation_layer.integration

        assert "CRITICAL SECURITY FAILURE" in str(excinfo.value)
        assert "dependencies are missing" in str(excinfo.value)
