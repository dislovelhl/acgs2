"""
ACGS-2 Tenant-Scoped Audit Logger Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- AuditAction and AuditSeverity enums
- AuditEntry dataclass creation and serialization
- AuditQueryParams filtering and pagination
- AuditLogConfig from defaults and environment
- InMemoryAuditStore operations
- TenantAuditLogger tenant scoping
- Cross-tenant access prevention
- Sensitive field redaction
- Query functionality with filters
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.logging.audit_logger import (  # noqa: E402, I001
    AUDIT_LOGGER_AVAILABLE,
    CONSTITUTIONAL_HASH,
    SENSITIVE_FIELDS,
    AuditAction,
    AuditEntry,
    AuditLogConfig,
    AuditQueryParams,
    AuditQueryResult,
    AuditSeverity,
    InMemoryAuditStore,
    TenantAuditLogger,
    create_tenant_audit_logger,
    get_tenant_audit_logger,
)


# ============================================================================
# AuditAction Enum Tests
# ============================================================================


class TestAuditAction:
    """Test AuditAction enum."""

    def test_crud_operations_defined(self):
        """Test CRUD operation values are defined."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.READ.value == "read"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.LIST.value == "list"

    def test_auth_operations_defined(self):
        """Test authentication operation values are defined."""
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.AUTH_FAILURE.value == "auth_failure"
        assert AuditAction.ACCESS_DENIED.value == "access_denied"

    def test_policy_operations_defined(self):
        """Test policy operation values are defined."""
        assert AuditAction.POLICY_EVALUATE.value == "policy_evaluate"
        assert AuditAction.POLICY_APPROVE.value == "policy_approve"
        assert AuditAction.POLICY_REJECT.value == "policy_reject"

    def test_tenant_operations_defined(self):
        """Test tenant operation values are defined."""
        assert AuditAction.TENANT_CREATE.value == "tenant_create"
        assert AuditAction.TENANT_UPDATE.value == "tenant_update"
        assert AuditAction.TENANT_DELETE.value == "tenant_delete"
        assert AuditAction.TENANT_QUOTA_UPDATE.value == "tenant_quota_update"

    def test_action_is_string_enum(self):
        """Test AuditAction inherits from str."""
        assert isinstance(AuditAction.CREATE, str)
        assert AuditAction.CREATE == "create"


# ============================================================================
# AuditSeverity Enum Tests
# ============================================================================


class TestAuditSeverity:
    """Test AuditSeverity enum."""

    def test_severity_levels_defined(self):
        """Test all severity levels are defined."""
        assert AuditSeverity.DEBUG.value == "debug"
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_severity_is_string_enum(self):
        """Test AuditSeverity inherits from str."""
        assert isinstance(AuditSeverity.INFO, str)
        assert AuditSeverity.INFO == "info"


# ============================================================================
# AuditEntry Tests
# ============================================================================


class TestAuditEntry:
    """Test AuditEntry dataclass."""

    def test_create_minimal_entry(self):
        """Test creating entry with minimal required fields."""
        entry = AuditEntry(
            id="entry-123",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )
        assert entry.id == "entry-123"
        assert entry.tenant_id == "tenant-a"
        assert entry.action == "create"

    def test_create_full_entry(self):
        """Test creating entry with all fields."""
        entry = AuditEntry(
            id="entry-456",
            tenant_id="tenant-b",
            timestamp="2024-01-01T12:00:00Z",
            action="update",
            severity="warning",
            resource_type="policy",
            resource_id="policy-789",
            actor_id="user-123",
            actor_type="service",
            client_ip="192.168.1.1",
            user_agent="TestClient/1.0",
            request_id="req-abc",
            details={"key": "value"},
            outcome="success",
            error_message=None,
        )
        assert entry.resource_type == "policy"
        assert entry.resource_id == "policy-789"
        assert entry.actor_id == "user-123"
        assert entry.client_ip == "192.168.1.1"
        assert entry.details == {"key": "value"}

    def test_default_values(self):
        """Test default values are applied."""
        entry = AuditEntry(
            id="entry-001",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="read",
        )
        assert entry.severity == AuditSeverity.INFO.value
        assert entry.actor_type == "user"
        assert entry.outcome == "success"
        assert entry.details == {}
        assert entry.constitutional_hash == CONSTITUTIONAL_HASH

    def test_to_dict(self):
        """Test to_dict method."""
        entry = AuditEntry(
            id="entry-001",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )
        result = entry.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "entry-001"
        assert result["tenant_id"] == "tenant-a"
        assert result["action"] == "create"

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "id": "entry-002",
            "tenant_id": "tenant-b",
            "timestamp": "2024-01-02T00:00:00Z",
            "action": "delete",
            "severity": "warning",
        }
        entry = AuditEntry.from_dict(data)

        assert entry.id == "entry-002"
        assert entry.tenant_id == "tenant-b"
        assert entry.action == "delete"
        assert entry.severity == "warning"

    def test_from_dict_with_enum_values(self):
        """Test from_dict handles enum values."""
        data = {
            "id": "entry-003",
            "tenant_id": "tenant-c",
            "timestamp": "2024-01-03T00:00:00Z",
            "action": AuditAction.UPDATE,
            "severity": AuditSeverity.ERROR,
        }
        entry = AuditEntry.from_dict(data)

        assert entry.action == "update"
        assert entry.severity == "error"


