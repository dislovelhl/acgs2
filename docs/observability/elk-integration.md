# ACGS-2 ELK Stack Integration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-02
> **Status**: Production Ready

This guide covers integrating ACGS-2 structured logging with the ELK Stack (Elasticsearch, Logstash, Kibana) for centralized log aggregation, search, and visualization.

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

- **Elasticsearch 8.x+** (or OpenSearch 2.x)
- **Logstash 8.x+** (or Fluent Bit/Filebeat)
- **Kibana 8.x+** (or OpenSearch Dashboards)
- **ACGS-2 services** with structured logging enabled (see [Log Schema Reference](./log-schema.md))
- Network connectivity from ACGS-2 services to the ELK stack

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
                    │   Log Shipper         │
                    │  (Filebeat/Fluent Bit)│
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │      Logstash         │
                    │  (Parse & Transform)  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Elasticsearch      │
                    │  (acgs2-logs index)   │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │       Kibana          │
                    │  (Dashboards/Alerts)  │
                    └───────────────────────┘
```

## Step 1: Configure Elasticsearch Index

### 1.1 Create Index Template

ACGS-2 logs use a consistent JSON schema. Create an index template to optimize field mappings:

```json
PUT _index_template/acgs2-logs-template
{
  "index_patterns": ["acgs2-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1,
      "index.lifecycle.name": "acgs2-logs-policy",
      "index.lifecycle.rollover_alias": "acgs2-logs",
      "index.refresh_interval": "5s"
    },
    "mappings": {
      "properties": {
        "@timestamp": {
          "type": "date",
          "format": "strict_date_optional_time||epoch_millis"
        },
        "timestamp": {
          "type": "date",
          "format": "strict_date_optional_time||epoch_millis"
        },
        "level": {
          "type": "keyword"
        },
        "event": {
          "type": "keyword"
        },
        "message": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "service": {
          "type": "keyword"
        },
        "correlation_id": {
          "type": "keyword"
        },
        "trace_id": {
          "type": "keyword"
        },
        "span_id": {
          "type": "keyword"
        },
        "logger": {
          "type": "keyword"
        },
        "host": {
          "type": "keyword"
        },
        "environment": {
          "type": "keyword"
        },
        "tenant_id": {
          "type": "keyword"
        },
        "user_id": {
          "type": "keyword"
        },
        "duration_ms": {
          "type": "float"
        },
        "status_code": {
          "type": "integer"
        },
        "endpoint": {
          "type": "keyword"
        },
        "method": {
          "type": "keyword"
        },
        "error_type": {
          "type": "keyword"
        },
        "exc_info": {
          "type": "object",
          "enabled": true
        },
        "request": {
          "type": "object",
          "enabled": true
        },
        "response": {
          "type": "object",
          "enabled": true
        }
      }
    }
  },
  "priority": 200
}
```

### 1.2 Create Index Lifecycle Management (ILM) Policy

Configure automatic rollover and retention:

```json
PUT _ilm/policy/acgs2-logs-policy
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_primary_shard_size": "50gb"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "searchable_snapshot": {
            "snapshot_repository": "logs-snapshots"
          },
          "set_priority": {
            "priority": 0
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### 1.3 Create Initial Index with Alias

```json
PUT acgs2-logs-000001
{
  "aliases": {
    "acgs2-logs": {
      "is_write_index": true
    }
  }
}
```

### 1.4 Verify Index Setup via CLI

```bash
# Check index template
curl -X GET "localhost:9200/_index_template/acgs2-logs-template?pretty"

# Check ILM policy
curl -X GET "localhost:9200/_ilm/policy/acgs2-logs-policy?pretty"

# List indices
curl -X GET "localhost:9200/_cat/indices/acgs2-logs-*?v"
```

## Step 2: Configure Logstash

### 2.1 Basic JSON Pipeline (Recommended)

Since ACGS-2 logs are already JSON-formatted, minimal parsing is required:

```ruby
# /etc/logstash/conf.d/acgs2-logs.conf

input {
  beats {
    port => 5044
    tags => ["acgs2"]
  }

  # Alternative: TCP input for direct log shipping
  tcp {
    port => 5000
    codec => json_lines
    tags => ["acgs2", "direct"]
  }
}

filter {
  if "acgs2" in [tags] {
    # Parse JSON log message if needed
    if [message] {
      json {
        source => "message"
        target => "log"
        skip_on_invalid_json => true
      }

      # Promote fields from nested log object
      if [log] {
        mutate {
          rename => {
            "[log][timestamp]" => "@timestamp"
            "[log][level]" => "level"
            "[log][event]" => "event"
            "[log][service]" => "service"
            "[log][correlation_id]" => "correlation_id"
            "[log][trace_id]" => "trace_id"
            "[log][logger]" => "logger"
          }
          remove_field => ["log", "message"]
        }
      }
    }

    # Parse timestamp if not already a date type
    date {
      match => ["@timestamp", "ISO8601", "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'"]
      target => "@timestamp"
      timezone => "UTC"
    }

    # Normalize log levels to uppercase
    mutate {
      uppercase => ["level"]
    }

    # Add metadata
    mutate {
      add_field => {
        "[@metadata][index_prefix]" => "acgs2-logs"
      }
    }

    # Extract HTTP status code category
    if [status_code] {
      ruby {
        code => '
          status = event.get("status_code")
          if status
            event.set("status_category", "#{status.to_i / 100}xx")
          end
        '
      }
    }
  }
}

output {
  if "acgs2" in [tags] {
    elasticsearch {
      hosts => ["http://elasticsearch:9200"]
      index => "acgs2-logs"
      # Use template defined in Elasticsearch
      manage_template => false

      # Performance tuning
      pipeline => "acgs2-ingest"

      # Authentication (uncomment for secured clusters)
      # user => "${ELASTICSEARCH_USER}"
      # password => "${ELASTICSEARCH_PASSWORD}"
      # ssl => true
      # cacert => "/etc/logstash/certs/ca.crt"
    }
  }
}
```

### 2.2 Grok Patterns for Legacy Format (Optional)

If you need to parse logs that are not JSON-formatted (fallback scenarios):

```ruby
# /etc/logstash/patterns/acgs2
# ACGS-2 Log Pattern Definitions

# Timestamp pattern: 2026-01-02T14:30:00.123456Z
ACGS2_TIMESTAMP %{TIMESTAMP_ISO8601}

# Log level: INFO, DEBUG, WARNING, ERROR, CRITICAL
ACGS2_LEVEL (?:DEBUG|INFO|NOTICE|WARNING|ERROR|CRITICAL|ALERT|EMERGENCY)

# Correlation ID: UUID format
ACGS2_CORRELATION_ID [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}

# Trace ID: 32-character hex
ACGS2_TRACE_ID [0-9a-f]{32}

# Service name
ACGS2_SERVICE (?:api_gateway|policy_registry|audit_service|enhanced_agent_bus|claude-flow|acgs2-neural-mcp)

# Combined pattern for structured text logs
ACGS2_LOG %{ACGS2_TIMESTAMP:timestamp} \| %{ACGS2_LEVEL:level} \| %{ACGS2_SERVICE:service} \| %{ACGS2_CORRELATION_ID:correlation_id} \| %{GREEDYDATA:event}
```

**Grok filter configuration:**

```ruby
# Legacy text log parsing filter
filter {
  if "acgs2-legacy" in [tags] {
    grok {
      patterns_dir => ["/etc/logstash/patterns"]
      match => {
        "message" => [
          "%{ACGS2_LOG}",
          # Fallback pattern
          "%{ACGS2_TIMESTAMP:timestamp} - %{ACGS2_SERVICE:service} - %{ACGS2_LEVEL:level} - %{GREEDYDATA:event}"
        ]
      }
      tag_on_failure => ["_acgs2_parse_failure"]
    }

    # Extract correlation ID from message if not captured
    if ![correlation_id] {
      grok {
        match => {
          "message" => "correlation_id[=:]%{ACGS2_CORRELATION_ID:correlation_id}"
        }
        tag_on_failure => []
      }
    }
  }
}
```

### 2.3 High-Performance Pipeline Configuration

For production deployments with high log volume:

```ruby
# /etc/logstash/conf.d/acgs2-performance.conf

input {
  beats {
    port => 5044
    tags => ["acgs2"]
    # Performance tuning
    client_inactivity_timeout => 300
  }
}

filter {
  if "acgs2" in [tags] {
    # Minimal processing for pre-formatted JSON
    json {
      source => "message"
      skip_on_invalid_json => true
    }

    # Only process required fields
    prune {
      whitelist_names => [
        "@timestamp", "timestamp", "level", "event", "service",
        "correlation_id", "trace_id", "logger", "error_type",
        "duration_ms", "status_code", "endpoint", "method",
        "user_id", "tenant_id", "host", "exc_info"
      ]
    }
  }
}

output {
  if "acgs2" in [tags] {
    elasticsearch {
      hosts => ["http://es01:9200", "http://es02:9200", "http://es03:9200"]
      index => "acgs2-logs"

      # Performance optimizations
      document_type => "_doc"
      manage_template => false

      # Bulk processing
      flush_size => 5000
      idle_flush_time => 1

      # Retry configuration
      retry_max_interval => 64
      retry_initial_interval => 2
    }
  }
}
```

### 2.4 Logstash Pipeline Settings

Optimize `/etc/logstash/pipelines.yml`:

```yaml
- pipeline.id: acgs2-logs
  path.config: "/etc/logstash/conf.d/acgs2-logs.conf"
  pipeline.workers: 4
  pipeline.batch.size: 1000
  pipeline.batch.delay: 50
  queue.type: persisted
  queue.max_bytes: 1gb
```

## Step 3: Configure Log Shipper

### Option A: Filebeat (Recommended for Files)

```yaml
# /etc/filebeat/filebeat.yml

filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/acgs2/*.log
      - /var/log/acgs2/**/*.log
    json.keys_under_root: true
    json.add_error_key: true
    json.message_key: message
    tags: ["acgs2"]

    # Multiline for stack traces
    multiline:
      pattern: '^\{'
      negate: true
      match: after

  # Container logs (Docker/Kubernetes)
  - type: container
    enabled: true
    paths:
      - /var/lib/docker/containers/*/*.log
    processors:
      - add_kubernetes_metadata: ~
    tags: ["acgs2", "kubernetes"]

processors:
  - decode_json_fields:
      fields: ["message"]
      target: ""
      overwrite_keys: true
      add_error_key: true

  - rename:
      fields:
        - from: "json.timestamp"
          to: "@timestamp"
      ignore_missing: true
      fail_on_error: false

output.logstash:
  hosts: ["logstash:5044"]
  bulk_max_size: 2048
  compression_level: 3

# For direct Elasticsearch output (bypass Logstash)
# output.elasticsearch:
#   hosts: ["elasticsearch:9200"]
#   index: "acgs2-logs"
#   pipeline: "acgs2-ingest"
```

### Option B: Fluent Bit (Recommended for Kubernetes)

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
        HTTP_Server   On
        HTTP_Listen   0.0.0.0
        HTTP_Port     2020

    [INPUT]
        Name              tail
        Path              /var/log/containers/acgs2-*.log
        Parser            docker
        Tag               acgs2.*
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name              parser
        Match             acgs2.*
        Key_Name          log
        Parser            json
        Reserve_Data      On
        Preserve_Key      Off

    [FILTER]
        Name              modify
        Match             acgs2.*
        Rename            timestamp @timestamp

    [FILTER]
        Name              nest
        Match             acgs2.*
        Operation         lift
        Nested_under      kubernetes
        Add_prefix        k8s_

    [OUTPUT]
        Name              es
        Match             acgs2.*
        Host              elasticsearch.elastic-system.svc.cluster.local
        Port              9200
        Index             acgs2-logs
        Type              _doc
        Suppress_Type_Name On
        Logstash_Format   Off
        Time_Key          @timestamp
        Time_Key_Nanos    On
        Include_Tag_Key   Off
        Retry_Limit       5
        Buffer_Size       5MB

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
        Time_Key    timestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On
```

## Step 4: Elasticsearch Ingest Pipeline (Optional)

For additional processing at ingest time:

```json
PUT _ingest/pipeline/acgs2-ingest
{
  "description": "ACGS-2 log processing pipeline",
  "processors": [
    {
      "date": {
        "field": "timestamp",
        "target_field": "@timestamp",
        "formats": ["ISO8601", "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ"],
        "timezone": "UTC",
        "ignore_failure": true
      }
    },
    {
      "uppercase": {
        "field": "level",
        "ignore_failure": true
      }
    },
    {
      "set": {
        "field": "severity_order",
        "value": 0,
        "override": true
      }
    },
    {
      "script": {
        "source": """
          def levels = ['DEBUG': 0, 'INFO': 1, 'NOTICE': 2, 'WARNING': 3, 'ERROR': 4, 'CRITICAL': 5, 'ALERT': 6, 'EMERGENCY': 7];
          def level = ctx.level?.toUpperCase();
          if (levels.containsKey(level)) {
            ctx.severity_order = levels[level];
          }
        """,
        "ignore_failure": true
      }
    },
    {
      "geoip": {
        "field": "client_ip",
        "target_field": "geo",
        "ignore_missing": true,
        "ignore_failure": true
      }
    },
    {
      "user_agent": {
        "field": "user_agent",
        "target_field": "ua",
        "ignore_missing": true,
        "ignore_failure": true
      }
    },
    {
      "remove": {
        "field": ["_source.message"],
        "ignore_missing": true,
        "ignore_failure": true
      }
    }
  ],
  "on_failure": [
    {
      "set": {
        "field": "_index",
        "value": "acgs2-logs-failed"
      }
    },
    {
      "set": {
        "field": "error.message",
        "value": "{{ _ingest.on_failure_message }}"
      }
    }
  ]
}
```

## Step 5: Sample Elasticsearch Queries

### 5.1 Basic Searches

```json
// All logs in last hour
GET acgs2-logs/_search
{
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-1h"
      }
    }
  },
  "sort": [{"@timestamp": "desc"}]
}

