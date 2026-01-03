# ACGS-2 Datadog Integration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-02
> **Status**: Production Ready

This guide covers integrating ACGS-2 structured logging with Datadog for centralized log management, APM correlation, and real-time monitoring.

## Overview

ACGS-2 services emit JSON-formatted structured logs with:
- **RFC 5424 severity levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Request tracing across distributed services
- **OpenTelemetry trace IDs**: Distributed tracing correlation
- **Service identifiers**: Multi-service filtering and dashboards

This integration enables enterprise DevOps teams to:
- Aggregate logs from all ACGS-2 microservices
- Trace requests end-to-end using correlation IDs
- Correlate logs with APM traces and infrastructure metrics
- Create real-time alerts and SLOs based on log data
- Build operational dashboards for system health monitoring

## Prerequisites

- **Datadog account** (any tier - Essentials, Pro, or Enterprise)
- **Datadog Agent 7.x+** installed on hosts or Kubernetes cluster
- **ACGS-2 services** with structured logging enabled (see [Log Schema Reference](./log-schema.md))
- API and Application keys from Datadog

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
                    │    Datadog Agent      │
                    │   (Log Collection)    │
                    └───────────┬───────────┘
                                │ HTTPS (api.datadoghq.com)
                    ┌───────────▼───────────┐
                    │   Datadog Platform    │
                    │  (Logs, APM, Metrics) │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Datadog Web UI      │
                    │  (Dashboards/Alerts)  │
                    └───────────────────────┘
```

## Step 1: Install and Configure Datadog Agent

### 1.1 Install Datadog Agent

**Linux (Ubuntu/Debian):**

```bash
DD_API_KEY=<YOUR_API_KEY> DD_SITE="datadoghq.com" bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"
```

**Docker:**

```bash
docker run -d --name dd-agent \
  -e DD_API_KEY=<YOUR_API_KEY> \
  -e DD_SITE="datadoghq.com" \
  -e DD_LOGS_ENABLED=true \
  -e DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true \
  -e DD_APM_ENABLED=true \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -v /var/log/acgs2:/var/log/acgs2:ro \
  gcr.io/datadoghq/agent:7
```

**Kubernetes (Helm):**

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update

helm install datadog-agent datadog/datadog \
  --set datadog.apiKey=<YOUR_API_KEY> \
  --set datadog.site="datadoghq.com" \
  --set datadog.logs.enabled=true \
  --set datadog.logs.containerCollectAll=true \
  --set datadog.apm.enabled=true \
  --namespace datadog \
  --create-namespace
```

### 1.2 Enable Log Collection

Edit the Datadog Agent configuration:

```yaml
# /etc/datadog-agent/datadog.yaml
api_key: <YOUR_API_KEY>
site: datadoghq.com

# Enable log collection
logs_enabled: true

# Enable APM for trace correlation
apm_config:
  enabled: true
  env: production

# Process and container collection
process_config:
  enabled: true
```

### 1.3 Verify Agent Installation

```bash
# Check agent status
sudo datadog-agent status

# Verify log collection is enabled
sudo datadog-agent status | grep -A5 "Logs Agent"

# Expected output:
# Logs Agent
# ==========
#   Logs Agent is running
```

## Step 2: Configure Log Forwarding

### Option A: File-based Collection (Recommended for VMs)

Create a log configuration file for ACGS-2 services:

```yaml
# /etc/datadog-agent/conf.d/acgs2.d/conf.yaml
logs:
  # API Gateway logs
  - type: file
    path: /var/log/acgs2/api_gateway/*.log
    service: api_gateway
    source: acgs2
    sourcecategory: python
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"

  # Policy Registry logs
  - type: file
    path: /var/log/acgs2/policy_registry/*.log
    service: policy_registry
    source: acgs2
    sourcecategory: python
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"

  # Audit Service logs
  - type: file
    path: /var/log/acgs2/audit_service/*.log
    service: audit_service
    source: acgs2
    sourcecategory: python
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"

  # Enhanced Agent Bus logs
  - type: file
    path: /var/log/acgs2/enhanced_agent_bus/*.log
    service: enhanced_agent_bus
    source: acgs2
    sourcecategory: python
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"

  # Claude Flow CLI logs (TypeScript)
  - type: file
    path: /var/log/acgs2/claude-flow/*.log
    service: claude-flow
    source: acgs2
    sourcecategory: nodejs
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"

  # Neural MCP logs (TypeScript)
  - type: file
    path: /var/log/acgs2/neural-mcp/*.log
    service: acgs2-neural-mcp
    source: acgs2
    sourcecategory: nodejs
    tags:
      - "env:production"
      - "team:platform"
      - "app:acgs2"
```

