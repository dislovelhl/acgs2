# Add Batch Event Processing to BaseIntegration

## Overview

Extend BaseIntegration with send_events_batch() method to efficiently send multiple events in a single API call where supported. Reduces API calls and improves throughput for high-volume governance event scenarios.

## Rationale

Current adapters send events one at a time via send_event(). Splunk HEC, Sentinel DCR API, and DataDog all support batch ingestion. The BaseIntegration pattern already has metrics tracking (_events_sent, _events_failed) that can be extended for batch operations.

---
*This spec was created from ideation and is pending detailed specification.*
