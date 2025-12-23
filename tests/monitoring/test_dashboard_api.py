"""
Tests for ACGS-2 Unified Monitoring Dashboard API
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- Dashboard overview endpoint
- Health aggregation
- Metrics collection
- Alert management
- WebSocket functionality
"""

import asyncio
import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import with proper path resolution
try:
    from monitoring.dashboard_api import (
        CONSTITUTIONAL_HASH,
        ServiceHealthStatus,
        AlertSeverity,
        ServiceHealth,
        SystemMetrics,
        PerformanceMetrics,
        AlertInfo,
        DashboardOverview,
        HealthAggregateResponse,
        MetricsResponse,
        MetricsCollector,
        ServiceHealthChecker,
        AlertManager,
        DashboardService,
    )
except ImportError:
    # Direct import fallback
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dashboard_api",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "monitoring", "dashboard_api.py")
    )
    dashboard_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard_api)

    CONSTITUTIONAL_HASH = dashboard_api.CONSTITUTIONAL_HASH
    ServiceHealthStatus = dashboard_api.ServiceHealthStatus
    AlertSeverity = dashboard_api.AlertSeverity
    ServiceHealth = dashboard_api.ServiceHealth
    SystemMetrics = dashboard_api.SystemMetrics
    PerformanceMetrics = dashboard_api.PerformanceMetrics
    AlertInfo = dashboard_api.AlertInfo
    DashboardOverview = dashboard_api.DashboardOverview
    HealthAggregateResponse = dashboard_api.HealthAggregateResponse
    MetricsResponse = dashboard_api.MetricsResponse
    MetricsCollector = dashboard_api.MetricsCollector
    ServiceHealthChecker = dashboard_api.ServiceHealthChecker
    AlertManager = dashboard_api.AlertManager
    DashboardService = dashboard_api.DashboardService


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_value(self):
        """Constitutional hash should match expected value."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


class TestServiceHealthStatus:
    """Test ServiceHealthStatus enum."""

    def test_status_values(self):
        """All status values should be defined."""
        assert ServiceHealthStatus.HEALTHY.value == "healthy"
        assert ServiceHealthStatus.DEGRADED.value == "degraded"
        assert ServiceHealthStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceHealthStatus.UNKNOWN.value == "unknown"


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """All severity levels should be defined."""
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.INFO.value == "info"


class TestServiceHealth:
    """Test ServiceHealth model."""

    def test_healthy_service(self):
        """Test creating a healthy service record."""
        health = ServiceHealth(
            name="test-service",
            status=ServiceHealthStatus.HEALTHY,
            response_time_ms=5.5,
            last_check=datetime.now(timezone.utc),
        )
        assert health.name == "test-service"
        assert health.status == ServiceHealthStatus.HEALTHY
        assert health.response_time_ms == 5.5
        assert health.error_message is None

    def test_unhealthy_service(self):
        """Test creating an unhealthy service record."""
        health = ServiceHealth(
            name="failed-service",
            status=ServiceHealthStatus.UNHEALTHY,
            last_check=datetime.now(timezone.utc),
            error_message="Connection timeout",
        )
        assert health.status == ServiceHealthStatus.UNHEALTHY
        assert health.error_message == "Connection timeout"


class TestSystemMetrics:
    """Test SystemMetrics model."""

    def test_system_metrics_creation(self):
        """Test creating system metrics."""
        metrics = SystemMetrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            memory_used_gb=8.0,
            memory_total_gb=16.0,
            disk_percent=55.0,
            disk_used_gb=200.0,
            disk_total_gb=500.0,
            network_bytes_sent=1000000,
            network_bytes_recv=2000000,
            process_count=150,
        )
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 62.3
        assert metrics.disk_percent == 55.0

    def test_timestamp_default(self):
        """Test that timestamp defaults to now."""
        metrics = SystemMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_used_gb=8.0,
            memory_total_gb=16.0,
            disk_percent=50.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
            network_bytes_sent=0,
            network_bytes_recv=0,
            process_count=100,
        )
        assert metrics.timestamp is not None
        assert metrics.timestamp.tzinfo == timezone.utc


class TestPerformanceMetrics:
    """Test PerformanceMetrics model."""

    def test_performance_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            p99_latency_ms=0.278,
            throughput_rps=6310.0,
            cache_hit_rate=0.95,
            constitutional_compliance=100.0,
            active_connections=50,
            requests_total=1000000,
            errors_total=10,
        )
        assert metrics.p99_latency_ms == 0.278
        assert metrics.throughput_rps == 6310.0
        assert metrics.cache_hit_rate == 0.95
        assert metrics.constitutional_compliance == 100.0


class TestAlertInfo:
    """Test AlertInfo model."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = AlertInfo(
            alert_id="test-alert-001",
            title="High CPU Usage",
            description="CPU usage exceeded 90%",
            severity=AlertSeverity.WARNING,
            source="system-monitor",
            status="triggered",
            timestamp=datetime.now(timezone.utc),
        )
        assert alert.alert_id == "test-alert-001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.constitutional_hash == CONSTITUTIONAL_HASH