Restart the agent after configuration:

```bash
sudo systemctl restart datadog-agent
```

### Option B: Docker Container Collection (Recommended for Docker/Kubernetes)

Add labels to ACGS-2 service containers:

```yaml
# docker-compose.yaml
version: "3.8"

services:
  api_gateway:
    image: acgs2/api_gateway:latest
    labels:
      com.datadoghq.ad.logs: '[{"source": "acgs2", "service": "api_gateway", "tags": ["env:production", "app:acgs2"]}]'
    environment:
      - DD_SERVICE=api_gateway
      - DD_ENV=production
      - DD_VERSION=1.0.0
      - DD_LOGS_INJECTION=true

  policy_registry:
    image: acgs2/policy_registry:latest
    labels:
      com.datadoghq.ad.logs: '[{"source": "acgs2", "service": "policy_registry", "tags": ["env:production", "app:acgs2"]}]'
    environment:
      - DD_SERVICE=policy_registry
      - DD_ENV=production
      - DD_VERSION=1.0.0
      - DD_LOGS_INJECTION=true

  audit_service:
    image: acgs2/audit_service:latest
    labels:
      com.datadoghq.ad.logs: '[{"source": "acgs2", "service": "audit_service", "tags": ["env:production", "app:acgs2"]}]'
    environment:
      - DD_SERVICE=audit_service
      - DD_ENV=production
      - DD_VERSION=1.0.0
      - DD_LOGS_INJECTION=true

  enhanced_agent_bus:
    image: acgs2/enhanced_agent_bus:latest
    labels:
      com.datadoghq.ad.logs: '[{"source": "acgs2", "service": "enhanced_agent_bus", "tags": ["env:production", "app:acgs2"]}]'
    environment:
      - DD_SERVICE=enhanced_agent_bus
      - DD_ENV=production
      - DD_VERSION=1.0.0
      - DD_LOGS_INJECTION=true
```

### Option C: Kubernetes Pod Annotations

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: acgs2
spec:
  template:
    metadata:
      annotations:
        ad.datadoghq.com/api-gateway.logs: |
          [{
            "source": "acgs2",
            "service": "api_gateway",
            "tags": ["env:production", "app:acgs2", "team:platform"]
          }]
      labels:
        tags.datadoghq.com/env: production
        tags.datadoghq.com/service: api_gateway
        tags.datadoghq.com/version: "1.0.0"
    spec:
      containers:
        - name: api-gateway
          image: acgs2/api_gateway:latest
          env:
            - name: DD_SERVICE
              value: api_gateway
            - name: DD_ENV
              value: production
            - name: DD_VERSION
              value: "1.0.0"
            - name: DD_LOGS_INJECTION
              value: "true"
            - name: DD_TRACE_AGENT_URL
              value: "http://datadog-agent.datadog.svc.cluster.local:8126"
```

### Option D: Direct HTTP Submission

For development or direct integration without the Datadog Agent:

```python
# acgs2-core/shared/logging_datadog.py
"""Direct Datadog log submission processor for structlog."""
import os
import json
import requests
import structlog

DD_API_KEY = os.getenv("DD_API_KEY")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_LOG_URL = f"https://http-intake.logs.{DD_SITE}/api/v2/logs"
DD_SERVICE = os.getenv("DD_SERVICE", "acgs2")
DD_ENV = os.getenv("DD_ENV", "development")

