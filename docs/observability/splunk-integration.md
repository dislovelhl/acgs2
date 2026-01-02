# ACGS-2 Splunk Integration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-02
> **Status**: Production Ready

This guide covers integrating ACGS-2 structured logging with Splunk Enterprise or Splunk Cloud for centralized log aggregation, search, and alerting.

## Overview

ACGS-2 services emit JSON-formatted structured logs with:
- **RFC 5424 severity levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Request tracing across distributed services
- **OpenTelemetry trace IDs**: Distributed tracing correlation
- **Service identifiers**: Multi-service filtering and dashboards

This integration enables enterprise DevOps teams to:
- Aggregate logs from all ACGS-2 microservices
- Trace requests end-to-end using correlation IDs
- Create real-time alerts for errors and anomalies
- Build operational dashboards for system health monitoring

## Prerequisites

- **Splunk Enterprise 8.x+** or **Splunk Cloud**
- **Splunk HTTP Event Collector (HEC)** enabled
- **ACGS-2 services** with structured logging enabled (see [Log Schema Reference](./log-schema.md))
- Network connectivity from ACGS-2 services to Splunk HEC endpoint

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   api_gateway   │    │ policy_registry │    │  audit_service  │
│   (JSON logs)   │    │   (JSON logs)   │    │   (JSON logs)   │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Log Forwarder       │
                    │  (Fluent Bit/Vector)  │
                    └───────────┬───────────┘
                                │ HTTPS (HEC)
                    ┌───────────▼───────────┐
                    │   Splunk Indexer      │
                    │   (acgs2_logs index)  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Splunk Search Head  │
                    │   (Dashboards/Alerts) │
                    └───────────────────────┘
```

## Step 1: Configure Splunk HTTP Event Collector (HEC)

### 1.1 Enable HEC in Splunk

1. Log in to Splunk Web as an administrator
2. Navigate to **Settings > Data Inputs > HTTP Event Collector**
3. Click **Global Settings** and enable HEC:
   - Set **All Tokens** to **Enabled**
   - Configure **HTTP Port Number** (default: 8088)
   - Enable **SSL** for production environments

### 1.2 Create HEC Token for ACGS-2

1. Click **New Token**
2. Configure the token:

| Field | Value | Description |
|-------|-------|-------------|
| **Name** | `acgs2-logging` | Descriptive token name |
| **Source name override** | `acgs2` | Optional: override source |
| **Description** | `ACGS-2 structured logging token` | Token purpose |
| **Output Group** | (select indexer) | Target indexer cluster |
| **Enable indexer acknowledgment** | Recommended for production | Ensures delivery |

3. Configure **Input Settings**:

| Field | Value |
|-------|-------|
| **Source type** | `_json` |
| **Index** | `acgs2_logs` (create if needed) |
| **App context** | `search` |

4. Click **Review > Submit** and copy the generated token

### 1.3 Verify HEC Endpoint

```bash
# Test HEC endpoint (replace with your values)
curl -k https://splunk.example.com:8088/services/collector/event \
  -H "Authorization: Splunk YOUR_HEC_TOKEN" \
  -d '{"event": "test", "sourcetype": "_json", "index": "acgs2_logs"}'

# Expected response:
# {"text":"Success","code":0}
```

## Step 2: Create Splunk Index for ACGS-2

### 2.1 Create Index via Splunk Web

1. Navigate to **Settings > Indexes**
2. Click **New Index**
3. Configure index settings:

| Field | Value | Recommendation |
|-------|-------|----------------|
| **Index Name** | `acgs2_logs` | Primary log storage |
| **Index Data Type** | Events | Standard event index |
| **Max Size of Entire Index** | 500 GB | Adjust based on log volume |
| **Searchable Time** | 90 days | Adjust for compliance requirements |
| **Max Hot/Warm DB Count** | Auto | Let Splunk manage |

### 2.2 Create Index via CLI (Alternative)

```bash
# Create index using Splunk CLI
/opt/splunk/bin/splunk add index acgs2_logs \
  -maxTotalDataSizeMB 512000 \
  -frozenTimePeriodInSecs 7776000 \
  -auth admin:password
