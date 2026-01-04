# Batch Processing Verification for Non-Batch Adapters

## Overview

This document explains how Jira and ServiceNow adapters support batch processing through the default fallback implementation in `BaseIntegration`.

## Design Pattern

### BaseIntegration Default Batch Behavior

The `BaseIntegration` class provides a default implementation of `_do_send_events_batch()` that automatically falls back to sending events one-by-one for adapters that don't support native batch operations.

**Implementation Location:** `integration-service/src/integrations/base.py` (lines 782-871)

**Key Features:**
- Automatically sends events one-by-one using `_do_send_event()`
- Handles exceptions gracefully, creating failure results for individual events
- Allows partial success (some events succeed, some fail)
- Logs debug message indicating use of default fallback implementation

### Adapters Using Default Batch Behavior

The following adapters use the default batch fallback:

#### 1. Jira Adapter (`jira_adapter.py`)

**Batch Support:** NO (uses default fallback)

**Reason:** Jira REST API does not support native batch ticket creation

**Implementation:**
- Inherits from `BaseIntegration` (line 188)
- Implements `_do_send_event()` to create individual tickets (line 495)
- Does NOT override `_do_send_events_batch()`
- Automatically uses default fallback when `send_events_batch()` is called

**Behavior:**
When `send_events_batch([event1, event2, event3])` is called:
1. `BaseIntegration.send_events_batch()` validates authentication
2. Calls `_send_events_batch_with_retry()` with retry logic
3. Calls `_do_send_events_batch()` (default implementation from base class)
4. Default implementation loops through events, calling `_do_send_event()` for each
5. Each event creates a separate Jira ticket via REST API
6. Returns `List[IntegrationResult]` with one result per event

#### 2. ServiceNow Adapter (`servicenow_adapter.py`)

**Batch Support:** NO (uses default fallback)

**Reason:** ServiceNow Table API does not support standard batch incident creation

**Implementation:**
- Inherits from `BaseIntegration` (line 219)
- Implements `_do_send_event()` to create individual incidents (line 573)
- Does NOT override `_do_send_events_batch()`
- Automatically uses default fallback when `send_events_batch()` is called

**Behavior:**
When `send_events_batch([event1, event2, event3])` is called:
1. `BaseIntegration.send_events_batch()` validates authentication
2. Calls `_send_events_batch_with_retry()` with retry logic
3. Calls `_do_send_events_batch()` (default implementation from base class)
4. Default implementation loops through events, calling `_do_send_event()` for each
5. Each event creates a separate ServiceNow incident via Table API
6. Returns `List[IntegrationResult]` with one result per event

## Verification

### Code Review Verification

**Verification Checklist:**
- [x] Both adapters inherit from `BaseIntegration`
- [x] Both adapters implement `_do_send_event()` for single event processing
- [x] Neither adapter overrides `_do_send_events_batch()`
- [x] `BaseIntegration._do_send_events_batch()` provides default implementation
- [x] Default implementation calls `_do_send_event()` for each event
- [x] Public `send_events_batch()` method handles auth, retry, and metrics

### Manual Verification Script

A verification script is provided at:
```
integration-service/tests/integrations/verify_batch_fallback.py
```

**To run the verification:**
```bash
cd integration-service
python3 tests/integrations/verify_batch_fallback.py
```

**What it verifies:**
1. Both adapters have `send_events_batch()` method (inherited from base)
2. Both adapters use default `_do_send_events_batch()` (not overridden)
3. Both adapters implement `_do_send_event()` for individual event processing

**Expected output:**
```
✓ JIRA ADAPTER VERIFICATION PASSED
  - Inherits send_events_batch() from BaseIntegration
  - Uses default batch implementation (sends one-by-one)
  - Implements _do_send_event() for individual event sending

✓ SERVICENOW ADAPTER VERIFICATION PASSED
  - Inherits send_events_batch() from BaseIntegration
  - Uses default batch implementation (sends one-by-one)
  - Implements _do_send_event() for individual event sending

✓ ALL VERIFICATIONS PASSED
```

## API Usage

### Jira Adapter Batch Usage

```python
from integrations import JiraAdapter, JiraCredentials, IntegrationEvent, EventSeverity
from pydantic import SecretStr
from datetime import datetime, timezone

# Create adapter
credentials = JiraCredentials(
    integration_name="Production Jira",
    base_url="https://your-domain.atlassian.net",
    username="your-email@example.com",
    api_token=SecretStr("your-api-token"),
    project_key="GOV",
)
adapter = JiraAdapter(credentials)
await adapter.authenticate()

# Create events
events = [
    IntegrationEvent(
        event_id="evt-1",
        event_type="policy_violation",
        severity=EventSeverity.HIGH,
        title="Policy Violation 1",
        source="acgs2",
        timestamp=datetime.now(timezone.utc),
    ),
    IntegrationEvent(
        event_id="evt-2",
        event_type="policy_violation",
        severity=EventSeverity.MEDIUM,
        title="Policy Violation 2",
        source="acgs2",
        timestamp=datetime.now(timezone.utc),
    ),
]

# Send batch (will create 2 separate Jira tickets)
results = await adapter.send_events_batch(events)

# Process results
for event, result in zip(events, results):
    if result.success:
        print(f"Created ticket {result.external_id} for event {event.event_id}")
    else:
        print(f"Failed to create ticket for event {event.event_id}: {result.error_message}")
```