def datadog_processor(logger, method_name, event_dict):
    """Structlog processor to forward logs directly to Datadog."""
    if DD_API_KEY:
        try:
            # Map structlog level to Datadog status
            level_map = {
                "debug": "debug",
                "info": "info",
                "warning": "warning",
                "error": "error",
                "critical": "critical",
            }

            log_entry = {
                "ddsource": "acgs2",
                "ddtags": f"env:{DD_ENV},service:{DD_SERVICE}",
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "service": event_dict.get("service", DD_SERVICE),
                "status": level_map.get(event_dict.get("level", "info"), "info"),
                "message": json.dumps(event_dict),
            }

            requests.post(
                DD_LOG_URL,
                headers={
                    "Content-Type": "application/json",
                    "DD-API-KEY": DD_API_KEY,
                },
                json=[log_entry],
                timeout=1.0,  # Non-blocking timeout
            )
        except requests.RequestException:
            pass  # Don't fail logging if Datadog is unavailable

    return event_dict
```

## Step 3: Log Processing Pipeline

### 3.1 Create Log Pipeline

Navigate to **Logs > Configuration > Pipelines** in Datadog and create a new pipeline:

1. Click **New Pipeline**
2. Configure:
   - **Name**: `ACGS-2 Logs`
   - **Filter**: `source:acgs2`
   - **Description**: `Processing pipeline for ACGS-2 structured logs`

### 3.2 Add JSON Parser Processor

Add a processor to extract JSON fields:

1. In the ACGS-2 pipeline, click **Add Processor**
2. Select **Grok Parser** and configure:

```
# Name: JSON Field Extraction
# Filter: *

# Define parsing rules:
json_parser %{data::json}
```

Alternatively, use the **JSON Parser** processor type if logs are already JSON-formatted.

### 3.3 Add Attribute Remapper Processors

Create remappers for standard ACGS-2 fields:

**Timestamp Remapper:**
```
Name: Timestamp Remapper
Source attribute: timestamp
Target attribute: @timestamp
Preserve source: true
```

**Service Remapper:**
```
Name: Service Remapper
Source attribute: service
Target attribute: service
Preserve source: true
```

**Status Remapper:**
```
Name: Status Remapper
Source attribute: level
Target attribute: status
Preserve source: true
```

### 3.4 Add Trace ID Remapper

Map OpenTelemetry trace IDs for APM correlation:

```
Name: Trace ID Remapper
Source attribute: trace_id
Target attribute: dd.trace_id
Preserve source: true
```

### 3.5 Complete Pipeline Configuration (YAML Export)

```yaml
# Datadog Log Pipeline Configuration
name: ACGS-2 Logs
filter:
  query: "source:acgs2"
processors:
  - type: grok-parser
    name: JSON Parser
    enabled: true
    source: message
    samples:
      - '{"timestamp": "2026-01-02T14:30:00.123456Z", "level": "INFO", "event": "request_received", "service": "api_gateway"}'
    grok:
      supportRules: ""
      matchRules: "json_parse %{data::json}"

  - type: date-remapper
    name: Timestamp Remapper
    enabled: true
    sources:
      - timestamp

  - type: status-remapper
    name: Log Level to Status
    enabled: true
    sources:
      - level

  - type: service-remapper
    name: Service Remapper
    enabled: true
    sources:
      - service

  - type: trace-id-remapper
    name: OpenTelemetry Trace Correlation
    enabled: true
    sources:
      - trace_id

  - type: attribute-remapper
    name: Correlation ID
    enabled: true
    sources:
      - correlation_id
    target: correlation_id
    preserveSource: true
    targetType: attribute