```

### 2.3 Index Configuration File

For advanced deployments, add to `indexes.conf`:

```ini
# /opt/splunk/etc/system/local/indexes.conf
[acgs2_logs]
homePath   = $SPLUNK_DB/acgs2_logs/db
coldPath   = $SPLUNK_DB/acgs2_logs/colddb
thawedPath = $SPLUNK_DB/acgs2_logs/thaweddb
maxTotalDataSizeMB = 512000
frozenTimePeriodInSecs = 7776000
```

## Step 3: Configure Log Forwarding

Choose one of the following options based on your deployment:

### Option A: Fluent Bit (Recommended for Kubernetes)

```yaml
# fluent-bit-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: acgs2
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Daemon        Off
        Log_Level     info
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Path              /var/log/containers/acgs2-*.log
        Parser            docker
        Tag               acgs2.*
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On

    [FILTER]
        Name              parser
        Match             acgs2.*
        Key_Name          log
        Parser            json
        Reserve_Data      On

    [OUTPUT]
        Name              splunk
        Match             acgs2.*
        Host              splunk.example.com
        Port              8088
        TLS               On
        TLS.Verify        On
        Splunk_Token      YOUR_HEC_TOKEN
        Splunk_Send_Raw   Off
        Event_Index       acgs2_logs
        Event_Sourcetype  _json
        Event_Source      acgs2

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On

    [PARSER]
        Name        json
        Format      json
```

### Option B: Vector (High-Performance Alternative)

```toml
# vector.toml
[sources.acgs2_logs]
type = "file"
include = ["/var/log/acgs2/*.log"]
read_from = "beginning"

[transforms.parse_json]
type = "remap"
inputs = ["acgs2_logs"]
source = '''
. = parse_json!(.message)
'''

[sinks.splunk_hec]
type = "splunk_hec_logs"
inputs = ["parse_json"]
endpoint = "https://splunk.example.com:8088"
token = "${SPLUNK_HEC_TOKEN}"
index = "acgs2_logs"
sourcetype = "_json"
compression = "gzip"

[sinks.splunk_hec.encoding]
codec = "json"

[sinks.splunk_hec.tls]
verify_certificate = true
```

### Option C: Direct HEC from Python Services

For development or direct integration, configure services to send logs directly to HEC:

```python
# acgs2-core/shared/logging_splunk.py
import os
import requests
import structlog

SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "https://splunk.example.com:8088/services/collector/event")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN")

def splunk_processor(logger, method_name, event_dict):
    """Structlog processor to forward logs to Splunk HEC."""
    if SPLUNK_HEC_TOKEN:
        try:
            requests.post(
                SPLUNK_HEC_URL,
                headers={"Authorization": f"Splunk {SPLUNK_HEC_TOKEN}"},
                json={"event": event_dict, "sourcetype": "_json", "index": "acgs2_logs"},
                timeout=1.0,  # Non-blocking timeout
                verify=True
            )
        except requests.RequestException:
            pass  # Don't fail logging if Splunk is unavailable
    return event_dict
```

## Step 4: Field Extraction Configuration

### 4.1 Automatic JSON Field Extraction

ACGS-2 logs are JSON-formatted, so Splunk automatically extracts fields. Verify extraction:

```spl
index=acgs2_logs sourcetype=_json
| head 10
| table _time, level, event, service, correlation_id, trace_id
```

### 4.2 Create Field Aliases (Optional)

For compatibility with existing dashboards, create aliases in `props.conf`:

```ini
# /opt/splunk/etc/apps/acgs2/local/props.conf
[acgs2:logs]
SHOULD_LINEMERGE = false
KV_MODE = json
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%f%Z
TIME_PREFIX = "timestamp":"
MAX_TIMESTAMP_LOOKAHEAD = 30

# Field aliases for compatibility
FIELDALIAS-severity = level AS severity
FIELDALIAS-request_id = correlation_id AS request_id
FIELDALIAS-span_id = trace_id AS span_id
```

### 4.3 ACGS-2 Log Field Reference

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | ISO 8601 | Event timestamp (UTC) | `2026-01-02T14:30:00.123456Z` |
| `level` | string | RFC 5424 severity | `INFO`, `ERROR`, `WARNING` |
| `event` | string | Event name/message | `request_received` |
| `service` | string | Source service | `api_gateway` |
| `correlation_id` | UUID | Request correlation ID | `550e8400-e29b-41d4-a716-446655440000` |
| `trace_id` | hex | OpenTelemetry trace ID | `4bf92f3577b34da6a3ce929d0e0e4736` |
| `logger` | string | Logger name (module) | `app.main` |
| `exc_info` | object | Exception details | `{"type": "ValueError", ...}` |

## Step 5: Sample Search Queries

### 5.1 Basic Searches

```spl
# All ACGS-2 logs in last hour
index=acgs2_logs sourcetype=_json earliest=-1h