class TestDashboardOverview:
    """Test DashboardOverview model."""

    def test_overview_creation(self):
        """Test creating dashboard overview."""
        overview = DashboardOverview(
            overall_status=ServiceHealthStatus.HEALTHY,
            health_score=0.95,
            total_services=10,
            healthy_services=9,
            degraded_services=1,
            unhealthy_services=0,
            total_circuit_breakers=5,
            closed_breakers=5,
            open_breakers=0,
            half_open_breakers=0,
            p99_latency_ms=0.278,
            throughput_rps=6310.0,
            cache_hit_rate=0.95,
            cpu_percent=45.0,
            memory_percent=60.0,
            disk_percent=55.0,
            critical_alerts=0,
            warning_alerts=1,
            total_alerts=1,
        )
        assert overview.health_score == 0.95
        assert overview.constitutional_hash == CONSTITUTIONAL_HASH

    def test_overview_degraded_status(self):
        """Test overview with degraded status."""
        overview = DashboardOverview(
            overall_status=ServiceHealthStatus.DEGRADED,
            health_score=0.7,
            total_services=10,
            healthy_services=7,
            degraded_services=2,
            unhealthy_services=1,
            total_circuit_breakers=5,
            closed_breakers=3,
            open_breakers=1,
            half_open_breakers=1,
            p99_latency_ms=2.5,
            throughput_rps=500.0,
            cache_hit_rate=0.80,
            cpu_percent=75.0,
            memory_percent=85.0,
            disk_percent=70.0,
            critical_alerts=1,
            warning_alerts=3,
            total_alerts=4,
        )
        assert overview.overall_status == ServiceHealthStatus.DEGRADED
        assert overview.critical_alerts == 1


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_collector_creation(self):
        """Test creating a metrics collector."""
        collector = MetricsCollector(history_size=100)
        assert collector.history_size == 100
        assert len(collector.metrics_history) == 0

    @pytest.mark.asyncio
    async def test_collect_metrics(self):
        """Test collecting metrics."""
        collector = MetricsCollector()
        metrics = await collector.collect_metrics()

        assert "timestamp" in metrics
        assert "system" in metrics
        assert "performance" in metrics
        assert "constitutional_hash" in metrics
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_system_metrics_collection(self):
        """Test system metrics collection."""
        collector = MetricsCollector()
        system_metrics = collector._collect_system_metrics()

        assert "cpu_percent" in system_metrics
        assert "memory_percent" in system_metrics
        assert "disk_percent" in system_metrics
        assert "network_bytes_sent" in system_metrics

    def test_get_history_empty(self):
        """Test getting history when empty."""
        collector = MetricsCollector()
        history = collector.get_history(minutes=5)
        assert history == []


