# ACGS-2 Exception Catalog
**Constitutional Hash:** cdd01ef066bc6cf2
**Last Updated:** 2026-01-03
**Status:** Complete

## Overview

This document catalogs all custom exception classes across the ACGS-2 codebase, their error codes, hierarchy, and usage patterns. This catalog serves as a reference for developers, operators, and troubleshooting documentation.

**Purpose:**
- Centralized reference for all exception types
- Error code documentation for troubleshooting
- Exception hierarchy and inheritance patterns
- Common usage scenarios and resolution guidance

---

## Table of Contents

1. [Integration Service Exceptions](#integration-service-exceptions)
2. [Enhanced Agent Bus Exceptions](#enhanced-agent-bus-exceptions)
3. [HITL Approvals Service Exceptions](#hitl-approvals-service-exceptions)
4. [Shared Authentication Exceptions](#shared-authentication-exceptions)
5. [Tenant Management Exceptions](#tenant-management-exceptions)
6. [SDK Client Exceptions](#sdk-client-exceptions)
7. [Other Service-Specific Exceptions](#other-service-specific-exceptions)

---

## Integration Service Exceptions

### Webhook Authentication (`integration-service/src/webhooks/auth.py`)

#### Base Exception

**`WebhookAuthError`**
- **Description:** Base exception for all webhook authentication errors
- **Error Code:** `AUTH_ERROR` (default)
- **HTTP Status:** 401
- **Attributes:**
  - `message`: Error message
  - `error_code`: Specific error code
  - `status_code`: HTTP status code
  - `details`: Additional error details dict
- **Usage:** Base class for all webhook auth-related exceptions

---

#### Derived Exceptions

**`InvalidSignatureError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `INVALID_SIGNATURE`
- **HTTP Status:** 401
- **Description:** Raised when HMAC signature verification fails
- **Common Causes:**
  - Incorrect secret key
  - Signature algorithm mismatch
  - Payload tampering
  - Timestamp mismatch in signed payload
- **Resolution:** Verify HMAC secret matches sender configuration

**`InvalidApiKeyError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `INVALID_API_KEY`
- **HTTP Status:** 401
- **Description:** Raised when API key validation fails
- **Common Causes:**
  - Missing API key header
  - Invalid or revoked API key
  - Key not registered in handler
- **Resolution:** Check X-API-Key header or Authorization header format

**`InvalidBearerTokenError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `INVALID_BEARER_TOKEN`
- **HTTP Status:** 401
- **Description:** Raised when Bearer token validation fails
- **Common Causes:**
  - Expired token
  - Invalid token format
  - Token not in token store
- **Resolution:** Refresh token or verify token configuration

**`TokenExpiredError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `TOKEN_EXPIRED`
- **HTTP Status:** 401
- **Description:** Raised when OAuth token has expired
- **Common Causes:**
  - Token TTL exceeded
  - System clock drift
- **Resolution:** Use refresh token to obtain new access token

**`SignatureTimestampError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `TIMESTAMP_ERROR`
- **HTTP Status:** 401
- **Description:** Raised when signature timestamp is outside acceptable window (default 300s)
- **Common Causes:**
  - Request replay attack
  - Clock skew between systems
  - Network delay > tolerance
- **Resolution:** Synchronize system clocks, check timestamp tolerance settings

**`MissingAuthHeaderError`**
- **Inherits:** `WebhookAuthError`
- **Error Code:** `MISSING_AUTH_HEADER`
- **HTTP Status:** 401
- **Description:** Raised when required authentication header is missing
- **Attributes:**
  - `header`: Name of the missing header
- **Resolution:** Ensure required header is present in request

---

### Webhook Delivery (`integration-service/src/webhooks/delivery.py`)

**`WebhookDeliveryError`**
- **Description:** Base exception for webhook delivery errors
- **Attributes:**
  - `message`: Error description
  - `delivery_id`: UUID of the delivery attempt
  - `status_code`: HTTP status code if applicable
- **Usage:** Base class for delivery-related exceptions

**`WebhookAuthenticationError`**
- **Inherits:** `WebhookDeliveryError`
- **Description:** Raised when webhook delivery authentication fails
- **Usage:** Used during outgoing webhook requests that fail authentication

**`WebhookTimeoutError`**
- **Inherits:** `WebhookDeliveryError`
- **Description:** Raised when webhook delivery times out
- **Common Causes:**
  - Slow endpoint response
  - Network latency
  - Endpoint unavailable
- **Resolution:** Check endpoint health, increase timeout configuration

**`WebhookConnectionError`**
- **Inherits:** `WebhookDeliveryError`
- **Description:** Raised when connection to webhook endpoint fails
- **Common Causes:**
  - DNS resolution failure
  - Network unreachable
  - Connection refused
- **Resolution:** Verify endpoint URL, check network connectivity

---

### Webhook Retry (`integration-service/src/webhooks/retry.py`)

**`WebhookRetryError`**
- **Description:** Raised when a webhook delivery fails after all retries
- **Attributes:**
  - `message`: Error description
  - `attempts`: Number of attempts made
  - `last_error`: The last exception encountered
  - `last_status_code`: Last HTTP status code received
- **Usage:** Terminal error after retry exhaustion

**`RetryableError`**
- **Description:** Indicates an error that should trigger a retry
- **Attributes:**
  - `message`: Error description
  - `status_code`: HTTP status code if applicable
  - `retry_after`: Delay in seconds before retry (from Retry-After header)
- **Usage:** Raised for transient failures (network, 5xx, 429)

**`NonRetryableError`**
- **Description:** Indicates an error that should NOT trigger a retry
- **Attributes:**
  - `message`: Error description
  - `status_code`: HTTP status code if applicable
- **Usage:** Raised for permanent failures (4xx client errors)

---

### Configuration Validation (`integration-service/src/config/validation.py`)

**`ConfigValidationError`**
- **Description:** Raised when configuration validation fails
- **Attributes:**
  - `message`: Error description
  - `field`: Name of the invalid field (optional)
  - `details`: Additional validation details
- **Method:** `to_dict()` - Converts error to dictionary
- **Common Causes:**
  - Invalid URL format
  - Missing required fields
  - Invalid enum values
  - Regex pattern mismatch
- **Resolution:** Review configuration against schema requirements

---

### Integration Base (`integration-service/src/integrations/base.py`)

**`IntegrationError`**
- **Description:** Base exception for integration errors
- **Attributes:**
  - `message`: Error description
  - `integration_name`: Name of the integration
  - `details`: Additional details dict
- **Usage:** Base class for third-party integration exceptions

**`AuthenticationError`**
- **Inherits:** `IntegrationError`
- **Description:** Raised when authentication to third-party service fails
- **Usage:** OAuth failures, API key rejections

**`ValidationError`**
- **Inherits:** `IntegrationError`
- **Description:** Raised when integration request validation fails

**`DeliveryError`**
- **Inherits:** `IntegrationError`
- **Description:** Raised when event delivery to third-party service fails

**`RateLimitError`**
- **Inherits:** `IntegrationError`
- **Description:** Raised when rate limit is exceeded
- **Attributes:**
  - `retry_after`: Seconds to wait before retry (optional)
- **Resolution:** Implement backoff, respect Retry-After header

**`IntegrationConnectionError`**
- **Inherits:** `IntegrationError`
- **Description:** Raised when connection to external service fails

---

## Enhanced Agent Bus Exceptions

### Location: `src/core/enhanced_agent_bus/exceptions.py`

This module provides the core exception hierarchy for the Enhanced Agent Bus system.

### Base Exception

**`AgentBusError`**
- **Description:** Base exception for all Enhanced Agent Bus errors
- **Attributes:**
  - `message`: Error description
  - `details`: Additional details dict
  - `constitutional_hash`: Constitutional hash for validation (default: `cdd01ef066bc6cf2`)
- **Method:** `to_dict()` - Convert to dictionary for logging/serialization
- **Usage:** All agent bus exceptions inherit from this class

---

### Constitutional Validation Errors

**`ConstitutionalError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for constitutional compliance failures

**`ConstitutionalHashMismatchError`**
- **Inherits:** `ConstitutionalError`
- **Description:** Raised when constitutional hash validation fails
- **Attributes:**
  - `expected_hash`: Expected constitutional hash (sanitized)
  - `actual_hash`: Received constitutional hash (sanitized)
  - `context`: Optional context string
- **Security:** Hash values are sanitized (first 8 chars + "...") in messages
- **Resolution:** Verify constitutional hash matches: `cdd01ef066bc6cf2`

**`ConstitutionalValidationError`**
- **Inherits:** `ConstitutionalError`
- **Description:** Raised when constitutional validation fails
- **Attributes:**
  - `validation_errors`: List of validation error messages
  - `agent_id`: Agent that failed validation (optional)
  - `action_type`: Type of action attempted (optional)
- **Resolution:** Review validation errors and ensure compliance

---

### Message Processing Errors

**`MessageError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for message-related errors

**`MessageValidationError`**
- **Inherits:** `MessageError`
- **Description:** Raised when message validation fails
- **Attributes:**
  - `message_id`: ID of the invalid message
  - `errors`: List of validation errors
  - `warnings`: List of validation warnings

**`MessageDeliveryError`**
- **Inherits:** `MessageError`
- **Description:** Raised when message delivery fails
- **Attributes:**
  - `message_id`: Message ID
  - `target_agent`: Target agent ID
  - `reason`: Delivery failure reason

**`MessageTimeoutError`**
- **Inherits:** `MessageError`
- **Description:** Raised when message processing times out
- **Attributes:**
  - `message_id`: Message ID
  - `timeout_ms`: Timeout duration in milliseconds
  - `operation`: Operation that timed out (optional)

**`MessageRoutingError`**
- **Inherits:** `MessageError`
- **Description:** Raised when message routing fails
- **Attributes:**
  - `message_id`: Message ID
  - `source_agent`: Source agent ID
  - `target_agent`: Target agent ID
  - `reason`: Routing failure reason

**`RateLimitExceeded`**
- **Inherits:** `MessageError`
- **Description:** Raised when an agent exceeds its message rate limit
- **Attributes:**
  - `agent_id`: Agent ID
  - `limit`: Rate limit threshold
  - `window_seconds`: Rate limit window
  - `retry_after_ms`: Milliseconds to wait before retry

---

### Agent Registration Errors

**`AgentError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for agent-related errors

**`AgentNotRegisteredError`**
- **Inherits:** `AgentError`
- **Description:** Raised when operation requires a registered agent that doesn't exist
- **Attributes:**
  - `agent_id`: Agent ID
  - `operation`: Operation that requires the agent (optional)

**`AgentAlreadyRegisteredError`**
- **Inherits:** `AgentError`
- **Description:** Raised when attempting to register an agent that already exists
- **Attributes:**
  - `agent_id`: Agent ID

**`AgentCapabilityError`**
- **Inherits:** `AgentError`
- **Description:** Raised when an agent lacks required capabilities
- **Attributes:**
  - `agent_id`: Agent ID
  - `required_capabilities`: List of required capabilities
  - `available_capabilities`: List of available capabilities
  - `missing_capabilities`: Computed list of missing capabilities

---

### Policy and OPA Errors

**`PolicyError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for policy-related errors

**`PolicyEvaluationError`**
- **Inherits:** `PolicyError`
- **Description:** Raised when policy evaluation fails
- **Attributes:**
  - `policy_path`: OPA policy path
  - `reason`: Failure reason
  - `input_data`: Policy input data (optional)

**`PolicyNotFoundError`**
- **Inherits:** `PolicyError`
- **Description:** Raised when a required policy is not found
- **Attributes:**
  - `policy_path`: Policy path that was not found

**`OPAConnectionError`**
- **Inherits:** `PolicyError`
- **Description:** Raised when connection to OPA server fails
- **Attributes:**
  - `opa_url`: OPA server URL
  - `reason`: Connection failure reason

**`OPANotInitializedError`**
- **Inherits:** `PolicyError`
- **Description:** Raised when OPA client is not properly initialized
- **Attributes:**
  - `operation`: Operation that requires OPA

---

### Governance Errors

**`GovernanceError`**
- **Inherits:** `AgentBusError`
- **Description:** Raised when governance operations fail

**`ImpactAssessmentError`**
- **Inherits:** `GovernanceError`
- **Description:** Raised when impact assessment operations fail
- **Attributes:**
  - `assessment_type`: Type of impact assessment
  - `reason`: Failure reason

---

### Deliberation Layer Errors

**`DeliberationError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for deliberation layer errors

**`DeliberationTimeoutError`**
- **Inherits:** `DeliberationError`
- **Description:** Raised when deliberation process times out
- **Attributes:**
  - `decision_id`: Decision ID
  - `timeout_seconds`: Timeout duration
  - `pending_reviews`: Number of pending reviews
  - `pending_signatures`: Number of pending signatures

**`SignatureCollectionError`**
- **Inherits:** `DeliberationError`
- **Description:** Raised when signature collection fails
- **Attributes:**
  - `decision_id`: Decision ID
  - `required_signers`: List of required signers
  - `collected_signers`: List of collected signers
  - `missing_signers`: Computed list of missing signers
  - `reason`: Failure reason

**`ReviewConsensusError`**
- **Inherits:** `DeliberationError`
- **Description:** Raised when critic review consensus cannot be reached
- **Attributes:**
  - `decision_id`: Decision ID
  - `approval_count`: Number of approvals
  - `rejection_count`: Number of rejections
  - `escalation_count`: Number of escalations

---

### Bus Operation Errors

**`BusOperationError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for bus operation errors

**`BusNotStartedError`**
- **Inherits:** `BusOperationError`
- **Description:** Raised when operation requires a started bus
- **Attributes:**
  - `operation`: Operation attempted

**`BusAlreadyStartedError`**
- **Inherits:** `BusOperationError`
- **Description:** Raised when attempting to start an already running bus

**`HandlerExecutionError`**
- **Inherits:** `BusOperationError`
- **Description:** Raised when a message handler fails during execution
- **Attributes:**
  - `handler_name`: Handler name
  - `message_id`: Message ID
  - `original_error`: The original exception
  - `original_error_type`: Type of original exception

---

### Configuration Errors

**`ConfigurationError`**
- **Inherits:** `AgentBusError`
- **Description:** Raised when configuration is invalid or missing
- **Attributes:**
  - `config_key`: Configuration key
  - `reason`: Error reason

---

### MACI Role Separation Errors (Gödel Bypass Prevention)

**`MACIError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for MACI role separation errors

**`MACIRoleViolationError`**
- **Inherits:** `MACIError`
- **Description:** Raised when an agent attempts an action outside its role
- **Attributes:**
  - `agent_id`: Agent ID
  - `role`: Agent's role
  - `action`: Action attempted
  - `allowed_roles`: List of roles allowed for the action

**`MACISelfValidationError`**
- **Inherits:** `MACIError`
- **Description:** Raised when an agent attempts to validate its own output (Gödel bypass prevention)
- **Attributes:**
  - `agent_id`: Agent ID
  - `action`: Action attempted
  - `output_id`: Output ID (optional)
  - `prevention_type`: Always "godel_bypass"

**`MACICrossRoleValidationError`**
- **Inherits:** `MACIError`
- **Description:** Raised when cross-role validation constraints are violated
- **Attributes:**
  - `validator_agent`: Validating agent ID
  - `validator_role`: Validator's role
  - `target_agent`: Target agent ID
  - `target_role`: Target's role
  - `reason`: Violation reason

**`MACIRoleNotAssignedError`**
- **Inherits:** `MACIError`
- **Description:** Raised when an agent has no MACI role assigned
- **Attributes:**
  - `agent_id`: Agent ID
  - `operation`: Operation attempted

---

### Alignment and Governance Errors

**`AlignmentViolationError`**
- **Inherits:** `AgentBusError`
- **Description:** Raised when an agent message or action violates constitutional alignment
- **Attributes:**
  - `reason`: Violation reason
  - `alignment_score`: Alignment score (optional)
  - `agent_id`: Agent ID (optional)

---

## HITL Approvals Service Exceptions

### OPA Client (`src/core/services/hitl-approvals/app/core/opa_client.py`)

**`OPAClientError`**
- **Description:** Base exception for OPA client errors

**`OPAConnectionError`**
- **Inherits:** `OPAClientError`
- **Description:** Raised when unable to connect to OPA

**`OPANotInitializedError`**
- **Inherits:** `OPAClientError`
- **Description:** Raised when OPA client is not initialized

**`PolicyEvaluationError`**
- **Inherits:** `OPAClientError`
- **Description:** Raised when policy evaluation fails

---

### Kafka Client (`src/core/services/hitl-approvals/app/core/kafka_client.py`)

**`KafkaClientError`**
- **Description:** Base exception for Kafka client errors

**`KafkaConnectionError`**
- **Inherits:** `KafkaClientError`
- **Description:** Raised when Kafka connection fails

**`KafkaNotAvailableError`**
- **Inherits:** `KafkaClientError`
- **Description:** Raised when aiokafka is not installed

**`KafkaPublishError`**
- **Inherits:** `KafkaClientError`
- **Description:** Raised when message publishing fails

---

### Approval Engine (`src/core/services/hitl-approvals/app/core/approval_engine.py`)

**`ApprovalEngineError`**
- **Description:** Base exception for approval engine errors

**`ApprovalNotFoundError`**
- **Inherits:** `ApprovalEngineError`
- **Description:** Raised when approval request is not found

**`ChainNotFoundError`**
- **Inherits:** `ApprovalEngineError`
- **Description:** Raised when approval chain is not found

**`ApprovalStateError`**
- **Inherits:** `ApprovalEngineError`
- **Description:** Raised when approval state transition is invalid

---

### Escalation (`src/core/services/hitl-approvals/app/core/escalation.py`)

**`EscalationTimerError`**
- **Description:** Base exception for escalation timer errors

**`RedisConnectionError`**
- **Inherits:** `EscalationTimerError`
- **Description:** Raised when Redis connection fails for escalation timers

**`TimerNotFoundError`**
- **Inherits:** `EscalationTimerError`
- **Description:** Raised when escalation timer is not found

---

### Audit Ledger (`src/core/services/hitl-approvals/app/audit/ledger.py`)

**`AuditLedgerError`**
- **Description:** Base exception for audit ledger errors

**`IntegrityError`**
- **Inherits:** `AuditLedgerError`
- **Description:** Raised when audit log integrity check fails

**`ImmutabilityError`**
- **Inherits:** `AuditLedgerError`
- **Description:** Raised when immutability constraint is violated

**`RedisNotAvailableError`**
- **Inherits:** `AuditLedgerError`
- **Description:** Raised when Redis is not available for audit logging

---

## Shared Authentication Exceptions

### OIDC Handler (`src/core/shared/auth/oidc_handler.py`)

**`OIDCError`**
- **Description:** Base exception for OIDC-related errors

**`OIDCConfigurationError`**
- **Inherits:** `OIDCError`
- **Description:** Configuration error for OIDC provider
- **Common Causes:**
  - Missing client ID or secret
  - Invalid discovery URL
  - Provider not registered

**`OIDCAuthenticationError`**
- **Inherits:** `OIDCError`
- **Description:** Authentication failed during OIDC flow
- **Common Causes:**
  - Invalid authorization code
  - State parameter mismatch
  - User denied consent

**`OIDCTokenError`**
- **Inherits:** `OIDCError`
- **Description:** Token exchange or validation failed
- **Common Causes:**
  - Invalid token signature
  - Expired token
  - Token issuer mismatch

**`OIDCProviderError`**
- **Inherits:** `OIDCError`
- **Description:** Error communicating with OIDC provider
- **Common Causes:**
  - Network connectivity issues
  - Provider unavailable
  - Invalid provider response

---

### SAML Handler (`src/core/shared/auth/saml_handler.py`)

**`SAMLError`**
- **Description:** Base exception for SAML-related errors

**`SAMLValidationError`**
- **Inherits:** `SAMLError`
- **Description:** SAML assertion validation failed

**`SAMLAuthenticationError`**
- **Inherits:** `SAMLError`
- **Description:** SAML authentication failed

**`SAMLProviderError`**
- **Inherits:** `SAMLError`
- **Description:** Error communicating with SAML IdP

**`SAMLReplayError`**
- **Inherits:** `SAMLError`
- **Description:** SAML replay attack detected

---

### SAML Configuration (`src/core/shared/auth/saml_config.py`)

**`SAMLConfigurationError`**
- **Description:** SAML configuration error

---

### Role Mapper (`src/core/shared/auth/role_mapper.py`)

**`RoleMappingError`**
- **Description:** Base exception for role mapping errors

**`ProviderNotFoundError`**
- **Inherits:** `RoleMappingError`
- **Description:** Identity provider not found for role mapping

---

### Provisioning (`src/core/shared/auth/provisioning.py`)

**`ProvisioningError`**
- **Description:** Base exception for user provisioning errors

**`DomainNotAllowedError`**
- **Inherits:** `ProvisioningError`
- **Description:** User domain not in allowed list

**`ProvisioningDisabledError`**
- **Inherits:** `ProvisioningError`
- **Description:** Auto-provisioning is disabled

---

## Tenant Management Exceptions

### Location: `src/core/services/tenant_management/src/`

**`TenantNotFoundError`**
- **Description:** Raised when tenant is not found

**`DuplicateTenantError`**
- **Description:** Raised when attempting to create duplicate tenant

**`InvalidTenantOperationError`**
- **Description:** Raised when tenant operation is invalid

**`AccessDeniedError`**
- **Description:** Raised when tenant access is denied

**`InvalidComplianceRequirementError`**
- **Description:** Raised when compliance requirement is invalid

**`QuotaExceededError`**
- **Description:** Raised when tenant quota is exceeded

**`TenantIsolationError`**
- **Description:** Raised when tenant isolation is violated

---

### Shared Tenant Integration (`src/core/shared/tenant_integration.py`)

**`TenantError`**
- **Description:** Base exception for tenant errors

**`TenantNotFoundError`**
- **Inherits:** `TenantError`
- **Description:** Tenant not found

**`TenantNotActiveError`**
- **Inherits:** `TenantError`
- **Description:** Tenant is not active

**`QuotaExceededError`**
- **Inherits:** `TenantError`
- **Description:** Tenant quota exceeded

**`AccessDeniedError`**
- **Inherits:** `TenantError`
- **Description:** Tenant access denied

---

### Tenant Context (`src/core/shared/security/tenant_context.py`)

**`TenantValidationError`**
- **Description:** Tenant context validation error

---

## SDK Client Exceptions

### Location: `src/core/sdk/python/acgs2_sdk/exceptions.py`

**`ACGS2Error`**
- **Description:** Base exception for ACGS-2 SDK errors
- **Error Code:** `UNKNOWN_ERROR` (default)
- **Attributes:**
  - `message`: Error message
  - `code`: Error code string
  - `constitutional_hash`: Constitutional hash (default: `cdd01ef066bc6cf2`)
  - `details`: Additional details dict
- **Usage:** Base class for all SDK exceptions

**`ConstitutionalHashMismatchError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `CONSTITUTIONAL_HASH_MISMATCH`
- **Attributes:**
  - `expected`: Expected hash
  - `received`: Received hash

**`AuthenticationError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `AUTHENTICATION_ERROR`
- **Description:** Raised when authentication fails

**`AuthorizationError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `AUTHORIZATION_ERROR`
- **Description:** Raised when authorization is denied

**`ValidationError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `VALIDATION_ERROR`
- **Attributes:**
  - `errors`: Dict of validation errors
- **Description:** Raised when request validation fails

**`NetworkError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `NETWORK_ERROR`
- **Attributes:**
  - `status_code`: HTTP status code (optional)
- **Description:** Raised when a network error occurs

**`RateLimitError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `RATE_LIMIT_ERROR`
- **Attributes:**
  - `retry_after`: Seconds to wait before retry (optional)
- **Description:** Raised when rate limit is exceeded

**`TimeoutError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `TIMEOUT_ERROR`
- **Description:** Raised when a request times out

**`ResourceNotFoundError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `RESOURCE_NOT_FOUND`
- **Attributes:**
  - `resource_type`: Type of resource (optional)
  - `resource_id`: Resource ID (optional)
- **Description:** Raised when a resource is not found

**`ConflictError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `CONFLICT_ERROR`
- **Description:** Raised when a resource conflict occurs

**`ServiceUnavailableError`**
- **Inherits:** `ACGS2Error`
- **Error Code:** `SERVICE_UNAVAILABLE`
- **Description:** Raised when the service is unavailable

---

## Other Service-Specific Exceptions

### Identity Service

#### Azure AD Connector (`src/core/services/identity/connectors/azure_ad_connector.py`)

**`AzureADError`**
- **Description:** Base exception for Azure AD errors

**`AzureADAuthError`**
- **Inherits:** `AzureADError`
- **Description:** Azure AD authentication error

**`AzureADConfigError`**
- **Inherits:** `AzureADError`
- **Description:** Azure AD configuration error

**`AzureADGraphError`**
- **Inherits:** `AzureADError`
- **Description:** Azure AD Graph API error

---

#### Okta Models (`src/core/services/identity/connectors/okta_models.py`)

**`OktaAuthError`**
- **Description:** Okta authentication error

**`OktaConfigError`**
- **Description:** Okta configuration error

**`OktaProvisioningError`**
- **Description:** Okta user provisioning error

**`OktaGroupError`**
- **Description:** Okta group operation error

---

### Audit Service (`src/core/services/audit_service/app/services/email_service.py`)

**`EmailDeliveryError`**
- **Description:** Email delivery failed

**`EmailConfigurationError`**
- **Description:** Email service configuration error

**`EmailRetryExhaustedError`**
- **Description:** Email delivery failed after all retries

---

### Policy Registry (`src/core/services/policy_registry/app/services/secure_fallback_crypto.py`)

**`FallbackCryptoError`**
- **Description:** Base exception for fallback crypto errors

**`KeyDerivationError`**
- **Inherits:** `FallbackCryptoError`
- **Description:** Key derivation failed

**`EncryptionError`**
- **Inherits:** `FallbackCryptoError`
- **Description:** Encryption operation failed

**`DecryptionError`**
- **Inherits:** `FallbackCryptoError`
- **Description:** Decryption operation failed

**`CiphertextFormatError`**
- **Inherits:** `FallbackCryptoError`
- **Description:** Invalid ciphertext format

**`CryptoNotAvailableError`**
- **Inherits:** `FallbackCryptoError`
- **Description:** Cryptography library not available

---

### Search Platform (`src/core/services/integration/search_platform/client.py`)

**`SearchPlatformError`**
- **Description:** Search platform integration error

---

### Enhanced Agent Bus - ACL Adapters (`src/core/enhanced_agent_bus/acl_adapters/base.py`)

**`AdapterTimeoutError`**
- **Description:** ACL adapter operation timed out

**`AdapterCircuitOpenError`**
- **Description:** Circuit breaker is open for adapter

**`RateLimitExceededError`**
- **Description:** Rate limit exceeded for adapter

---

### Enhanced Agent Bus - Observability (`src/core/enhanced_agent_bus/observability/timeout_budget.py`)

**`LayerTimeoutError`**
- **Description:** Timeout budget exceeded for observability layer

---

### Enhanced Agent Bus - ML Governance (`src/core/enhanced_agent_bus/integrations/ml_governance.py`)

**`MLGovernanceError`**
- **Inherits:** `AgentBusError`
- **Description:** Base exception for ML governance errors

**`MLGovernanceConnectionError`**
- **Inherits:** `MLGovernanceError`
- **Description:** ML governance service connection error

**`MLGovernanceTimeoutError`**
- **Inherits:** `MLGovernanceError`
- **Description:** ML governance operation timeout

---

### Enhanced Agent Bus - Recovery Orchestrator (`src/core/enhanced_agent_bus/recovery_orchestrator.py`)

**`RecoveryOrchestratorError`**
- **Description:** Recovery orchestrator error

**`RecoveryConstitutionalError`**
- **Description:** Constitutional error during recovery

**`RecoveryValidationError`**
- **Description:** Validation error during recovery

---

### CLI - OPA Service (`src/core/cli/opa_service.py`)

**`OPAServiceError`**
- **Description:** Base exception for OPA service CLI errors

**`OPAConnectionError`**
- **Inherits:** `OPAServiceError`
- **Description:** OPA service connection error

---

### Breakthrough - Temporal (`src/core/breakthrough/temporal/timeline_engine.py`)

**`TemporalViolationError`**
- **Description:** Temporal constraint violation

**`CausalViolationError`**
- **Description:** Causal constraint violation

---

### Breakthrough - Policy (`src/core/breakthrough/policy/verified_policy_generator.py`)

**`PolicyVerificationError`**
- **Description:** Policy verification failed

---

## Error Code Summary

### Error Code Ranges (Proposed for Phase 2)

Based on this catalog, the following error code ranges are recommended:

- **ACGS-1xxx:** Configuration and validation errors
- **ACGS-2xxx:** Authentication and authorization errors
- **ACGS-3xxx:** Deployment and infrastructure errors
- **ACGS-4xxx:** Service integration and connectivity errors
- **ACGS-5xxx:** Runtime and operational errors
- **ACGS-6xxx:** Constitutional and governance errors
- **ACGS-7xxx:** Message and delivery errors
- **ACGS-8xxx:** Agent and bus operation errors

These will be mapped in detail during Phase 2 (Error Code Taxonomy Design).

---

## Exception Hierarchy Visualization

```
Exception (Python Built-in)
├── IntegrationError (Integration Service)
│   ├── AuthenticationError
│   ├── ValidationError
│   ├── DeliveryError
│   ├── RateLimitError
│   └── IntegrationConnectionError
│
├── WebhookAuthError (Integration Service)
│   ├── InvalidSignatureError
│   ├── InvalidApiKeyError
│   ├── InvalidBearerTokenError
│   ├── TokenExpiredError
│   ├── SignatureTimestampError
│   └── MissingAuthHeaderError
│
├── WebhookDeliveryError (Integration Service)
│   ├── WebhookAuthenticationError
│   ├── WebhookTimeoutError
│   └── WebhookConnectionError
│
├── WebhookRetryError (Integration Service)
│   ├── RetryableError
│   └── NonRetryableError
│
├── ConfigValidationError (Integration Service)
│
├── AgentBusError (Enhanced Agent Bus)
│   ├── ConstitutionalError
│   │   ├── ConstitutionalHashMismatchError
│   │   └── ConstitutionalValidationError
│   │
│   ├── MessageError
│   │   ├── MessageValidationError
│   │   ├── MessageDeliveryError
│   │   ├── MessageTimeoutError
│   │   ├── MessageRoutingError
│   │   └── RateLimitExceeded
│   │
│   ├── AgentError
│   │   ├── AgentNotRegisteredError
│   │   ├── AgentAlreadyRegisteredError
│   │   └── AgentCapabilityError
│   │
│   ├── PolicyError
│   │   ├── PolicyEvaluationError
│   │   ├── PolicyNotFoundError
│   │   ├── OPAConnectionError
│   │   └── OPANotInitializedError
│   │
│   ├── GovernanceError
│   │   └── ImpactAssessmentError
│   │
│   ├── DeliberationError
│   │   ├── DeliberationTimeoutError
│   │   ├── SignatureCollectionError
│   │   └── ReviewConsensusError
│   │
│   ├── BusOperationError
│   │   ├── BusNotStartedError
│   │   ├── BusAlreadyStartedError
│   │   └── HandlerExecutionError
│   │
│   ├── ConfigurationError
│   │
│   ├── MACIError
│   │   ├── MACIRoleViolationError
│   │   ├── MACISelfValidationError
│   │   ├── MACICrossRoleValidationError
│   │   └── MACIRoleNotAssignedError
│   │
│   ├── AlignmentViolationError
│   └── MLGovernanceError
│       ├── MLGovernanceConnectionError
│       └── MLGovernanceTimeoutError
│
├── ACGS2Error (SDK)
│   ├── ConstitutionalHashMismatchError
│   ├── AuthenticationError
│   ├── AuthorizationError
│   ├── ValidationError
│   ├── NetworkError
│   ├── RateLimitError
│   ├── TimeoutError
│   ├── ResourceNotFoundError
│   ├── ConflictError
│   └── ServiceUnavailableError
│
└── [Service-Specific Exceptions]
    ├── OPAClientError
    ├── KafkaClientError
    ├── ApprovalEngineError
    ├── EscalationTimerError
    ├── AuditLedgerError
    ├── OIDCError
    ├── SAMLError
    ├── TenantError
    └── [Others...]
```

---

## Statistics

- **Total Exception Classes:** 137
- **Total Base Exception Classes:** 25
- **Services with Custom Exceptions:** 12
- **Most Common Error Categories:**
  1. Authentication/Authorization (18 exceptions)
  2. Configuration/Validation (12 exceptions)
  3. Connection/Network (15 exceptions)
  4. Message/Delivery (10 exceptions)
  5. Constitutional/Governance (8 exceptions)

---

## Next Steps

This catalog will be used in the following phases:

1. **Phase 2 - Error Code Taxonomy Design:**
   - Assign systematic error codes (ACGS-xxxx) to all exceptions
   - Define severity levels
   - Create error code mapping

2. **Phase 3 - Centralized Error Documentation:**
   - Create ERROR_CODES.md with troubleshooting guidance
   - Document symptoms, causes, and solutions for each error
   - Add diagnostic procedures

3. **Phase 6 - Integration and Cross-Referencing:**
   - Update exception class docstrings with assigned error codes
   - Create searchable error code index
   - Link documentation to code locations

---

## References

- Implementation Plan: `.auto-claude/specs/060-document-error-codes-and-troubleshooting-for-commo/implementation_plan.json`
- TODO Catalog: `src/core/docs/operations/TODO_CATALOG.md`
- Spec: `.auto-claude/specs/060-document-error-codes-and-troubleshooting-for-commo/spec.md`

---

**Constitutional Hash:** cdd01ef066bc6cf2