// Errors only
GET acgs2-logs/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}

// Specific service logs
GET acgs2-logs/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"service": "api_gateway"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}

// Logs by correlation ID (request tracing)
GET acgs2-logs/_search
{
  "query": {
    "term": {"correlation_id": "550e8400-e29b-41d4-a716-446655440000"}
  },
  "sort": [{"@timestamp": "asc"}]
}
```

### 5.2 Request Flow Tracing

```json
// Trace a request across all services
GET acgs2-logs/_search
{
  "query": {
    "term": {"correlation_id": "YOUR_CORRELATION_ID"}
  },
  "sort": [{"@timestamp": "asc"}],
  "_source": ["@timestamp", "service", "level", "event", "duration_ms"]
}

// Find related logs using OpenTelemetry trace ID
GET acgs2-logs/_search
{
  "query": {
    "term": {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"}
  },
  "sort": [{"@timestamp": "asc"}],
  "_source": ["@timestamp", "service", "event", "correlation_id"]
}
```

### 5.3 Error Analysis Aggregations

```json
// Error count by service (last 24h)
GET acgs2-logs/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  },
  "aggs": {
    "by_service": {
      "terms": {"field": "service", "size": 20}
    }
  }
}

// Top error events
GET acgs2-logs/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  },
  "aggs": {
    "by_event": {
      "terms": {"field": "event", "size": 10}
    }
  }
}

