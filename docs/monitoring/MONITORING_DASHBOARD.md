# ACGS-2 Unified Monitoring Dashboard

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-12-23

## Overview

The ACGS-2 Unified Monitoring Dashboard provides real-time visibility into the health, performance, and operational status of all ACGS-2 services. It aggregates metrics from multiple sources including the Enhanced Agent Bus, service health checks, and system resources.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACGS-2 Monitoring Dashboard                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Health Panel │  │Metrics Chart │  │ Alerts List  │               │
│  │              │  │              │  │              │               │
│  │ - Status     │  │ - CPU        │  │ - Critical   │               │
│  │ - Score      │  │ - Memory     │  │ - Warning    │               │
│  │ - Services   │  │ - Disk       │  │ - Info       │               │
│  │ - Breakers   │  │ - Network    │  │              │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                     Services Grid                           │     │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │     │
│  │  │Service 1│ │Service 2│ │Service 3│ │Service N│  ...      │     │
│  │  │ HEALTHY │ │DEGRADED │ │UNHEALTHY│ │ UNKNOWN │           │     │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │    Dashboard API (Port 8090)    │
              │                                │
              │  GET /dashboard/overview       │
              │  GET /dashboard/health         │
              │  GET /dashboard/metrics        │
              │  GET /dashboard/alerts         │
              │  GET /dashboard/services       │
              │  WS  /dashboard/ws             │
              └────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌──────────────┐ ┌──────────┐ ┌──────────────┐
        │Health Checker│ │ Metrics  │ │    Alert     │
        │              │ │Collector │ │   Manager    │
        └──────────────┘ └──────────┘ └──────────────┘
```

## Components

### Backend API (Python/FastAPI)

**Location**: `monitoring/dashboard_api.py`

The Dashboard API provides RESTful endpoints and WebSocket support for real-time monitoring:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard/overview` | GET | Complete system overview |
| `/dashboard/health` | GET | Aggregated health status |
| `/dashboard/metrics` | GET | System and performance metrics |
| `/dashboard/alerts` | GET | Active alerts |
| `/dashboard/services` | GET | Service health details |
| `/dashboard/ws` | WebSocket | Real-time updates |

### Frontend Dashboard (React/TypeScript)

**Location**: `monitoring/dashboard/`

React-based dashboard with the following components:

| Component | Description |
|-----------|-------------|
| `Dashboard` | Main dashboard layout |
| `HealthPanel` | System health overview and score |
| `MetricsChart` | CPU, memory, disk usage charts |
| `AlertsList` | Active alerts with severity |
| `ServiceGrid` | Service status grid |
| `StatusBadge` | Health status indicator |
| `MetricCard` | Individual metric display |

## API Reference

### GET /dashboard/overview

Returns complete system overview including health score, service counts, and key metrics.

