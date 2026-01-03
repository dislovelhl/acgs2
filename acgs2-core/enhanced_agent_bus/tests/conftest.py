"""
ACGS-2 Enhanced Agent Bus - Shared Test Fixtures
Constitutional Hash: cdd01ef066bc6cf2

Provides common fixtures for all test modules.
"""

import logging

logger = logging.getLogger(__name__)
import os
import sys

# CRITICAL: Block Rust imports BEFORE any module imports
_test_with_rust = os.environ.get("TEST_WITH_RUST", "0") == "1"
if not _test_with_rust:
    sys.modules["enhanced_agent_bus_rust"] = None

import asyncio

import pytest

# Add enhanced_agent_bus directory to path if not already there
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)

# Ensure consistent class identity by patching sys.modules
try:
    import enhanced_agent_bus.audit_client as _audit_client
    import enhanced_agent_bus.core as _core
    import enhanced_agent_bus.exceptions as _exceptions
    import enhanced_agent_bus.imports as _imports
    import enhanced_agent_bus.interfaces as _interfaces
    import enhanced_agent_bus.maci_enforcement as _maci_enforcement
    import enhanced_agent_bus.models as _models
    import enhanced_agent_bus.registry as _registry
    import enhanced_agent_bus.utils as _utils
    import enhanced_agent_bus.validators as _validators

    # Import online_learning module for ML tests
    try:
        import enhanced_agent_bus.online_learning as _online_learning

        sys.modules["online_learning"] = _online_learning
        sys.modules["enhanced_agent_bus.online_learning"] = _online_learning
    except ImportError:
        _online_learning = None  # River/numpy may not be installed

    # Import ab_testing module for A/B testing tests
    try:
        import enhanced_agent_bus.ab_testing as _ab_testing

        sys.modules["ab_testing"] = _ab_testing
        sys.modules["enhanced_agent_bus.ab_testing"] = _ab_testing
    except ImportError:
        _ab_testing = None  # NumPy may not be installed

    # Patch sys.models to point flat names to package-qualified modules
    sys.modules["audit_client"] = _audit_client
    sys.modules["models"] = _models
    sys.modules["validators"] = _validators
    sys.modules["exceptions"] = _exceptions
    sys.modules["interfaces"] = _interfaces
    sys.modules["registry"] = _registry
    sys.modules["core"] = _core
    sys.modules["maci_enforcement"] = _maci_enforcement
    sys.modules["utils"] = _utils
    sys.modules["imports"] = _imports
    sys.modules["agent_bus"] = sys.modules.get("enhanced_agent_bus.agent_bus") or _core
except ImportError:
    # Fallback if the package structure is not respected during execution
    try:
        import audit_client as _audit_client
        import core as _core
        import exceptions as _exceptions
        import imports as _imports
        import interfaces as _interfaces
        import maci_enforcement as _maci_enforcement
        import models as _models
        import registry as _registry
        import utils as _utils
        import validators as _validators

        # Import online_learning module for ML tests (fallback)
        try:
            import online_learning as _online_learning

            sys.modules["online_learning"] = _online_learning
            sys.modules["enhanced_agent_bus.online_learning"] = _online_learning
        except ImportError:
            _online_learning = None  # River/numpy may not be installed

        # Import ab_testing module for A/B testing tests (fallback)
        try:
            import ab_testing as _ab_testing

            sys.modules["ab_testing"] = _ab_testing
            sys.modules["enhanced_agent_bus.ab_testing"] = _ab_testing
        except ImportError:
            _ab_testing = None  # NumPy may not be installed

        # Patch package names to point to flat modules
        sys.modules["audit_client"] = _audit_client
        sys.modules["enhanced_agent_bus.audit_client"] = _audit_client
        sys.modules["enhanced_agent_bus.models"] = _models
        sys.modules["enhanced_agent_bus.validators"] = _validators
        sys.modules["enhanced_agent_bus.exceptions"] = _exceptions
        sys.modules["enhanced_agent_bus.interfaces"] = _interfaces
        sys.modules["enhanced_agent_bus.registry"] = _registry
        sys.modules["enhanced_agent_bus.core"] = _core
        sys.modules["enhanced_agent_bus.maci_enforcement"] = _maci_enforcement
        sys.modules["enhanced_agent_bus.utils"] = _utils
        sys.modules["enhanced_agent_bus.imports"] = _imports
        sys.modules["agent_bus"] = sys.modules.get("enhanced_agent_bus.agent_bus") or _core
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to load test dependencies: {e}")
        # Final desperate attempt to find utils if it's being shadowed
        import importlib.util

        u_path = os.path.join(enhanced_agent_bus_dir, "utils.py")
        if os.path.exists(u_path):
            spec = importlib.util.spec_from_file_location("utils", u_path)
            _utils = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_utils)
            sys.modules["utils"] = _utils

# Rust availability check
if not _test_with_rust:
    _core.USE_RUST = False
    RUST_AVAILABLE = False
else:
    try:
        import enhanced_agent_bus_rust as _rust_bus

        RUST_AVAILABLE = True
        _core.USE_RUST = True
    except ImportError:
        RUST_AVAILABLE = False
        _core.USE_RUST = False

# Re-export commonly used items
AgentMessage = _models.AgentMessage
MessageType = _models.MessageType
Priority = _models.Priority
MessageStatus = _models.MessageStatus
CONSTITUTIONAL_HASH = _models.CONSTITUTIONAL_HASH
ValidationResult = _validators.ValidationResult
MessageProcessor = _core.MessageProcessor
EnhancedAgentBus = _core.EnhancedAgentBus


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ... (rest of the fixtures)
