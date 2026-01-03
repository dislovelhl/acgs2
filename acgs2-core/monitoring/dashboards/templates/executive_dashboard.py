"""
ACGS-2 Executive Dashboard Template
High-level business metrics and KPIs for executive leadership
Constitutional Hash: cdd01ef066bc6cf2
"""

from ..real_time.dashboard_engine import (
    KPI,
    AlertRule,
    AlertSeverity,
    Dashboard,
    DashboardPanel,
    DashboardType,
    KPICategory,
    MetricType,
)

# Executive Dashboard KPIs
executive_kpis = [
    KPI(
        id="system_availability",
        name="System Availability",
        description="Overall system availability percentage",
        category=KPICategory.AVAILABILITY,
        metric_type=MetricType.GAUGE,
        query="up{job='acgs2'}",
        unit="%",
        target_value=99.9,
        warning_threshold=99.5,
        critical_threshold=99.0,
        tags=["executive", "availability", "sla"],
    ),
    KPI(
        id="active_tenants",
        name="Active Tenants",
        description="Number of active tenants in the system",
        category=KPICategory.BUSINESS,
        metric_type=MetricType.GAUGE,
        query="acgs2_tenants_active_total",
        unit="count",
        target_value=1000,  # Expected tenant count
        tags=["executive", "business", "tenants"],
    ),
    KPI(
        id="api_response_time",
        name="API Response Time (P95)",
        description="95th percentile API response time",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        unit="ms",
        target_value=500,
        warning_threshold=1000,
        critical_threshold=2000,
        tags=["executive", "performance", "api"],
    ),
    KPI(
        id="security_incidents",
        name="Security Incidents (24h)",
        description="Number of security incidents in the last 24 hours",
        category=KPICategory.SECURITY,
        metric_type=MetricType.COUNTER,
        query="increase(acgs2_security_incidents_total[24h])",
        unit="incidents",
        warning_threshold=5,
        critical_threshold=10,
        tags=["executive", "security", "incidents"],
    ),
    KPI(
        id="compliance_score",
        name="Compliance Score",
        description="Overall compliance score across all frameworks",
        category=KPICategory.COMPLIANCE,
        metric_type=MetricType.GAUGE,
        query="acgs2_compliance_score",
        unit="%",
        target_value=98.0,
        warning_threshold=95.0,
        critical_threshold=90.0,
        tags=["executive", "compliance", "score"],
    ),
    KPI(
        id="revenue_impact",
        name="Revenue Impact",
        description="Estimated revenue impact from downtime/issues",
        category=KPICategory.BUSINESS,
        metric_type=MetricType.GAUGE,
        query="acgs2_revenue_impact_per_hour",
        unit="$/hour",
        tags=["executive", "business", "revenue"],
    ),
    KPI(
        id="user_satisfaction",
        name="User Satisfaction Score",
        description="Average user satisfaction score",
        category=KPICategory.BUSINESS,
        metric_type=MetricType.GAUGE,
        query="acgs2_user_satisfaction_score",
        unit="score",
        target_value=4.5,
        warning_threshold=4.0,
        tags=["executive", "business", "satisfaction"],
    ),
    KPI(
        id="data_processed",
        name="Data Processed",
        description="Total data processed in GB per hour",
        category=KPICategory.OPERATIONAL,
        metric_type=MetricType.GAUGE,
        query="rate(acgs2_data_processed_bytes_total[1h]) / 1024 / 1024 / 1024",
        unit="GB/h",
        tags=["executive", "operational", "data"],
    ),
]

# Executive Dashboard Alert Rules
executive_alerts = [
    AlertRule(
        id="availability_critical",
        name="Critical System Availability",
        description="System availability dropped below 99%",
        kpi_id="system_availability",
        condition="value < 99.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=300,
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="high_security_incidents",
        name="High Security Incidents",
        description="Security incidents exceeded threshold",
        kpi_id="security_incidents",
        condition="value > 10",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=3600,
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="compliance_drift",
        name="Compliance Score Drift",
        description="Compliance score dropped significantly",
        kpi_id="compliance_score",
        condition="value < 90.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=1800,
        channels=["email", "pagerduty"],
    ),
    AlertRule(
        id="api_performance_degradation",
        name="API Performance Degradation",
        description="API response time exceeded 2 seconds",
        kpi_id="api_response_time",
        condition="value > 2000",
        severity=AlertSeverity.WARNING,
        duration_seconds=600,
        channels=["email", "slack"],
    ),
]