```

## Step 4: Facet Configuration

### 4.1 Create Standard Facets

Navigate to **Logs > Facets** and create the following facets for ACGS-2 logs:

| Facet Name | Field Path | Type | Group |
|------------|------------|------|-------|
| **Service** | `@service` | string | ACGS-2 |
| **Level** | `@level` | string | ACGS-2 |
| **Event** | `@event` | string | ACGS-2 |
| **Correlation ID** | `@correlation_id` | string | ACGS-2 |
| **Trace ID** | `@trace_id` | string | ACGS-2 |
| **Environment** | `@environment` | string | ACGS-2 |
| **Tenant ID** | `@tenant_id` | string | ACGS-2 |
| **Endpoint** | `@endpoint` | string | ACGS-2 |
| **Method** | `@method` | string | ACGS-2 |
| **Status Code** | `@status_code` | integer | ACGS-2 |
| **Duration (ms)** | `@duration_ms` | double | ACGS-2 |
| **Error Type** | `@error_type` | string | ACGS-2 |
| **User ID** | `@user_id` | string | ACGS-2 |
| **Logger** | `@logger` | string | ACGS-2 |
| **Host** | `@host` | string | ACGS-2 |

### 4.2 Create Facets via API

```bash
# Create facets programmatically using Datadog API
curl -X POST "https://api.datadoghq.com/api/v1/logs/config/indexes" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -d '{
    "name": "acgs2-logs",
    "filter": {
      "query": "source:acgs2"
    }
  }'
```

### 4.3 Standard Measures

Create measures for numeric fields:

| Measure Name | Field Path | Type | Unit |
|--------------|------------|------|------|
| **Request Duration** | `@duration_ms` | double | milliseconds |
| **Status Code** | `@status_code` | integer | - |
| **Error Count** | `@error_count` | integer | - |

### 4.4 ACGS-2 Log Field Reference

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

## Step 5: Sample Log Queries

### 5.1 Basic Queries

```
# All ACGS-2 logs
source:acgs2

# Errors only
source:acgs2 status:error

# Specific service logs
source:acgs2 service:api_gateway

# Logs with specific correlation ID (request tracing)
source:acgs2 @correlation_id:550e8400-e29b-41d4-a716-446655440000

# Multiple services
source:acgs2 service:(api_gateway OR policy_registry)

# Exclude debug logs
source:acgs2 -status:debug
```

### 5.2 Request Flow Tracing

```
# Trace a request across all services using correlation ID
source:acgs2 @correlation_id:"YOUR_CORRELATION_ID"

# Find related logs using OpenTelemetry trace ID
source:acgs2 @trace_id:4bf92f3577b34da6a3ce929d0e0e4736

# All requests to a specific endpoint
source:acgs2 @endpoint:"/api/v1/policies"

# Slow requests (>500ms)
source:acgs2 @duration_ms:>500
```

### 5.3 Error Analysis

```
# Error count by service
source:acgs2 status:error | stats count by service

# Top error events
source:acgs2 status:error | top @event

# Errors with stack traces
source:acgs2 status:error @exc_info:*

# Critical errors only
source:acgs2 status:(error OR critical)
```

### 5.4 Performance Analysis

```
# Average request duration by service
source:acgs2 @duration_ms:* | stats avg(@duration_ms) by service

# P95 latency by endpoint
source:acgs2 @duration_ms:* | percentile(@duration_ms, 0.95) by @endpoint

# Requests over time
source:acgs2 | timeseries count by service
```

### 5.5 Service Health Overview

```
# Service health summary
source:acgs2 | stats count, count(status:error) as errors, dc(@correlation_id) as unique_requests by service

# Log volume trend
source:acgs2 | timeseries count by service .rollup(sum, 60)

# Error rate calculation
source:acgs2 | stats count(status:error) / count * 100 as error_rate by service
```

## Step 6: Monitor Configuration

### 6.1 High Error Rate Monitor

Create a log-based monitor for high error rates:

**Monitor Configuration:**

```yaml
Name: ACGS-2 High Error Rate
Type: Logs
Query: |
  source:acgs2 status:error
Metric: count
Group By: service
Alert Threshold:
  - Warning: > 10 errors in 5 minutes
  - Alert: > 50 errors in 5 minutes
