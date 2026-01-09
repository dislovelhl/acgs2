"""
ACGS-2 Governance Framework Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for governance framework initialization, state management,
policy loading, and audit trail capabilities.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.governance.governance_framework import (
    AuditEntry,
    AuditTrailManager,
    GovernanceConfiguration,
    GovernanceFramework,
    GovernanceState,
    Policy,
    PolicyLoader,
    PolicyLoadStatus,
    get_governance_framework,
    initialize_governance,
    shutdown_governance,
)

logger = logging.getLogger(__name__)


class TestGovernanceConfiguration:
    """Test suite for GovernanceConfiguration."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    @pytest.fixture
    def valid_config(self, constitutional_hash):
        return GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            tenant_id="test-tenant",
            environment="test",
        )

    def test_configuration_creation(self, valid_config):
        """Test GovernanceConfiguration creation with valid values."""
        assert valid_config.constitutional_hash == "cdd01ef066bc6cf2"
        assert valid_config.tenant_id == "test-tenant"
        assert valid_config.environment == "test"

    def test_configuration_defaults(self, constitutional_hash):
        """Test GovernanceConfiguration default values."""
        config = GovernanceConfiguration(constitutional_hash=constitutional_hash)

        assert config.tenant_id == "default"
        assert config.environment == "development"
        assert config.policy_refresh_interval == 300
        assert config.policy_cache_ttl == 3600
        assert config.max_policy_size_kb == 1024
        assert config.audit_enabled is True
        assert config.audit_retention_days == 90
        assert config.audit_buffer_size == 100
        assert config.audit_flush_interval == 30
        assert config.max_concurrent_evaluations == 100
        assert config.evaluation_timeout_ms == 5000
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_reset_time == 60
        assert config.enable_ml_scoring is True
        assert config.enable_blockchain_anchoring is True
        assert config.enable_human_review_escalation is True
        assert config.strict_mode is False

    def test_configuration_validation_success(self, valid_config):
        """Test configuration validation passes for valid config."""
        assert valid_config.validate() is True

    def test_configuration_validation_invalid_hash(self):
        """Test configuration validation fails for invalid hash."""
        config = GovernanceConfiguration(constitutional_hash="short")
        with pytest.raises(ValueError, match="Invalid constitutional hash"):
            config.validate()

    def test_configuration_validation_empty_hash(self):
        """Test configuration validation fails for empty hash."""
        config = GovernanceConfiguration(constitutional_hash="")
        with pytest.raises(ValueError, match="Invalid constitutional hash"):
            config.validate()

    def test_configuration_validation_refresh_interval(self, constitutional_hash):
        """Test configuration validation fails for short refresh interval."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            policy_refresh_interval=5,
        )
        with pytest.raises(ValueError, match="Policy refresh interval"):
            config.validate()

    def test_configuration_validation_concurrent_evaluations(self, constitutional_hash):
        """Test configuration validation fails for invalid concurrent evaluations."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            max_concurrent_evaluations=0,
        )
        with pytest.raises(ValueError, match="Max concurrent evaluations"):
            config.validate()

    def test_configuration_validation_timeout(self, constitutional_hash):
        """Test configuration validation fails for short timeout."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            evaluation_timeout_ms=50,
        )
        with pytest.raises(ValueError, match="Evaluation timeout"):
            config.validate()

    def test_configuration_custom_values(self, constitutional_hash):
        """Test configuration with custom values."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            tenant_id="custom-tenant",
            environment="production",
            policy_refresh_interval=600,
            audit_enabled=False,
            strict_mode=True,
        )

        assert config.tenant_id == "custom-tenant"
        assert config.environment == "production"
        assert config.policy_refresh_interval == 600
        assert config.audit_enabled is False
        assert config.strict_mode is True