**Response**:
```json
{
  "overall_status": "healthy",
  "health_score": 0.95,
  "total_services": 10,
  "healthy_services": 9,
  "degraded_services": 1,
  "unhealthy_services": 0,
  "total_circuit_breakers": 5,
  "closed_breakers": 5,
  "open_breakers": 0,
  "half_open_breakers": 0,
  "p99_latency_ms": 0.278,
  "throughput_rps": 6310.0,
  "cache_hit_rate": 0.95,
  "cpu_percent": 45.0,
  "memory_percent": 60.0,
  "disk_percent": 55.0,
  "critical_alerts": 0,
  "warning_alerts": 1,
  "total_alerts": 1,
  "timestamp": "2025-12-23T12:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### GET /dashboard/health

Returns aggregated health status of all services and circuit breakers.

**Response**:
```json
{
  "overall_status": "healthy",
  "health_score": 0.95,
  "services": [
    {
      "name": "enhanced-agent-bus",
      "status": "healthy",
      "response_time_ms": 5.2,
      "last_check": "2025-12-23T12:00:00Z",
      "constitutional_hash": "cdd01ef066bc6cf2"
    }
  ],
  "circuit_breakers": [
    {
      "name": "policy-client",
      "state": "closed",
      "failure_count": 0,
      "success_count": 100
    }
  ],
  "timestamp": "2025-12-23T12:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### GET /dashboard/metrics

Returns system and performance metrics with optional history.

**Query Parameters**:
- `minutes` (optional): Minutes of history to include (default: 5)

**Response**:
```json
{
  "system": {
    "cpu_percent": 45.5,
    "memory_percent": 62.3,
    "memory_used_gb": 8.0,
    "memory_total_gb": 16.0,
    "disk_percent": 55.0,
    "disk_used_gb": 200.0,
    "disk_total_gb": 500.0,
    "network_bytes_sent": 1000000,
    "network_bytes_recv": 2000000,
    "process_count": 150,
    "timestamp": "2025-12-23T12:00:00Z"
  },
  "performance": {
    "p99_latency_ms": 0.278,
    "throughput_rps": 6310.0,
    "cache_hit_rate": 0.95,
    "constitutional_compliance": 100.0
  },
  "history": [],
  "timestamp": "2025-12-23T12:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### GET /dashboard/alerts

Returns active alerts filtered by severity.

**Query Parameters**:
- `severity` (optional): Filter by severity (critical, error, warning, info)

**Response**:
```json
[
  {
    "alert_id": "alert-001",
    "title": "High CPU Usage",
    "description": "CPU usage exceeded 90%",
    "severity": "warning",
    "source": "system-monitor",
    "status": "triggered",
    "timestamp": "2025-12-23T11:55:00Z",
    "constitutional_hash": "cdd01ef066bc6cf2"
  }
]
```

### WebSocket /dashboard/ws

Real-time updates for dashboard data.

**Message Format**:
```json
{
  "type": "overview",
  "data": { ... },
  "timestamp": "2025-12-23T12:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Message Types**:
- `overview`: Dashboard overview update
- `health`: Health status update
- `metrics`: Metrics update
- `alert`: New alert notification

## Installation

### Backend API

```bash
# From project root
cd monitoring

# Install dependencies
pip install fastapi uvicorn psutil redis aiohttp

# Run the API server
uvicorn dashboard_api:app --host 0.0.0.0 --port 8090
```

### Frontend Dashboard

```bash
# Navigate to dashboard directory
cd monitoring/dashboard

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8090` | Dashboard API URL |
| `VITE_WS_URL` | `ws://localhost:8090` | WebSocket URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `METRICS_COLLECTION_INTERVAL` | `5` | Metrics collection interval (seconds) |

### Service Configuration

Default monitored services are configured in `dashboard_api.py`:

```python
DEFAULT_SERVICES = {
    "enhanced-agent-bus": "http://localhost:8080",
    "policy-registry": "http://localhost:8000",
    "audit-service": "http://localhost:8084",
    "constitutional-ai": "http://localhost:8001",
    "integrity-service": "http://localhost:8002",
}
```

## Performance Targets

The monitoring dashboard itself must meet these performance requirements:

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time | <100ms | <50ms |
| Dashboard Load Time | <2s | <1s |
| WebSocket Latency | <50ms | <20ms |
| Memory Usage | <100MB | <50MB |

## Constitutional Compliance

All monitoring operations include constitutional hash validation:

- Every API response includes `constitutional_hash: "cdd01ef066bc6cf2"`
- WebSocket messages include constitutional hash
- Alert metadata includes constitutional hash
- Health checks validate constitutional compliance

## Testing

### Backend Tests

```bash
# Run dashboard API tests
PYTHONPATH=/path/to/acgs2 python3 -m pytest tests/monitoring/test_dashboard_api.py -v

# Test with coverage
python3 -m pytest tests/monitoring/ --cov=monitoring --cov-report=html
```

### Frontend Tests

```bash
cd monitoring/dashboard
npm run test
```

## Troubleshooting

### Common Issues

**API Connection Failed**
- Verify the dashboard API is running on port 8090
- Check firewall settings
- Verify CORS configuration

**WebSocket Disconnects**
- Check network stability
- Verify WebSocket URL configuration
- Check server logs for errors

**Missing Metrics**
- Ensure Redis is running if using Redis-backed storage
- Check psutil installation
- Verify system permissions for metric collection

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
uvicorn dashboard_api:app --host 0.0.0.0 --port 8090 --log-level debug
```

## Integration with Existing Monitoring

The dashboard integrates with existing ACGS-2 monitoring components:

- **Health Aggregator**: `enhanced_agent_bus/health_aggregator.py`
- **Health Check Endpoints**: `monitoring/health_check_endpoints.py`
- **Alerting System**: `monitoring/alerting.py`
- **Prometheus Metrics**: `monitoring/prometheus.yml`
- **Grafana Dashboards**: `monitoring/grafana/`

## Changelog

### Version 1.0.0 (2025-12-23)

- Initial unified monitoring dashboard implementation
- REST API with 5 endpoints
- WebSocket real-time updates
- React frontend with 7 components
- 28 backend tests
- Constitutional hash compliance

---

## References

- [ACGS-2 Architecture Documentation](../architecture/)
- [Security Hardening Guide](../security/SECURITY_HARDENING.md)
- [Enhanced Agent Bus Documentation](../../enhanced_agent_bus/README.md)
