# Batch Event Processing: Usage Examples

This guide provides practical, real-world examples for using and implementing batch event processing in the ACGS2 integration service. These examples demonstrate common patterns, best practices, and gotchas when working with the batch processing API.

## Table of Contents

- [Using Batch Processing](#using-batch-processing)
  - [Basic Batch Sending](#basic-batch-sending)
  - [Monitoring Batch Metrics](#monitoring-batch-metrics)
  - [Handling Partial Failures](#handling-partial-failures)
  - [Error Handling and Retry](#error-handling-and-retry)
- [Implementing Batch Processing in Custom Adapters](#implementing-batch-processing-in-custom-adapters)
  - [All-or-Nothing Batch Pattern](#all-or-nothing-batch-pattern)
  - [Partial Success Batch Pattern](#partial-success-batch-pattern)
  - [Chunking Large Batches](#chunking-large-batches)
  - [Rate Limiting Handling](#rate-limiting-handling)
- [Performance Optimization](#performance-optimization)
  - [Batch Size Recommendations](#batch-size-recommendations)
  - [When to Use Batch Processing](#when-to-use-batch-processing)
- [Common Patterns and Best Practices](#common-patterns-and-best-practices)

---

## Using Batch Processing

### Basic Batch Sending

The simplest way to send multiple events is using the `send_events_batch()` method:

```python
from integrations import SplunkAdapter, IntegrationEvent
from models.events import EventSeverity

# Initialize and authenticate adapter
adapter = SplunkAdapter(credentials=splunk_credentials)
await adapter.authenticate()

# Create multiple events
events = [
    IntegrationEvent(
        event_id=f"evt-{i}",
        event_type="policy_violation",
        severity=EventSeverity.HIGH,
        source="acgs2-core",
        title=f"Policy Violation {i}",
        description=f"User performed unauthorized action {i}",
        policy_id="pol-123",
        resource_id=f"res-{i}",
        tenant_id="tenant-1",
    )
    for i in range(20)
]

# Send all events in a single batch
results = await adapter.send_events_batch(events)

# Check results
for event, result in zip(events, results):
    if result.success:
        print(f"✓ Event {event.event_id} sent successfully")
    else:
        print(f"✗ Event {event.event_id} failed: {result.error_message}")
```

**Key Points:**
- Always authenticate before sending events
- Results are returned in the same order as input events
- Use `zip()` to correlate events with their results
- Each result contains success status and error details if applicable

### Monitoring Batch Metrics

Track batch performance and success rates using built-in metrics:

```python
from integrations import SplunkAdapter

adapter = SplunkAdapter(credentials=splunk_credentials)
await adapter.authenticate()

# Send multiple batches
batch1 = [event1, event2, event3]
batch2 = [event4, event5, event6, event7]
batch3 = [event8, event9]

await adapter.send_events_batch(batch1)
await adapter.send_events_batch(batch2)
await adapter.send_events_batch(batch3)

# Check batch statistics
metrics = adapter.metrics

print(f"Batches sent: {metrics['batches_sent']}")
print(f"Batches failed: {metrics['batches_failed']}")
print(f"Total events via batch: {metrics['batch_events_total']}")
print(f"Total events sent: {metrics['events_sent']}")
print(f"Total events failed: {metrics['events_failed']}")

# Calculate batch success rate
total_batches = metrics['batches_sent'] + metrics['batches_failed']
if total_batches > 0:
    batch_success_rate = (metrics['batches_sent'] / total_batches) * 100
    print(f"Batch success rate: {batch_success_rate:.1f}%")

# Calculate average batch size
if metrics['batches_sent'] > 0:
    avg_batch_size = metrics['batch_events_total'] / metrics['batches_sent']
    print(f"Average batch size: {avg_batch_size:.1f} events")
```

**Key Points:**
- `batches_sent` counts successful batch operations (all or partial success)
- `batches_failed` counts batches where all events failed
- `batch_events_total` only counts successfully sent events
- `events_sent`/`events_failed` track individual event outcomes
- Metrics accumulate across multiple batch operations

### Handling Partial Failures

Some adapters support partial success (default fallback), while others are all-or-nothing:

```python
from integrations import JiraAdapter  # Uses default fallback (allows partial success)

adapter = JiraAdapter(credentials=jira_credentials)
await adapter.authenticate()

# Send batch that may have some failures
events = [event1, event2, event3, event4, event5]
results = await adapter.send_events_batch(events)

# Separate successful and failed events
successful = [(events[i], results[i]) for i in range(len(events)) if results[i].success]
failed = [(events[i], results[i]) for i in range(len(events)) if not results[i].success]

print(f"Success: {len(successful)}/{len(events)}")
print(f"Failed: {len(failed)}/{len(events)}")

# Retry failed events individually if needed
if failed:
    print("Retrying failed events individually...")
    for event, failed_result in failed:
        try:
            retry_result = await adapter.send_event(event)
            if retry_result.success:
                print(f"✓ Retry successful for {event.event_id}")
            else:
                print(f"✗ Retry failed for {event.event_id}: {retry_result.error_message}")
        except Exception as e:
            print(f"✗ Exception retrying {event.event_id}: {str(e)}")
```

**Adapter Batch Semantics:**
- **Splunk HEC:** All-or-nothing (all succeed or all fail)
- **Sentinel DCR:** All-or-nothing (all succeed or all fail)
- **Jira:** Default fallback allows partial success (creates tickets one-by-one)
- **ServiceNow:** Default fallback allows partial success (creates incidents one-by-one)

### Error Handling and Retry

Handle common error scenarios when sending batches:

```python
from integrations import SplunkAdapter
from integrations.exceptions import (
    AuthenticationError,
    RateLimitError,
    DeliveryError,
)
import asyncio

adapter = SplunkAdapter(credentials=splunk_credentials)
await adapter.authenticate()

async def send_batch_with_error_handling(events):
    """Send batch with comprehensive error handling."""
    try:
        results = await adapter.send_events_batch(events)

        # Check for any failures
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            print(f"⚠ Partial failure: {failed_count}/{len(events)} events failed")
        else:
            print(f"✓ All {len(events)} events sent successfully")

        return results

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        print("Re-authenticating and retrying...")
        await adapter.authenticate()
        return await adapter.send_events_batch(events)

    except RateLimitError as e:
        retry_after = getattr(e, 'retry_after', 60)
        print(f"⚠ Rate limited. Waiting {retry_after} seconds...")
        await asyncio.sleep(retry_after)
        return await adapter.send_events_batch(events)

    except DeliveryError as e:
        print(f"✗ Delivery failed after retries: {e}")
        print("Check adapter configuration and service availability")
        raise

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

# Use the error-handling wrapper
events = [event1, event2, event3]
results = await send_batch_with_error_handling(events)
```

**Key Points:**
- `AuthenticationError`: Re-authenticate and retry
- `RateLimitError`: Respect `retry_after` attribute
- `DeliveryError`: Indicates failure after all retries
- Automatic retry logic built into `send_events_batch()` (3 attempts)

---

## Implementing Batch Processing in Custom Adapters

### All-or-Nothing Batch Pattern

Implement batch processing for services with dedicated batch APIs (like Splunk HEC):

```python
from integrations.base import BaseIntegration, IntegrationEvent, IntegrationResult
from integrations.exceptions import RateLimitError, DeliveryError
from typing import List
import httpx

class MyBatchAdapter(BaseIntegration):
    """Adapter with all-or-nothing batch semantics."""

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send events using service's batch API with all-or-nothing semantics.

        If the batch is accepted, all events succeed. If it fails, all fail.
        """
        if not events:
            return []

        # Format events for service's batch API
        batch_payload = {
            "events": [
                self._format_event_for_service(event)
                for event in events
            ]
        }

        # Send batch request
        client = await self.get_http_client()
        response = await client.post(
            f"{self.api_url}/api/v1/batch",
            json=batch_payload,
            headers={"Authorization": f"Bearer {self.token}"}
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(
                "Batch rate limited by service",
                self.name,
                retry_after=retry_after
            )

        # Handle authentication errors
        if response.status_code == 401:
            from integrations.exceptions import AuthenticationError
            raise AuthenticationError("Token expired", self.name)

        # All-or-nothing semantics
        if response.status_code == 200:
            # All events succeeded
            response_data = response.json()
            return [
                IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=response_data.get("batch_id", event.event_id),
                )
                for event in events
            ]
        else:
            # All events failed
            error_msg = response.text or f"HTTP {response.status_code}"
            raise DeliveryError(f"Batch delivery failed: {error_msg}", self.name)

    def _format_event_for_service(self, event: IntegrationEvent) -> dict:
        """Format single event for the service's API."""
        return {
            "id": event.event_id,
            "type": event.event_type,
            "severity": event.severity.value,
            "title": event.title,
            "description": event.description,
            "timestamp": event.timestamp.isoformat(),
            "tenant": event.tenant_id,
        }
```

**Usage:**

```python
adapter = MyBatchAdapter(credentials=my_credentials)
await adapter.authenticate()

events = [event1, event2, event3]
results = await adapter.send_events_batch(events)

# With all-or-nothing, all results have the same success status
all_succeeded = all(r.success for r in results)
print(f"Batch {'succeeded' if all_succeeded else 'failed'}")
```

### Partial Success Batch Pattern

Implement batch processing with per-event success/failure tracking:

```python
from integrations.base import BaseIntegration, IntegrationEvent, IntegrationResult
from integrations.exceptions import DeliveryError
from typing import List

class MyPartialSuccessAdapter(BaseIntegration):
    """Adapter with per-event success/failure tracking."""

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send events with per-event result tracking.

        Returns individual success/failure for each event.
        """
        if not events:
            return []

        # Format events for service's batch API
        batch_payload = [
            self._format_event(event)
            for event in events
        ]

        # Send batch request
        client = await self.get_http_client()
        response = await client.post(
            f"{self.api_url}/api/batch",
            json={"items": batch_payload},
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code != 200:
            # Entire batch request failed
            raise DeliveryError(
                f"Batch request failed: {response.text}",
                self.name
            )

        # Parse per-event results from response
        results = []
        response_data = response.json()

        for idx, event in enumerate(events):
            event_result = response_data["results"][idx]

            if event_result["status"] == "success":
                results.append(IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=event_result["id"],
                ))
            else:
                results.append(IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="send_event",
                    error_code=event_result.get("error_code", "UNKNOWN"),
                    error_message=event_result.get("error_message", "Unknown error"),
                ))

        return results

    def _format_event(self, event: IntegrationEvent) -> dict:
        """Format single event."""
        return {
            "id": event.event_id,
            "type": event.event_type,
            "data": {
                "title": event.title,
                "description": event.description,
                "severity": event.severity.value,
            }
        }
```

**Usage:**

```python
adapter = MyPartialSuccessAdapter(credentials=my_credentials)
await adapter.authenticate()

events = [event1, event2, event3, event4]
results = await adapter.send_events_batch(events)

# Check individual results
for event, result in zip(events, results):
    if result.success:
        print(f"✓ {event.event_id}: {result.external_id}")
    else:
        print(f"✗ {event.event_id}: {result.error_message}")
```

### Chunking Large Batches

Handle service batch size limits by chunking:

```python
from integrations.base import BaseIntegration, IntegrationEvent, IntegrationResult
from typing import List

class MyChunkedAdapter(BaseIntegration):
    """Adapter that chunks large batches to respect service limits."""

    MAX_BATCH_SIZE = 100  # Service limit

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send events in chunks to respect service batch size limits.

        Automatically splits large batches into smaller chunks.
        """
        if len(events) <= self.MAX_BATCH_SIZE:
            # Single batch - send directly
            return await self._send_single_batch(events)

        # Chunk and send multiple batches
        results = []
        for i in range(0, len(events), self.MAX_BATCH_SIZE):
            chunk = events[i:i + self.MAX_BATCH_SIZE]
            chunk_results = await self._send_single_batch(chunk)
            results.extend(chunk_results)

        return results

    async def _send_single_batch(
        self,
        events: List[IntegrationEvent]
    ) -> List[IntegrationResult]:
        """Send a single batch (≤ MAX_BATCH_SIZE events)."""
        client = await self.get_http_client()

        batch_payload = [self._format_event(e) for e in events]

        response = await client.post(
            f"{self.api_url}/api/batch",
            json=batch_payload,
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            return [
                IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=event.event_id,
                )
                for event in events
            ]
        else:
            from integrations.exceptions import DeliveryError
            raise DeliveryError(
                f"Batch failed: {response.text}",
                self.name
            )

    def _format_event(self, event: IntegrationEvent) -> dict:
        """Format event for service API."""
        return {
            "id": event.event_id,
            "data": event.description,
        }
```

**Usage:**

```python
adapter = MyChunkedAdapter(credentials=my_credentials)
await adapter.authenticate()

# Send 250 events (will be split into 3 chunks: 100, 100, 50)
large_batch = [create_event(i) for i in range(250)]
results = await adapter.send_events_batch(large_batch)

print(f"Sent {len(results)} events in {len(large_batch) // 100 + 1} chunks")
```

### Rate Limiting Handling

Properly handle rate limiting with retry hints:

```python
from integrations.base import BaseIntegration, IntegrationEvent, IntegrationResult
from integrations.exceptions import RateLimitError, DeliveryError
from typing import List

class MyRateLimitedAdapter(BaseIntegration):
    """Adapter with proper rate limit handling."""

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """Send events with rate limit detection."""
        if not events:
            return []

        client = await self.get_http_client()

        batch_payload = {
            "events": [self._format_event(e) for e in events]
        }

        response = await client.post(
            f"{self.api_url}/batch",
            json=batch_payload,
            headers={"Authorization": f"Bearer {self.token}"}
        )

        # Check for rate limiting
        if response.status_code == 429:
            # Extract retry-after from header or response body
            retry_after = int(
                response.headers.get(
                    "Retry-After",
                    response.headers.get("X-RateLimit-Reset", 60)
                )
            )

            raise RateLimitError(
                f"Service rate limit exceeded. Retry after {retry_after}s",
                self.name,
                retry_after=retry_after
            )

        # Check for success
        if response.status_code == 200:
            return [
                IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=event.event_id,
                )
                for event in events
            ]
        else:
            raise DeliveryError(
                f"Batch delivery failed: HTTP {response.status_code}",
                self.name
            )

    def _format_event(self, event: IntegrationEvent) -> dict:
        """Format event."""
        return {"id": event.event_id, "data": event.description}
```

**Usage:**

```python
import asyncio
from integrations.exceptions import RateLimitError

adapter = MyRateLimitedAdapter(credentials=my_credentials)
await adapter.authenticate()

async def send_with_rate_limit_handling(events):
    """Send batch with automatic rate limit retry."""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            results = await adapter.send_events_batch(events)
            print(f"✓ Batch sent successfully")
            return results
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after
                print(f"⚠ Rate limited. Waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                await asyncio.sleep(wait_time)
            else:
                print(f"✗ Rate limited after {max_retries} attempts")
                raise

    raise Exception("Max retries exceeded")

# Send with automatic rate limit handling
results = await send_with_rate_limit_handling(events)
```

---

## Performance Optimization

### Batch Size Recommendations

Choose batch sizes based on your adapter and use case:

```python
from integrations import SplunkAdapter, SentinelAdapter, JiraAdapter

# Splunk HEC: Optimal batch size 50-1000 events
splunk = SplunkAdapter(credentials=splunk_creds)
await splunk.authenticate()

# For 500 events, send as single batch (within limit)
events_500 = [create_event(i) for i in range(500)]
results = await splunk.send_events_batch(events_500)
print(f"Splunk: Sent {len(events_500)} events in 1 batch")

# Sentinel DCR: Max 500 events or 1MB, optimal 100-500 events
sentinel = SentinelAdapter(credentials=sentinel_creds)
await sentinel.authenticate()

# For 300 events, send as single batch
events_300 = [create_event(i) for i in range(300)]
results = await sentinel.send_events_batch(events_300)
print(f"Sentinel: Sent {len(events_300)} events in 1 batch")

# Jira: No native batch API, uses one-by-one fallback
# Use smaller batches to avoid long processing times
jira = JiraAdapter(credentials=jira_creds)
await jira.authenticate()

# For 50 events, send in smaller batches for better progress visibility
events_50 = [create_event(i) for i in range(50)]
batch_size = 10

for i in range(0, len(events_50), batch_size):
    chunk = events_50[i:i+batch_size]
    results = await jira.send_events_batch(chunk)
    print(f"Jira: Processed batch {i//batch_size + 1}/{(len(events_50)-1)//batch_size + 1}")
```

**Adapter Batch Size Guidelines:**

| Adapter | Max Batch Size | Recommended Size | Notes |
|---------|---------------|------------------|-------|
| Splunk HEC | ~1000 events | 50-500 events | Depends on event size |
| Sentinel DCR | 500 events / 1MB | 100-300 events | Whichever limit is hit first |
| Jira | No limit | 10-20 events | Uses one-by-one fallback |
| ServiceNow | No limit | 10-20 events | Uses one-by-one fallback |

### When to Use Batch Processing

Use batch processing when:

```python
# ✓ GOOD: High-volume event streams (10+ events)
events = collect_events_from_stream()  # Returns 50 events
if len(events) >= 10:
    results = await adapter.send_events_batch(events)
else:
    # Use send_event for small quantities
    for event in events:
        result = await adapter.send_event(event)

# ✓ GOOD: Periodic batch jobs
async def hourly_batch_job():
    """Send accumulated events every hour."""
    events = await db.get_pending_events()

    if events:
        print(f"Sending {len(events)} accumulated events")
        results = await adapter.send_events_batch(events)

        # Update database based on results
        for event, result in zip(events, results):
            if result.success:
                await db.mark_event_sent(event.event_id)

# ✓ GOOD: Bulk migration/backfill
async def migrate_historical_events():
    """Migrate historical events to new system."""
    total_events = await db.count_historical_events()
    batch_size = 100

    for offset in range(0, total_events, batch_size):
        events = await db.get_historical_events(limit=batch_size, offset=offset)
        results = await adapter.send_events_batch(events)

        print(f"Progress: {offset + len(events)}/{total_events}")

# ✗ BAD: Single event with batch API
event = create_event()
results = await adapter.send_events_batch([event])  # Wasteful
# Use send_event instead:
result = await adapter.send_event(event)

# ✗ BAD: Real-time individual events
async def on_policy_violation(event):
    """Handle real-time policy violations."""
    # Don't accumulate for batching if real-time response needed
    results = await adapter.send_events_batch([event])  # Wrong

    # Use send_event for immediate delivery:
    result = await adapter.send_event(event)
```

**Use Batch When:**
- Sending 10+ events at once
- Processing periodic batch jobs
- Performing bulk migrations/backfills
- Latency is less critical than throughput
- Adapter has native batch API support

**Use Single Event When:**
- Sending 1-5 events
- Real-time event delivery required
- Immediate feedback needed per event
- Events arrive individually over time

---

## Common Patterns and Best Practices

### Pattern 1: Batch with Automatic Chunking

```python
async def send_events_in_optimal_chunks(
    adapter: BaseIntegration,
    events: List[IntegrationEvent],
    chunk_size: int = 100
):
    """
    Send events in optimally-sized chunks.

    Useful for adapters with batch size limits or to provide progress visibility.
    """
    total_results = []
    total_chunks = (len(events) - 1) // chunk_size + 1

    for i in range(0, len(events), chunk_size):
        chunk = events[i:i+chunk_size]
        chunk_num = i // chunk_size + 1

        print(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} events)...")

        results = await adapter.send_events_batch(chunk)
        total_results.extend(results)

        # Check chunk results
        success_count = sum(1 for r in results if r.success)
        print(f"  ✓ {success_count}/{len(results)} succeeded")

    return total_results

# Usage
events = [create_event(i) for i in range(500)]
results = await send_events_in_optimal_chunks(adapter, events, chunk_size=50)
```

### Pattern 2: Batch with Progress Reporting

```python
from typing import Callable

async def send_batch_with_progress(
    adapter: BaseIntegration,
    events: List[IntegrationEvent],
    progress_callback: Callable[[int, int], None] = None
):
    """Send batch with progress reporting."""
    chunk_size = 100
    total_sent = 0
    total_events = len(events)

    for i in range(0, total_events, chunk_size):
        chunk = events[i:i+chunk_size]
        results = await adapter.send_events_batch(chunk)

        total_sent += len(results)

        # Report progress
        if progress_callback:
            progress_callback(total_sent, total_events)

    return total_sent

# Usage
def print_progress(sent, total):
    pct = (sent / total) * 100
    print(f"Progress: {sent}/{total} ({pct:.1f}%)")

events = [create_event(i) for i in range(1000)]
await send_batch_with_progress(adapter, events, progress_callback=print_progress)
```

### Pattern 3: Batch with Failure Retry

```python
async def send_batch_with_individual_retry(
    adapter: BaseIntegration,
    events: List[IntegrationEvent],
    max_retries: int = 3
):
    """
    Send batch, then retry individual failures.

    Useful for adapters with partial success support.
    """
    # Send initial batch
    results = await adapter.send_events_batch(events)

    # Find failures
    failed_indices = [i for i, r in enumerate(results) if not r.success]

    if not failed_indices:
        print(f"✓ All {len(events)} events sent successfully")
        return results

    print(f"⚠ {len(failed_indices)}/{len(events)} events failed. Retrying individually...")

    # Retry failed events individually
    for idx in failed_indices:
        event = events[idx]

        for attempt in range(max_retries):
            try:
                retry_result = await adapter.send_event(event)
                results[idx] = retry_result

                if retry_result.success:
                    print(f"  ✓ Retry succeeded for event {idx}")
                    break
                else:
                    print(f"  ✗ Retry {attempt+1} failed for event {idx}")
            except Exception as e:
                print(f"  ✗ Exception on retry {attempt+1} for event {idx}: {e}")

    # Final summary
    final_success = sum(1 for r in results if r.success)
    final_failed = len(results) - final_success
    print(f"Final: {final_success} succeeded, {final_failed} failed")

    return results

# Usage
events = [create_event(i) for i in range(50)]
results = await send_batch_with_individual_retry(adapter, events)
```

### Pattern 4: Batch with Metrics Monitoring

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BatchMetrics:
    """Batch operation metrics."""
    start_time: datetime
    end_time: datetime
    total_events: int
    successful_events: int
    failed_events: int
    duration_seconds: float
    events_per_second: float

async def send_batch_with_metrics(
    adapter: BaseIntegration,
    events: List[IntegrationEvent]
) -> tuple[List[IntegrationResult], BatchMetrics]:
    """Send batch and return detailed metrics."""
    start_time = datetime.now()

    results = await adapter.send_events_batch(events)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    metrics = BatchMetrics(
        start_time=start_time,
        end_time=end_time,
        total_events=len(events),
        successful_events=successful,
        failed_events=failed,
        duration_seconds=duration,
        events_per_second=len(events) / duration if duration > 0 else 0
    )

    print(f"Batch Metrics:")
    print(f"  Duration: {metrics.duration_seconds:.2f}s")
    print(f"  Throughput: {metrics.events_per_second:.1f} events/sec")
    print(f"  Success: {metrics.successful_events}/{metrics.total_events}")

    return results, metrics

# Usage
events = [create_event(i) for i in range(200)]
results, metrics = await send_batch_with_metrics(adapter, events)
```

### Best Practices Summary

1. **Always authenticate before sending events**
   ```python
   await adapter.authenticate()
   ```

2. **Check adapter batch semantics**
   - Splunk/Sentinel: All-or-nothing
   - Jira/ServiceNow: Partial success (one-by-one fallback)

3. **Handle rate limiting gracefully**
   ```python
   except RateLimitError as e:
       await asyncio.sleep(e.retry_after)
   ```

4. **Monitor batch metrics**
   ```python
   metrics = adapter.metrics
   print(f"Batch success rate: {metrics['batches_sent']/(metrics['batches_sent']+metrics['batches_failed']):.1%}")
   ```

5. **Use appropriate batch sizes**
   - Splunk: 50-500 events
   - Sentinel: 100-300 events
   - Jira/ServiceNow: 10-20 events

6. **Preserve event order**
   ```python
   for event, result in zip(events, results):
       # Results are in same order as events
   ```

7. **Chunk large batches**
   ```python
   for i in range(0, len(events), CHUNK_SIZE):
       chunk = events[i:i+CHUNK_SIZE]
       await adapter.send_events_batch(chunk)
   ```

8. **Don't use batch API for single events**
   ```python
   # Wrong
   await adapter.send_events_batch([single_event])

   # Right
   await adapter.send_event(single_event)
   ```

---

## Conclusion

Batch event processing provides significant performance improvements for high-volume scenarios. Key takeaways:

- **For consumers**: Use `send_events_batch()` for 10+ events with appropriate batch sizes
- **For implementers**: Override `_do_send_events_batch()` only if the service has a native batch API
- **Monitor metrics**: Track batch success rates and throughput
- **Handle errors**: Implement proper retry logic for rate limiting and transient failures
- **Choose batch sizes wisely**: Balance throughput vs. latency based on your use case

For more details, see:
- `BaseIntegration.send_events_batch()` docstring in `base.py`
- `BaseIntegration._do_send_events_batch()` implementation examples in `base.py`
- Adapter implementations: `splunk_adapter.py`, `sentinel_adapter.py`
- Test coverage: `test_base.py`, `test_splunk.py`, `test_sentinel.py`
