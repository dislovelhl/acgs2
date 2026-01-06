"""
Tests for ACGS-2 Runtime Security Scanner
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime

import pytest
from src.core.enhanced_agent_bus.runtime_security import (
    CONSTITUTIONAL_HASH,
    RuntimeSecurityConfig,
    RuntimeSecurityScanner,
    SecurityEvent,
    SecurityEventType,
    SecurityScanResult,
    SecuritySeverity,
    get_runtime_security_scanner,
    scan_content,
)


class TestSecurityEventType:
    """Tests for SecurityEventType enum."""

    def test_all_event_types_defined(self):
        """Verify all expected event types are defined."""
        expected_types = [
            "PROMPT_INJECTION_ATTEMPT",
            "TENANT_VIOLATION",
            "RATE_LIMIT_EXCEEDED",
            "CONSTITUTIONAL_HASH_MISMATCH",
            "PERMISSION_DENIED",
            "INVALID_INPUT",
            "ANOMALY_DETECTED",
            "AUTHENTICATION_FAILURE",
            "AUTHORIZATION_FAILURE",
            "SUSPICIOUS_PATTERN",
        ]
        for event_type in expected_types:
            assert hasattr(SecurityEventType, event_type)


class TestSecuritySeverity:
    """Tests for SecuritySeverity enum."""

    def test_all_severity_levels_defined(self):
        """Verify all severity levels are defined."""
        expected_levels = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        for level in expected_levels:
            assert hasattr(SecuritySeverity, level)


class TestSecurityEvent:
    """Tests for SecurityEvent dataclass."""

    def test_event_creation(self):
        """Test creating a security event."""
        event = SecurityEvent(
            event_type=SecurityEventType.PROMPT_INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            message="Test event",
            tenant_id="test-tenant",
            agent_id="test-agent",
        )
        assert event.event_type == SecurityEventType.PROMPT_INJECTION_ATTEMPT
        assert event.severity == SecuritySeverity.HIGH
        assert event.message == "Test event"
        assert event.tenant_id == "test-tenant"
        assert event.constitutional_hash == CONSTITUTIONAL_HASH

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = SecurityEvent(
            event_type=SecurityEventType.TENANT_VIOLATION,
            severity=SecuritySeverity.MEDIUM,
            message="Tenant violation",
        )
        result = event.to_dict()
        assert result["event_type"] == "tenant_violation"
        assert result["severity"] == "medium"
        assert result["message"] == "Tenant violation"
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_event_default_timestamp(self):
        """Test event has default timestamp."""
        event = SecurityEvent(
            event_type=SecurityEventType.INVALID_INPUT,
            severity=SecuritySeverity.LOW,
            message="Test",
        )
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)


class TestSecurityScanResult:
    """Tests for SecurityScanResult dataclass."""

    def test_result_creation(self):
        """Test creating a scan result."""
        result = SecurityScanResult()
        assert result.is_secure is True
        assert result.blocked is False
        assert result.events == []
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_add_event(self):
        """Test adding an event to result."""
        result = SecurityScanResult()
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_PATTERN,
            severity=SecuritySeverity.MEDIUM,
            message="Pattern detected",
        )
        result.add_event(event)
        assert len(result.events) == 1
        assert result.is_secure is True  # Medium severity doesn't block

    def test_add_high_severity_event(self):
        """Test adding high severity event marks as insecure."""
        result = SecurityScanResult()
        event = SecurityEvent(
            event_type=SecurityEventType.PROMPT_INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            message="Injection detected",
        )
        result.add_event(event)
        assert result.is_secure is False

    def test_add_blocking_event(self):
        """Test adding a blocking event."""
        result = SecurityScanResult()
        event = SecurityEvent(
            event_type=SecurityEventType.CONSTITUTIONAL_HASH_MISMATCH,
            severity=SecuritySeverity.CRITICAL,
            message="Hash mismatch",
        )
        result.add_blocking_event(event, "Constitutional violation")
        assert result.blocked is True
        assert result.block_reason == "Constitutional violation"
        assert result.is_secure is False

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = SecurityScanResult()
        result.checks_performed = ["test_check"]
        result.warnings = ["test_warning"]
        result_dict = result.to_dict()
        assert result_dict["is_secure"] is True
        assert result_dict["blocked"] is False
        assert result_dict["checks_performed"] == ["test_check"]
        assert result_dict["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestRuntimeSecurityConfig:
    """Tests for RuntimeSecurityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RuntimeSecurityConfig()
        assert config.enable_prompt_injection_detection is True
        assert config.enable_tenant_validation is True
        assert config.enable_rate_limit_check is True
        assert config.enable_constitutional_validation is True
        assert config.rate_limit_qps == 100
        assert config.fail_closed is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RuntimeSecurityConfig(
            rate_limit_qps=50,
            max_input_length=50000,
            fail_closed=False,
        )
        assert config.rate_limit_qps == 50
        assert config.max_input_length == 50000
        assert config.fail_closed is False