# Errors only
index=acgs2_logs level=ERROR earliest=-1h

# Specific service logs
index=acgs2_logs service="api_gateway" earliest=-1h

# Logs with specific correlation ID (request tracing)
index=acgs2_logs correlation_id="550e8400-e29b-41d4-a716-446655440000"
```

### 5.2 Request Flow Tracing

```spl
# Trace a request across all services using correlation ID
index=acgs2_logs correlation_id="YOUR_CORRELATION_ID"
| sort _time
| table _time, service, level, event, duration_ms

# Find related logs using OpenTelemetry trace ID
index=acgs2_logs trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
| sort _time
| table _time, service, event, correlation_id
```

### 5.3 Error Analysis

```spl
# Error count by service (last 24h)
index=acgs2_logs level=ERROR earliest=-24h
| stats count by service
| sort -count

# Top error events
index=acgs2_logs level=ERROR earliest=-24h
| stats count by event
| sort -count
| head 10

# Error rate over time
index=acgs2_logs earliest=-24h
| timechart span=1h count(eval(level="ERROR")) AS errors, count AS total
| eval error_rate = round((errors/total)*100, 2)
```

### 5.4 Performance Analysis

```spl
# Average request duration by endpoint
index=acgs2_logs service="api_gateway" duration_ms=* earliest=-1h
| stats avg(duration_ms) as avg_duration, p95(duration_ms) as p95_duration by endpoint
| sort -avg_duration

# Slow requests (>500ms)
index=acgs2_logs duration_ms>500 earliest=-1h
| table _time, service, event, duration_ms, correlation_id
| sort -duration_ms
```

### 5.5 Service Health Overview

```spl
# Service health summary
index=acgs2_logs earliest=-1h
| stats
    count as total_logs,
    count(eval(level="ERROR")) as errors,
    count(eval(level="WARNING")) as warnings,
    dc(correlation_id) as unique_requests
    by service
| eval error_rate = round((errors/total_logs)*100, 2)
| table service, total_logs, errors, warnings, error_rate, unique_requests
| sort -error_rate
```

## Step 6: Alert Configuration

### 6.1 High Error Rate Alert

Create a saved search with alerting:

```spl
# Alert: High error rate (>5% in 5 minutes)
index=acgs2_logs earliest=-5m
| stats count(eval(level="ERROR")) as errors, count as total by service
| eval error_rate = (errors/total)*100
| where error_rate > 5
| table service, errors, total, error_rate
```

**Alert Configuration:**
- **Trigger condition**: Number of results > 0
- **Trigger alert when**: Per-Result
- **Throttle**: 15 minutes

### 6.2 Service Down Alert

```spl
# Alert: No logs from service in 5 minutes
| tstats count where index=acgs2_logs earliest=-5m by service
| append [| makeresults | eval service="api_gateway"]
| append [| makeresults | eval service="policy_registry"]
| append [| makeresults | eval service="audit_service"]
| append [| makeresults | eval service="enhanced_agent_bus"]
| stats sum(count) as log_count by service
| where log_count=0 OR isnull(log_count)
```

### 6.3 Critical Error Alert (Immediate)

```spl
# Alert: Critical/Emergency level logs
index=acgs2_logs (level="CRITICAL" OR level="EMERGENCY") earliest=-1m
| table _time, service, event, correlation_id, exc_info
```

**Alert Configuration:**
- **Trigger condition**: Number of results > 0
- **Trigger alert when**: Once
- **Action**: Email, PagerDuty, Slack

### 6.4 Correlation ID Timeout Alert

```spl
# Alert: Requests taking >30 seconds (potential timeout)
index=acgs2_logs earliest=-5m
| transaction correlation_id maxspan=30s
| where duration > 30
| table correlation_id, service, duration, eventcount
```

## Step 7: Dashboard Configuration

### 7.1 Import ACGS-2 Dashboard

Save the following as `acgs2_overview_dashboard.xml` and import via **Settings > Knowledge > User Interface > Views > Create Dashboard**:

```xml
<dashboard version="1.1" theme="dark">
  <label>ACGS-2 Observability Overview</label>
  <description>Real-time monitoring of ACGS-2 microservices</description>

  <row>
    <panel>
      <title>Total Log Volume (24h)</title>
      <single>
        <search>
          <query>index=acgs2_logs earliest=-24h | stats count</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="colorMode">block</option>
        <option name="drilldown">none</option>
        <option name="rangeColors">["0x53A051","0xF8BE34","0xF1813F","0xDC4E41"]</option>
        <option name="rangeValues">[100000,500000,1000000]</option>
        <option name="useColors">1</option>
      </single>
    </panel>
    <panel>
      <title>Error Rate (24h)</title>
      <single>
        <search>
          <query>index=acgs2_logs earliest=-24h