# ============================================================================
# AuditQueryParams Tests
# ============================================================================


class TestAuditQueryParams:
    """Test AuditQueryParams dataclass."""

    def test_default_values(self):
        """Test default values."""
        params = AuditQueryParams()

        assert params.limit == 100
        assert params.offset == 0
        assert params.order_by == "timestamp"
        assert params.order_desc is True

    def test_custom_values(self):
        """Test custom values."""
        params = AuditQueryParams(
            action=AuditAction.CREATE,
            resource_type="policy",
            actor_id="user-123",
            limit=50,
            offset=10,
        )

        assert params.action == AuditAction.CREATE
        assert params.resource_type == "policy"
        assert params.actor_id == "user-123"
        assert params.limit == 50
        assert params.offset == 10

    def test_time_range_filters(self):
        """Test time range filters."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)

        params = AuditQueryParams(start_time=start, end_time=end)

        assert params.start_time == start
        assert params.end_time == end


# ============================================================================
# AuditQueryResult Tests
# ============================================================================


class TestAuditQueryResult:
    """Test AuditQueryResult dataclass."""

    def test_create_result(self):
        """Test creating query result."""
        entries = [
            AuditEntry(
                id="e1",
                tenant_id="tenant-a",
                timestamp="2024-01-01T00:00:00Z",
                action="create",
            )
        ]
        params = AuditQueryParams()

        result = AuditQueryResult(
            entries=entries,
            total_count=1,
            tenant_id="tenant-a",
            query_params=params,
        )

        assert len(result.entries) == 1
        assert result.total_count == 1
        assert result.tenant_id == "tenant-a"
        assert result.has_more is False

    def test_has_more_pagination(self):
        """Test has_more flag for pagination."""
        params = AuditQueryParams()

        result = AuditQueryResult(
            entries=[],
            total_count=200,
            tenant_id="tenant-a",
            query_params=params,
            has_more=True,
        )

        assert result.has_more is True


# ============================================================================
# AuditLogConfig Tests
# ============================================================================


class TestAuditLogConfig:
    """Test AuditLogConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AuditLogConfig()

        assert config.redis_url == "redis://localhost:6379/0"
        assert config.use_redis is False
        assert config.max_entries_per_tenant == 100000
        assert config.retention_days == 90
        assert config.enable_redaction is True
        assert config.audit_enabled is True
        assert config.fail_open is True
        assert config.key_prefix == "acgs2:audit"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AuditLogConfig(
            redis_url="redis://custom:6380/1",
            use_redis=True,
            max_entries_per_tenant=50000,
            retention_days=30,
            enable_redaction=False,
            audit_enabled=False,
            fail_open=False,
        )

        assert config.redis_url == "redis://custom:6380/1"
        assert config.use_redis is True
        assert config.max_entries_per_tenant == 50000
        assert config.retention_days == 30

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        env_vars_to_clear = [
            "REDIS_URL",
            "AUDIT_USE_REDIS",
            "AUDIT_MAX_ENTRIES_PER_TENANT",
            "AUDIT_RETENTION_DAYS",
            "AUDIT_ENABLE_REDACTION",
            "AUDIT_ENABLED",
            "AUDIT_FAIL_OPEN",
            "AUDIT_KEY_PREFIX",
        ]
        for key in env_vars_to_clear:
            monkeypatch.delenv(key, raising=False)

        config = AuditLogConfig.from_env()

        assert config.redis_url == "redis://localhost:6379/0"
        assert config.use_redis is False
        assert config.audit_enabled is True

    def test_from_env_custom(self, monkeypatch):
        """Test from_env with custom environment variables."""
        monkeypatch.setenv("REDIS_URL", "redis://prod:6379/2")
        monkeypatch.setenv("AUDIT_USE_REDIS", "true")
        monkeypatch.setenv("AUDIT_MAX_ENTRIES_PER_TENANT", "25000")
        monkeypatch.setenv("AUDIT_RETENTION_DAYS", "60")
        monkeypatch.setenv("AUDIT_ENABLE_REDACTION", "false")
        monkeypatch.setenv("AUDIT_ENABLED", "false")
        monkeypatch.setenv("AUDIT_FAIL_OPEN", "false")
        monkeypatch.setenv("AUDIT_KEY_PREFIX", "custom:audit")

        config = AuditLogConfig.from_env()

        assert config.redis_url == "redis://prod:6379/2"
        assert config.use_redis is True
        assert config.max_entries_per_tenant == 25000
        assert config.retention_days == 60
        assert config.enable_redaction is False
        assert config.audit_enabled is False
        assert config.fail_open is False
        assert config.key_prefix == "custom:audit"


