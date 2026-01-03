# ACGS-2 Structured Logging Guide

**Constitutional Hash:** cdd01ef066bc6cf2

This guide covers the structured logging implementation in ACGS-2, including configuration, usage patterns, and integration with enterprise observability platforms.

## Overview

ACGS-2 uses structured logging with:
- **JSON output format** for machine parsing
- **Correlation IDs** for request tracing across services
- **RFC 5424 log levels** for consistent severity classification
- **Sensitive data redaction** for security compliance

## Quick Start

### Python Services

```python
from shared.structured_logging import configure_logging, get_logger

# Configure logging (call once at startup)
configure_logging()

# Get a logger instance
logger = get_logger(__name__)

# Log with structured data
logger.info("User authenticated", user_id="123", method="sso")
logger.warning("Rate limit approaching", current=95, limit=100)
logger.error("Database connection failed", db_host="postgres", exc_info=True)
```

### TypeScript Services (claude-flow)

```typescript
import { logger } from './utils/logger';

// Log with structured data
logger.info({ userId: '123', method: 'sso' }, 'User authenticated');
logger.warn({ current: 95, limit: 100 }, 'Rate limit approaching');
logger.error({ dbHost: 'postgres', error }, 'Database connection failed');
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO |
| `LOG_FORMAT` | Output format (json, text) | json |
| `CORRELATION_ID_HEADER` | HTTP header for correlation ID | X-Correlation-ID |

### Log Levels (RFC 5424)

| Level | Numeric | When to Use |
|-------|---------|-------------|
| DEBUG | 10 | Detailed debugging information |
| INFO | 20 | Routine operational messages |
| WARNING | 30 | Unexpected situations that are handled |
| ERROR | 40 | Error conditions requiring attention |
| CRITICAL | 50 | System-wide failures requiring immediate action |

## Log Format

### JSON Output Schema

```json
{
  "timestamp": "2025-01-03T12:00:00.000Z",
  "level": "INFO",
  "logger": "enhanced_agent_bus.api",
  "message": "Request processed",
  "correlation_id": "abc-123-def-456",
  "tenant_id": "acgs-prod",
  "extra": {
    "request_id": "req-789",
    "duration_ms": 45,
    "status_code": 200
  }
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp (UTC) |
| `level` | Log level name |
| `logger` | Logger name (module path) |
| `message` | Human-readable message |

### Optional Fields

| Field | Description |
|-------|-------------|
| `correlation_id` | Request correlation ID |
| `tenant_id` | Multi-tenant identifier |
| `request_id` | Unique request identifier |
| `extra` | Additional structured data |
| `exception` | Exception details (for errors) |
| `source` | Source file/line (for warnings+) |

## Correlation ID Propagation

### Setting Correlation ID

```python
from shared.structured_logging import set_correlation_id

# Generate new correlation ID
correlation_id = set_correlation_id()

# Or use existing ID from request header
correlation_id = set_correlation_id(request.headers.get("X-Correlation-ID"))
```

### FastAPI Middleware

```python
from fastapi import Request
from shared.structured_logging import set_correlation_id

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = get_correlation_id()
    return response
```

### HTTP Client Propagation

```python
import httpx
from shared.structured_logging import get_correlation_id

async def call_external_service():
    headers = {"X-Correlation-ID": get_correlation_id()}
    async with httpx.AsyncClient() as client:
        response = await client.get("http://other-service/api", headers=headers)
```

## Sensitive Data Redaction

The logger automatically redacts fields containing sensitive keywords:

- `password`, `secret`, `token`
- `api_key`, `apikey`, `auth`
- `credential`, `private_key`
- `client_secret`, `access_token`

```python
# This will be logged as: {"password": "[REDACTED]"}
logger.info("Config loaded", password="secret123", host="localhost")
```

## Integration Guides

### Splunk

**Index Configuration:**
```
[acgs2_logs]
DATETIME_CONFIG =
TIME_PREFIX = "timestamp":
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3N%:z
KV_MODE = json
```

**Search Examples:**
```spl
# Find all errors
index=acgs2_logs level=ERROR

# Trace request by correlation ID
index=acgs2_logs correlation_id="abc-123"

# Latency analysis
index=acgs2_logs | stats avg(extra.duration_ms) by logger
```

### Elasticsearch/OpenSearch (ELK)

**Index Template:**
```json
{
  "index_patterns": ["acgs2-*"],
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "level": { "type": "keyword" },
      "logger": { "type": "keyword" },
      "correlation_id": { "type": "keyword" },
      "tenant_id": { "type": "keyword" },
      "message": { "type": "text" }
    }
  }
}
```

**Kibana Discover Filters:**
- `level: ERROR OR CRITICAL` - Show errors
- `correlation_id: "abc-*"` - Trace requests
- `tenant_id: "prod-*"` - Filter by tenant

### Datadog

**Log Pipeline:**
```yaml
# datadog-log-pipeline.yaml
processors:
  - type: grok-parser
    name: Parse JSON logs
    enabled: true
    source: message
    samples: []

  - type: date-remapper
    name: Define timestamp
    enabled: true
    sources:
      - timestamp

  - type: status-remapper
    name: Map log level
    enabled: true
    sources:
      - level
```

**Log Facets:**
- `@correlation_id`
- `@tenant_id`
- `@extra.duration_ms`
- `@logger`

### Grafana Loki

**LogQL Queries:**
```logql
# Error rate over time
sum by (logger) (rate({app="acgs2"} | json | level="ERROR" [5m]))

# Request tracing
{app="acgs2"} | json | correlation_id="abc-123"

# Latency percentiles
quantile_over_time(0.95,
  {app="acgs2"} | json | unwrap extra_duration_ms [5m]
)
```

## Best Practices

### DO

✅ Use structured key-value pairs for data:
```python
logger.info("Order placed", order_id="123", total=99.99, items=3)
```

✅ Include relevant context:
```python
logger.error("Payment failed",
    order_id=order.id,
    error_code=e.code,
    exc_info=True
)
```

✅ Use appropriate log levels:
```python
logger.debug("Cache hit", key=cache_key)  # Debugging
logger.info("Request completed", duration_ms=45)  # Normal operation
logger.warning("Retry attempt", attempt=2, max=3)  # Recoverable issue
logger.error("External service timeout", service="payments")  # Error
```

### DON'T

❌ Use print statements in production code:
```python
# BAD
print(f"Processing order {order_id}")

# GOOD
logger.info("Processing order", order_id=order_id)
```

❌ Log sensitive data:
```python
# BAD
logger.info("Auth", token=user.api_token)

# GOOD - token will be auto-redacted
logger.info("Auth", user_id=user.id, has_token=bool(user.api_token))
```

❌ Use overly generic messages:
```python
# BAD
logger.error("An error occurred")

# GOOD
logger.error("Failed to process payment",
    order_id=order.id,
    error=str(e),
    exc_info=True
)
```

## Troubleshooting

### Logs Not Appearing

1. Check `LOG_LEVEL` environment variable
2. Verify `configure_logging()` was called at startup
3. Check for handler conflicts with other logging configs

### JSON Parse Errors

1. Ensure `LOG_FORMAT=json` is set
2. Check for multiline log messages
3. Verify no print statements are mixed in

### Missing Correlation IDs

1. Verify middleware is configured
2. Check that `set_correlation_id()` is called
3. Ensure HTTP headers are propagated to downstream services

## Migration Guide

### Converting Print Statements

```python
# Before
print(f"Processing message {msg.id} from {msg.sender}")

# After
logger.info("Processing message",
    message_id=msg.id,
    sender=msg.sender
)
```

### Converting Basic Logging

```python
# Before
logging.info(f"User {user_id} logged in")

# After
from shared.structured_logging import get_logger
logger = get_logger(__name__)
logger.info("User logged in", user_id=user_id)
```