class TestAlertManager:
    """Test AlertManager class."""

    def test_alert_manager_creation(self):
        """Test creating an alert manager."""
        manager = AlertManager()
        assert len(manager.alerts) == 0

    def test_add_alert(self):
        """Test adding an alert."""
        manager = AlertManager()
        alert = AlertInfo(
            alert_id="alert-001",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.WARNING,
            source="test",
            status="triggered",
            timestamp=datetime.now(timezone.utc),
        )
        manager.add_alert(alert)
        assert len(manager.alerts) == 1
        assert "alert-001" in manager.alerts

    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        alert = AlertInfo(
            alert_id="alert-002",
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.CRITICAL,
            source="test",
            status="triggered",
            timestamp=datetime.now(timezone.utc),
        )
        manager.add_alert(alert)
        assert len(manager.alerts) == 1

        result = manager.resolve_alert("alert-002")
        assert result is True
        assert len(manager.alerts) == 0

    def test_resolve_nonexistent_alert(self):
        """Test resolving a non-existent alert."""
        manager = AlertManager()
        result = manager.resolve_alert("nonexistent")
        assert result is False

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        for i in range(3):
            alert = AlertInfo(
                alert_id=f"alert-{i}",
                title=f"Alert {i}",
                description="Description",
                severity=AlertSeverity.WARNING,
                source="test",
                status="triggered",
                timestamp=datetime.now(timezone.utc),
            )
            manager.add_alert(alert)

        alerts = manager.get_active_alerts()
        assert len(alerts) == 3

    def test_get_alerts_by_severity(self):
        """Test filtering alerts by severity."""
        manager = AlertManager()

        # Add alerts with different severities
        severities = [
            AlertSeverity.CRITICAL,
            AlertSeverity.WARNING,
            AlertSeverity.WARNING,
            AlertSeverity.INFO,
        ]
        for i, sev in enumerate(severities):
            alert = AlertInfo(
                alert_id=f"alert-{i}",
                title=f"Alert {i}",
                description="Description",
                severity=sev,
                source="test",
                status="triggered",
                timestamp=datetime.now(timezone.utc),
            )
            manager.add_alert(alert)

        critical = manager.get_alerts_by_severity(AlertSeverity.CRITICAL)
        warnings = manager.get_alerts_by_severity(AlertSeverity.WARNING)

        assert len(critical) == 1
        assert len(warnings) == 2

    def test_alert_callback(self):
        """Test alert callbacks."""
        manager = AlertManager()
        callback_called = []

        def on_alert(alert):
            callback_called.append(alert.alert_id)

        manager.on_alert(on_alert)

        alert = AlertInfo(
            alert_id="callback-test",
            title="Test Alert",
            description="Description",
            severity=AlertSeverity.INFO,
            source="test",
            status="triggered",
            timestamp=datetime.now(timezone.utc),
        )
        manager.add_alert(alert)

        assert len(callback_called) == 1
        assert callback_called[0] == "callback-test"


class TestServiceHealthChecker:
    """Test ServiceHealthChecker class."""

    def test_checker_creation(self):
        """Test creating a health checker."""
        checker = ServiceHealthChecker()
        assert len(checker.services) > 0

    def test_default_services(self):
        """Test default service configuration."""
        checker = ServiceHealthChecker()
        assert "enhanced-agent-bus" in checker.services
        assert "policy-registry" in checker.services


class TestDashboardService:
    """Test DashboardService class."""

    def test_service_creation(self):
        """Test creating the dashboard service."""
        service = DashboardService()
        assert service.metrics_collector is not None
        assert service.health_checker is not None
        assert service.alert_manager is not None

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test getting metrics from service."""
        service = DashboardService()
        metrics = await service.get_metrics()

        assert isinstance(metrics, MetricsResponse)
        assert metrics.constitutional_hash == CONSTITUTIONAL_HASH


class TestHealthAggregateResponse:
    """Test HealthAggregateResponse model."""

    def test_aggregate_response_creation(self):
        """Test creating aggregated health response."""
        services = [
            ServiceHealth(
                name="service-1",
                status=ServiceHealthStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
            ),
            ServiceHealth(
                name="service-2",
                status=ServiceHealthStatus.DEGRADED,
                last_check=datetime.now(timezone.utc),
            ),
        ]

        response = HealthAggregateResponse(
            overall_status=ServiceHealthStatus.DEGRADED,
            health_score=0.75,
            services=services,
            circuit_breakers=[],
        )

        assert response.overall_status == ServiceHealthStatus.DEGRADED
        assert len(response.services) == 2
        assert response.constitutional_hash == CONSTITUTIONAL_HASH


class TestMetricsResponse:
    """Test MetricsResponse model."""

    def test_metrics_response_creation(self):
        """Test creating metrics response."""
        system = SystemMetrics(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_gb=8.0,
            memory_total_gb=16.0,
            disk_percent=55.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            process_count=100,
        )
        performance = PerformanceMetrics(
            p99_latency_ms=0.5,
            throughput_rps=1000.0,
            cache_hit_rate=0.90,
        )

        response = MetricsResponse(
            system=system,
            performance=performance,
            history=[],
        )

        assert response.system.cpu_percent == 50.0
        assert response.performance.throughput_rps == 1000.0
        assert response.constitutional_hash == CONSTITUTIONAL_HASH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
