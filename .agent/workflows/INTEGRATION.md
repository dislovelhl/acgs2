---
description: Integration Guide
---

# ACGS-2 Integration Guide

_Hash: `cdd01ef066bc6cf2`_

## Core Integration

Integrate via `EnhancedAgentBus` using the constitutional hash.

### Minimal Example

```python
bus = EnhancedAgentBus(constitutional_hash="cdd01ef066bc6cf2")
await bus.start()
msg = AgentMessage(..., constitutional_hash="cdd01ef066bc6cf2")
await bus.send(msg)
await bus.stop()
```

### Config

- `CONSTITUTIONAL_HASH`: `cdd01ef066bc6cf2` (Required)
- `REDIS_URL`, `OPA_URL`, `POLICY_REGISTRY_URL`

## Communication Protocols

1. **Request-Response**: Synchronous for simple lookups.
2. **Pub/Sub**: Asynchronous for system updates.
3. **Governance Request**: Mandatory for high-impact actions.

## Event Patterns

- **TraceID Propagation**: Must include `trace_id` in all messages.
- **Idempotency**: Use `message_id` for deduplication.
- **Security**: All messages MUST include the current constitutional hash.

## Best Practices

- **Resilience**: Use circuit breakers and connection pools.
- **Logging**: Use structured JSON. Bind `constitutional_hash` to all loggers.
- **Metrics**: Expose Prometheus metrics (latency, throughput, error rates).

## Deployment Checklist

- [ ] Hash matches `cdd01ef066bc6cf2`
- [ ] TLS enabled for all endpoints
- [ ] OPA/Metrics/Redis configured
- [ ] Circuit breakers enabled
- [ ] TraceID propagation verified
