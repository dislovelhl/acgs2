# SIEM Integration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version:** 1.0.0
> **Last Updated:** 2025-01-01
> **Status:** Production Ready

## Overview

The Enhanced Agent Bus provides enterprise-grade SIEM (Security Information and Event Management) integration for real-time security event monitoring, alerting, and incident response. This guide covers configuration, usage patterns, and best practices.

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Format Support** | CEF, LEEF, Syslog, JSON event formats |
| **Fire-and-Forget** | <5μs latency impact on main operations |
| **Alert Thresholds** | Configurable thresholds with escalation |
| **Event Correlation** | Pattern detection for attack identification |
| **Constitutional Compliance** | All events include constitutional hash |

## Quick Start

### Basic Setup

```python
from enhanced_agent_bus import (
    SIEMConfig,
    SIEMFormat,
    SIEMIntegration,
    initialize_siem,
    log_security_event,
    SecurityEventType,
    SecuritySeverity,
)

# Initialize SIEM with default configuration
siem = await initialize_siem(SIEMConfig(
    format=SIEMFormat.JSON,
    endpoint_url="https://siem.example.com/api/events",
    enable_alerting=True,
))

# Log security events (fire-and-forget)
await log_security_event(
    event_type=SecurityEventType.AUTHENTICATION_FAILURE,
    severity=SecuritySeverity.HIGH,
    message="Failed login attempt from unknown IP",
    tenant_id="tenant-123",
    metadata={"ip": "192.168.1.100", "attempts": 3}
)
```

### Using the Decorator

```python
from enhanced_agent_bus import security_audit, SecurityEventType, SecuritySeverity

@security_audit(
    event_type=SecurityEventType.AUTHORIZATION_FAILURE,
    severity=SecuritySeverity.INFO,
)
async def sensitive_operation(user_id: str):
    # Function is automatically audited to SIEM
    return await perform_sensitive_action(user_id)
```

## Configuration Options

### SIEMConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | `SIEMFormat` | `JSON` | Output format (CEF, LEEF, Syslog, JSON) |
| `endpoint_url` | `str` | `None` | HTTP endpoint for event shipping |
| `syslog_host` | `str` | `None` | Syslog server hostname |
| `syslog_port` | `int` | `514` | Syslog server port |
| `use_tls` | `bool` | `True` | Enable TLS for HTTP shipping |
| `batch_size` | `int` | `100` | Events per batch |
| `flush_interval_seconds` | `float` | `5.0` | Batch flush interval |
| `enable_alerting` | `bool` | `True` | Enable alert threshold checking |
| `max_queue_size` | `int` | `10000` | Maximum queued events |
| `drop_on_overflow` | `bool` | `True` | Drop events if queue full |
| `correlation_window_seconds` | `int` | `300` | Window for pattern detection |
| `enable_anomaly_detection` | `bool` | `True` | Enable event correlation |

### Example Configurations

#### Splunk Integration

```python
config = SIEMConfig(
    format=SIEMFormat.JSON,
    endpoint_url="https://splunk.example.com:8088/services/collector/event",
    use_tls=True,
    batch_size=50,
    flush_interval_seconds=2.0,
)
```

#### ELK Stack Integration

```python
config = SIEMConfig(
    format=SIEMFormat.JSON,
    endpoint_url="https://elasticsearch.example.com:9200/security-events/_doc",
    use_tls=True,
)
```

#### QRadar Integration (LEEF)

```python
config = SIEMConfig(
    format=SIEMFormat.LEEF,
    syslog_host="qradar.example.com",
    syslog_port=514,
)
```

#### ArcSight Integration (CEF)

```python
config = SIEMConfig(
    format=SIEMFormat.CEF,
    syslog_host="arcsight.example.com",
    syslog_port=514,
)
```

## Event Formats

### JSON Format