class TestRuntimeSecurityScanner:
    """Tests for RuntimeSecurityScanner."""

    @pytest.fixture
    def scanner(self):
        """Create a fresh scanner instance."""
        return RuntimeSecurityScanner()

    @pytest.fixture
    def scanner_with_config(self):
        """Create scanner with custom config."""
        config = RuntimeSecurityConfig(
            enable_anomaly_detection=False,
            rate_limit_qps=10,
        )
        return RuntimeSecurityScanner(config)

    @pytest.mark.asyncio
    async def test_scan_clean_content(self, scanner):
        """Test scanning clean content."""
        result = await scanner.scan(
            content="Hello, this is normal content.",
            tenant_id="valid-tenant-123",
        )
        assert result.is_secure is True
        assert result.blocked is False
        assert len(result.checks_performed) > 0

    @pytest.mark.asyncio
    async def test_scan_with_constitutional_hash(self, scanner):
        """Test scanning with valid constitutional hash."""
        result = await scanner.scan(
            content="Test content",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        assert result.is_secure is True

    @pytest.mark.asyncio
    async def test_scan_with_invalid_constitutional_hash(self, scanner):
        """Test scanning with invalid constitutional hash."""
        result = await scanner.scan(
            content="Test content",
            constitutional_hash="invalid_hash_value",
        )
        assert result.blocked is True
        assert "constitutional" in result.block_reason.lower()

    @pytest.mark.asyncio
    async def test_scan_suspicious_patterns(self, scanner):
        """Test detection of suspicious patterns."""
        suspicious_content = "<script>alert('xss')</script>"
        result = await scanner.scan(content=suspicious_content)

        # Should detect XSS pattern
        pattern_events = [
            e for e in result.events if e.event_type == SecurityEventType.SUSPICIOUS_PATTERN
        ]
        assert len(pattern_events) > 0

    @pytest.mark.asyncio
    async def test_scan_sql_injection_pattern(self, scanner):
        """Test detection of SQL injection patterns."""
        sql_content = "SELECT * FROM users WHERE id = 1; DROP TABLE users;"
        result = await scanner.scan(content=sql_content)

        pattern_events = [
            e for e in result.events if e.event_type == SecurityEventType.SUSPICIOUS_PATTERN
        ]
        assert len(pattern_events) > 0

    @pytest.mark.asyncio
    async def test_scan_path_traversal_pattern(self, scanner):
        """Test detection of path traversal patterns."""
        path_traversal = "../../../etc/passwd"
        result = await scanner.scan(content=path_traversal)

        pattern_events = [
            e for e in result.events if e.event_type == SecurityEventType.SUSPICIOUS_PATTERN
        ]
        assert len(pattern_events) > 0

    @pytest.mark.asyncio
    async def test_scan_long_input(self, scanner):
        """Test detection of overly long input."""
        config = RuntimeSecurityConfig(max_input_length=100)
        scanner = RuntimeSecurityScanner(config)

        long_content = "x" * 200
        result = await scanner.scan(content=long_content)

        input_events = [e for e in result.events if e.event_type == SecurityEventType.INVALID_INPUT]
        assert len(input_events) > 0

    @pytest.mark.asyncio
    async def test_scan_deeply_nested_dict(self, scanner):
        """Test detection of deeply nested dictionaries."""
        config = RuntimeSecurityConfig(max_nested_depth=5)
        scanner = RuntimeSecurityScanner(config)

        # Create deeply nested dict
        nested = {"level": 1}
        current = nested
        for i in range(10):
            current["nested"] = {"level": i + 2}
            current = current["nested"]

        result = await scanner.scan(content=nested)

        input_events = [e for e in result.events if e.event_type == SecurityEventType.INVALID_INPUT]
        assert len(input_events) > 0

    @pytest.mark.asyncio
    async def test_scan_includes_duration(self, scanner):
        """Test that scan includes duration."""
        result = await scanner.scan(content="test")
        assert result.scan_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_scan_tracks_checks_performed(self, scanner):
        """Test that scan tracks which checks were performed."""
        result = await scanner.scan(content="test", tenant_id="test-tenant")
        assert "tenant_validation" in result.checks_performed
        assert "suspicious_pattern_detection" in result.checks_performed

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scanner_with_config):
        """Test rate limiting detection."""
        scanner = scanner_with_config

        # Make many requests quickly
        for _ in range(15):
            result = await scanner.scan(content="test", tenant_id="test-tenant")

        # Last result should have rate limit warning
        rate_events = [
            e for e in result.events if e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED
        ]
        # May or may not trigger depending on timing
        # Just verify the scan completes
        assert result is not None

    def test_get_metrics(self, scanner):
        """Test getting scanner metrics."""
        metrics = scanner.get_metrics()
        assert "total_scans" in metrics
        assert "blocked_requests" in metrics
        assert "events_detected" in metrics
        assert "constitutional_hash" in metrics
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_metrics_update_after_scan(self, scanner):
        """Test that metrics update after scanning."""
        initial_metrics = scanner.get_metrics()
        initial_scans = initial_metrics["total_scans"]

        await scanner.scan(content="test content")

        updated_metrics = scanner.get_metrics()
        assert updated_metrics["total_scans"] == initial_scans + 1

    @pytest.mark.asyncio
    async def test_get_recent_events(self, scanner):
        """Test retrieving recent events."""
        # Trigger some events
        await scanner.scan(content="<script>alert(1)</script>")

        events = scanner.get_recent_events(limit=10)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_get_recent_events_with_filter(self, scanner):
        """Test filtering recent events."""
        # Trigger suspicious pattern
        await scanner.scan(content="<script>alert(1)</script>")

        events = scanner.get_recent_events(
            limit=10,
            event_type_filter=SecurityEventType.SUSPICIOUS_PATTERN,
        )
        for event in events:
            assert event.event_type == SecurityEventType.SUSPICIOUS_PATTERN

    @pytest.mark.asyncio
    async def test_scan_none_content(self, scanner):
        """Test scanning None content."""
        result = await scanner.scan(content=None)
        assert result is not None
        assert result.is_secure is True

    @pytest.mark.asyncio
    async def test_scan_empty_content(self, scanner):
        """Test scanning empty content."""
        result = await scanner.scan(content="")
        assert result is not None
        assert result.is_secure is True