# ============================================================================
# InMemoryAuditStore Tests
# ============================================================================


class TestInMemoryAuditStore:
    """Test InMemoryAuditStore class."""

    @pytest.mark.asyncio
    async def test_store_entry(self):
        """Test storing an audit entry."""
        store = InMemoryAuditStore()
        entry = AuditEntry(
            id="entry-001",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )

        result = await store.store(entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_store_multiple_tenants_isolated(self):
        """Test entries are isolated by tenant."""
        store = InMemoryAuditStore()

        entry_a = AuditEntry(
            id="entry-a",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )
        entry_b = AuditEntry(
            id="entry-b",
            tenant_id="tenant-b",
            timestamp="2024-01-01T00:00:00Z",
            action="update",
        )

        await store.store(entry_a)
        await store.store(entry_b)

        result_a = await store.query("tenant-a", AuditQueryParams())
        result_b = await store.query("tenant-b", AuditQueryParams())

        assert len(result_a.entries) == 1
        assert result_a.entries[0].id == "entry-a"
        assert len(result_b.entries) == 1
        assert result_b.entries[0].id == "entry-b"

    @pytest.mark.asyncio
    async def test_query_filters_by_action(self):
        """Test query filters by action."""
        store = InMemoryAuditStore()

        for i, action in enumerate(["create", "read", "create", "delete"]):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action=action,
            )
            await store.store(entry)

        params = AuditQueryParams(action=AuditAction.CREATE)
        result = await store.query("tenant-a", params)

        assert len(result.entries) == 2
        assert all(e.action == "create" for e in result.entries)

    @pytest.mark.asyncio
    async def test_query_filters_by_resource_type(self):
        """Test query filters by resource type."""
        store = InMemoryAuditStore()

        for i, rtype in enumerate(["policy", "user", "policy"]):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action="create",
                resource_type=rtype,
            )
            await store.store(entry)

        params = AuditQueryParams(resource_type="policy")
        result = await store.query("tenant-a", params)

        assert len(result.entries) == 2
        assert all(e.resource_type == "policy" for e in result.entries)

    @pytest.mark.asyncio
    async def test_query_filters_by_actor_id(self):
        """Test query filters by actor ID."""
        store = InMemoryAuditStore()

        for i, actor in enumerate(["user-1", "user-2", "user-1"]):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action="read",
                actor_id=actor,
            )
            await store.store(entry)

        params = AuditQueryParams(actor_id="user-1")
        result = await store.query("tenant-a", params)

        assert len(result.entries) == 2
        assert all(e.actor_id == "user-1" for e in result.entries)

    @pytest.mark.asyncio
    async def test_query_pagination(self):
        """Test query pagination."""
        store = InMemoryAuditStore()

        for i in range(5):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action="create",
            )
            await store.store(entry)

        params = AuditQueryParams(limit=2, offset=0)
        result = await store.query("tenant-a", params)

        assert len(result.entries) == 2
        assert result.total_count == 5
        assert result.has_more is True

    @pytest.mark.asyncio
    async def test_query_sorting_desc(self):
        """Test query sorting descending."""
        store = InMemoryAuditStore()

        timestamps = ["2024-01-01T00:00:00Z", "2024-01-03T00:00:00Z", "2024-01-02T00:00:00Z"]
        for i, ts in enumerate(timestamps):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=ts,
                action="create",
            )
            await store.store(entry)

        params = AuditQueryParams(order_desc=True)
        result = await store.query("tenant-a", params)

        assert result.entries[0].timestamp == "2024-01-03T00:00:00Z"
        assert result.entries[2].timestamp == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_query_sorting_asc(self):
        """Test query sorting ascending."""
        store = InMemoryAuditStore()

        timestamps = ["2024-01-01T00:00:00Z", "2024-01-03T00:00:00Z", "2024-01-02T00:00:00Z"]
        for i, ts in enumerate(timestamps):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=ts,
                action="create",
            )
            await store.store(entry)

        params = AuditQueryParams(order_desc=False)
        result = await store.query("tenant-a", params)

        assert result.entries[0].timestamp == "2024-01-01T00:00:00Z"
        assert result.entries[2].timestamp == "2024-01-03T00:00:00Z"

    @pytest.mark.asyncio
    async def test_count_entries(self):
        """Test counting entries for tenant."""
        store = InMemoryAuditStore()

        for i in range(3):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action="create",
            )
            await store.store(entry)

        count = await store.count("tenant-a")
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_empty_tenant(self):
        """Test counting entries for non-existent tenant."""
        store = InMemoryAuditStore()

        count = await store.count("non-existent-tenant")
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self):
        """Test cleanup removes old entries."""
        store = InMemoryAuditStore()

        # Add old and new entries
        old_entry = AuditEntry(
            id="old-entry",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )
        new_entry = AuditEntry(
            id="new-entry",
            tenant_id="tenant-a",
            timestamp="2024-12-31T00:00:00Z",
            action="update",
        )

        await store.store(old_entry)
        await store.store(new_entry)

        # Cleanup entries before June
        cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)
        removed = await store.cleanup("tenant-a", cutoff)

        assert removed == 1
        count = await store.count("tenant-a")
        assert count == 1

    @pytest.mark.asyncio
    async def test_max_entries_limit(self):
        """Test max entries limit enforced."""
        store = InMemoryAuditStore(max_entries_per_tenant=3)

        for i in range(5):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="tenant-a",
                timestamp=f"2024-01-0{i+1}T00:00:00Z",
                action="create",
            )
            await store.store(entry)

        count = await store.count("tenant-a")
        assert count == 3

    @pytest.mark.asyncio
    async def test_close_no_op(self):
        """Test close is a no-op for in-memory store."""
        store = InMemoryAuditStore()
        await store.close()  # Should not raise

    def test_get_all_tenant_ids(self):
        """Test getting all tenant IDs."""
        store = InMemoryAuditStore()

        # Store entries for multiple tenants synchronously through _entries
        store._entries["tenant-a"] = []
        store._entries["tenant-b"] = []
        store._entries["tenant-c"] = []

        tenant_ids = store.get_all_tenant_ids()

        assert set(tenant_ids) == {"tenant-a", "tenant-b", "tenant-c"}