Evaluation Window: last_5m
Notification:
  Message: |
    {{#is_alert}}
    🚨 ACGS-2 High Error Rate Alert

    Service: {{service.name}}
    Error Count: {{value}}
    Time: {{last_triggered_at}}

    View logs: https://app.datadoghq.com/logs?query=source:acgs2%20status:error%20service:{{service.name}}
    {{/is_alert}}

    {{#is_warning}}
    ⚠️ ACGS-2 Error Rate Warning

    Service: {{service.name}}
    Error Count: {{value}}
    {{/is_warning}}
Tags:
  - env:production
  - team:platform
  - app:acgs2
```

### 6.2 Service Down Monitor

```yaml
Name: ACGS-2 Service Down
Type: Logs
Query: |
  source:acgs2
Metric: count
Group By: service
Alert Threshold:
  - Alert: < 1 in 5 minutes
Evaluation Window: last_5m
Notification:
  Message: |
    🔴 ACGS-2 Service Down Alert

    Service: {{service.name}}
    No logs received in the last 5 minutes.

    This may indicate:
    - Service crash
    - Network connectivity issue
    - Log forwarding failure

    Check service status immediately.
Tags:
  - env:production
  - severity:critical
  - team:platform
```

### 6.3 Critical Error Monitor (Immediate)

```yaml
Name: ACGS-2 Critical Errors
Type: Logs
Query: |
  source:acgs2 @level:(CRITICAL OR EMERGENCY)
Metric: count
Alert Threshold:
  - Alert: > 0 in 1 minute
Evaluation Window: last_1m
Notification:
  Message: |
    🚨🚨 CRITICAL ERROR DETECTED 🚨🚨

    Service: {{service.name}}
    Event: {{event}}
    Correlation ID: {{correlation_id}}

    Immediate attention required!

    View details: https://app.datadoghq.com/logs?query=source:acgs2%20@correlation_id:{{correlation_id}}
Priority: P1
Tags:
  - env:production
  - severity:critical
  - team:platform
  - oncall:pagerduty
```

### 6.4 Slow Request Monitor

```yaml
Name: ACGS-2 Slow Requests
Type: Metric
Query: |
  avg:acgs2.request.duration{*} by {service,endpoint}
Alert Threshold:
  - Warning: > 500ms
  - Alert: > 1000ms
Evaluation Window: last_5m
Notification:
  Message: |
    ⏱️ Slow Request Alert

    Service: {{service.name}}
    Endpoint: {{endpoint.name}}
    Average Duration: {{value}}ms

    Investigate performance degradation.
Tags:
  - env:production
  - team:platform
```

### 6.5 Anomaly Detection Monitor

```yaml
Name: ACGS-2 Error Rate Anomaly
Type: Anomaly
Query: |
  sum:acgs2.errors{*} by {service}.as_rate()
Algorithm: agile
Alert Threshold:
  - Alert: 3 deviations above normal
Evaluation Window: last_1h
Recovery Window: last_15m
Notification:
  Message: |
    📈 Error Rate Anomaly Detected

    Service: {{service.name}}
    Current Rate: {{value}}
    Expected Range: {{threshold}}

    Unusual error pattern detected. Investigate recent deployments or infrastructure changes.
Tags:
  - env:production
  - team:platform
```

### 6.6 Correlation ID Timeout Monitor

```yaml
Name: ACGS-2 Request Timeout
Type: Logs
Query: |
  source:acgs2 @duration_ms:>30000
Metric: count
Group By: correlation_id
Alert Threshold:
  - Alert: > 0 in 5 minutes
Evaluation Window: last_5m
Notification:
  Message: |
    ⏰ Request Timeout Alert

    Correlation ID: {{correlation_id}}
    Duration: {{duration_ms}}ms

    Request exceeded 30-second threshold.

    Trace request: https://app.datadoghq.com/logs?query=source:acgs2%20@correlation_id:{{correlation_id}}
Tags:
  - env:production
  - severity:warning
```

## Step 7: Dashboard Configuration

### 7.1 Create ACGS-2 Overview Dashboard

Navigate to **Dashboards > New Dashboard** and create:

**Dashboard JSON Export:**

```json
{
  "title": "ACGS-2 Observability Overview",
  "description": "Real-time monitoring of ACGS-2 microservices",
  "widgets": [
    {
      "id": 1,
      "definition": {
        "title": "Total Log Volume (24h)",
        "type": "query_value",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2}.rollup(sum, 86400)",
            "aggregator": "sum"
          }
        ],
        "precision": 0
      }
    },
    {
      "id": 2,
      "definition": {
        "title": "Error Rate (24h)",
        "type": "query_value",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2,status:error}.rollup(sum, 86400) / sum:logs.count{source:acgs2}.rollup(sum, 86400) * 100",
            "aggregator": "avg"
          }
        ],
        "precision": 2,
        "unit": "%",
        "conditional_formats": [
          {"comparator": "<", "value": 1, "palette": "green_on_white"},
          {"comparator": "<", "value": 5, "palette": "yellow_on_white"},
          {"comparator": ">=", "value": 5, "palette": "red_on_white"}
        ]
      }
    },
    {
      "id": 3,
      "definition": {
        "title": "Unique Requests (24h)",
        "type": "query_value",
        "requests": [
          {
            "q": "count:logs.distinct{source:acgs2,@correlation_id:*}.rollup(count, 86400)",
            "aggregator": "cardinality"
          }
        ]
      }
    },
    {
      "id": 4,
      "definition": {
        "title": "Log Volume by Service",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2} by {service}.rollup(sum, 3600)",
            "display_type": "area",
            "style": {"palette": "dog_classic"}
          }
        ]
      }
    },
    {
      "id": 5,
      "definition": {
        "title": "Error Trend by Service",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2,status:error} by {service}.rollup(sum, 900)",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "id": 6,
      "definition": {
        "title": "Top Error Events",
        "type": "toplist",
        "requests": [
          {
            "q": "top(sum:logs.count{source:acgs2,status:error} by {event}.rollup(sum, 86400), 10, 'sum', 'desc')"
          }
        ]
      }
    },
    {
      "id": 7,
      "definition": {
        "title": "Service Health Matrix",
        "type": "query_table",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2} by {service}.rollup(sum, 3600)",
            "aggregator": "sum",
            "conditional_formats": []
          }
        ],
        "has_search_bar": "auto"
      }
    },
    {
      "id": 8,
      "definition": {
        "title": "Recent Errors",
        "type": "log_stream",
        "query": "source:acgs2 status:error",
        "columns": ["@timestamp", "service", "event", "correlation_id"],
        "indexes": [],
        "message_display": "inline",
        "show_date_column": true,
        "show_message_column": true,
        "sort": {"column": "@timestamp", "order": "desc"}
      }
    },
    {
      "id": 9,
      "definition": {
        "title": "Request Duration Distribution",
        "type": "distribution",
        "requests": [
          {
            "q": "avg:logs.measure{source:acgs2,@duration_ms:*} by {service}"
          }
        ]
      }
    },
    {
      "id": 10,
      "definition": {
        "title": "P95 Latency by Endpoint",
        "type": "toplist",
        "requests": [
          {
            "q": "top(p95:logs.measure{source:acgs2,@duration_ms:*} by {endpoint}.rollup(p95, 3600), 10, 'p95', 'desc')"
          }
        ]
      }
    }
  ],
  "template_variables": [
    {
      "name": "service",
      "default": "*",
      "prefix": "service"
    },
    {
      "name": "env",
      "default": "production",
      "prefix": "env"
    }
  ],
  "layout_type": "ordered",
  "notify_list": [],
  "tags": ["env:production", "team:platform", "app:acgs2"]
}
```

### 7.2 Request Tracing Dashboard

Create a dedicated dashboard for tracing individual requests:

```json
{
  "title": "ACGS-2 Request Tracing",
  "description": "Trace requests across services using correlation ID",
  "widgets": [
    {
      "id": 1,
      "definition": {
        "title": "Search by Correlation ID",
        "type": "free_text",
        "text": "Enter correlation ID in the template variable above to trace a request"
      }
    },
    {
      "id": 2,
      "definition": {
        "title": "Request Timeline",
        "type": "log_stream",
        "query": "source:acgs2 @correlation_id:$correlation_id",
        "columns": ["@timestamp", "service", "level", "event", "@duration_ms"],
        "indexes": [],
        "sort": {"column": "@timestamp", "order": "asc"}
      }
    },
    {
      "id": 3,
      "definition": {
        "title": "Services Involved",
        "type": "pie_chart",
        "requests": [
          {
            "q": "sum:logs.count{source:acgs2,@correlation_id:$correlation_id} by {service}"
          }
        ]
      }
    },
    {
      "id": 4,
      "definition": {
        "title": "Request Flow",
        "type": "service_map",
        "service": "api_gateway",
        "filters": ["@correlation_id:$correlation_id"]
      }
    }
  ],
  "template_variables": [
    {
      "name": "correlation_id",
      "default": "*",
      "prefix": "@correlation_id"
    }
  ],
  "layout_type": "ordered"
}
```

## Step 8: APM Integration

### 8.1 Enable Trace-Log Correlation

ACGS-2 logs include OpenTelemetry trace IDs that can be correlated with Datadog APM. Configure the Python services:

```python
# acgs2-core/shared/logging_config.py (addition)
import os