| stats count(eval(level="ERROR")) as errors, count as total
| eval rate=round((errors/total)*100,2)
| fields rate</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="colorMode">block</option>
        <option name="drilldown">none</option>
        <option name="rangeColors">["0x53A051","0xF8BE34","0xF1813F","0xDC4E41"]</option>
        <option name="rangeValues">[1,5,10]</option>
        <option name="unit">%</option>
        <option name="useColors">1</option>
      </single>
    </panel>
    <panel>
      <title>Unique Requests (24h)</title>
      <single>
        <search>
          <query>index=acgs2_logs earliest=-24h | stats dc(correlation_id)</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="colorMode">block</option>
        <option name="drilldown">none</option>
      </single>
    </panel>
  </row>

  <row>
    <panel>
      <title>Log Volume by Service</title>
      <chart>
        <search>
          <query>index=acgs2_logs earliest=-24h
| timechart span=1h count by service</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">area</option>
        <option name="charting.chart.stackMode">stacked</option>
        <option name="charting.legend.placement">bottom</option>
      </chart>
    </panel>
  </row>

  <row>
    <panel>
      <title>Error Trend</title>
      <chart>
        <search>
          <query>index=acgs2_logs level=ERROR earliest=-24h
| timechart span=15m count by service</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">line</option>
        <option name="charting.legend.placement">bottom</option>
      </chart>
    </panel>
    <panel>
      <title>Top Error Events</title>
      <table>
        <search>
          <query>index=acgs2_logs level=ERROR earliest=-24h
| stats count by event, service
| sort -count
| head 10</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="drilldown">cell</option>
      </table>
    </panel>
  </row>

  <row>
    <panel>
      <title>Service Health Matrix</title>
      <table>
        <search>
          <query>index=acgs2_logs earliest=-1h
| stats
    count as total,
    count(eval(level="ERROR")) as errors,
    count(eval(level="WARNING")) as warnings,
    dc(correlation_id) as requests
    by service
