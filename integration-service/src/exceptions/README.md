# Integration Service Exception Hierarchy

This document provides comprehensive documentation for the unified exception hierarchy in the integration-service.

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [Exception Hierarchy](#exception-hierarchy)
- [Base Exception Class](#base-exception-class)
- [Exception Categories](#exception-categories)
- [Usage Patterns](#usage-patterns)
- [Error Codes Reference](#error-codes-reference)
- [HTTP Status Codes](#http-status-codes)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)
- [FAQ](#faq)

## Overview

The integration-service exception hierarchy provides a unified, maintainable approach to error handling across all components. All exceptions inherit from a common base class and follow consistent patterns for attributes, error codes, and status codes.

**Key Benefits:**
- **Single Source of Truth**: All exceptions defined in `integration-service/src/exceptions/`
- **Consistent Attributes**: Every exception has `message`, `error_code`, `status_code`, and `details`
- **Backward Compatible**: Old exception names remain as aliases
- **Type Safety**: Proper inheritance for `isinstance()` checks
- **Rich Context**: Context-specific attributes for debugging
- **API-Ready**: Built-in `to_dict()` for JSON serialization

## Design Principles

1. **Single Source of Truth**: All exception classes are defined in the `exceptions/` module
2. **Common Attributes**: Base class provides consistent attributes across all exceptions
3. **Backward Compatibility**: Old exception names maintained as aliases for zero breaking changes
4. **Type Safety**: Proper exception inheritance for type checking and error handling
5. **Informative Errors**: Include context-specific attributes and error codes for debugging

## Exception Hierarchy

```
BaseIntegrationServiceError (exceptions.base)
├── AuthenticationError (exceptions.auth)
│   ├── InvalidSignatureError
│   ├── InvalidApiKeyError
│   ├── InvalidBearerTokenError
│   ├── TokenExpiredError
│   ├── SignatureTimestampError
│   └── MissingAuthHeaderError
│
├── ValidationError (exceptions.validation)
│   └── ConfigValidationError
│
├── RetryError (exceptions.retry)
│   ├── RetryableError
│   ├── NonRetryableError
│   └── MaxRetriesExceededError
│
├── DeliveryError (exceptions.delivery)
│   ├── DeliveryTimeoutError
│   └── DeliveryConnectionError
│
└── IntegrationError (exceptions.integration)
    ├── RateLimitError
    └── IntegrationConnectionError
```

## Base Exception Class

### BaseIntegrationServiceError

**Location**: `exceptions.base`

All custom exceptions inherit from this base class, ensuring consistent behavior across the service.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error description |
| `error_code` | `str` | Machine-readable error identifier (default: "INTEGRATION_ERROR") |
| `status_code` | `int \| None` | HTTP status code for API responses (default: None) |
| `details` | `dict` | Additional context-specific information (default: {}) |

**Methods:**

- `to_dict() -> dict`: Convert exception to dictionary representation for JSON serialization

**Example:**

```python
from exceptions import BaseIntegrationServiceError

error = BaseIntegrationServiceError(
    message="Something went wrong",
    error_code="CUSTOM_ERROR",
    status_code=500,
    details={"context": "additional info"}
)

# Serialize for API response
error_dict = error.to_dict()
# {
#     'error': 'BaseIntegrationServiceError',
#     'message': 'Something went wrong',
#     'error_code': 'CUSTOM_ERROR',
#     'status_code': 500,
#     'details': {'context': 'additional info'}
# }
```

## Exception Categories

### 1. Authentication Exceptions

**Location**: `exceptions.auth`

Used for webhook and API authentication errors.

#### AuthenticationError

Base class for all authentication-related errors.

- **Error Code**: `AUTH_ERROR`
- **Status Code**: `401`
- **Use Case**: Generic authentication failures

#### InvalidSignatureError

HMAC signature verification failed.

- **Error Code**: `INVALID_SIGNATURE`
- **Status Code**: `401`
- **Use Case**: Webhook signature validation

**Example:**

```python
from exceptions.auth import InvalidSignatureError

raise InvalidSignatureError(
    message="Signature mismatch",
    details={"algorithm": "sha256", "header": "X-Hub-Signature"}
)
```

#### InvalidApiKeyError

API key validation failed.

- **Error Code**: `INVALID_API_KEY`
- **Status Code**: `401`
- **Use Case**: API key authentication

**Example:**

```python
from exceptions.auth import InvalidApiKeyError

raise InvalidApiKeyError(
    message="API key not recognized",
    details={"header": "X-API-Key"}
)
```

#### InvalidBearerTokenError

Bearer token validation failed.

- **Error Code**: `INVALID_BEARER_TOKEN`
- **Status Code**: `401`
- **Use Case**: OAuth/Bearer token validation

**Example:**

```python
from exceptions.auth import InvalidBearerTokenError

raise InvalidBearerTokenError(
    message="Token validation failed",
    details={"token_endpoint": "https://auth.example.com/validate"}
)
```

#### TokenExpiredError

OAuth/Bearer token has expired.

- **Error Code**: `TOKEN_EXPIRED`
- **Status Code**: `401`
- **Use Case**: Expired authentication tokens

**Example:**

```python
from exceptions.auth import TokenExpiredError

raise TokenExpiredError(
    message="Access token expired at 2024-01-01T12:00:00Z",
    details={"expired_at": "2024-01-01T12:00:00Z"}
)
```

#### SignatureTimestampError

Signature timestamp outside acceptable window.

- **Error Code**: `TIMESTAMP_ERROR`
- **Status Code**: `401`
- **Use Case**: Replay attack protection

**Example:**

```python
from exceptions.auth import SignatureTimestampError

raise SignatureTimestampError(
    message="Request is 600 seconds old (max: 300)",
    details={"age_seconds": 600, "max_age": 300}
)
```

#### MissingAuthHeaderError

Required authentication header is missing.

- **Error Code**: `MISSING_AUTH_HEADER`
- **Status Code**: `401`
- **Use Case**: Missing authentication headers

**Additional Attributes:**
- `header`: Name of the missing header (automatically added to details)

**Example:**

```python
from exceptions.auth import MissingAuthHeaderError

raise MissingAuthHeaderError(
    header_name="X-API-Key",
    message="X-API-Key header is required"
)
```

### 2. Validation Exceptions

**Location**: `exceptions.validation`

Used for configuration and data validation errors.

#### ValidationError

Base class for all validation-related errors.

- **Error Code**: `VALIDATION_ERROR`
- **Status Code**: `400`
- **Use Case**: Generic validation failures

**Example:**

```python
from exceptions.validation import ValidationError

raise ValidationError(
    message="Invalid email format",
    details={"field": "email", "value": "invalid-email"}
)
```

#### ConfigValidationError

Configuration validation failed.

- **Error Code**: `CONFIG_VALIDATION_ERROR`
- **Status Code**: `400`
- **Use Case**: Integration configuration errors

**Additional Attributes:**
- `field`: Name of the specific field that failed validation (optional)

**Example:**

```python
from exceptions.validation import ConfigValidationError

raise ConfigValidationError(
    message="Invalid Splunk configuration",
    field="hec_token",
    details={"reason": "token must be at least 32 characters"}
)
```

### 3. Retry Exceptions

**Location**: `exceptions.retry`

Used for retry logic and backoff strategies.

#### RetryError

Base class for all retry-related errors.

- **Error Code**: `RETRY_ERROR`
- **Status Code**: `503`
- **Use Case**: Generic retry failures

#### RetryableError

Indicates an error that should trigger retry logic.

- **Error Code**: `RETRYABLE_ERROR`
- **Status Code**: `503` (default)
- **Use Case**: Temporary failures that can be retried

**Additional Attributes:**
- `retry_after`: Delay in seconds before next retry attempt (optional)

**Example:**

```python
from exceptions.retry import RetryableError

raise RetryableError(
    message="Service temporarily unavailable",
    status_code=503,
    retry_after=60.0,
    details={"service": "webhook-delivery"}
)
```

#### NonRetryableError

Indicates an error that should NOT trigger retry logic.

- **Error Code**: `NON_RETRYABLE_ERROR`
- **Status Code**: `400` (default)
- **Use Case**: Permanent failures (e.g., validation errors, 4xx responses)

**Example:**

```python
from exceptions.retry import NonRetryableError

raise NonRetryableError(
    message="Invalid webhook payload",
    status_code=400,
    details={"validation_error": "missing required field"}
)
```

#### MaxRetriesExceededError

Raised when all retry attempts are exhausted.

- **Error Code**: `MAX_RETRIES_EXCEEDED`
- **Status Code**: `503` (uses last_status_code if provided)
- **Use Case**: Retry limit reached

**Additional Attributes:**
- `attempts`: Total number of retry attempts made
- `last_error`: The exception from the final retry attempt (optional)
- `last_status_code`: HTTP status code from the final attempt (optional)

**Example:**

```python
from exceptions.retry import MaxRetriesExceededError, RetryableError

last_err = RetryableError("Connection timeout")
raise MaxRetriesExceededError(
    message="Webhook delivery failed after 3 attempts",
    attempts=3,
    last_error=last_err,
    last_status_code=503
)
```

### 4. Delivery Exceptions

**Location**: `exceptions.delivery`

Used for webhook and event delivery failures.

#### DeliveryError

Base class for all delivery-related errors.

- **Error Code**: `DELIVERY_ERROR`
- **Status Code**: `502`
- **Use Case**: Generic delivery failures

**Additional Attributes:**
- `delivery_id`: Delivery attempt identifier for tracking (optional)

**Example:**

```python
from exceptions.delivery import DeliveryError

raise DeliveryError(
    message="Failed to deliver webhook",
    delivery_id="dlv_abc123",
    details={"endpoint": "https://example.com/webhook"}
)
```

#### DeliveryTimeoutError

Webhook or event delivery timed out.

- **Error Code**: `DELIVERY_TIMEOUT`
- **Status Code**: `504`
- **Use Case**: Timeout failures

**Example:**

```python
from exceptions.delivery import DeliveryTimeoutError

raise DeliveryTimeoutError(
    message="Webhook delivery timed out after 30 seconds",
    delivery_id="dlv_xyz789",
    details={"timeout_seconds": 30, "endpoint": "https://slow.example.com"}
)
```

#### DeliveryConnectionError

Connection to webhook endpoint failed.

- **Error Code**: `DELIVERY_CONNECTION_ERROR`
- **Status Code**: `502`
- **Use Case**: Network connectivity issues

**Example:**

```python
from exceptions.delivery import DeliveryConnectionError

raise DeliveryConnectionError(
    message="Failed to connect to webhook endpoint",
    delivery_id="dlv_abc456",
    details={
        "endpoint": "https://unreachable.example.com",
        "error": "Connection refused"
    }
)
```

### 5. Integration Exceptions

**Location**: `exceptions.integration`

Used for third-party integration errors.

#### IntegrationError

Base class for all integration-specific errors.

- **Error Code**: `INTEGRATION_ERROR`
- **Status Code**: `500`
- **Use Case**: Generic integration failures

**Additional Attributes:**
- `integration_name`: Name of the integration that failed (required)

**Example:**

```python
from exceptions.integration import IntegrationError

raise IntegrationError(
    message="Failed to connect to Splunk",
    integration_name="splunk-prod",
    details={"endpoint": "https://splunk.example.com"}
)
```

#### RateLimitError

External service rate limit exceeded.

- **Error Code**: `RATE_LIMIT_ERROR`
- **Status Code**: `429`
- **Use Case**: API rate limiting

**Additional Attributes:**
- `integration_name`: Name of the rate-limited integration
- `retry_after`: Seconds to wait before retrying (optional)

**Example:**

```python
from exceptions.integration import RateLimitError

raise RateLimitError(
    message="Splunk rate limit exceeded: 100 requests/minute",
    integration_name="splunk-prod",
    retry_after=60,
    details={"limit": 100, "window": "1 minute"}
)
```

#### IntegrationConnectionError

Connection to external service failed.

- **Error Code**: `CONNECTION_ERROR`
- **Status Code**: `502`
- **Use Case**: Network-level failures

**Example:**

```python
from exceptions.integration import IntegrationConnectionError

raise IntegrationConnectionError(
    message="Failed to connect to Jira: Connection timeout",
    integration_name="jira-cloud",
    details={"host": "example.atlassian.net", "timeout": 30}
)
```

## Usage Patterns

### Pattern 1: Raising Exceptions

Always provide informative error messages and include relevant context in the `details` dictionary.

```python
from exceptions.auth import InvalidApiKeyError

# Good: Informative message with context
raise InvalidApiKeyError(
    message="API key validation failed for integration 'splunk-prod'",
    details={
        "key_prefix": key[:8],
        "header": "X-API-Key",
        "integration": "splunk-prod"
    }
)

# Avoid: Generic message without context
raise InvalidApiKeyError("Invalid API key")
```

### Pattern 2: Catching Exceptions

Catch specific exception types when possible, or use base classes for broader error handling.

```python
from exceptions.auth import AuthenticationError, InvalidApiKeyError
from exceptions.retry import RetryableError

try:
    await authenticate_request(headers, body)
except InvalidApiKeyError as e:
    # Handle specific authentication type
    logger.error(f"API key validation failed: {e.message}")
    return {"error": e.to_dict()}, 401
except AuthenticationError as e:
    # Handle all other authentication errors
    logger.error(f"Auth failed: {e.error_code} - {e.message}")
    return {"error": e.to_dict()}, e.status_code or 401
except RetryableError as e:
    # Handle retryable errors
    logger.warning(f"Retryable error: {e.message}")
    await schedule_retry(e.retry_after)
```

### Pattern 3: Exception Chaining

Use exception chaining to preserve the original error context.

```python
from exceptions.delivery import DeliveryError
import httpx

try:
    response = await http_client.post(url, json=payload)
except httpx.NetworkError as e:
    # Chain the original exception for debugging
    raise DeliveryError(
        message=f"Failed to deliver webhook to {url}",
        error_code="NETWORK_ERROR",
        details={"url": url, "original_error": str(e)}
    ) from e
```

### Pattern 4: Serializing for API Responses

Use the `to_dict()` method to serialize exceptions for JSON API responses.

```python
from exceptions.validation import ConfigValidationError

try:
    validate_config(config)
except ConfigValidationError as e:
    # Serialize exception for API response
    error_response = {
        "success": False,
        "error": e.to_dict()
    }
    return error_response, e.status_code
```

### Pattern 5: Accessing Error Attributes

All exceptions provide consistent attributes for logging and monitoring.

```python
from exceptions.retry import MaxRetriesExceededError

try:
    await deliver_webhook_with_retry(url, payload)
except MaxRetriesExceededError as e:
    # Access standard attributes
    logger.error(
        f"Delivery failed after {e.attempts} attempts",
        extra={
            "error_code": e.error_code,
            "status_code": e.status_code,
            "last_error": str(e.last_error),
            "details": e.details
        }
    )
```

## Error Codes Reference

### Authentication Error Codes

| Error Code | Exception | Description |
|------------|-----------|-------------|
| `AUTH_ERROR` | `AuthenticationError` | Generic authentication failure |
| `INVALID_SIGNATURE` | `InvalidSignatureError` | HMAC signature verification failed |
| `INVALID_API_KEY` | `InvalidApiKeyError` | API key validation failed |
| `INVALID_BEARER_TOKEN` | `InvalidBearerTokenError` | Bearer token validation failed |
| `TOKEN_EXPIRED` | `TokenExpiredError` | OAuth token expired |
| `TIMESTAMP_ERROR` | `SignatureTimestampError` | Request timestamp outside acceptable window |
| `MISSING_AUTH_HEADER` | `MissingAuthHeaderError` | Required authentication header missing |

### Validation Error Codes

| Error Code | Exception | Description |
|------------|-----------|-------------|
| `VALIDATION_ERROR` | `ValidationError` | Generic validation failure |
| `CONFIG_VALIDATION_ERROR` | `ConfigValidationError` | Configuration validation failed |

### Retry Error Codes

| Error Code | Exception | Description |
|------------|-----------|-------------|
| `RETRY_ERROR` | `RetryError` | Generic retry failure |
| `RETRYABLE_ERROR` | `RetryableError` | Retryable operation failed |
| `NON_RETRYABLE_ERROR` | `NonRetryableError` | Non-retryable operation failed |
| `MAX_RETRIES_EXCEEDED` | `MaxRetriesExceededError` | Maximum retry attempts exceeded |

### Delivery Error Codes

| Error Code | Exception | Description |
|------------|-----------|-------------|
| `DELIVERY_ERROR` | `DeliveryError` | Generic delivery failure |
| `DELIVERY_TIMEOUT` | `DeliveryTimeoutError` | Delivery request timed out |
| `DELIVERY_CONNECTION_ERROR` | `DeliveryConnectionError` | Connection to endpoint failed |

### Integration Error Codes

| Error Code | Exception | Description |
|------------|-----------|-------------|
| `INTEGRATION_ERROR` | `IntegrationError` | Generic integration failure |
| `RATE_LIMIT_ERROR` | `RateLimitError` | Rate limit exceeded |
| `CONNECTION_ERROR` | `IntegrationConnectionError` | Connection to external service failed |

## HTTP Status Codes

Each exception has a default HTTP status code appropriate for its error type:

| Status Code | Description | Exception Types |
|-------------|-------------|-----------------|
| `400` | Bad Request | `ValidationError`, `ConfigValidationError`, `NonRetryableError` |
| `401` | Unauthorized | All `AuthenticationError` subclasses |
| `429` | Too Many Requests | `RateLimitError` |
| `502` | Bad Gateway | `DeliveryError`, `DeliveryConnectionError`, `IntegrationConnectionError` |
| `503` | Service Unavailable | `RetryError`, `RetryableError`, `MaxRetriesExceededError` |
| `504` | Gateway Timeout | `DeliveryTimeoutError` |

**Note**: You can override the default status code when raising an exception:

```python
from exceptions.delivery import DeliveryError

# Override default status code (502) with custom value
raise DeliveryError(
    message="Webhook endpoint returned 404",
    status_code=404,  # Override
    details={"endpoint": "https://example.com/webhook"}
)
```

## Migration Guide

### For Existing Code

The new exception hierarchy is **100% backward compatible**. All old exception names remain as aliases:

#### Old Import Paths (Still Work)

```python
# These old imports still work
from webhooks.auth import WebhookAuthError
from webhooks.retry import RetryableError, WebhookRetryError
from webhooks.delivery import WebhookDeliveryError
from integrations.base import IntegrationError
from config.validation import ConfigValidationError
```

#### New Import Paths (Recommended)

```python
# New centralized imports (recommended)
from exceptions.auth import AuthenticationError, InvalidApiKeyError
from exceptions.retry import RetryableError, MaxRetriesExceededError
from exceptions.delivery import DeliveryError
from exceptions.integration import IntegrationError
from exceptions.validation import ConfigValidationError
```

### Migration Steps

**Step 1**: Update imports to use new exception module paths

```python
# Before
from webhooks.auth import InvalidApiKeyError

# After
from exceptions.auth import InvalidApiKeyError
```

**Step 2**: Update exception catching to use new base classes (optional)

```python
# Before: Catch specific old exception
try:
    authenticate()
except WebhookAuthError as e:
    handle_error(e)

# After: Catch new base class (more flexible)
try:
    authenticate()
except AuthenticationError as e:
    handle_error(e)
```

**Step 3**: Update raise statements to use new exception classes

```python
# Before
raise WebhookAuthError(
    message="Auth failed",
    error_code="AUTH_ERROR",
    status_code=401
)

# After
raise AuthenticationError(
    message="Auth failed"
)
```

### Backward Compatibility Aliases

The following aliases are maintained for backward compatibility:

| Old Name | New Name | Module |
|----------|----------|--------|
| `WebhookAuthError` | `AuthenticationError` | `exceptions.auth` |
| `WebhookRetryError` | `MaxRetriesExceededError` | `exceptions.retry` |
| `WebhookDeliveryError` | `DeliveryError` | `exceptions.delivery` |
| `WebhookTimeoutError` | `DeliveryTimeoutError` | `exceptions.delivery` |
| `WebhookConnectionError` | `DeliveryConnectionError` | `exceptions.delivery` |

**Example:**

```python
from webhooks.auth import WebhookAuthError
from exceptions.auth import AuthenticationError

# These are the same class
assert WebhookAuthError is AuthenticationError  # True

# Both names catch the same exceptions
try:
    raise AuthenticationError("test")
except WebhookAuthError as e:  # This works
    print("Caught")
```

## Best Practices

### 1. Use Specific Exception Types

Raise the most specific exception type appropriate for the error:

```python
# Good: Specific exception type
raise InvalidApiKeyError("API key validation failed")

# Avoid: Too generic
raise AuthenticationError("API key validation failed")
```

### 2. Provide Informative Messages

Include enough context to debug the issue without exposing sensitive data:

```python
# Good: Informative but safe
raise InvalidApiKeyError(
    message=f"API key validation failed for integration '{integration_name}'",
    details={"key_prefix": key[:8]}  # Only first 8 chars
)

# Avoid: Exposing sensitive data
raise InvalidApiKeyError(
    message=f"API key '{full_api_key}' is invalid"  # Exposes full key!
)
```

### 3. Use Details Dictionary for Context

Store structured context in the `details` dictionary:

```python
# Good: Structured context
raise DeliveryTimeoutError(
    message="Webhook delivery timed out",
    delivery_id="dlv_123",
    details={
        "endpoint": url,
        "timeout_seconds": timeout,
        "attempt": attempt_number
    }
)

# Avoid: Unstructured string
raise DeliveryTimeoutError(
    message=f"Webhook to {url} timed out after {timeout}s on attempt {attempt_number}"
)
```

### 4. Chain Exceptions

Preserve original exception context using exception chaining:

```python
# Good: Exception chaining
try:
    response = await http_client.post(url, json=payload)
except httpx.TimeoutException as e:
    raise DeliveryTimeoutError(
        message=f"Delivery to {url} timed out",
        details={"url": url}
    ) from e  # Preserves original exception

# Avoid: Losing original context
try:
    response = await http_client.post(url, json=payload)
except httpx.TimeoutException:
    raise DeliveryTimeoutError("Delivery timed out")  # Lost original error
```

### 5. Use to_dict() for Serialization

Always use `to_dict()` for consistent API responses:

```python
# Good: Consistent serialization
try:
    validate_config(config)
except ConfigValidationError as e:
    return {"error": e.to_dict()}, e.status_code

# Avoid: Manual serialization (inconsistent)
try:
    validate_config(config)
except ConfigValidationError as e:
    return {"error": str(e)}, 400  # Missing error_code, details
```

### 6. Log Error Context

Use error attributes for structured logging:

```python
# Good: Structured logging
try:
    deliver_webhook(url, payload)
except DeliveryError as e:
    logger.error(
        f"Webhook delivery failed: {e.message}",
        extra={
            "error_code": e.error_code,
            "status_code": e.status_code,
            "delivery_id": e.delivery_id,
            "details": e.details
        }
    )

# Avoid: Unstructured logging
try:
    deliver_webhook(url, payload)
except DeliveryError as e:
    logger.error(f"Error: {str(e)}")  # Missing structured context
```

## FAQ

### Q: Should I use the old exception names or the new ones?

**A**: Use the **new exception names** from the `exceptions` module in new code. The old names remain as aliases for backward compatibility but are not recommended for new development.

### Q: Will old code break after this change?

**A**: **No**. All old import paths and exception names continue to work. The migration is 100% backward compatible.

### Q: How do I know which exception to raise?

**A**: Choose the most specific exception type that matches your error:
- Authentication issues → `exceptions.auth`
- Validation errors → `exceptions.validation`
- Retry logic → `exceptions.retry`
- Delivery failures → `exceptions.delivery`
- Integration errors → `exceptions.integration`

### Q: Can I create custom exceptions?

**A**: Yes. Inherit from the appropriate base class:

```python
from exceptions.integration import IntegrationError

class CustomIntegrationError(IntegrationError):
    def __init__(self, message: str, custom_field: str):
        super().__init__(
            message=message,
            error_code="CUSTOM_INTEGRATION_ERROR",
            details={"custom_field": custom_field}
        )
```

### Q: What if I need a different status code?

**A**: Override the default status code when raising the exception:

```python
from exceptions.delivery import DeliveryError

raise DeliveryError(
    message="Custom status code",
    status_code=503  # Override default 502
)
```

### Q: How do I test exception handling?

**A**: Use pytest to test both raising and catching exceptions:

```python
import pytest
from exceptions.auth import InvalidApiKeyError

def test_invalid_api_key():
    with pytest.raises(InvalidApiKeyError) as exc_info:
        authenticate_with_invalid_key()

    # Check exception attributes
    assert exc_info.value.error_code == "INVALID_API_KEY"
    assert exc_info.value.status_code == 401
    assert "key_prefix" in exc_info.value.details
```

### Q: Are deprecation warnings planned?

**A**: Not immediately. The aliases will remain indefinitely for backward compatibility. Future versions may add optional deprecation warnings to guide migration, but this will be communicated well in advance.

---

**Last Updated**: 2026-01-03

**Version**: 1.0.0

For questions or issues, please consult the integration-service team or open an issue in the project repository.
