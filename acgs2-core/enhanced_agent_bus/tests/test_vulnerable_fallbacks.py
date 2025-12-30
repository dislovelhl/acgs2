"""
Verification test for VULN-003 remediation.
Ensures that the Deliberation Layer fails closed instead of using mocks.
Constitutional Hash: cdd01ef066bc6cf2
"""

import subprocess
import sys

import pytest


def test_deliberation_layer_fail_closed_on_missing_deps():
    """
    Test that importing the deliberation layer integration fails
    when critical dependencies are missing, instead of falling back to mocks.

    This test runs in a subprocess to ensure clean module state, avoiding
    interference from other tests that may have already imported the module.
    """
    # Run test in subprocess to get clean import state
    test_code = """
import sys
import builtins

# Block the dependency modules by hooking __import__
# Must block all possible import paths (relative and absolute)
blocked_modules = {
    "interfaces",
    "impact_scorer",
    "adaptive_router",
    "deliberation_queue",
}

original_import = builtins.__import__

def blocking_import(name, globals=None, locals=None, fromlist=(), level=0):
    # Block direct imports of critical modules
    base_name = name.split(".")[-1]
    if base_name in blocked_modules:
        raise ImportError(f"Blocked for security test: {name}")
    # Also block fromlist items
    if fromlist:
        for item in fromlist:
            if item in blocked_modules:
                raise ImportError(f"Blocked fromlist item: {item}")
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = blocking_import

try:
    import enhanced_agent_bus.deliberation_layer.integration
    print("ERROR: Import succeeded when it should have failed")
    sys.exit(1)
except RuntimeError as e:
    if "CRITICAL" in str(e) or "missing" in str(e).lower():
        print(f"OK: Got expected RuntimeError: {e}")
        sys.exit(0)
    print(f"ERROR: Unexpected RuntimeError: {e}")
    sys.exit(2)
except ImportError as e:
    # ImportError is also acceptable - shows fail-closed behavior
    print(f"OK: Got ImportError (fail-closed): {e}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: Unexpected exception type {type(e).__name__}: {e}")
    sys.exit(3)
"""

    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True,
        cwd="/home/dislove/document/acgs2/acgs2-core",
        env={
            **dict(__import__("os").environ),
            "PYTHONPATH": "/home/dislove/document/acgs2/acgs2-core",
        },
    )

    if result.returncode != 0:
        pytest.fail(
            f"Fail-closed test failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
            f"returncode: {result.returncode}"
        )


def test_deliberation_layer_imports_successfully_when_deps_available():
    """
    Verify that the deliberation layer imports successfully when all
    dependencies are available (normal operation).
    """
    try:
        from enhanced_agent_bus.deliberation_layer import integration

        # Verify module loaded with expected attributes
        assert hasattr(integration, "DeliberationEngine") or hasattr(
            integration, "CONSTITUTIONAL_HASH"
        )
    except ImportError as e:
        # If dependencies genuinely missing in test env, skip
        pytest.skip(f"Dependencies not available in test environment: {e}")
