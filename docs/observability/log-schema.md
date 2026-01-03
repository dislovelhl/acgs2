# ACGS-2 Log Schema Reference

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-03
> **Status**: Production Ready

This document defines the structured log schema used by all ACGS-2 services. All services emit JSON-formatted logs following this schema for consistent enterprise observability.

## Overview

ACGS-2 structured logging provides:
- **Consistent JSON format** across Python (structlog) and TypeScript (winston) services
- **RFC 5424 severity levels** for standardized log classification
- **Correlation ID propagation** for distributed request tracing
- **OpenTelemetry integration** for trace ID correlation
- **Enterprise compatibility** with Splunk, ELK Stack, and Datadog

## JSON Schema Definition

### Complete Log Entry Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://acgs2.local/schemas/log-entry.json",
  "title": "ACGS-2 Log Entry",
  "description": "Standard log entry format for all ACGS-2 services",
  "type": "object",
  "required": ["timestamp", "level", "event", "service"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp in UTC (e.g., 2026-01-03T14:30:00.123456Z)"
    },
    "level": {
      "type": "string",
      "enum": ["debug", "info", "warning", "error", "critical"],
      "description": "RFC 5424 severity level (lowercase)"
    },
    "event": {
      "type": "string",
      "description": "Event name using snake_case (e.g., request_received, payment_failed)"
    },
    "service": {
      "type": "string",
      "description": "Service identifier (e.g., api_gateway, policy_registry)"
    },
    "logger": {
      "type": "string",
      "description": "Logger name, typically module path (e.g., app.main, commands/agent)"
    },
    "correlation_id": {
      "type": "string",
      "format": "uuid",
      "description": "Request correlation ID (UUID v4) for distributed tracing"
    },
    "trace_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{32}$",
      "description": "OpenTelemetry 32-character hex trace ID"
    },
    "span_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{16}$",
      "description": "OpenTelemetry 16-character hex span ID"
    },
    "exc_info": {
      "type": "object",
      "description": "Exception information for error logs",
      "properties": {
        "type": { "type": "string", "description": "Exception class name" },
        "message": { "type": "string", "description": "Exception message" },
        "stack": { "type": "string", "description": "Stack trace" }
      }
    }
  },
  "additionalProperties": {
    "description": "Custom context fields specific to the logged event"
  }
}
```

### Minimal Required Fields

Every log entry MUST contain these fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Event timestamp in UTC |
| `level` | string (enum) | Severity level |
| `event` | string | Event name/message |
| `service` | string | Source service identifier |

### Recommended Fields

These fields SHOULD be included when available:

| Field | Type | Description |
|-------|------|-------------|
| `logger` | string | Logger/module name |
| `correlation_id` | string (UUID) | Request correlation ID |
| `trace_id` | string (32 hex) | OpenTelemetry trace ID |

## Field Reference

### Core Fields

#### `timestamp`

- **Type**: ISO 8601 string with timezone
- **Format**: `YYYY-MM-DDTHH:mm:ss.ffffffZ`
- **Timezone**: Always UTC (indicated by `Z` suffix)
- **Precision**: Microseconds (6 decimal places)
- **Example**: `"2026-01-03T14:30:00.123456Z"`

```json
{
  "timestamp": "2026-01-03T14:30:00.123456Z"
}
```

#### `level`

- **Type**: String enum (lowercase)
- **Values**: `debug`, `info`, `warning`, `error`, `critical`
- **Mapping**: Follows RFC 5424 (see [Severity Level Mapping](#rfc-5424-severity-level-mapping))

```json
{
  "level": "info"
}
```

#### `event`

- **Type**: String
- **Format**: `snake_case` event name
- **Convention**: Verb + noun describing what happened
- **Examples**: `request_received`, `user_authenticated`, `payment_failed`

```json
{
  "event": "request_received"
}
```

#### `service`

- **Type**: String
- **Values**: Service identifier from deployment
- **Python Services**: `api_gateway`, `policy_registry`, `audit_service`, `enhanced_agent_bus`
- **TypeScript Services**: `claude-flow`, `acgs2-neural-mcp`

```json
{
  "service": "api_gateway"
}
```

### Tracing Fields

#### `correlation_id`

- **Type**: String (UUID v4)
- **Format**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Source**: Extracted from `X-Request-ID` header or generated
- **Purpose**: Link logs across services for a single request

```json
{
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### `trace_id`

- **Type**: String (32 hex characters)
- **Source**: OpenTelemetry active span context
- **Purpose**: Correlate logs with distributed traces

```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

#### `span_id`

- **Type**: String (16 hex characters)
- **Source**: OpenTelemetry active span context
- **Purpose**: Identify specific span within a trace

```json
{
  "span_id": "a3ce929d0e0e4736"
}
```

### Error Fields

#### `exc_info`

- **Type**: Object or string
- **Content**: Exception details including type, message, and stack trace
- **When Present**: Error and critical level logs with exceptions

**Python (structlog) format**:
```json
{
  "exc_info": "Traceback (most recent call last):\n  File \"app.py\", line 42...\nValueError: Invalid input"
}
```

**TypeScript (winston) format**:
```json
{
  "error_type": "ValidationError",
  "error_message": "Invalid input format",
  "stack_trace": "Error: Invalid input format\n    at validate (/app/src/validator.ts:15:11)..."
}
```

#### `error_type`

- **Type**: String
- **Content**: Exception class/constructor name
- **Example**: `"ValueError"`, `"TypeError"`, `"ValidationError"`

#### `error_message`

- **Type**: String
- **Content**: Human-readable error description
- **Example**: `"Connection refused to database at localhost:5432"`

### Context Fields

Custom context fields are added as additional properties at the root level:

| Common Field | Type | Description | Example |
|--------------|------|-------------|---------|
| `user_id` | string | Authenticated user identifier | `"user_123"` |
| `tenant_id` | string | Multi-tenant identifier | `"acgs-prod"` |
| `endpoint` | string | API endpoint path | `"/api/v1/policies"` |
| `method` | string | HTTP method | `"POST"` |
| `status_code` | integer | HTTP response status | `200` |
| `duration_ms` | number | Operation duration in milliseconds | `150.5` |
| `policy_id` | string | Policy identifier | `"pol_abc123"` |
| `agent_id` | string | Agent identifier | `"agent_xyz"` |
| `command` | string | CLI command name | `"agent spawn"` |
| `success` | boolean | Operation success indicator | `true` |

## Example Log Entries

### Python Service: API Gateway

**Request Received**:
```json
{
  "timestamp": "2026-01-03T14:30:00.123456Z",
  "level": "info",
  "event": "request_received",
  "service": "api_gateway",
  "logger": "app.main",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "method": "POST",
  "endpoint": "/api/v1/policies",
  "user_id": "user_123",
  "tenant_id": "acgs-prod"
}
```

**Request Completed**:
```json
{
  "timestamp": "2026-01-03T14:30:00.275123Z",
  "level": "info",
  "event": "request_completed",
  "service": "api_gateway",
  "logger": "app.main",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "method": "POST",
  "endpoint": "/api/v1/policies",
  "status_code": 201,
  "duration_ms": 151.7
}
```

**Error with Exception**:
```json
{
  "timestamp": "2026-01-03T14:30:00.500000Z",
  "level": "error",
  "event": "policy_validation_failed",
  "service": "api_gateway",
  "logger": "app.validators",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "policy_id": "pol_invalid",
  "error_type": "ValidationError",
  "exc_info": "Traceback (most recent call last):\n  File \"/app/validators.py\", line 42, in validate\n    raise ValidationError(\"Invalid policy structure\")\nValidationError: Invalid policy structure"
}
```

### Python Service: Policy Registry

**Policy Created**:
```json
{
  "timestamp": "2026-01-03T14:30:00.200000Z",
  "level": "info",
  "event": "policy_created",
  "service": "policy_registry",
  "logger": "app.services.policy",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "policy_id": "pol_abc123",
  "policy_type": "constitutional",
  "version": "1.0.0",
  "success": true
}
```

**Database Connection Error**:
```json
{
  "timestamp": "2026-01-03T14:30:01.000000Z",
  "level": "critical",
  "event": "database_connection_failed",
  "service": "policy_registry",
  "logger": "app.database",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440001",
  "error_type": "ConnectionError",
  "error_message": "Cannot connect to PostgreSQL at localhost:5432",
  "retry_count": 3,
  "max_retries": 3
}
```

### Python Service: Audit Service

**Audit Event Recorded**:
```json
{
  "timestamp": "2026-01-03T14:30:00.300000Z",
  "level": "info",
  "event": "audit_event_recorded",
  "service": "audit_service",
  "logger": "app.audit",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "audit_event_type": "policy_created",
  "actor_id": "user_123",
  "resource_type": "policy",
  "resource_id": "pol_abc123",
  "action": "create"
}
```

### TypeScript Service: Claude Flow

**Command Started**:
```json
{
  "timestamp": "2026-01-03T14:30:00.000Z",
  "level": "info",
  "message": "command_started",
  "service": "claude-flow",
  "logger": "command/agent-spawn",
  "correlation_id": "cmd-lxyz123-abc456def",
  "command": "agent spawn",
  "args": {
    "type": "coder",
    "name": "my-agent"
  }
}
```

**Command Completed**:
```json
{
  "timestamp": "2026-01-03T14:30:01.500Z",
  "level": "info",
  "message": "command_completed",
  "service": "claude-flow",
  "logger": "command/agent-spawn",
  "correlation_id": "cmd-lxyz123-abc456def",
  "command": "agent spawn",
  "duration_ms": 1500,
  "success": true,
  "agent_id": "agent_abc123"
}
```

**Command Failed**:
```json
{
  "timestamp": "2026-01-03T14:30:00.050Z",
  "level": "error",
  "message": "command_failed",
  "service": "claude-flow",
  "logger": "command/agent-spawn",
  "correlation_id": "cmd-lxyz123-abc456def",
  "command": "agent spawn",
  "duration_ms": 50,
  "success": false,
  "error_type": "Error",
  "error_message": "Connection refused"
}
```

### TypeScript Service: Neural MCP

**Tool Execution**:
```json
{
  "timestamp": "2026-01-03T14:30:00.000Z",
  "level": "info",
  "message": "tool_execution_started",
  "service": "acgs2-neural-mcp",
  "logger": "tools/neural-mapper",
  "tool_name": "neural_domain_mapping",
  "input_size": 256
}
```

**Training Early Stop**:
```json
{
  "timestamp": "2026-01-03T14:30:05.000Z",
  "level": "info",
  "message": "training_early_stop",
  "service": "acgs2-neural-mcp",
  "logger": "neural/domain-mapper",
  "epoch": 15,
  "patience": 5,
  "patience_threshold": 5,
  "current_accuracy": 0.9523,
  "best_accuracy": 0.9550
}
```

## RFC 5424 Severity Level Mapping

ACGS-2 uses a subset of RFC 5424 severity levels appropriate for application logging:

| Level | Numeric | RFC 5424 | Use Case | When to Use |
|-------|---------|----------|----------|-------------|
| `debug` | 7 | Debug | Detailed debugging information | Development-only diagnostics, variable values, execution flow |
| `info` | 6 | Informational | Normal operational events | Request handling, successful operations, state changes |
| `warning` | 4 | Warning | Potential issues | Deprecated features, recoverable errors, approaching limits |
| `error` | 3 | Error | Error conditions | Failed operations, caught exceptions, invalid inputs |
| `critical` | 2 | Critical | Critical failures | System failures, unrecoverable errors, service unavailable |

### Severity Level Guidelines

#### DEBUG
Use for information only useful during development or debugging:
- Variable values and state
- Execution path tracing
- Correlation ID generation events
- Detailed request/response data

```python
logger.debug("correlation_id_generated", correlation_id=corr_id, path=request.path)
```

#### INFO
Use for normal operational events worth recording:
- Request received/completed
- Successful operations
- Configuration loaded
- Service startup/shutdown

```python
logger.info("request_completed", method="POST", endpoint="/policies", status_code=201)
```

#### WARNING
Use for potentially problematic situations that don't prevent operation:
- Deprecated API usage
- Rate limit approaching
- Configuration issues with fallbacks
- Retry attempts

```python
logger.warning("rate_limit_approaching", current_rate=95, limit=100, endpoint="/api/query")
```

#### ERROR
Use for failures that prevent an operation from completing:
- Validation failures
- Database errors
- External service failures
- Authentication failures

```python
logger.error("payment_processing_failed", order_id=order_id, error_type="PaymentError", exc_info=True)
```

#### CRITICAL
Use for severe failures that may require immediate attention:
- Database connection lost
- Service unavailable
- Configuration errors preventing startup
- Security breaches

```python
logger.critical("database_connection_lost", host="db.example.com", port=5432, retry_exhausted=True)
```

### RFC 5424 Extended Levels

These additional levels are defined in RFC 5424 but NOT commonly used in ACGS-2:

| Level | Numeric | Description | ACGS-2 Mapping |
|-------|---------|-------------|----------------|
| Emergency (0) | 0 | System is unusable | Map to `critical` |
| Alert (1) | 1 | Immediate action required | Map to `critical` |
| Notice (5) | 5 | Normal but significant | Map to `info` |

## Data Types Reference

### String Formats

| Format | Pattern | Example |
|--------|---------|---------|
| UUID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | `550e8400-e29b-41d4-a716-446655440000` |
| Trace ID | `[a-f0-9]{32}` | `4bf92f3577b34da6a3ce929d0e0e4736` |
| Span ID | `[a-f0-9]{16}` | `a3ce929d0e0e4736` |
| ISO 8601 | `YYYY-MM-DDTHH:mm:ss.ffffffZ` | `2026-01-03T14:30:00.123456Z` |

### Naming Conventions

| Type | Convention | Examples |
|------|------------|----------|
| Event names | `snake_case` | `request_received`, `user_authenticated` |
| Service names | `snake_case` | `api_gateway`, `policy_registry` |
| Logger names | `dot.notation` or `path/notation` | `app.main`, `commands/agent` |
| Context fields | `snake_case` | `user_id`, `duration_ms` |

## Security Considerations

### PII and Sensitive Data

**NEVER log**:
- Passwords or authentication tokens
- API keys or secrets
- Social Security Numbers
- Credit card numbers
- Personal health information (PHI)
- Full email addresses (mask as `u***@example.com`)

**Acceptable to log**:
- User IDs (non-identifiable tokens)
- Request correlation IDs
- Tenant/organization IDs
- Anonymized identifiers

### Log Injection Prevention

ACGS-2 logging libraries (structlog, winston) automatically handle:
- JSON escaping for special characters
- Newline sanitization
- Unicode normalization

**Best Practices**:
```python
# GOOD: Structured fields (automatically escaped)
logger.info("search_executed", query=user_input)

# BAD: String formatting (potential injection)
logger.info(f"Search query: {user_input}")  # NEVER DO THIS
```

### Environment-Specific Filtering

Configure log levels by environment:

| Environment | Recommended Level | Notes |
|-------------|-------------------|-------|
| Development | `debug` | Full verbosity for debugging |
| Staging | `info` | Standard operational logging |
| Production | `info` | Balance detail with volume |
| Security audit | `debug` | Temporary verbose logging |

## Log Volume Estimation

### Per-Request Log Events

| Event Type | Expected Logs | Services |
|------------|--------------|----------|
| Request lifecycle | 2 (start + end) | All HTTP services |
| Database operations | 1-3 | Registry, Audit |
| External calls | 1-2 per call | Gateway |
| Errors | Variable | All |

### Volume Calculation

```
Daily logs ≈ (requests/day) × (logs/request) × (1 + error_rate)

Example:
- 100,000 requests/day
- 3 logs/request average
- 5% error rate (additional logging)
= 100,000 × 3 × 1.05 = 315,000 logs/day
```

### Size Estimation

| Log Type | Average Size | Notes |
|----------|--------------|-------|
| Info log | 200-400 bytes | Standard request log |
| Error log | 1-5 KB | Includes stack trace |
| Debug log | 300-800 bytes | More context data |

## Integration Reference

For platform-specific integration guides:

- **[Splunk Integration](./splunk-integration.md)**: HEC setup, index configuration, sample queries
- **[ELK Stack Integration](./elk-integration.md)**: Logstash patterns, Elasticsearch templates, Kibana dashboards
- **[Datadog Integration](./datadog-integration.md)**: Agent configuration, facets, monitors

## Parsing Examples

### Python: Parse Log Entries

```python
import json
from datetime import datetime

def parse_log_entry(log_line: str) -> dict:
    """Parse a JSON log entry."""
    entry = json.loads(log_line)

    # Parse timestamp
    entry['timestamp_parsed'] = datetime.fromisoformat(
        entry['timestamp'].replace('Z', '+00:00')
    )

    return entry

# Filter by correlation ID
def filter_by_correlation_id(logs: list, correlation_id: str) -> list:
    return [log for log in logs if log.get('correlation_id') == correlation_id]
```

### JavaScript: Parse Log Entries

```javascript
function parseLogEntry(logLine) {
  const entry = JSON.parse(logLine);
  entry.timestampParsed = new Date(entry.timestamp);
  return entry;
}

// Filter by service
function filterByService(logs, serviceName) {
  return logs.filter(log => log.service === serviceName);
}
```

### JQ: Command-Line Parsing

```bash
# Extract all error logs
cat logs.json | jq 'select(.level == "error")'

# Get correlation IDs for failed requests
cat logs.json | jq 'select(.level == "error") | .correlation_id' | sort | uniq

# Count logs by service
cat logs.json | jq -s 'group_by(.service) | map({service: .[0].service, count: length})'

# Trace a request across services
cat logs.json | jq --arg id "550e8400-e29b-41d4-a716-446655440000" \
  'select(.correlation_id == $id) | {time: .timestamp, service: .service, event: .event}'
```

## Validation

### JSON Schema Validation

Use the schema defined above for runtime validation:

```python
import jsonschema

LOG_SCHEMA = {
    "type": "object",
    "required": ["timestamp", "level", "event", "service"],
    "properties": {
        "timestamp": {"type": "string", "format": "date-time"},
        "level": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical"]},
        "event": {"type": "string"},
        "service": {"type": "string"}
    },
    "additionalProperties": True
}

def validate_log_entry(entry: dict) -> bool:
    try:
        jsonschema.validate(entry, LOG_SCHEMA)
        return True
    except jsonschema.ValidationError:
        return False
```

### Log Format Testing

```bash
# Verify JSON format from service logs
docker-compose logs api_gateway 2>&1 | head -10 | while read line; do
  echo "$line" | python -c "import sys,json; json.loads(sys.stdin.read())" && \
    echo "VALID: $line" || echo "INVALID: $line"
done
```

## Changelog

### Version 1.0.0 (2026-01-03)
- Initial log schema definition
- RFC 5424 severity level mapping
- Python (structlog) and TypeScript (winston) examples
- Integration documentation cross-references

---

*Constitutional Hash: cdd01ef066bc6cf2*
