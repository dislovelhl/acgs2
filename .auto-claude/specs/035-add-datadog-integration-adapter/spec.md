# Add DataDog Integration Adapter

## Overview

Implement a DataDogAdapter following the BaseIntegration pattern to send governance events to DataDog's Log Management API. Uses existing adapter infrastructure including retry logic, credential management, and event formatting.

## Rationale

The integration-service has well-established adapters for Splunk, Sentinel, JIRA, ServiceNow. DataDog is a common enterprise observability platform. The BaseIntegration abstract class provides authenticate/validate/send_event/test_connection methods that just need DataDog-specific implementation.

---
*This spec was created from ideation and is pending detailed specification.*