// Error rate over time
GET acgs2-logs/_search
{
  "size": 0,
  "query": {
    "range": {"@timestamp": {"gte": "now-24h"}}
  },
  "aggs": {
    "over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "1h"
      },
      "aggs": {
        "total": {"value_count": {"field": "_id"}},
        "errors": {
          "filter": {"term": {"level": "ERROR"}},
          "aggs": {
            "count": {"value_count": {"field": "_id"}}
          }
        }
      }
    }
  }
}
```

### 5.4 Performance Analysis

```json
// Average request duration by endpoint
GET acgs2-logs/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {"term": {"service": "api_gateway"}},
        {"exists": {"field": "duration_ms"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "by_endpoint": {
      "terms": {"field": "endpoint", "size": 20},
      "aggs": {
        "avg_duration": {"avg": {"field": "duration_ms"}},
        "p95_duration": {"percentiles": {"field": "duration_ms", "percents": [95]}}
      }
    }
  }
}

// Slow requests (>500ms)
GET acgs2-logs/_search
{
  "query": {
    "bool": {
      "must": [
        {"range": {"duration_ms": {"gt": 500}}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "sort": [{"duration_ms": "desc"}],
  "_source": ["@timestamp", "service", "event", "duration_ms", "correlation_id"]
}
```

### 5.5 Service Health Overview

```json
// Service health summary
GET acgs2-logs/_search
{
  "size": 0,
  "query": {
    "range": {"@timestamp": {"gte": "now-1h"}}
  },
  "aggs": {
    "by_service": {
      "terms": {"field": "service", "size": 10},
      "aggs": {
        "total_logs": {"value_count": {"field": "_id"}},
        "errors": {
          "filter": {"term": {"level": "ERROR"}},
          "aggs": {"count": {"value_count": {"field": "_id"}}}
        },
        "warnings": {
          "filter": {"term": {"level": "WARNING"}},
          "aggs": {"count": {"value_count": {"field": "_id"}}}
        },
        "unique_requests": {
          "cardinality": {"field": "correlation_id"}
        }
      }
    }
  }
}
```

## Step 6: Kibana Dashboard Configuration

### 6.1 Create Index Pattern

1. Navigate to **Stack Management > Index Patterns**
2. Click **Create index pattern**
3. Enter pattern: `acgs2-logs-*`
4. Select `@timestamp` as the time field
5. Click **Create index pattern**

### 6.2 Import ACGS-2 Dashboard

Save the following as `acgs2-kibana-dashboard.ndjson` and import via **Stack Management > Saved Objects > Import**:

```json
{"attributes":{"title":"ACGS-2 Logs","timeFieldName":"@timestamp"},"id":"acgs2-logs-*","type":"index-pattern"}
{"attributes":{"description":"ACGS-2 Observability Overview","hits":0,"kibanaSavedObjectMeta":{"searchSourceJSON":"{\"query\":{\"language\":\"kuery\",\"query\":\"\"},\"filter\":[]}"},"optionsJSON":"{\"useMargins\":true,\"syncColors\":false,\"hidePanelTitles\":false}","panelsJSON":"[{\"version\":\"8.0.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":0,\"w\":12,\"h\":8,\"i\":\"1\"},\"panelIndex\":\"1\",\"embeddableConfig\":{\"attributes\":{\"title\":\"Total Logs (24h)\",\"visualizationType\":\"lnsMetric\",\"state\":{\"datasourceStates\":{\"indexpattern\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"dataType\":\"number\",\"isBucketed\":false,\"operationType\":\"count\",\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\"},\"query\":{\"language\":\"kuery\",\"query\":\"\"},\"filters\":[]}},\"hidePanelTitles\":false}},{\"version\":\"8.0.0\",\"type\":\"lens\",\"gridData\":{\"x\":12,\"y\":0,\"w\":12,\"h\":8,\"i\":\"2\"},\"panelIndex\":\"2\",\"embeddableConfig\":{\"attributes\":{\"title\":\"Error Count (24h)\",\"visualizationType\":\"lnsMetric\",\"state\":{\"datasourceStates\":{\"indexpattern\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"dataType\":\"number\",\"isBucketed\":false,\"operationType\":\"count\",\"scale\":\"ratio\",\"sourceField\":\"___records___\",\"filter\":{\"language\":\"kuery\",\"query\":\"level: ERROR\"}}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\"},\"query\":{\"language\":\"kuery\",\"query\":\"\"},\"filters\":[]}},\"hidePanelTitles\":false}},{\"version\":\"8.0.0\",\"type\":\"lens\",\"gridData\":{\"x\":24,\"y\":0,\"w\":12,\"h\":8,\"i\":\"3\"},\"panelIndex\":\"3\",\"embeddableConfig\":{\"attributes\":{\"title\":\"Unique Requests (24h)\",\"visualizationType\":\"lnsMetric\",\"state\":{\"datasourceStates\":{\"indexpattern\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"dataType\":\"number\",\"isBucketed\":false,\"operationType\":\"unique_count\",\"scale\":\"ratio\",\"sourceField\":\"correlation_id\"}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\"},\"query\":{\"language\":\"kuery\",\"query\":\"\"},\"filters\":[]}},\"hidePanelTitles\":false}}]","refreshInterval":{"pause":true,"value":0},"timeFrom":"now-24h","timeRestore":true,"timeTo":"now","title":"ACGS-2 Observability Overview","version":1},"id":"acgs2-overview-dashboard","type":"dashboard"}
```

### 6.3 Dashboard Panels (Manual Setup)

Create these visualizations in Kibana:

#### Panel 1: Log Volume by Service (Area Chart)

```json
{
  "title": "Log Volume by Service",
  "type": "area",
  "params": {
    "type": "area",
    "grid": {"categoryLines": false},
    "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom"}],
    "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "left"}],
    "seriesParams": [{"type": "area", "mode": "stacked"}]
  },
  "aggs": [
    {"id": "1", "type": "count", "schema": "metric"},
    {"id": "2", "type": "date_histogram", "schema": "segment", "params": {"field": "@timestamp", "interval": "auto"}},
    {"id": "3", "type": "terms", "schema": "group", "params": {"field": "service", "size": 10}}
  ]
}
```

#### Panel 2: Error Trend (Line Chart)

```json
{
  "title": "Error Trend",
  "type": "line",
  "params": {
    "type": "line",
    "grid": {"categoryLines": false}
  },
  "aggs": [
    {"id": "1", "type": "count", "schema": "metric"},
    {"id": "2", "type": "date_histogram", "schema": "segment", "params": {"field": "@timestamp", "interval": "15m"}},
    {"id": "3", "type": "terms", "schema": "group", "params": {"field": "service", "size": 10}}
  ],
  "filter": {"query": "level: ERROR"}
}
```

#### Panel 3: Service Health Matrix (Data Table)

```json
{
  "title": "Service Health Matrix",
  "type": "table",
  "aggs": [
    {"id": "1", "type": "count", "schema": "metric", "customLabel": "Total Logs"},
    {"id": "2", "type": "count", "schema": "metric", "customLabel": "Errors", "params": {"json": "{\"query\": {\"match\": {\"level\": \"ERROR\"}}}"}},
    {"id": "3", "type": "cardinality", "schema": "metric", "params": {"field": "correlation_id"}, "customLabel": "Unique Requests"},
    {"id": "4", "type": "terms", "schema": "bucket", "params": {"field": "service", "size": 10}}
  ]
}
```

#### Panel 4: Top Error Events (Pie Chart)

```json
{
  "title": "Top Error Events",
  "type": "pie",
  "params": {
    "type": "pie",
    "isDonut": true
  },
  "aggs": [
    {"id": "1", "type": "count", "schema": "metric"},
    {"id": "2", "type": "terms", "schema": "segment", "params": {"field": "event", "size": 10}}
  ],
  "filter": {"query": "level: ERROR"}
}
```

#### Panel 5: Recent Errors (Table)

```json
{
  "title": "Recent Errors",
  "type": "table",
  "columns": ["@timestamp", "service", "event", "correlation_id"],
  "sort": [["@timestamp", "desc"]],
  "filter": {"query": "level: ERROR"}
}
```

### 6.4 Request Tracing Dashboard

Create a separate dashboard for request tracing with these components:

1. **Search bar** with correlation_id filter
2. **Timeline table** showing logs sorted by timestamp
3. **Service flow visualization** showing log count per service
4. **Full log details** panel

**KQL Query for correlation ID search:**
```
correlation_id: "550e8400-e29b-41d4-a716-446655440000"
```

## Step 7: Kibana Alerting

### 7.1 Create Alert: High Error Rate

1. Navigate to **Stack Management > Rules and Connectors**
2. Click **Create rule**
3. Select **Elasticsearch query** rule type

```json
{
  "name": "ACGS-2 High Error Rate",
  "tags": ["acgs2", "error-rate"],
  "schedule": {"interval": "5m"},
  "params": {
    "index": ["acgs2-logs-*"],
    "timeField": "@timestamp",
    "esQuery": {
      "bool": {
        "must": [
          {"range": {"@timestamp": {"gte": "now-5m"}}},
          {"term": {"level": "ERROR"}}
        ]
      }
    },
    "threshold": [100],
    "thresholdComparator": ">",
    "timeWindowSize": 5,
    "timeWindowUnit": "m"
  },
  "actions": [
    {
      "group": "threshold met",
      "params": {
        "message": "High error rate detected: {{context.value}} errors in 5 minutes"
      }
    }
  ]
}
```

### 7.2 Create Alert: Service Down (No Logs)

```json
{
  "name": "ACGS-2 Service Down - No Logs",
  "tags": ["acgs2", "availability"],
  "schedule": {"interval": "5m"},
  "params": {
    "index": ["acgs2-logs-*"],
    "timeField": "@timestamp",
    "esQuery": {
      "bool": {
        "must": [
          {"range": {"@timestamp": {"gte": "now-5m"}}},
          {"term": {"service": "api_gateway"}}
        ]
      }
    },
    "threshold": [1],
    "thresholdComparator": "<",
    "timeWindowSize": 5,
    "timeWindowUnit": "m"
  },
  "actions": [
    {
      "group": "threshold met",
      "params": {
        "message": "No logs from api_gateway in last 5 minutes - service may be down"
      }
    }
  ]
}
```

### 7.3 Create Alert: Critical Errors

```json
{
  "name": "ACGS-2 Critical Error Alert",
  "tags": ["acgs2", "critical"],
  "schedule": {"interval": "1m"},
  "params": {
    "index": ["acgs2-logs-*"],
    "timeField": "@timestamp",
    "esQuery": {
      "bool": {
        "must": [
          {"range": {"@timestamp": {"gte": "now-1m"}}},
          {"terms": {"level": ["CRITICAL", "EMERGENCY"]}}
        ]
      }
    },
    "threshold": [0],
    "thresholdComparator": ">",
    "timeWindowSize": 1,
    "timeWindowUnit": "m"
  },
  "actions": [
    {
      "group": "threshold met",
      "params": {
        "message": "CRITICAL: {{context.value}} critical/emergency logs detected. Check immediately."
      }
    }
  ]
}
```

### 7.4 Create Alert: Slow Requests

```json
{
  "name": "ACGS-2 Slow Request Alert",
  "tags": ["acgs2", "performance"],
  "schedule": {"interval": "5m"},
  "params": {
    "index": ["acgs2-logs-*"],
    "timeField": "@timestamp",
    "esQuery": {
      "bool": {
        "must": [
          {"range": {"@timestamp": {"gte": "now-5m"}}},
          {"range": {"duration_ms": {"gte": 5000}}}
        ]
      }
    },
    "threshold": [10],
    "thresholdComparator": ">",
    "timeWindowSize": 5,
    "timeWindowUnit": "m"
  },
  "actions": [
    {
      "group": "threshold met",
      "params": {
        "message": "{{context.value}} slow requests (>5s) detected in last 5 minutes"
      }
    }
  ]
}
```

## Step 8: Performance Tuning

### 8.1 Elasticsearch Tuning for Log Ingestion

```yaml
# elasticsearch.yml
cluster.name: acgs2-logs

# Disable automatic index creation for security
action.auto_create_index: "acgs2-logs-*"

# Bulk processing optimization
indices.memory.index_buffer_size: 30%
thread_pool.write.queue_size: 1000

# Refresh interval (trade off between search latency and indexing throughput)
index.refresh_interval: 5s
```

### 8.2 Logstash Tuning

```yaml
# logstash.yml
pipeline.workers: 4
pipeline.batch.size: 1000
pipeline.batch.delay: 50
queue.type: persisted
queue.max_bytes: 4gb
```

### 8.3 Recommended Settings by Log Volume

| Log Volume | Elasticsearch Nodes | Shards | Replicas | Logstash Workers |
|------------|---------------------|--------|----------|------------------|
| < 10 GB/day | 1-3 | 1-2 | 1 | 2 |
| 10-100 GB/day | 3-6 | 2-4 | 1 | 4 |
| 100+ GB/day | 6+ | 4-8 | 1-2 | 8+ |

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No logs in Elasticsearch | Logstash not receiving | Check Filebeat → Logstash connectivity |
| Missing fields | JSON parsing failure | Verify `json.keys_under_root: true` in Filebeat |
| Duplicate events | Multiple shippers | Ensure single log shipper per source |
| High latency | Index refresh interval | Increase `refresh_interval` to 30s |
| Mapping conflicts | Dynamic mapping | Use explicit index template mappings |
| Out of disk space | Retention policy | Configure ILM policy with delete phase |

### Verify Log Flow

```bash
# Check Elasticsearch cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check index stats
curl -X GET "localhost:9200/acgs2-logs-*/_stats?pretty"

# Check recent documents
curl -X GET "localhost:9200/acgs2-logs-*/_search?size=5&sort=@timestamp:desc&pretty"

# Check Logstash pipeline
curl -X GET "localhost:9600/_node/stats/pipelines?pretty"
```

### Debug Queries

```json
// Check recent log ingestion
GET acgs2-logs-*/_search
{
  "size": 0,
  "aggs": {
    "by_service": {
      "terms": {"field": "service", "size": 10},
      "aggs": {
        "recent": {
          "filter": {"range": {"@timestamp": {"gte": "now-5m"}}}
        }
      }
    }
  }
}

// Verify JSON field extraction
GET acgs2-logs-*/_search
{
  "size": 1,
  "_source": true
}

// Check for parsing errors
GET acgs2-logs-*/_search
{
  "query": {
    "exists": {"field": "tags"}
  },
  "size": 10
}
```

## Security Considerations

1. **Enable TLS** for all ELK stack communications
2. **Use authentication** (Elastic Security or OpenSearch Security)
3. **Implement RBAC** for index access control
4. **Encrypt data at rest** using Elasticsearch encryption
5. **Audit logging** for compliance requirements
6. **Network isolation** - place ELK stack in private subnet

### Example Security Configuration

```yaml
# elasticsearch.yml (X-Pack Security)
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true
```

## Environment Variables

Configure ACGS-2 services with these environment variables for ELK integration:

| Variable | Description | Example |
|----------|-------------|---------|
| `ELASTICSEARCH_URL` | Elasticsearch endpoint | `http://elasticsearch:9200` |
| `LOGSTASH_HOST` | Logstash TCP input host | `logstash:5000` |
| `LOG_LEVEL` | Log verbosity | `INFO` |
| `LOG_FORMAT` | Output format | `json` |
| `OTEL_SERVICE_NAME` | Service name for tracing | `api_gateway` |

## Next Steps

- [Splunk Integration](./splunk-integration.md)
- [Datadog Integration](./datadog-integration.md)
- [Log Schema Reference](./log-schema.md)
- [Development Guide](../DEVELOPMENT.md)

---

*Constitutional Hash: cdd01ef066bc6cf2*