# Executive Dashboard Panels
executive_panels = [
    DashboardPanel(
        id="system_health_panel",
        title="System Health Overview",
        kpi_ids=["system_availability", "api_response_time"],
        chart_type="gauge",
        time_range="1h",
        width=6,
        height=4,
        position={"x": 0, "y": 0},
    ),
    DashboardPanel(
        id="business_metrics_panel",
        title="Business Metrics",
        kpi_ids=["active_tenants", "revenue_impact", "user_satisfaction"],
        chart_type="line",
        time_range="24h",
        width=6,
        height=4,
        position={"x": 6, "y": 0},
    ),
    DashboardPanel(
        id="security_compliance_panel",
        title="Security & Compliance",
        kpi_ids=["security_incidents", "compliance_score"],
        chart_type="bar",
        time_range="24h",
        width=6,
        height=4,
        position={"x": 0, "y": 4},
    ),
    DashboardPanel(
        id="operational_metrics_panel",
        title="Operational Metrics",
        kpi_ids=["data_processed"],
        chart_type="area",
        time_range="24h",
        width=6,
        height=4,
        position={"x": 6, "y": 4},
    ),
    DashboardPanel(
        id="trends_panel",
        title="Performance Trends",
        kpi_ids=["system_availability", "api_response_time", "compliance_score"],
        chart_type="line",
        time_range="7d",
        width=12,
        height=6,
        position={"x": 0, "y": 8},
    ),
]

# Complete Executive Dashboard
executive_dashboard = Dashboard(
    id="executive_overview",
    name="Executive Overview Dashboard",
    description="High-level business and operational metrics for executive leadership",
    dashboard_type=DashboardType.EXECUTIVE,
    panels=executive_panels,
    tags=["executive", "business", "leadership"],
    refresh_interval_seconds=60,  # Refresh every minute for executives
    auto_refresh=True,
    public_access=False,
    owner="system",
)

# Operational Dashboard KPIs
operational_kpis = [
    KPI(
        id="cpu_usage",
        name="CPU Usage",
        description="Average CPU usage across all nodes",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="avg(rate(cpu_usage_percent[5m]))",
        unit="%",
        warning_threshold=70.0,
        critical_threshold=85.0,
        tags=["operational", "infrastructure", "cpu"],
    ),
    KPI(
        id="memory_usage",
        name="Memory Usage",
        description="Average memory usage across all nodes",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="avg(memory_usage_percent)",
        unit="%",
        warning_threshold=75.0,
        critical_threshold=90.0,
        tags=["operational", "infrastructure", "memory"],
    ),
    KPI(
        id="disk_usage",
        name="Disk Usage",
        description="Average disk usage across all nodes",
        category=KPICategory.OPERATIONAL,
        metric_type=MetricType.GAUGE,
        query="avg(disk_usage_percent)",
        unit="%",
        warning_threshold=80.0,
        critical_threshold=95.0,
        tags=["operational", "infrastructure", "disk"],
    ),
    KPI(
        id="network_traffic",
        name="Network Traffic",
        description="Total network traffic in/out",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="rate(network_bytes_total[5m])",
        unit="MB/s",
        tags=["operational", "network", "traffic"],
    ),
    KPI(
        id="active_connections",
        name="Active Connections",
        description="Number of active client connections",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="acgs2_active_connections",
        unit="connections",
        tags=["operational", "connections", "clients"],
    ),
    KPI(
        id="error_rate",
        name="Error Rate",
        description="Overall system error rate",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query='rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100',
        unit="%",
        warning_threshold=1.0,
        critical_threshold=5.0,
        tags=["operational", "errors", "reliability"],
    ),
    KPI(
        id="queue_depth",
        name="Queue Depth",
        description="Average queue depth for async processing",
        category=KPICategory.PERFORMANCE,
        metric_type=MetricType.GAUGE,
        query="acgs2_queue_depth",
        unit="messages",
        warning_threshold=1000,
        critical_threshold=5000,
        tags=["operational", "queue", "processing"],
    ),
    KPI(
        id="database_connections",
        name="Database Connections",
        description="Active database connections",
        category=KPICategory.OPERATIONAL,
        metric_type=MetricType.GAUGE,
        query="pg_stat_activity_count",
        unit="connections",
        warning_threshold=80,
        critical_threshold=95,
        tags=["operational", "database", "connections"],
    ),
]