# ============================================================================
# TenantAuditLogger Tests
# ============================================================================


class TestTenantAuditLogger:
    """Test TenantAuditLogger class."""

    @pytest.mark.asyncio
    async def test_log_basic_entry(self):
        """Test logging a basic audit entry."""
        config = AuditLogConfig(audit_enabled=True)
        logger = TenantAuditLogger(config=config)

        entry_id = await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.CREATE,
            resource_type="policy",
            resource_id="policy-123",
        )

        assert entry_id is not None
        count = await logger.count("tenant-a")
        assert count == 1

    @pytest.mark.asyncio
    async def test_log_with_all_fields(self):
        """Test logging with all fields."""
        config = AuditLogConfig(audit_enabled=True)
        logger = TenantAuditLogger(config=config)

        entry_id = await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.UPDATE,
            resource_type="user",
            resource_id="user-456",
            actor_id="admin-123",
            actor_type="service",
            client_ip="10.0.0.1",
            user_agent="TestClient/2.0",
            request_id="req-789",
            details={"field": "value"},
            severity=AuditSeverity.WARNING,
            outcome="failure",
            error_message="Update failed",
        )

        assert entry_id is not None

    @pytest.mark.asyncio
    async def test_log_disabled(self):
        """Test logging is skipped when disabled."""
        config = AuditLogConfig(audit_enabled=False)
        logger = TenantAuditLogger(config=config)

        entry_id = await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.CREATE,
        )

        assert entry_id is None

    @pytest.mark.asyncio
    async def test_query_scoped_to_tenant(self):
        """Test query is scoped to requesting tenant."""
        logger = TenantAuditLogger()

        # Log entries for two tenants
        await logger.log(tenant_id="tenant-a", action=AuditAction.CREATE)
        await logger.log(tenant_id="tenant-a", action=AuditAction.READ)
        await logger.log(tenant_id="tenant-b", action=AuditAction.UPDATE)

        # Query for tenant-a only
        result = await logger.query(requesting_tenant_id="tenant-a")

        assert result.tenant_id == "tenant-a"
        assert len(result.entries) == 2
        assert all(e.tenant_id == "tenant-a" for e in result.entries)

    @pytest.mark.asyncio
    async def test_query_cross_tenant_prevention(self):
        """Test cross-tenant access is prevented."""
        logger = TenantAuditLogger()

        # Log entries for tenant-b
        await logger.log(tenant_id="tenant-b", action=AuditAction.CREATE)
        await logger.log(tenant_id="tenant-b", action=AuditAction.UPDATE)

        # Query as tenant-a should not see tenant-b's entries
        result = await logger.query(requesting_tenant_id="tenant-a")

        assert result.tenant_id == "tenant-a"
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_query_with_filters(self):
        """Test query with filters."""
        logger = TenantAuditLogger()

        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.CREATE,
            resource_type="policy",
        )
        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.READ,
            resource_type="user",
        )
        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.CREATE,
            resource_type="user",
        )

        params = AuditQueryParams(action=AuditAction.CREATE)
        result = await logger.query(requesting_tenant_id="tenant-a", query=params)

        assert len(result.entries) == 2
        assert all(e.action == "create" for e in result.entries)

    @pytest.mark.asyncio
    async def test_sensitive_field_redaction(self):
        """Test sensitive fields are redacted."""
        config = AuditLogConfig(enable_redaction=True)
        logger = TenantAuditLogger(config=config)

        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.LOGIN,
            details={
                "username": "test-user",
                "password": "secret123",
                "api_key": "key-abc",
                "normal_field": "visible",
            },
        )

        result = await logger.query(requesting_tenant_id="tenant-a")
        entry = result.entries[0]

        assert entry.details["username"] == "test-user"
        assert entry.details["password"] == "[REDACTED]"
        assert entry.details["api_key"] == "[REDACTED]"
        assert entry.details["normal_field"] == "visible"

    @pytest.mark.asyncio
    async def test_nested_sensitive_field_redaction(self):
        """Test nested sensitive fields are redacted."""
        config = AuditLogConfig(enable_redaction=True)
        logger = TenantAuditLogger(config=config)

        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.CONFIG_CHANGE,
            details={
                "config": {
                    "database_url": "postgres://...",
                    "secret_token": "token123",
                }
            },
        )

        result = await logger.query(requesting_tenant_id="tenant-a")
        entry = result.entries[0]

        assert entry.details["config"]["database_url"] == "postgres://..."
        assert entry.details["config"]["secret_token"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_redaction_disabled(self):
        """Test redaction can be disabled."""
        config = AuditLogConfig(enable_redaction=False)
        logger = TenantAuditLogger(config=config)

        await logger.log(
            tenant_id="tenant-a",
            action=AuditAction.LOGIN,
            details={"password": "secret123"},
        )

        result = await logger.query(requesting_tenant_id="tenant-a")
        entry = result.entries[0]

        assert entry.details["password"] == "secret123"

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_rejected(self):
        """Test invalid tenant ID is rejected."""
        logger = TenantAuditLogger()

        # Very long tenant ID should be rejected
        long_tenant_id = "a" * 100

        entry_id = await logger.log(
            tenant_id=long_tenant_id,
            action=AuditAction.CREATE,
        )

        # With fail_open=True, should return None
        assert entry_id is None

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_query(self):
        """Test query with invalid tenant ID returns empty result."""
        logger = TenantAuditLogger()

        result = await logger.query(requesting_tenant_id="a" * 100)

        assert len(result.entries) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_count_per_tenant(self):
        """Test count returns entries for specific tenant."""
        logger = TenantAuditLogger()

        await logger.log(tenant_id="tenant-a", action=AuditAction.CREATE)
        await logger.log(tenant_id="tenant-a", action=AuditAction.READ)
        await logger.log(tenant_id="tenant-b", action=AuditAction.UPDATE)

        count_a = await logger.count("tenant-a")
        count_b = await logger.count("tenant-b")

        assert count_a == 2
        assert count_b == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self):
        """Test cleanup removes old entries."""
        logger = TenantAuditLogger()

        # We need to manually add entries with old timestamps
        store = logger.get_store()
        old_entry = AuditEntry(
            id="old-entry",
            tenant_id="tenant-a",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
        )
        await store.store(old_entry)

        new_entry = AuditEntry(
            id="new-entry",
            tenant_id="tenant-a",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="update",
        )
        await store.store(new_entry)

        # Cleanup entries older than 30 days
        removed = await logger.cleanup_old_entries("tenant-a", retention_days=30)

        assert removed >= 1

    @pytest.mark.asyncio
    async def test_fail_open_behavior(self):
        """Test fail-open behavior on errors."""
        config = AuditLogConfig(fail_open=True)
        logger = TenantAuditLogger(config=config)

        # Invalid tenant should not raise, just return None
        entry_id = await logger.log(
            tenant_id="",  # Empty tenant ID
            action=AuditAction.CREATE,
        )

        assert entry_id is None

    @pytest.mark.asyncio
    async def test_fail_closed_behavior(self):
        """Test fail-closed behavior on errors."""
        config = AuditLogConfig(fail_open=False)
        logger = TenantAuditLogger(config=config)

        with pytest.raises(ValueError):
            await logger.log(
                tenant_id="",  # Empty tenant ID
                action=AuditAction.CREATE,
            )

    @pytest.mark.asyncio
    async def test_get_store(self):
        """Test get_store returns underlying store."""
        logger = TenantAuditLogger()
        store = logger.get_store()

        assert isinstance(store, InMemoryAuditStore)

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close releases resources."""
        logger = TenantAuditLogger()
        await logger.close()  # Should not raise


# ============================================================================
# Factory Functions Tests
# ============================================================================


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_tenant_audit_logger_default(self):
        """Test create_tenant_audit_logger with defaults."""
        logger = create_tenant_audit_logger()

        assert isinstance(logger, TenantAuditLogger)

    def test_create_tenant_audit_logger_with_config(self):
        """Test create_tenant_audit_logger with custom config."""
        config = AuditLogConfig(audit_enabled=False)
        logger = create_tenant_audit_logger(config=config)

        assert logger.config.audit_enabled is False

    def test_create_tenant_audit_logger_with_store(self):
        """Test create_tenant_audit_logger with custom store."""
        store = InMemoryAuditStore(max_entries_per_tenant=500)
        logger = create_tenant_audit_logger(store=store)

        assert logger.get_store() == store

    def test_get_tenant_audit_logger_cached(self):
        """Test get_tenant_audit_logger returns cached instance."""
        # Clear the cache first
        get_tenant_audit_logger.cache_clear()

        logger1 = get_tenant_audit_logger()
        logger2 = get_tenant_audit_logger()

        assert logger1 is logger2


# ============================================================================
# Module Constants Tests
# ============================================================================


class TestModuleConstants:
    """Test module-level constants."""

    def test_constitutional_hash_defined(self):
        """Test constitutional hash is defined."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_audit_logger_available_flag(self):
        """Test AUDIT_LOGGER_AVAILABLE flag."""
        assert AUDIT_LOGGER_AVAILABLE is True

    def test_sensitive_fields_defined(self):
        """Test sensitive fields set is defined."""
        assert "password" in SENSITIVE_FIELDS
        assert "secret" in SENSITIVE_FIELDS
        assert "token" in SENSITIVE_FIELDS
        assert "api_key" in SENSITIVE_FIELDS


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuditLoggerIntegration:
    """Integration tests for audit logger."""

    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit workflow."""
        logger = TenantAuditLogger()

        # Log multiple actions
        await logger.log(
            tenant_id="enterprise-tenant",
            action=AuditAction.LOGIN,
            actor_id="user-001",
            details={"source": "web"},
        )
        await logger.log(
            tenant_id="enterprise-tenant",
            action=AuditAction.CREATE,
            resource_type="policy",
            resource_id="policy-001",
            actor_id="user-001",
        )
        await logger.log(
            tenant_id="enterprise-tenant",
            action=AuditAction.LOGOUT,
            actor_id="user-001",
        )

        # Query all entries
        result = await logger.query(requesting_tenant_id="enterprise-tenant")

        assert result.total_count == 3
        assert result.tenant_id == "enterprise-tenant"

        # Query specific action
        params = AuditQueryParams(action=AuditAction.CREATE)
        result = await logger.query(requesting_tenant_id="enterprise-tenant", query=params)

        assert len(result.entries) == 1
        assert result.entries[0].resource_type == "policy"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self):
        """Test multiple tenants are properly isolated."""
        logger = TenantAuditLogger()

        tenants = ["tenant-alpha", "tenant-beta", "tenant-gamma"]

        # Log entries for each tenant
        for i, tenant_id in enumerate(tenants):
            for j in range(3):
                await logger.log(
                    tenant_id=tenant_id,
                    action=AuditAction.CREATE,
                    resource_type="resource",
                    resource_id=f"res-{i}-{j}",
                )

        # Verify each tenant only sees their entries
        for tenant_id in tenants:
            result = await logger.query(requesting_tenant_id=tenant_id)

            assert result.tenant_id == tenant_id
            assert result.total_count == 3
            assert all(e.tenant_id == tenant_id for e in result.entries)

    @pytest.mark.asyncio
    async def test_audit_trail_for_security_events(self):
        """Test audit trail captures security events."""
        logger = TenantAuditLogger()

        # Simulate security events
        await logger.log(
            tenant_id="secure-tenant",
            action=AuditAction.AUTH_FAILURE,
            actor_id="attacker-ip",
            client_ip="192.168.1.100",
            severity=AuditSeverity.WARNING,
            details={"reason": "invalid_credentials"},
        )
        await logger.log(
            tenant_id="secure-tenant",
            action=AuditAction.ACCESS_DENIED,
            actor_id="user-456",
            resource_type="admin-panel",
            severity=AuditSeverity.ERROR,
            details={"reason": "insufficient_permissions"},
        )

        # Query security events
        params = AuditQueryParams(severity=AuditSeverity.WARNING)
        warnings = await logger.query(requesting_tenant_id="secure-tenant", query=params)

        params = AuditQueryParams(severity=AuditSeverity.ERROR)
        errors = await logger.query(requesting_tenant_id="secure-tenant", query=params)

        assert len(warnings.entries) == 1
        assert len(errors.entries) == 1

    @pytest.mark.asyncio
    async def test_time_range_filtering(self):
        """Test filtering by time range."""
        logger = TenantAuditLogger()
        store = logger.get_store()

        # Add entries with specific timestamps
        base_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        for i in range(5):
            entry = AuditEntry(
                id=f"entry-{i}",
                tenant_id="time-tenant",
                timestamp=(base_time + timedelta(days=i)).isoformat(),
                action="create",
            )
            await store.store(entry)

        # Query for specific time range (days 1-3)
        start = base_time + timedelta(days=1)
        end = base_time + timedelta(days=3)
        params = AuditQueryParams(start_time=start, end_time=end)

        result = await logger.query(requesting_tenant_id="time-tenant", query=params)

        assert len(result.entries) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