# Enable Datadog trace injection
if os.getenv("DD_LOGS_INJECTION") == "true":
    from ddtrace import tracer, patch

    # Patch logging to inject trace context
    patch(logging=True)

    # Add Datadog trace context to structlog
    def add_datadog_trace_context(logger, method_name, event_dict):
        """Add Datadog trace IDs to log context."""
        span = tracer.current_span()
        if span:
            event_dict["dd.trace_id"] = span.trace_id
            event_dict["dd.span_id"] = span.span_id
        return event_dict
```

### 8.2 Configure Unified Service Tagging

Set environment variables for all ACGS-2 services:

```bash
# Required for APM correlation
export DD_SERVICE=api_gateway  # or policy_registry, audit_service, etc.
export DD_ENV=production
export DD_VERSION=1.0.0
export DD_LOGS_INJECTION=true
export DD_TRACE_AGENT_URL=http://localhost:8126
```

### 8.3 View Correlated Logs in APM

1. Navigate to **APM > Traces**
2. Click on a trace
3. Switch to the **Logs** tab
4. Logs with matching `trace_id` are automatically displayed

## Step 9: Log Archives and Rehydration

### 9.1 Configure Log Archive

Archive ACGS-2 logs for long-term storage and compliance:

1. Navigate to **Logs > Configuration > Archives**
2. Click **New Archive**
3. Configure:

| Field | Value |
|-------|-------|
| **Name** | `acgs2-archive` |
| **Filter** | `source:acgs2` |
| **Storage** | AWS S3 / Azure Blob / GCS |
| **Path** | `acgs2/logs/%Y/%m/%d/` |
| **Include Timestamp** | Yes |
| **Compression** | gzip |

### 9.2 Rehydrate Historical Logs

```bash
# Rehydrate logs for a specific time range
curl -X POST "https://api.datadoghq.com/api/v1/logs/config/archives/acgs2-archive/readers" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -d '{
    "data": {
      "type": "archives",
      "attributes": {
        "query": "source:acgs2 @correlation_id:YOUR_CORRELATION_ID",
        "from": "2026-01-01T00:00:00Z",
        "to": "2026-01-02T00:00:00Z"
      }
    }
  }'