### ServiceNow Adapter Batch Usage

```python
from integrations import ServiceNowAdapter, ServiceNowCredentials, IntegrationEvent, EventSeverity
from pydantic import SecretStr
from datetime import datetime, timezone

# Create adapter
credentials = ServiceNowCredentials(
    integration_name="Production ServiceNow",
    instance="your-instance",
    username="integration-user",
    password=SecretStr("password"),
)
adapter = ServiceNowAdapter(credentials)
await adapter.authenticate()

# Create events
events = [
    IntegrationEvent(
        event_id="evt-1",
        event_type="policy_violation",
        severity=EventSeverity.CRITICAL,
        title="Critical Policy Violation",
        source="acgs2",
        timestamp=datetime.now(timezone.utc),
    ),
    IntegrationEvent(
        event_id="evt-2",
        event_type="access_denied",
        severity=EventSeverity.HIGH,
        title="Access Denied",
        source="acgs2",
        timestamp=datetime.now(timezone.utc),
    ),
]

# Send batch (will create 2 separate ServiceNow incidents)
results = await adapter.send_events_batch(events)

# Process results
for event, result in zip(events, results):
    if result.success:
        print(f"Created incident {result.external_id} for event {event.event_id}")
    else:
        print(f"Failed to create incident for event {event.event_id}: {result.error_message}")
```

## Metrics Tracking

Both adapters track batch metrics through `BaseIntegration`:

**Batch-Specific Metrics:**
- `batches_sent`: Number of successful batch operations
- `batches_failed`: Number of failed batch operations
- `batch_events_total`: Total events sent via batch operations

**Per-Event Metrics:**
- `events_sent`: Total successful events (includes both batch and single)
- `events_failed`: Total failed events (includes both batch and single)

**Example:**
```python
# After sending batches
metrics = adapter.metrics
print(f"Batches sent: {metrics['batches_sent']}")
print(f"Total events sent via batches: {metrics['batch_events_total']}")
print(f"Overall events sent: {metrics['events_sent']}")
```

## Performance Considerations

### Default Fallback Performance

Since the default implementation sends events one-by-one:
- **Network overhead:** Multiple HTTP requests instead of one
- **Latency:** Sequential processing (not parallel)
- **Rate limiting:** May hit rate limits faster than native batch implementations

### When to Use Batch API

For adapters without native batch support (Jira, ServiceNow):
- Use `send_events_batch()` for consistent API across all adapters
- Consider batching at application level to reduce overhead
- Monitor metrics to understand actual throughput

For adapters with native batch support (Splunk, Sentinel):
- Use `send_events_batch()` for optimal performance
- Significant reduction in API calls and improved throughput

## Comparison with Native Batch Adapters

### Adapters with Native Batch Support

| Adapter  | Batch API | Implementation | Performance |
|----------|-----------|----------------|-------------|
| Splunk   | HEC batch endpoint | `_do_send_events_batch()` overridden | High - single API call |
| Sentinel | Azure Monitor Ingestion | `_do_send_events_batch()` overridden | High - single API call |

### Adapters with Default Fallback

| Adapter     | Batch API | Implementation | Performance |
|-------------|-----------|----------------|-------------|
| Jira        | N/A       | Default fallback | Moderate - multiple API calls |
| ServiceNow  | N/A       | Default fallback | Moderate - multiple API calls |

## Future Enhancements

### Potential Batch Support

1. **Jira:** Could implement custom batch logic using Jira Bulk API if available
2. **ServiceNow:** Could implement batch insert via Import Set API or Batch API

### Parallel Processing

The default fallback could be enhanced to send events in parallel using `asyncio.gather()`:
```python
# Potential enhancement (not implemented yet)
results = await asyncio.gather(
    *[self._do_send_event(event) for event in events],
    return_exceptions=True
)
```

This would reduce total latency for non-batch adapters while maintaining separate API calls.

## Conclusion

Both Jira and ServiceNow adapters are correctly configured to use the default batch processing behavior from `BaseIntegration`. This provides:

1. **Consistent API:** All adapters support `send_events_batch()` regardless of native batch support
2. **Automatic fallback:** No code changes needed in adapters
3. **Transparent operation:** Callers don't need to know if adapter has native batch support
4. **Metrics tracking:** Batch operations are tracked consistently across all adapters
5. **Error handling:** Individual event failures are handled gracefully

The verification script confirms that both adapters inherit the correct behavior and will automatically send events one-by-one when `send_events_batch()` is called.
