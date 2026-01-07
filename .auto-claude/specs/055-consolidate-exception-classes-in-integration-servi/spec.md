# Consolidate Exception Classes in Integration Service

## Overview

The integration-service has exception classes scattered across 5+ modules with similar patterns: WebhookAuthError, IntegrationError, WebhookDeliveryError, ConfigValidationError, WebhookRetryError, RetryableError, NonRetryableError. Many of these share the same structure (message, error_code, status_code, details) but are defined independently.

## Rationale

Fragmented exception hierarchies make error handling inconsistent and harder to maintain. A unified exception structure improves error handling consistency, makes it easier to implement cross-cutting concerns like logging and monitoring, and reduces code duplication.

---
*This spec was created from ideation and is pending detailed specification.*