```

## Step 10: Performance Tuning

### 10.1 Agent Tuning for High Volume

```yaml
# /etc/datadog-agent/datadog.yaml
logs_config:
  # Increase processing capacity
  processing_rules: []
  use_http: true
  use_compression: true
  compression_level: 6

  # Batch settings
  batch_wait: 5
  batch_max_size: 1000
  batch_max_content_size: 5000000

  # TCP settings
  frame_size: 9000
  open_files_limit: 500
```

### 10.2 Log Exclusion Filters

Reduce noise by excluding verbose debug logs in production:

```yaml
# /etc/datadog-agent/conf.d/acgs2.d/conf.yaml
logs:
  - type: file
    path: /var/log/acgs2/*.log
    service: acgs2
    source: acgs2
    log_processing_rules:
      - type: exclude_at_match
        name: exclude_health_checks
        pattern: "health_check"

      - type: exclude_at_match
        name: exclude_debug_in_prod
        pattern: "\"level\":\\s*\"DEBUG\""
```

### 10.3 Recommended Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Compression** | gzip level 6 | Balance CPU vs bandwidth |
| **Batch size** | 1000 events | Optimize throughput |
| **Batch wait** | 5 seconds | Reduce API calls |
| **HTTP transport** | Enabled | More reliable than TCP |
| **File tailing** | 10MB buffer | Handle log rotation |

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No logs in Datadog | Agent not forwarding | Check `datadog-agent status` |
| Missing fields | JSON parsing failed | Verify log format is valid JSON |
| Duplicate logs | Multiple collection sources | Disable overlapping sources |
| High latency | Network/batch issues | Enable compression, increase batch size |
| Logs not correlated with APM | Missing trace context | Enable `DD_LOGS_INJECTION=true` |

### Debug Commands

```bash
# Check agent log collection status
sudo datadog-agent status | grep -A20 "Logs Agent"

# View agent logs
sudo tail -f /var/log/datadog/agent.log

# Test log file access
sudo -u dd-agent cat /var/log/acgs2/api_gateway/app.log | head -5

# Verify JSON parsing
cat /var/log/acgs2/api_gateway/app.log | head -1 | python -m json.tool

# Check network connectivity
curl -v https://http-intake.logs.datadoghq.com/api/v2/logs \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -d '{"message": "test"}'
```

### Validate Log Flow

```
# In Datadog Log Explorer, search for recent logs:
source:acgs2 | head 10

# Check for parsing errors:
source:acgs2 @_parsing_error:*

# Verify field extraction:
source:acgs2 @correlation_id:* | top @service
```

## Security Considerations

1. **Use HTTPS** for all log forwarding (default)
2. **Rotate API keys** periodically (every 90 days recommended)
3. **Restrict API key permissions** to logs:write only
4. **Use environment variables** for sensitive configuration
5. **Enable log exclusion rules** to prevent PII leakage
6. **Configure log retention** according to compliance requirements
7. **Audit API key usage** via Datadog Audit Trail

### Sensitive Data Scrubbing

Add scrubbing rules to remove PII before ingestion:

```yaml
# /etc/datadog-agent/conf.d/acgs2.d/conf.yaml
logs:
  - type: file
    path: /var/log/acgs2/*.log
    service: acgs2
    source: acgs2
    log_processing_rules:
      - type: mask_sequences
        name: mask_email
        pattern: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
        replace_placeholder: "[EMAIL_REDACTED]"

      - type: mask_sequences
        name: mask_credit_card
        pattern: "\\b(?:\\d[ -]*?){13,16}\\b"
        replace_placeholder: "[CC_REDACTED]"

      - type: mask_sequences
        name: mask_ssn
        pattern: "\\b\\d{3}-\\d{2}-\\d{4}\\b"
        replace_placeholder: "[SSN_REDACTED]"
```

## Environment Variables

Configure ACGS-2 services with these environment variables for Datadog integration:

| Variable | Description | Example |
|----------|-------------|---------|
| `DD_API_KEY` | Datadog API key | `abcdef1234567890` |
| `DD_SITE` | Datadog site | `datadoghq.com` |
| `DD_SERVICE` | Service name | `api_gateway` |
| `DD_ENV` | Environment | `production` |
| `DD_VERSION` | Service version | `1.0.0` |
| `DD_LOGS_INJECTION` | Enable trace-log correlation | `true` |
| `DD_TRACE_AGENT_URL` | APM agent endpoint | `http://localhost:8126` |
| `DD_LOGS_ENABLED` | Enable log collection | `true` |

## Next Steps

- [Splunk Integration](./splunk-integration.md)
- [ELK Stack Integration](./elk-integration.md)
- [Log Schema Reference](./log-schema.md)
- [Development Guide](../DEVELOPMENT.md)

---

*Constitutional Hash: cdd01ef066bc6cf2*