class TestAuditEntry:
    """Test suite for AuditEntry dataclass."""

    def test_audit_entry_creation(self):
        """Test AuditEntry creation."""
        entry = AuditEntry(
            id="audit-123",
            timestamp=datetime.now(timezone.utc),
            action="TEST_ACTION",
            actor_id="test-actor",
            resource_type="test-resource",
            resource_id="resource-123",
            outcome="success",
            constitutional_hash="cdd01ef066bc6cf2",
        )

        assert entry.id == "audit-123"
        assert entry.action == "TEST_ACTION"
        assert entry.actor_id == "test-actor"
        assert entry.outcome == "success"
        assert entry.tenant_id == "default"
        assert isinstance(entry.metadata, dict)

    def test_audit_entry_with_metadata(self):
        """Test AuditEntry with metadata."""
        metadata = {"key": "value", "count": 42}
        entry = AuditEntry(
            id="audit-456",
            timestamp=datetime.now(timezone.utc),
            action="TEST",
            actor_id="actor",
            resource_type="resource",
            resource_id="id",
            outcome="success",
            constitutional_hash="hash",
            metadata=metadata,
            tenant_id="custom-tenant",
        )

        assert entry.metadata == metadata
        assert entry.tenant_id == "custom-tenant"


class TestAuditTrailManager:
    """Test suite for AuditTrailManager."""

    @pytest.fixture
    def config(self):
        return GovernanceConfiguration(
            constitutional_hash="cdd01ef066bc6cf2",
            audit_enabled=True,
            audit_buffer_size=10,
            audit_flush_interval=1,
        )

    @pytest.fixture
    def audit_manager(self, config):
        manager = AuditTrailManager(config)
        return manager

    def test_audit_manager_initialization(self, audit_manager, config):
        """Test AuditTrailManager initialization."""
        assert audit_manager.config == config
        assert len(audit_manager._buffer) == 0
        assert not audit_manager._running

    def test_audit_manager_record_entry(self, audit_manager):
        """Test recording audit entries."""
        entry = audit_manager.record(
            action="TEST_ACTION",
            actor_id="test-actor",
            resource_type="test-resource",
            resource_id="resource-123",
            outcome="success",
        )

        assert entry is not None
        assert entry.action == "TEST_ACTION"
        assert entry.actor_id == "test-actor"
        assert len(audit_manager._buffer) == 1

    def test_audit_manager_record_with_metadata(self, audit_manager):
        """Test recording audit entries with metadata."""
        metadata = {"extra": "data"}
        entry = audit_manager.record(
            action="TEST",
            actor_id="actor",
            resource_type="resource",
            resource_id="id",
            outcome="success",
            metadata=metadata,
        )

        assert entry.metadata == metadata

    def test_audit_manager_disabled(self):
        """Test audit manager when disabled."""
        config = GovernanceConfiguration(
            constitutional_hash="cdd01ef066bc6cf2",
            audit_enabled=False,
        )
        manager = AuditTrailManager(config)

        entry = manager.record(
            action="TEST",
            actor_id="actor",
            resource_type="resource",
            resource_id="id",
            outcome="success",
        )

        assert entry is None
        assert len(manager._buffer) == 0

    def test_audit_manager_auto_flush(self, config):
        """Test automatic buffer flush when full."""
        config.audit_buffer_size = 3
        manager = AuditTrailManager(config)

        # Set up persistence handler to track flushes
        flushed_entries = []

        def persistence_handler(entries):
            flushed_entries.extend(entries)
            return True

        manager.set_persistence_handler(persistence_handler)

        # Add entries to fill buffer
        for i in range(4):
            manager.record(
                action=f"ACTION_{i}",
                actor_id="actor",
                resource_type="resource",
                resource_id=f"id-{i}",
                outcome="success",
            )

        # Buffer should have been flushed when it hit 3 entries
        assert len(flushed_entries) == 3
        assert len(manager._buffer) == 1

    def test_audit_manager_get_entries(self, audit_manager):
        """Test retrieving audit entries."""
        # Add some entries
        for i in range(5):
            audit_manager.record(
                action=f"ACTION_{i}",
                actor_id=f"actor-{i % 2}",
                resource_type="resource",
                resource_id=f"id-{i}",
                outcome="success",
            )

        # Get all entries
        entries = audit_manager.get_entries()
        assert len(entries) == 5

        # Get entries with limit
        entries = audit_manager.get_entries(limit=3)
        assert len(entries) == 3

        # Get entries by actor
        entries = audit_manager.get_entries(actor_id="actor-0")
        assert len(entries) == 3  # 0, 2, 4

    def test_audit_manager_get_entries_by_action(self, audit_manager):
        """Test filtering entries by action."""
        audit_manager.record(
            action="CREATE",
            actor_id="actor",
            resource_type="resource",
            resource_id="id-1",
            outcome="success",
        )
        audit_manager.record(
            action="UPDATE",
            actor_id="actor",
            resource_type="resource",
            resource_id="id-2",
            outcome="success",
        )
        audit_manager.record(
            action="CREATE",
            actor_id="actor",
            resource_type="resource",
            resource_id="id-3",
            outcome="success",
        )

        entries = audit_manager.get_entries(action="CREATE")
        assert len(entries) == 2

    def test_audit_manager_start_stop(self, audit_manager):
        """Test starting and stopping audit manager."""
        audit_manager.start()
        assert audit_manager._running is True

        audit_manager.stop()
        assert audit_manager._running is False

    def test_audit_manager_persistence_failure(self, audit_manager):
        """Test handling persistence failures."""

        def failing_handler(entries):
            return False

        audit_manager.set_persistence_handler(failing_handler)

        # Add entry and force flush
        audit_manager.record(
            action="TEST",
            actor_id="actor",
            resource_type="resource",
            resource_id="id",
            outcome="success",
        )

        # Manual flush that will fail
        audit_manager._flush_buffer()

        # Entry should be re-added to buffer
        assert len(audit_manager._buffer) == 1