```json
{
  "event_type": "authentication_failure",
  "severity": "high",
  "message": "Failed login attempt",
  "timestamp": "2025-01-01T12:00:00.000000Z",
  "source": "runtime_security_scanner",
  "tenant_id": "tenant-123",
  "agent_id": "agent-456",
  "metadata": {"ip": "192.168.1.100"},
  "constitutional_hash": "cdd01ef066bc6cf2",
  "correlation_id": "abc123def456",
  "_siem": {
    "vendor": "ACGS-2",
    "product": "EnhancedAgentBus",
    "version": "2.4.0",
    "hostname": "server-01"
  }
}
```

### CEF Format (Common Event Format)

```
CEF:0|ACGS-2|EnhancedAgentBus|2.4.0|authentication_failure|Security Event: authentication_failure|7|msg=Failed login attempt src=server-01 rt=1704110400000 cat=authentication_failure cs1=tenant-123 cs1Label=TenantID cs2=agent-456 cs2Label=AgentID cs4=cdd01ef066bc6cf2 cs4Label=ConstitutionalHash
```

### LEEF Format (QRadar)

```
LEEF:2.0|ACGS-2|EnhancedAgentBus|2.4.0|authentication_failure|devTime=Jan 01 2025 12:00:00	cat=authentication_failure	sev=7	msg=Failed login attempt	src=server-01	tenantId=tenant-123	agentId=agent-456	constitutionalHash=cdd01ef066bc6cf2
```

### Syslog Format (RFC 5424)

```
<27>1 2025-01-01T12:00:00.000000Z server-01 EnhancedAgentBus - authentication_failure [acgs2@12345 severity="high" constitutionalHash="cdd01ef066bc6cf2" tenantId="tenant-123"] Failed login attempt
```

## Alert Thresholds

### Default Thresholds

| Event Type | Count | Window | Alert Level | Cooldown |
|------------|-------|--------|-------------|----------|
| Constitutional Hash Mismatch | 1 | 60s | CRITICAL | 60s |
| Prompt Injection Attempt | 3 | 300s | PAGE | 300s |
| Tenant Violation | 5 | 300s | ESCALATE | 600s |
| Rate Limit Exceeded | 50 | 60s | NOTIFY | 300s |
| Authentication Failure | 10 | 300s | PAGE | 600s |
| Authorization Failure | 5 | 300s | NOTIFY | 300s |
| Anomaly Detected | 3 | 600s | ESCALATE | 600s |
| Suspicious Pattern | 5 | 300s | NOTIFY | 300s |

### Custom Thresholds

```python
from enhanced_agent_bus import (
    AlertThreshold,
    AlertLevel,
    AlertManager,
    SecurityEventType,
)

custom_thresholds = [
    AlertThreshold(
        event_type=SecurityEventType.AUTHENTICATION_FAILURE,
        count_threshold=5,  # More sensitive
        time_window_seconds=120,
        alert_level=AlertLevel.CRITICAL,
        cooldown_seconds=300,
        escalation_multiplier=2,
    ),
]

manager = AlertManager(thresholds=custom_thresholds)
```

### Alert Levels

| Level | Value | Description |
|-------|-------|-------------|
| `NONE` | 0 | No alert |
| `LOG` | 1 | Log only |
| `NOTIFY` | 2 | Send notification (email, Slack) |
| `PAGE` | 3 | Page on-call engineer |
| `ESCALATE` | 4 | Escalate to security team |
| `CRITICAL` | 5 | Critical incident - all hands |

### Alert Callbacks

```python
async def alert_handler(level: AlertLevel, message: str, context: dict):
    if level.value >= AlertLevel.PAGE.value:
        await send_pagerduty_alert(message, context)
    elif level.value >= AlertLevel.NOTIFY.value:
        await send_slack_notification(message, context)

config = SIEMConfig(
    enable_alerting=True,
    alert_callback=alert_handler,
)
```

## Event Correlation

The SIEM integration includes automatic event correlation to detect attack patterns:

### Detected Patterns