# Operational Dashboard Alert Rules
operational_alerts = [
    AlertRule(
        id="high_cpu_usage",
        name="High CPU Usage",
        description="CPU usage exceeded 85%",
        kpi_id="cpu_usage",
        condition="value > 85.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=300,
        channels=["email", "slack"],
    ),
    AlertRule(
        id="high_memory_usage",
        name="High Memory Usage",
        description="Memory usage exceeded 90%",
        kpi_id="memory_usage",
        condition="value > 90.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=300,
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="disk_space_critical",
        name="Disk Space Critical",
        description="Disk usage exceeded 95%",
        kpi_id="disk_usage",
        condition="value > 95.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=600,
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="high_error_rate",
        name="High Error Rate",
        description="Error rate exceeded 5%",
        kpi_id="error_rate",
        condition="value > 5.0",
        severity=AlertSeverity.CRITICAL,
        duration_seconds=300,
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="queue_backup",
        name="Queue Backup",
        description="Queue depth exceeded 5000 messages",
        kpi_id="queue_depth",
        condition="value > 5000",
        severity=AlertSeverity.WARNING,
        duration_seconds=600,
        channels=["email", "slack"],
    ),
]

# Operational Dashboard Panels
operational_panels = [
    DashboardPanel(
        id="infrastructure_health_panel",
        title="Infrastructure Health",
        kpi_ids=["cpu_usage", "memory_usage", "disk_usage"],
        chart_type="gauge",
        time_range="1h",
        width=6,
        height=4,
        position={"x": 0, "y": 0},
    ),
    DashboardPanel(
        id="system_performance_panel",
        title="System Performance",
        kpi_ids=["api_response_time", "error_rate", "active_connections"],
        chart_type="line",
        time_range="1h",
        width=6,
        height=4,
        position={"x": 6, "y": 0},
    ),
    DashboardPanel(
        id="network_io_panel",
        title="Network I/O",
        kpi_ids=["network_traffic"],
        chart_type="area",
        time_range="1h",
        width=6,
        height=4,
        position={"x": 0, "y": 4},
    ),
    DashboardPanel(
        id="database_panel",
        title="Database Metrics",
        kpi_ids=["database_connections", "queue_depth"],
        chart_type="line",
        time_range="1h",
        width=6,
        height=4,
        position={"x": 6, "y": 4},
    ),
    DashboardPanel(
        id="resource_trends_panel",
        title="Resource Usage Trends",
        kpi_ids=["cpu_usage", "memory_usage", "disk_usage", "network_traffic"],
        chart_type="line",
        time_range="24h",
        width=12,
        height=6,
        position={"x": 0, "y": 8},
    ),
    DashboardPanel(
        id="alert_summary_panel",
        title="Alert Summary",
        kpi_ids=[],  # Special panel for alerts
        chart_type="table",
        time_range="24h",
        width=12,
        height=4,
        position={"x": 0, "y": 14},
    ),
]

# Complete Operational Dashboard
operational_dashboard = Dashboard(
    id="operational_overview",
    name="Operational Overview Dashboard",
    description="Detailed operational metrics for system administrators and DevOps teams",
    dashboard_type=DashboardType.OPERATIONAL,
    panels=operational_panels,
    tags=["operational", "devops", "infrastructure"],
    refresh_interval_seconds=30,
    auto_refresh=True,
    public_access=False,
    owner="system",
)


# Dashboard Registration Function
async def register_executive_dashboard():
    """Register the executive dashboard with KPIs and alerts"""
    from ..real_time.dashboard_engine import (
        dashboard_engine,
        register_dashboard_alert,
        register_dashboard_kpi,
    )

    # Register KPIs
    for kpi in executive_kpis:
        register_dashboard_kpi(kpi)

    # Register alerts
    for alert in executive_alerts:
        register_dashboard_alert(alert)

    # Register dashboard
    dashboard_engine.register_dashboard(executive_dashboard)


async def register_operational_dashboard():
    """Register the operational dashboard with KPIs and alerts"""
    from ..real_time.dashboard_engine import (
        dashboard_engine,
        register_dashboard_alert,
        register_dashboard_kpi,
    )

    # Register KPIs
    for kpi in operational_kpis:
        register_dashboard_kpi(kpi)

    # Register alerts
    for alert in operational_alerts:
        register_dashboard_alert(alert)

    # Register dashboard
    dashboard_engine.register_dashboard(operational_dashboard)


# Export all dashboard components
__all__ = [
    "executive_dashboard",
    "operational_dashboard",
    "executive_kpis",
    "operational_kpis",
    "executive_alerts",
    "operational_alerts",
    "register_executive_dashboard",
    "register_operational_dashboard",
]