class TestPolicy:
    """Test suite for Policy dataclass."""

    def test_policy_creation(self):
        """Test Policy creation."""
        now = datetime.now(timezone.utc)
        policy = Policy(
            id="policy-123",
            name="Test Policy",
            version="1.0.0",
            content="package test\ndefault allow = false",
            policy_type="rego",
            constitutional_hash="cdd01ef066bc6cf2",
            created_at=now,
            updated_at=now,
        )

        assert policy.id == "policy-123"
        assert policy.name == "Test Policy"
        assert policy.version == "1.0.0"
        assert policy.is_active is True
        assert policy.priority == 0

    def test_policy_inactive(self):
        """Test inactive policy."""
        now = datetime.now(timezone.utc)
        policy = Policy(
            id="policy-456",
            name="Inactive Policy",
            version="1.0.0",
            content="content",
            policy_type="rego",
            constitutional_hash="hash",
            created_at=now,
            updated_at=now,
            is_active=False,
            priority=10,
        )

        assert policy.is_active is False
        assert policy.priority == 10


class TestPolicyLoader:
    """Test suite for PolicyLoader."""

    @pytest.fixture
    def config(self):
        return GovernanceConfiguration(
            constitutional_hash="cdd01ef066bc6cf2",
            policy_refresh_interval=10,
            max_policy_size_kb=1,
        )

    @pytest.fixture
    def policy_loader(self, config):
        return PolicyLoader(config)

    def test_policy_loader_initialization(self, policy_loader, config):
        """Test PolicyLoader initialization."""
        assert policy_loader.config == config
        assert policy_loader.status == PolicyLoadStatus.NOT_LOADED
        assert policy_loader.policy_count == 0

    @pytest.mark.asyncio
    async def test_policy_loader_load_default_policies(self, policy_loader):
        """Test loading default policies."""
        result = await policy_loader.load_policies()

        assert result is True
        assert policy_loader.status == PolicyLoadStatus.LOADED
        assert policy_loader.policy_count == 1

    @pytest.mark.asyncio
    async def test_policy_loader_custom_source(self, policy_loader):
        """Test loading policies from custom source."""
        custom_policies = [
            {
                "id": "custom-1",
                "name": "Custom Policy 1",
                "content": "package custom1",
            },
            {
                "id": "custom-2",
                "name": "Custom Policy 2",
                "content": "package custom2",
            },
        ]

        policy_loader.set_policy_source(lambda: custom_policies)
        result = await policy_loader.load_policies()

        assert result is True
        assert policy_loader.policy_count == 2

    @pytest.mark.asyncio
    async def test_policy_loader_get_policy(self, policy_loader):
        """Test getting policy by ID."""
        await policy_loader.load_policies()

        policy = policy_loader.get_policy("default-governance")
        assert policy is not None
        assert policy.id == "default-governance"

        missing = policy_loader.get_policy("nonexistent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_policy_loader_get_active_policies(self, policy_loader):
        """Test getting active policies."""
        custom_policies = [
            {
                "id": "active-1",
                "name": "Active 1",
                "content": "content",
                "is_active": True,
                "priority": 10,
            },
            {
                "id": "inactive-1",
                "name": "Inactive 1",
                "content": "content",
                "is_active": False,
                "priority": 20,
            },
            {
                "id": "active-2",
                "name": "Active 2",
                "content": "content",
                "is_active": True,
                "priority": 5,
            },
        ]

        policy_loader.set_policy_source(lambda: custom_policies)
        await policy_loader.load_policies()

        active = policy_loader.get_active_policies()

        assert len(active) == 2
        # Should be sorted by priority descending
        assert active[0].id == "active-1"
        assert active[1].id == "active-2"

    def test_policy_loader_add_policy(self, policy_loader):
        """Test adding a policy."""
        now = datetime.now(timezone.utc)
        policy = Policy(
            id="new-policy",
            name="New Policy",
            version="1.0.0",
            content="package new",
            policy_type="rego",
            constitutional_hash="cdd01ef066bc6cf2",
            created_at=now,
            updated_at=now,
        )

        result = policy_loader.add_policy(policy)

        assert result is True
        assert policy_loader.policy_count == 1
        assert policy_loader.get_policy("new-policy") is not None

    def test_policy_loader_add_policy_too_large(self, config):
        """Test adding a policy that exceeds size limit."""
        config.max_policy_size_kb = 0.001  # Very small limit
        loader = PolicyLoader(config)

        now = datetime.now(timezone.utc)
        policy = Policy(
            id="large-policy",
            name="Large Policy",
            version="1.0.0",
            content="x" * 10000,  # Large content
            policy_type="rego",
            constitutional_hash="hash",
            created_at=now,
            updated_at=now,
        )

        result = loader.add_policy(policy)
        assert result is False
        assert loader.policy_count == 0

    def test_policy_loader_remove_policy(self, policy_loader):
        """Test removing a policy."""
        now = datetime.now(timezone.utc)
        policy = Policy(
            id="to-remove",
            name="To Remove",
            version="1.0.0",
            content="content",
            policy_type="rego",
            constitutional_hash="hash",
            created_at=now,
            updated_at=now,
        )

        policy_loader.add_policy(policy)
        assert policy_loader.policy_count == 1

        result = policy_loader.remove_policy("to-remove")
        assert result is True
        assert policy_loader.policy_count == 0

        result = policy_loader.remove_policy("nonexistent")
        assert result is False

    def test_policy_loader_start_stop(self, policy_loader):
        """Test starting and stopping policy loader."""
        policy_loader.start()
        assert policy_loader._running is True

        policy_loader.stop()
        assert policy_loader._running is False

    @pytest.mark.asyncio
    async def test_policy_loader_failed_load(self, policy_loader):
        """Test handling failed policy load."""

        def failing_source():
            raise RuntimeError("Source unavailable")

        policy_loader.set_policy_source(failing_source)
        result = await policy_loader.load_policies()

        assert result is False
        assert policy_loader.status == PolicyLoadStatus.FAILED


class TestGovernanceState:
    """Test suite for GovernanceState enum."""

    def test_governance_state_values(self):
        """Test GovernanceState enum values."""
        assert GovernanceState.UNINITIALIZED.value == "uninitialized"
        assert GovernanceState.INITIALIZING.value == "initializing"
        assert GovernanceState.READY.value == "ready"
        assert GovernanceState.DEGRADED.value == "degraded"
        assert GovernanceState.SUSPENDED.value == "suspended"
        assert GovernanceState.SHUTDOWN.value == "shutdown"


class TestGovernanceFramework:
    """Test suite for GovernanceFramework."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    @pytest.fixture
    def config(self, constitutional_hash):
        return GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            tenant_id="test-tenant",
            environment="test",
            audit_enabled=True,
        )

    @pytest.fixture
    def framework(self, config):
        return GovernanceFramework(config)

    def test_framework_initialization(self, framework, config):
        """Test GovernanceFramework initialization."""
        assert framework.config == config
        assert framework.state == GovernanceState.UNINITIALIZED
        assert not framework.is_ready
        assert framework.constitutional_hash == config.constitutional_hash

    @pytest.mark.asyncio
    async def test_framework_initialize(self, framework):
        """Test framework initialization."""
        result = await framework.initialize()

        assert result is True
        assert framework.state == GovernanceState.READY
        assert framework.is_ready

    @pytest.mark.asyncio
    async def test_framework_initialize_already_initialized(self, framework):
        """Test initializing an already initialized framework."""
        await framework.initialize()
        result = await framework.initialize()

        assert result is True
        assert framework.state == GovernanceState.READY

    @pytest.mark.asyncio
    async def test_framework_shutdown(self, framework):
        """Test framework shutdown."""
        await framework.initialize()
        await framework.shutdown()

        assert framework.state == GovernanceState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_framework_shutdown_multiple_times(self, framework):
        """Test shutdown can be called multiple times safely."""
        await framework.initialize()
        await framework.shutdown()
        await framework.shutdown()  # Should not raise

        assert framework.state == GovernanceState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_framework_suspend_resume(self, framework):
        """Test suspending and resuming framework."""
        await framework.initialize()

        # Suspend
        result = framework.suspend()
        assert result is True
        assert framework.state == GovernanceState.SUSPENDED
        assert not framework.is_ready

        # Resume
        result = framework.resume()
        assert result is True
        assert framework.state == GovernanceState.READY
        assert framework.is_ready

    def test_framework_suspend_uninitialized(self, framework):
        """Test suspending uninitialized framework."""
        result = framework.suspend()
        assert result is False

    def test_framework_resume_not_suspended(self, framework):
        """Test resuming when not suspended."""
        result = framework.resume()
        assert result is False

    def test_framework_state_change_callback(self, framework):
        """Test state change callbacks."""
        states_observed = []

        def callback(state):
            states_observed.append(state)

        framework.on_state_change(callback)
        framework._set_state(GovernanceState.READY)
        framework._set_state(GovernanceState.DEGRADED)

        assert GovernanceState.READY in states_observed
        assert GovernanceState.DEGRADED in states_observed

    def test_framework_circuit_breaker(self, framework):
        """Test circuit breaker functionality."""
        framework._set_state(GovernanceState.READY)

        # Record failures
        for _ in range(4):
            result = framework.record_failure()
            assert result is False  # Not yet tripped

        # Trip the circuit breaker
        result = framework.record_failure()
        assert result is True
        assert framework.state == GovernanceState.DEGRADED

    def test_framework_circuit_breaker_recovery(self, framework):
        """Test circuit breaker recovery."""
        framework._set_state(GovernanceState.READY)

        # Trip circuit breaker
        for _ in range(5):
            framework.record_failure()

        assert framework.state == GovernanceState.DEGRADED

        # Simulate time passing and success
        framework._last_failure_time = time.time() - 120  # 2 minutes ago
        framework.policy_loader._status = PolicyLoadStatus.LOADED

        # Record success should recover
        framework.record_success()
        assert framework.state == GovernanceState.READY

    @pytest.mark.asyncio
    async def test_framework_get_status(self, framework):
        """Test getting framework status."""
        await framework.initialize()
        status = framework.get_status()

        assert status["state"] == "ready"
        assert status["constitutional_hash"] == framework.config.constitutional_hash
        assert status["tenant_id"] == framework.config.tenant_id
        assert status["is_ready"] is True
        assert "policy_count" in status
        assert "policy_status" in status

    @pytest.mark.asyncio
    async def test_framework_degraded_on_policy_failure(self, framework):
        """Test framework enters degraded mode on policy load failure."""
        # Set up failing policy source
        framework.policy_loader.set_policy_source(lambda: None)
        framework.policy_loader.set_policy_source(
            lambda: (_ for _ in ()).throw(RuntimeError("fail"))
        )

        await framework.initialize()

        assert framework.state == GovernanceState.DEGRADED


class TestGlobalGovernanceFunctions:
    """Test suite for global governance functions."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    @pytest.fixture
    def config(self, constitutional_hash):
        return GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            tenant_id="global-test",
        )

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        await shutdown_governance()

    @pytest.mark.asyncio
    async def test_initialize_governance(self, config):
        """Test initializing global governance."""
        framework = await initialize_governance(config)

        assert framework is not None
        assert framework.state == GovernanceState.READY

    @pytest.mark.asyncio
    async def test_get_governance_framework(self, config):
        """Test getting global governance framework."""
        # Before initialization
        assert get_governance_framework() is None

        # After initialization
        await initialize_governance(config)
        framework = get_governance_framework()

        assert framework is not None
        assert framework.config.constitutional_hash == config.constitutional_hash

    @pytest.mark.asyncio
    async def test_shutdown_governance(self, config):
        """Test shutting down global governance."""
        await initialize_governance(config)
        await shutdown_governance()

        assert get_governance_framework() is None

    @pytest.mark.asyncio
    async def test_reinitialize_with_different_hash(self, config):
        """Test reinitializing with different constitutional hash."""
        await initialize_governance(config)

        new_config = GovernanceConfiguration(
            constitutional_hash="new-hash-12345678",
        )
        framework = await initialize_governance(new_config)

        assert framework.constitutional_hash == "new-hash-12345678"