| Pattern | Detection Criteria | Correlation ID Format |
|---------|-------------------|----------------------|
| Tenant Attack | 3+ HIGH/CRITICAL events from same tenant | `tenant_attack:<tenant_id>:<timestamp>` |
| Distributed Attack | 3+ same event type from different agents | `distributed_attack:<event_type>:<timestamp>` |
| Escalating Attack | 3+ escalating severity in 10 events | `escalating_attack:severity:<timestamp>` |

### Retrieving Correlated Events

```python
from enhanced_agent_bus import EventCorrelator

correlator = EventCorrelator(window_seconds=300)

# Add events
correlation_id = await correlator.add_event(event)

if correlation_id:
    # Get all related events
    related_events = correlator.get_correlated_events(correlation_id)
    print(f"Attack pattern detected: {len(related_events)} related events")
```

## Metrics and Monitoring

### Available Metrics

```python
metrics = siem.get_metrics()

# {
#     "events_logged": 1234,
#     "events_dropped": 0,
#     "events_shipped": 1200,
#     "alerts_triggered": 15,
#     "correlations_detected": 3,
#     "ship_failures": 0,
#     "queue_size": 34,
#     "batch_size": 10,
#     "running": True,
#     "alert_states": {...}
# }
```

### Prometheus Integration

```python
from prometheus_client import Gauge, Counter

siem_events_total = Counter('siem_events_total', 'Total SIEM events logged')
siem_alerts_total = Counter('siem_alerts_total', 'Total alerts triggered')
siem_queue_size = Gauge('siem_queue_size', 'Current event queue size')

async def update_prometheus_metrics():
    metrics = siem.get_metrics()
    siem_events_total._value._value = metrics["events_logged"]
    siem_alerts_total._value._value = metrics["alerts_triggered"]
    siem_queue_size.set(metrics["queue_size"])
```

## Best Practices

### 1. Configure Appropriate Thresholds

Start with default thresholds and adjust based on your environment's baseline activity.

### 2. Use Correlation IDs

Always check for correlation IDs in events to identify related attack patterns:

```python
if correlation_id:
    # This event is part of a larger attack pattern
    logger.warning(f"Correlated attack: {correlation_id}")
```

### 3. Implement Alert Callbacks

Connect alerts to your incident response workflow:

```python
async def alert_callback(level, message, context):
    if level == AlertLevel.CRITICAL:
        await create_incident(priority="P1", description=message)
        await page_security_team()
    elif level == AlertLevel.PAGE:
        await page_oncall()
```

### 4. Monitor Queue Health

Watch for dropped events indicating capacity issues:

```python
metrics = siem.get_metrics()
if metrics["events_dropped"] > 0:
    logger.error(f"SIEM events dropped: {metrics['events_dropped']}")
```

### 5. Use Fire-and-Forget Pattern

The SIEM integration is designed for minimal latency impact. Don't await results unless needed:

```python
# Good: Fire-and-forget
await log_security_event(...)

# Avoid: Waiting for confirmation (unless required)
# await siem.log_event_and_confirm(...)
```

## Troubleshooting

### Events Not Shipping

1. Check endpoint connectivity
2. Verify TLS certificates
3. Check queue metrics for dropped events
4. Review ship_failures count

### Alerts Not Triggering

1. Verify `enable_alerting=True`
2. Check threshold configuration
3. Review cooldown periods
4. Ensure callback is async-compatible

### High Latency Impact

1. Reduce batch_size
2. Increase flush_interval
3. Enable drop_on_overflow
4. Check endpoint response times

## Security Considerations

- All events include constitutional hash for integrity verification
- TLS is enabled by default for HTTP shipping
- Event data should be treated as sensitive (may contain PII)
- Implement proper access controls on SIEM endpoints
- Consider data retention policies for compliance

---

*Constitutional Hash: cdd01ef066bc6cf2*
*Enhanced Agent Bus SIEM Integration v1.0.0*