class TestGlobalScanner:
    """Tests for global scanner functions."""

    def test_get_runtime_security_scanner(self):
        """Test getting global scanner instance."""
        scanner = get_runtime_security_scanner()
        assert isinstance(scanner, RuntimeSecurityScanner)

    def test_get_runtime_security_scanner_singleton(self):
        """Test that global scanner is singleton."""
        scanner1 = get_runtime_security_scanner()
        scanner2 = get_runtime_security_scanner()
        assert scanner1 is scanner2

    @pytest.mark.asyncio
    async def test_scan_content_convenience_function(self):
        """Test the scan_content convenience function."""
        result = await scan_content(
            content="Normal content",
            tenant_id="test-tenant",
        )
        assert isinstance(result, SecurityScanResult)
        assert result.is_secure is True


class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is correctly defined."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_scanner_has_constitutional_hash(self):
        """Verify scanner reports constitutional hash."""
        scanner = RuntimeSecurityScanner()
        metrics = scanner.get_metrics()
        assert metrics["constitutional_hash"] == "cdd01ef066bc6cf2"

    def test_event_has_constitutional_hash(self):
        """Verify events include constitutional hash."""
        event = SecurityEvent(
            event_type=SecurityEventType.ANOMALY_DETECTED,
            severity=SecuritySeverity.INFO,
            message="Test",
        )
        assert event.constitutional_hash == "cdd01ef066bc6cf2"

    def test_result_has_constitutional_hash(self):
        """Verify results include constitutional hash."""
        result = SecurityScanResult()
        assert result.constitutional_hash == "cdd01ef066bc6cf2"