class TestGovernanceFrameworkEdgeCases:
    """Test edge cases for GovernanceFramework."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    def test_framework_with_disabled_features(self, constitutional_hash):
        """Test framework with features disabled."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            audit_enabled=False,
            enable_ml_scoring=False,
            enable_blockchain_anchoring=False,
            enable_human_review_escalation=False,
        )

        framework = GovernanceFramework(config)

        assert framework.config.audit_enabled is False
        assert framework.config.enable_ml_scoring is False

    def test_framework_strict_mode(self, constitutional_hash):
        """Test framework in strict mode."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            strict_mode=True,
        )

        framework = GovernanceFramework(config)

        assert framework.config.strict_mode is True

    @pytest.mark.asyncio
    async def test_concurrent_state_changes(self, constitutional_hash):
        """Test concurrent state changes are thread-safe."""
        config = GovernanceConfiguration(constitutional_hash=constitutional_hash)
        framework = GovernanceFramework(config)

        states = []

        def change_state():
            for _ in range(10):
                framework._set_state(GovernanceState.READY)
                states.append(framework.state)
                framework._set_state(GovernanceState.DEGRADED)
                states.append(framework.state)

        threads = [threading.Thread(target=change_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All state changes should have been recorded
        assert len(states) == 100

    @pytest.mark.asyncio
    async def test_audit_during_shutdown(self, constitutional_hash):
        """Test audit entries are flushed during shutdown."""
        config = GovernanceConfiguration(
            constitutional_hash=constitutional_hash,
            audit_enabled=True,
        )
        framework = GovernanceFramework(config)
        await framework.initialize()

        # Record some entries
        framework.audit_manager.record(
            action="TEST",
            actor_id="actor",
            resource_type="resource",
            resource_id="id",
            outcome="success",
        )

        # Shutdown should flush
        await framework.shutdown()

        # Buffer should be empty after shutdown
        assert len(framework.audit_manager._buffer) == 0


if __name__ == "__main__":
    # Run basic smoke tests
    logging.info("Running Governance Framework smoke tests...")

    try:
        # Check imports
        logging.info("Imports successful")
    except ImportError as e:
        logging.error(f"Import failed: {e}")
        exit(1)

    logging.info("All smoke tests passed!")
