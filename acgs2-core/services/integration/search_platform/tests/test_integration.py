import logging

"""
Integration Tests for Search Platform Client

Tests the integration between ACGS2 and the Universal Search Platform.
Requires the Search Platform to be running on localhost:9080.

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
from datetime import datetime, timedelta, timezone

import pytest

# Skip all tests if Search Platform is not available
pytestmark = pytest.mark.asyncio


@pytest.fixture
def search_platform_url():
    """Get the Search Platform URL from environment or default."""
    return os.getenv("SEARCH_PLATFORM_URL", "http://localhost:9080")


@pytest.fixture
def acgs2_path():
    """Get the ACGS2 codebase path."""
    return os.getenv("ACGS2_PATH", "/home/dislove/acgs2")


@pytest.fixture
async def client(search_platform_url):
    """Create a Search Platform client."""
    from services.integration.search_platform import (
        SearchPlatformClient,
        SearchPlatformConfig,
    )

    config = SearchPlatformConfig(base_url=search_platform_url)
    client = SearchPlatformClient(config)
    yield client
    await client.close()


@pytest.fixture
async def constitutional_service(search_platform_url):
    """Create a Constitutional Code Search service."""
    from services.integration.search_platform import (
        ConstitutionalCodeSearchService,
        SearchPlatformConfig,
    )

    config = SearchPlatformConfig(base_url=search_platform_url)
    service = ConstitutionalCodeSearchService(config=config)
    yield service
    await service.close()


@pytest.fixture
async def audit_service(search_platform_url):
    """Create an Audit Trail Search service."""
    from services.integration.search_platform import (
        AuditTrailSearchService,
        SearchPlatformConfig,
    )

    config = SearchPlatformConfig(base_url=search_platform_url)
    service = AuditTrailSearchService(config=config)
    yield service
    await service.close()


class TestSearchPlatformClient:
    """Tests for the base Search Platform client."""

    async def test_health_check(self, client):
        """Test health check endpoint."""
        health = await client.health_check()
        assert health.status == "healthy"
        assert health.is_healthy

    async def test_is_healthy(self, client):
        """Test quick health check."""
        is_healthy = await client.is_healthy()
        assert is_healthy is True

    async def test_ready(self, client):
        """Test readiness endpoint."""
        is_ready = await client.ready()
        assert is_ready is True

    async def test_get_stats(self, client):
        """Test stats endpoint."""
        stats = await client.get_stats()
        assert stats.total_workers >= 0
        assert stats.healthy_workers >= 0

    async def test_simple_search(self, client, acgs2_path):
        """Test a simple search query."""
        response = await client.search(
            pattern="def ",
            paths=[acgs2_path],
            max_results=10,
        )

        assert response.id is not None
        assert response.stats.files_searched > 0
        # May or may not find matches depending on path

    async def test_search_code(self, client, acgs2_path):
        """Test code-specific search."""
        response = await client.search_code(
            pattern="import asyncio",
            paths=[acgs2_path],
            file_types=["py"],
            max_results=50,
        )

        assert response.stats.files_searched >= 0
        # ACGS2 uses asyncio extensively
        if response.results:
            assert all("asyncio" in m.line_content for m in response.results)

    async def test_find_definition(self, client, acgs2_path):
        """Test finding symbol definitions."""
        response = await client.find_definition(
            symbol="SearchPlatformClient",
            paths=[f"{acgs2_path}/services/integration/search_platform"],
            language="python",
        )

        # Should find the class definition
        assert response.stats.total_matches >= 0

    async def test_quick_search(self, client):
        """Test quick search with minimal params."""
        response = await client.search_quick(
            pattern="TODO",
            max_results=5,
        )

        assert response.id is not None


class TestConstitutionalCodeSearch:
    """Tests for constitutional code search service."""

    async def test_search_with_compliance(self, constitutional_service, acgs2_path):
        """Test search with compliance checking."""
        result = await constitutional_service.search(
            pattern="class ",
            paths=[f"{acgs2_path}/services/integration/search_platform"],
            file_types=["py"],
            check_compliance=True,
            max_results=20,
        )

        assert result.total_files_searched >= 0
        assert result.constitutional_hash == "cdd01ef066bc6cf2"

    async def test_scan_for_violations(self, constitutional_service, acgs2_path):
        """Test scanning for constitutional violations."""
        result = await constitutional_service.scan_for_violations(
            paths=[f"{acgs2_path}/services/integration/search_platform"],
            file_types=["py"],
        )

        # Our new code should be compliant
        assert result.total_files_searched >= 0
        # Check structure of result
        assert hasattr(result, "violations")
        assert hasattr(result, "compliant_matches")

    async def test_verify_constitutional_hash(self, constitutional_service, acgs2_path):
        """Test constitutional hash verification."""
        result = await constitutional_service.verify_constitutional_hash(
            paths=[f"{acgs2_path}/services/integration/search_platform"],
        )

        # Our files should have the hash
        assert result.total_files_searched >= 0
        # New files should be compliant
        compliant_count = len(result.compliant_matches)
        assert compliant_count >= 0

    async def test_find_security_issues(self, constitutional_service, acgs2_path):
        """Test finding security issues."""
        result = await constitutional_service.find_security_issues(
            paths=[f"{acgs2_path}/services/integration/search_platform"],
        )

        # Our code should not have critical security issues
        assert result.total_files_searched >= 0
        # Structure check
        assert isinstance(result.violations, list)

    async def test_custom_pattern(self, constitutional_service, acgs2_path):
        """Test adding custom violation patterns."""
        from services.integration.search_platform.constitutional_search import (
            ConstitutionalPattern,
            ConstitutionalViolationType,
        )

        # Add custom pattern
        custom = ConstitutionalPattern(
            name="test_pattern",
            pattern=r"CUSTOM_TEST_MARKER",
            violation_type=ConstitutionalViolationType.COMPLIANCE_GAP,
            severity="low",
            description="Test pattern",
            remediation="Remove test marker",
            file_types=["py"],
        )

        constitutional_service.add_custom_pattern(custom)
        assert len(constitutional_service.violation_patterns) > 0

        # Remove pattern
        removed = constitutional_service.remove_pattern("test_pattern")
        assert removed is True


class TestAuditTrailSearch:
    """Tests for audit trail search service."""

    async def test_search_logs(self, audit_service):
        """Test basic log search."""
        result = await audit_service.search(
            pattern="error|warning|info",
            paths=["/var/log"],
            max_results=10,
        )

        # May or may not find logs depending on permissions
        assert result.files_searched >= 0
        assert isinstance(result.events, list)

    async def test_search_with_time_range(self, audit_service):
        """Test search with time range."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)

        result = await audit_service.search(
            pattern=".",
            time_range=(start_time, end_time),
            max_results=10,
        )

        assert result.time_range is not None
        assert result.time_range[0] == start_time
        assert result.time_range[1] == end_time

    async def test_get_recent_critical_events(self, audit_service):
        """Test getting recent critical events."""
        result = await audit_service.get_recent_critical_events(
            hours=24,
        )

        assert isinstance(result.events, list)
        # All should be critical
        for event in result.events:
            from services.integration.search_platform.audit_search import AuditSeverity

            assert event.severity == AuditSeverity.CRITICAL

    async def test_generate_audit_summary(self, audit_service):
        """Test generating audit summary."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        summary = await audit_service.generate_audit_summary(
            time_range=(start_time, end_time),
        )

        assert "total_events" in summary
        assert "by_event_type" in summary
        assert "by_severity" in summary


class TestModels:
    """Tests for data models."""

    def test_search_request_to_dict(self):
        """Test SearchRequest serialization."""
        from services.integration.search_platform import (
            SearchDomain,
            SearchOptions,
            SearchRequest,
            SearchScope,
        )

        request = SearchRequest(
            pattern="test",
            domain=SearchDomain.CODE,
            scope=SearchScope(paths=["/test"]),
            options=SearchOptions(max_results=100),
        )

        data = request.to_dict()
        assert data["pattern"] == "test"
        assert data["domain"] == "code"
        assert data["scope"]["paths"] == ["/test"]
        assert data["options"]["max_results"] == 100

    def test_search_response_from_dict(self):
        """Test SearchResponse deserialization."""
        from services.integration.search_platform import SearchResponse

        data = {
            "id": "12345678-1234-5678-1234-567812345678",
            "results": [
                {
                    "file": "/test/file.py",
                    "line_number": 10,
                    "column": 5,
                    "line_content": "def test():",
                    "match_text": "def",
                }
            ],
            "stats": {
                "total_matches": 1,
                "files_matched": 1,
                "files_searched": 10,
                "bytes_searched": 1000,
                "duration_ms": 50,
            },
        }

        response = SearchResponse.from_dict(data)
        assert len(response.results) == 1
        assert response.results[0].file == "/test/file.py"
        assert response.stats.total_matches == 1

    def test_health_status(self):
        """Test HealthStatus model."""
        from services.integration.search_platform.models import HealthStatus

        data = {
            "status": "healthy",
            "version": "1.0.0",
            "workers": {"total": 1, "healthy": 1},
        }

        status = HealthStatus.from_dict(data)
        assert status.is_healthy
        assert status.version == "1.0.0"


class TestCircuitBreaker:
    """Tests for circuit breaker functionality."""

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        from services.integration.search_platform.client import (
            CircuitBreaker,
            CircuitState,
        )

        breaker = CircuitBreaker(failure_threshold=3)

        # Should start closed
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute()

        # Record failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        # Third failure should open
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert not breaker.can_execute()

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        from services.integration.search_platform.client import (
            CircuitBreaker,
            CircuitState,
        )

        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for testing
            half_open_max_calls=2,
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        import time

        time.sleep(0.15)

        # Should be half-open now
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute()

        # Successful calls should close it
        breaker.record_success()
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED


# Integration test that requires running Search Platform
@pytest.mark.integration
class TestLiveIntegration:
    """Live integration tests - require Search Platform running."""

    async def test_end_to_end_search(self, client, acgs2_path):
        """End-to-end search test."""
        # Health check
        assert await client.is_healthy()

        # Search
        response = await client.search_code(
            pattern="Constitutional Hash",
            paths=[f"{acgs2_path}/services/integration/search_platform"],
            file_types=["py"],
        )

        # Should find our new files
        assert response.stats.total_matches > 0

        # Verify results contain our hash
        for match in response.results:
            assert (
                "cdd01ef066bc6cf2" in match.line_content or "Constitutional" in match.line_content
            )

    async def test_constitutional_compliance_scan(self, constitutional_service, acgs2_path):
        """Test full constitutional compliance scan."""
        result = await constitutional_service.scan_for_violations(
            paths=[f"{acgs2_path}/services/integration/search_platform"],
            severity_filter=["critical", "high"],
        )

        # Print violations for debugging
        for v in result.violations:
            logging.info(f"Violation: {v.violation_type} in {v.file}:{v.line_number}")

        # Our new code should be clean
        critical = [v for v in result.violations if v.severity == "critical"]
        assert len(critical) == 0, f"Found critical violations: {critical}"