| eval error_rate=round((errors/total)*100,2)
| eval status=case(error_rate>10,"CRITICAL",error_rate>5,"WARNING",1=1,"HEALTHY")
| table service, status, total, errors, warnings, error_rate, requests
| sort -error_rate</query>
          <earliest>-1h</earliest>
          <latest>now</latest>
        </search>
        <option name="drilldown">cell</option>
        <format type="color" field="status">
          <colorPalette type="map">{"HEALTHY":#53A051,"WARNING":#F8BE34,"CRITICAL":#DC4E41}</colorPalette>
        </format>
      </table>
    </panel>
  </row>

  <row>
    <panel>
      <title>Recent Errors</title>
      <table>
        <search>
          <query>index=acgs2_logs level=ERROR earliest=-1h
| table _time, service, event, correlation_id
| sort -_time
| head 20</query>
          <earliest>-1h</earliest>
          <latest>now</latest>
        </search>
        <option name="drilldown">cell</option>
      </table>
    </panel>
  </row>
</dashboard>
```

### 7.2 Request Tracing Dashboard

Create a dashboard for end-to-end request tracing:

```xml
<form version="1.1" theme="dark">
  <label>ACGS-2 Request Tracing</label>
  <description>Trace requests across services using correlation ID</description>

  <fieldset submitButton="true">
    <input type="text" token="correlation_id">
      <label>Correlation ID</label>
      <default>*</default>
    </input>
    <input type="time" token="time">
      <label>Time Range</label>
      <default>
        <earliest>-24h</earliest>
        <latest>now</latest>
      </default>
    </input>
  </fieldset>

  <row>
    <panel>
      <title>Request Timeline</title>
      <table>
        <search>
          <query>index=acgs2_logs correlation_id="$correlation_id$"
| sort _time
| table _time, service, level, event, duration_ms
| rename _time as "Timestamp", service as "Service", level as "Level", event as "Event", duration_ms as "Duration (ms)"</query>
          <earliest>$time.earliest$</earliest>
          <latest>$time.latest$</latest>
        </search>
        <option name="drilldown">none</option>
        <format type="color" field="Level">
          <colorPalette type="map">{"INFO":#53A051,"WARNING":#F8BE34,"ERROR":#DC4E41,"DEBUG":#999999}</colorPalette>
        </format>
      </table>
    </panel>
  </row>

  <row>
    <panel>
      <title>Services Involved</title>
      <chart>
        <search>
          <query>index=acgs2_logs correlation_id="$correlation_id$"
| stats count by service</query>
          <earliest>$time.earliest$</earliest>
          <latest>$time.latest$</latest>
        </search>
        <option name="charting.chart">pie</option>
      </chart>
    </panel>
    <panel>
      <title>Full Log Details</title>
      <event>
        <search>
          <query>index=acgs2_logs correlation_id="$correlation_id$"</query>
          <earliest>$time.earliest$</earliest>
          <latest>$time.latest$</latest>
        </search>
        <option name="list.drilldown">full</option>
      </event>
    </panel>
  </row>
</form>
```

## Step 8: Performance Tuning

### 8.1 HEC Tuning

For high-volume deployments, tune HEC settings:

```ini
# /opt/splunk/etc/system/local/inputs.conf
[http]
disabled = 0
enableSSL = 1
port = 8088
maxThreads = 0
maxSockets = 0
dedicatedIoThreads = 2

[http://acgs2-logging]
token = YOUR_HEC_TOKEN
indexes = acgs2_logs
sourcetype = _json
```

### 8.2 Index Tuning for High Volume

```ini
# /opt/splunk/etc/system/local/indexes.conf
[acgs2_logs]
# Increase bucket sizes for high volume
maxHotSpanSecs = 86400
maxHotBuckets = 10
maxDataSize = auto_high_volume

# Parallel search optimization
parallelIngestionPipelines = 2
```

### 8.3 Recommended Log Forwarder Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Batch size** | 50-100 events | Balance latency vs. throughput |
| **Batch timeout** | 5 seconds | Ensure timely delivery |
| **Compression** | gzip | Reduce network bandwidth |
| **Retry count** | 3 | Handle transient failures |
| **Buffer size** | 10 MB | Survive short outages |

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No logs in index | HEC token disabled | Verify token status in Splunk Web |
| Missing fields | JSON parsing failure | Check `sourcetype=_json` is set |
| Duplicate events | Multiple forwarders | Use `dedup` or configure single forwarder |
| High latency | Network issues | Enable gzip compression, increase batch size |
| Index limit reached | Retention policy | Increase index size or reduce retention |

### Verify Log Flow

```bash
# Check HEC health
curl -k https://splunk.example.com:8088/services/collector/health \
  -H "Authorization: Splunk YOUR_HEC_TOKEN"

# Check index stats
curl -k https://splunk.example.com:8089/services/data/indexes/acgs2_logs \
  -u admin:password
```

### Debug Search

```spl
# Check recent log ingestion
index=acgs2_logs earliest=-5m
| stats count by source, sourcetype, host

# Verify JSON field extraction
index=acgs2_logs earliest=-1h
| head 1
| fields *
```

## Security Considerations

1. **Use HTTPS** for all HEC connections in production
2. **Rotate HEC tokens** periodically (every 90 days recommended)
3. **Restrict HEC access** using Splunk roles and capabilities
4. **Enable indexer acknowledgment** for delivery guarantee
5. **Monitor HEC token usage** for anomalies

## Environment Variables

Configure ACGS-2 services with these environment variables for Splunk integration:

| Variable | Description | Example |
|----------|-------------|---------|
| `SPLUNK_HEC_URL` | HEC endpoint URL | `https://splunk.example.com:8088/services/collector/event` |
| `SPLUNK_HEC_TOKEN` | HEC authentication token | `550e8400-e29b-41d4-a716-446655440000` |
| `SPLUNK_INDEX` | Target index name | `acgs2_logs` |
| `SPLUNK_VERIFY_SSL` | SSL verification | `true` |

## Next Steps

- [ELK Stack Integration](./elk-integration.md)
- [Datadog Integration](./datadog-integration.md)
- [Log Schema Reference](./log-schema.md)
- [Development Guide](../DEVELOPMENT.md)

---

*Constitutional Hash: cdd01ef066bc6cf2*
