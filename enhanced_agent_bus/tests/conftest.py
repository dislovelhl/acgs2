"""
ACGS-2 Enhanced Agent Bus - Shared Test Fixtures
Constitutional Hash: cdd01ef066bc6cf2

Provides common fixtures for all test modules.
"""

import asyncio
import os
import sys
import importlib.util
from datetime import datetime, timezone
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add enhanced_agent_bus directory to path
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)


def _load_module(name: str, path: str) -> Any:
    """Load a module directly from path to avoid package conflicts."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load core modules
_models = _load_module("_conftest_models", os.path.join(enhanced_agent_bus_dir, "models.py"))
_validators = _load_module("_conftest_validators", os.path.join(enhanced_agent_bus_dir, "validators.py"))

# Patch sys.modules for dependent imports
# Patch both absolute and package-relative import paths to ensure class identity
sys.modules['models'] = _models
sys.modules['validators'] = _validators
sys.modules['enhanced_agent_bus.models'] = _models
sys.modules['enhanced_agent_bus.validators'] = _validators

# Load additional modules that tests might import
_exceptions = _load_module("_conftest_exceptions", os.path.join(enhanced_agent_bus_dir, "exceptions.py"))
_interfaces = _load_module("_conftest_interfaces", os.path.join(enhanced_agent_bus_dir, "interfaces.py"))
_registry = _load_module("_conftest_registry", os.path.join(enhanced_agent_bus_dir, "registry.py"))

# Patch all module names for consistent class identity
sys.modules['exceptions'] = _exceptions
sys.modules['interfaces'] = _interfaces
sys.modules['registry'] = _registry
sys.modules['enhanced_agent_bus.exceptions'] = _exceptions
sys.modules['enhanced_agent_bus.interfaces'] = _interfaces
sys.modules['enhanced_agent_bus.registry'] = _registry

# Check if Rust implementation is available
# Set TEST_WITH_RUST=1 environment variable to enable Rust testing
_test_with_rust = os.environ.get("TEST_WITH_RUST", "0") == "1"

try:
    if _test_with_rust:
        import enhanced_agent_bus as _rust_bus
        RUST_AVAILABLE = True
    else:
        # Block Rust import for Python-only testing
        sys.modules['enhanced_agent_bus'] = None
        RUST_AVAILABLE = False
except ImportError:
    sys.modules['enhanced_agent_bus'] = None
    RUST_AVAILABLE = False

_core = _load_module("_conftest_core", os.path.join(enhanced_agent_bus_dir, "core.py"))

# Patch core module name for test imports
sys.modules['core'] = _core
sys.modules['enhanced_agent_bus.core'] = _core

# Set Rust mode based on availability and configuration
if not _test_with_rust:
    _core.USE_RUST = False

# Re-export commonly used items
AgentMessage = _models.AgentMessage
MessageType = _models.MessageType
Priority = _models.Priority
MessagePriority = _models.MessagePriority  # DEPRECATED: Use Priority instead
MessageStatus = _models.MessageStatus
CONSTITUTIONAL_HASH = _models.CONSTITUTIONAL_HASH

ValidationResult = _validators.ValidationResult
validate_constitutional_hash = _validators.validate_constitutional_hash
validate_message_content = _validators.validate_message_content

MessageProcessor = _core.MessageProcessor
EnhancedAgentBus = _core.EnhancedAgentBus


# === Pytest Configuration ===

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# === Model Fixtures ===

@pytest.fixture
def constitutional_hash() -> str:
    """Return the valid constitutional hash."""
    return CONSTITUTIONAL_HASH


@pytest.fixture
def invalid_hash() -> str:
    """Return an invalid constitutional hash."""
    return "invalid_hash_123"


@pytest.fixture
def valid_message() -> AgentMessage:
    """Create a valid test message with constitutional compliance."""
    return AgentMessage(
        from_agent="test_sender_agent",
        to_agent="test_receiver_agent",
        sender_id="test_sender_id",
        message_type=MessageType.COMMAND,
        content={"action": "test_action", "data": "test_data"},
        payload={"key": "value"},
        priority=Priority.NORMAL,
    )


@pytest.fixture
def invalid_hash_message() -> AgentMessage:
    """Create a message with invalid constitutional hash."""
    message = AgentMessage(
        from_agent="test_sender",
        to_agent="test_receiver",
        sender_id="sender_id",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )
    message.constitutional_hash = "invalid_hash"
    return message


@pytest.fixture
def governance_request_message() -> AgentMessage:
    """Create a governance request message."""
    return AgentMessage(
        from_agent="governance_agent",
        to_agent="policy_agent",
        sender_id="governance_sender",
        message_type=MessageType.GOVERNANCE_REQUEST,
        content={"policy_id": "test_policy", "action": "evaluate"},
        priority=Priority.HIGH,
    )


@pytest.fixture
def high_priority_message() -> AgentMessage:
    """Create a high-priority message."""
    return AgentMessage(
        from_agent="urgent_sender",
        to_agent="urgent_receiver",
        sender_id="urgent_sender_id",
        message_type=MessageType.COMMAND,
        content={"action": "urgent_action"},
        priority=Priority.CRITICAL,
    )


@pytest.fixture
def broadcast_message() -> AgentMessage:
    """Create a broadcast message (no specific recipient)."""
    return AgentMessage(
        from_agent="broadcaster",
        to_agent="",  # Empty for broadcast
        sender_id="broadcast_sender",
        message_type=MessageType.EVENT,
        content={"event": "system_update"},
    )


# === Processor Fixtures ===

@pytest.fixture
def message_processor() -> MessageProcessor:
    """Create a fresh MessageProcessor instance."""
    return MessageProcessor()


@pytest.fixture
def processor_with_handler(message_processor) -> MessageProcessor:
    """Create a MessageProcessor with a registered handler."""
    handler_calls = []

    async def test_handler(msg):
        handler_calls.append(msg)

    message_processor.register_handler(MessageType.COMMAND, test_handler)
    message_processor._handler_calls = handler_calls
    return message_processor


# === Agent Bus Fixtures ===

@pytest.fixture
def agent_bus() -> EnhancedAgentBus:
    """Create a fresh EnhancedAgentBus instance."""
    return EnhancedAgentBus()


@pytest.fixture
async def started_agent_bus(agent_bus) -> EnhancedAgentBus:
    """Create and start an EnhancedAgentBus."""
    await agent_bus.start()
    yield agent_bus
    await agent_bus.stop()


@pytest.fixture
async def agent_bus_with_agents(started_agent_bus) -> EnhancedAgentBus:
    """Create an agent bus with pre-registered agents."""
    await started_agent_bus.register_agent(
        agent_id="agent_alpha",
        agent_type="worker",
        capabilities=["task_processing", "data_analysis"],
    )
    await started_agent_bus.register_agent(
        agent_id="agent_beta",
        agent_type="coordinator",
        capabilities=["orchestration", "scheduling"],
    )
    return started_agent_bus


# === Mock Fixtures ===

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.lpush = AsyncMock(return_value=1)
    mock.rpop = AsyncMock(return_value=None)
    mock.llen = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.pipeline = MagicMock(return_value=mock)
    mock.execute = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for policy fetching."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.put = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def mock_deliberation_approver():
    """Create a mock approver for deliberation tests."""
    async def auto_approve(item):
        return {"approved": True, "reason": "Auto-approved for testing"}
    return auto_approve


@pytest.fixture
def mock_deliberation_rejector():
    """Create a mock rejector for deliberation tests."""
    async def auto_reject(item):
        return {"approved": False, "reason": "Auto-rejected for testing"}
    return auto_reject


# === Validation Fixtures ===

@pytest.fixture
def valid_validation_result() -> ValidationResult:
    """Create a valid ValidationResult."""
    return ValidationResult(is_valid=True)


@pytest.fixture
def invalid_validation_result() -> ValidationResult:
    """Create an invalid ValidationResult with errors."""
    result = ValidationResult(is_valid=False)
    result.add_error("Test validation error")
    return result


@pytest.fixture
def validation_result_with_warnings() -> ValidationResult:
    """Create a ValidationResult with warnings but valid."""
    result = ValidationResult(is_valid=True)
    result.add_warning("Test warning 1")
    result.add_warning("Test warning 2")
    return result


# === Time-related Fixtures ===

@pytest.fixture
def fixed_timestamp() -> datetime:
    """Return a fixed timestamp for deterministic tests."""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_datetime(fixed_timestamp):
    """Mock datetime.now() to return fixed timestamp."""
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_timestamp
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield mock_dt


# === Performance Testing Fixtures ===

@pytest.fixture
def performance_messages(valid_message) -> list:
    """Create a batch of messages for performance testing."""
    messages = []
    for i in range(100):
        msg = AgentMessage(
            from_agent=f"sender_{i}",
            to_agent=f"receiver_{i}",
            sender_id=f"sender_id_{i}",
            message_type=MessageType.COMMAND,
            content={"action": f"action_{i}", "index": i},
        )
        messages.append(msg)
    return messages


# === Cleanup Fixtures ===

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state that might persist between tests
    yield
    # Cleanup after test
    # Reset core module singletons if they have reset functions
    if hasattr(_core, 'reset_agent_bus'):
        _core.reset_agent_bus()


# === Rust Testing Support ===

@pytest.fixture
def rust_available() -> bool:
    """Check if Rust implementation is available for testing."""
    return RUST_AVAILABLE


@pytest.fixture
def rust_enabled_processor():
    """
    Create a MessageProcessor with Rust enabled (if available).

    Skip test if Rust is not available.
    """
    if not RUST_AVAILABLE:
        pytest.skip("Rust implementation not available")
    return MessageProcessor()


@pytest.fixture
def rust_enabled_bus():
    """
    Create an EnhancedAgentBus with Rust enabled (if available).

    Skip test if Rust is not available.
    """
    if not RUST_AVAILABLE:
        pytest.skip("Rust implementation not available")
    return EnhancedAgentBus()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_rust: mark test as requiring Rust implementation"
    )


@pytest.fixture(autouse=True)
def skip_rust_tests(request):
    """Skip tests marked with requires_rust if Rust is not available."""
    if request.node.get_closest_marker("requires_rust"):
        if not RUST_AVAILABLE:
            pytest.skip("Rust implementation not available")
